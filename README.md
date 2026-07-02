# Serverless Tasks API (Terraform + AWS Lambda + API Gateway + DynamoDB)

A small serverless REST API, fully provisioned with Terraform. Built as a
stand-in for the AWS Summit "Building Serverless Applications with Terraform"
workshop, covering the same core skill: defining serverless infrastructure
as code end to end.

## Architecture

```
Client
  │  HTTPS
  ▼
API Gateway (HTTP API)
  │  AWS_PROXY integration
  ▼
Lambda (Python 3.12)
  │  boto3, least-privilege IAM role
  ▼
DynamoDB (pay-per-request, encrypted, PITR enabled)
```

- **API Gateway (HTTP API, not REST API)** — cheaper and simpler than the
  older REST API type, sufficient for most serverless backends.
- **Lambda** — single function, routed by `routeKey` (`GET /tasks`,
  `POST /tasks`, etc.) rather than one function per route. Fine at this
  scale; splitting into per-route functions is a reasonable next step if
  you want to demonstrate finer-grained IAM scoping per operation.
- **DynamoDB** — on-demand billing (no capacity planning), server-side
  encryption on, point-in-time recovery on.
- **IAM** — the Lambda execution role can only write to its own log group
  and touch this one DynamoDB table. No `*` resources anywhere.

## Prerequisites

- Terraform >= 1.6
- AWS CLI configured with credentials that can create IAM roles, Lambda
  functions, API Gateway APIs, and DynamoDB tables
- Python 3.12 (matches the Lambda runtime, not strictly required locally
  since Terraform packages the zip for you)

## Deploy

```bash
terraform init
terraform plan
terraform apply
```

Grab the API endpoint from the output:

```bash
terraform output api_endpoint
```

## Test it

```bash
API=$(terraform output -raw api_endpoint)

# Create a task
curl -X POST "$API/tasks" -d '{"title": "finish DevOps Pro cert"}'

# List tasks
curl "$API/tasks"

# Get one task (replace <id> with an id from the list above)
curl "$API/tasks/<id>"

# Update it
curl -X PUT "$API/tasks/<id>" -d '{"title": "finish DevOps Pro cert", "done": true}'

# Delete it
curl -X DELETE "$API/tasks/<id>"
```

## Teardown

```bash
terraform destroy
```

Confirm in the console afterward that the DynamoDB table, both CloudWatch
log groups, the Lambda function, and the API Gateway API are gone. DynamoDB
and CloudWatch Logs are the two resources most likely to be left behind
silently, so it's worth the extra look.

## Where to take this next (portfolio-building order)

1. **Add authentication** — API Gateway JWT authorizer backed by Cognito,
   or a simple API key to start. Right now this API is wide open.
2. **Add input validation** — a JSON schema on the API Gateway route or
   stricter checks in the handler.
3. **Add a CI/CD pipeline** — GitHub Actions workflow that runs
   `terraform fmt -check`, `terraform validate`, `tflint`, and
   `terraform plan` on PRs, then `terraform apply` on merge to main. This
   is the piece that turns this from "a Terraform config" into "a
   DevSecOps pipeline," which is the framing you want for interviews.
4. **Add a WAF** in front of API Gateway and talk through why (rate
   limiting, common exploit protection) — good Cloud Security Engineer
   talking point.
5. **Move state to S3 + DynamoDB locking** — the commented-out backend
   block in `main.tf` is ready to uncomment once you've created the
   bucket and lock table.
6. **Write a one-page architecture doc** (or reuse this README) for your
   portfolio repo so a reviewer doesn't have to read Terraform to
   understand what it does.

## CI/CD (GitHub Actions)

`.github/workflows/terraform.yml` runs on every PR and push to `main`:

- **On PRs**: `terraform fmt -check`, `terraform validate`, `tflint`, and
  `terraform plan` — so you (or a reviewer) see the plan before merging.
- **On merge to `main`**: `terraform apply` runs automatically.

This uses **OIDC federation** instead of long-lived AWS access keys stored
in GitHub — the safer, more "I know what I'm doing" pattern for a
portfolio project. One-time setup before this workflow will run:

1. In AWS, create an IAM OIDC identity provider for
   `token.actions.githubusercontent.com` (Console: IAM → Identity providers
   → Add provider → OpenID Connect).
2. Create an IAM role that trusts that provider, scoped to your specific
   GitHub repo (the trust policy condition should restrict
   `token.actions.githubusercontent.com:sub` to
   `repo:YOUR_GITHUB_USERNAME/serverless-tasks-api:*`). Attach a policy
   granting the permissions Terraform needs (Lambda, API Gateway,
   DynamoDB, IAM, CloudWatch Logs — broad while you're building, then
   narrow it down as a follow-up hardening exercise).
3. In your GitHub repo: Settings → Secrets and variables → Actions → New
   repository secret → name it `AWS_ROLE_ARN`, value is the ARN of the
   role from step 2.
4. If you want the `apply` job to require manual approval before it runs,
   go to Settings → Environments → New environment → name it `production`
   → add a required reviewer.

The full walkthrough for all of this is in the companion PDF guide.


#I started with broad IAM permissions to get the project working, then iteratively scoped the policy down to only the specific actions and resources this project touches, verifying against real deploy errors rather than guessing.