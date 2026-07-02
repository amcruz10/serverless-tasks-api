# Serverless Tasks API

A serverless REST API for managing tasks, built on AWS Lambda, API Gateway, and DynamoDB, fully provisioned with Terraform. Deployment is automated through a GitHub Actions pipeline using OIDC federation for AWS authentication.

## Architecture

```
Client
  │  HTTPS
  ▼
API Gateway (HTTP API)
  │  AWS_PROXY integration
  ▼
Lambda (Python 3.12)
  │  boto3
  ▼
DynamoDB (pay-per-request, encrypted, point-in-time recovery enabled)
```

- **API Gateway (HTTP API)** — routes requests to a single Lambda function based on method and path.
- **Lambda** — one function handling all routes (`GET /tasks`, `GET /tasks/{id}`, `POST /tasks`, `PUT /tasks/{id}`, `DELETE /tasks/{id}`), dispatched by `routeKey`.
- **DynamoDB** — on-demand billing, server-side encryption, point-in-time recovery.
- **IAM** — the Lambda execution role is scoped to only its own log group and its one DynamoDB table.

## Prerequisites

- Terraform >= 1.6
- AWS CLI
- An AWS account with permissions to create the resources above (see **IAM and Access** below for how this project scopes that down)

## Project structure

```
.
├── main.tf                        # provider + backend config
├── variables.tf
├── outputs.tf
├── dynamodb.tf
├── iam.tf
├── lambda.tf
├── api_gateway.tf
├── lambda/
│   └── handler.py                 # CRUD handler
└── .github/workflows/terraform.yml  # CI/CD pipeline
```

## State management

Terraform state is stored remotely in S3 with DynamoDB-backed locking, rather than locally, so that both local development and the CI/CD pipeline read and write the same state:

```hcl
backend "s3" {
  bucket         = "tfstate-serverless-tasks-api-<account-id>"
  key            = "serverless-tasks-api/terraform.tfstate"
  region         = "us-east-1"
  dynamodb_table = "terraform-locks"
  encrypt        = true
}
```

The S3 bucket and DynamoDB lock table are created once, outside of Terraform, and are not managed by this configuration.

## Deploy

```bash
terraform init
terraform plan
terraform apply
```

Get the API endpoint:

```bash
terraform output -raw api_endpoint
```

## Usage

```bash
API=$(terraform output -raw api_endpoint)

# Create a task
curl -X POST "$API/tasks" -H "Content-Type: application/json" -d '{"title": "example task"}'

# List tasks
curl "$API/tasks"

# Get one task
curl "$API/tasks/<id>"

# Update a task
curl -X PUT "$API/tasks/<id>" -H "Content-Type: application/json" -d '{"title": "example task", "done": true}'

# Delete a task
curl -X DELETE "$API/tasks/<id>"
```

## Teardown

```bash
terraform destroy
```

This removes the DynamoDB table, both CloudWatch log groups, the Lambda function, the IAM role, and the API Gateway API. It does not touch the S3 state bucket or the DynamoDB lock table, since those aren't managed by this configuration.

## IAM and access

This project does not run under an AWS account's admin credentials. Two scoped identities are used instead:

- **Local development**: a dedicated IAM user (`tasks-api-terraform`) with a custom least-privilege policy attached, used via a named AWS CLI profile rather than default credentials.
- **CI/CD**: an IAM role assumed via GitHub Actions OIDC federation, using the same least-privilege policy. No long-lived AWS access keys are stored in GitHub.

The policy (`terraform-deploy-policy.json`) grants only the specific actions this project's resources require, scoped by resource ARN where AWS permission models allow it (Lambda functions, the DynamoDB table, the IAM role, CloudWatch log groups, the S3 state path). A small number of actions — API Gateway management calls and CloudWatch Logs delivery configuration — cannot be scoped below the account/region level, since AWS does not support resource-level permissions for those specific actions.

### One-time setup

**OIDC provider:**

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

**IAM role for GitHub Actions**, trusted only for this specific repo:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<account-id>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:<github-username>/serverless-tasks-api:*"
        }
      }
    }
  ]
}
```

Attach `terraform-deploy-policy.json` to that role, then add its ARN as a GitHub repository secret named `AWS_ROLE_ARN` (Settings → Secrets and variables → Actions).

## CI/CD

`.github/workflows/terraform.yml` runs on every pull request and push to `main`:

- **Pull requests**: `terraform fmt -check`, `terraform validate`, `tflint`, and `terraform plan`.
- **Push to `main`**: `terraform apply`, using the OIDC-federated role described above.

## Possible extensions

- Authentication (API Gateway JWT authorizer via Cognito, or an API key)
- Request validation via JSON schema
- WAF in front of API Gateway
- Splitting the single Lambda handler into per-route functions for finer-grained IAM scoping