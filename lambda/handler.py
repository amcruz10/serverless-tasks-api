import json
import os
import uuid
import boto3
import base64
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def handler(event, context):
    route_key = event.get("routeKey", "")
    path_params = event.get("pathParameters") or {}

    raw_body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw_body = base64.b64decode(raw_body).decode("utf-8")

    try:
        if route_key == "GET /tasks":
            items = table.scan().get("Items", [])
            return _response(200, items)

        if route_key == "GET /tasks/{id}":
            item = table.get_item(Key={"id": path_params["id"]}).get("Item")
            if not item:
                return _response(404, {"message": "task not found"})
            return _response(200, item)

        if route_key == "POST /tasks":
            body = json.loads(raw_body)
            if "title" not in body:
                return _response(400, {"message": "'title' is required"})
            task = {
                "id": str(uuid.uuid4()),
                "title": body["title"],
                "done": body.get("done", False),
            }
            table.put_item(Item=task)
            return _response(201, task)

        if route_key == "PUT /tasks/{id}":
            body = json.loads(raw_body)
            table.update_item(
                Key={"id": path_params["id"]},
                UpdateExpression="SET title = :t, done = :d",
                ExpressionAttributeValues={
                    ":t": body.get("title", ""),
                    ":d": body.get("done", False),
                },
            )
            return _response(200, {"message": "updated"})

        if route_key == "DELETE /tasks/{id}":
            table.delete_item(Key={"id": path_params["id"]})
            return _response(204, {})

        return _response(404, {"message": "route not found"})

    except ClientError as e:
        # Don't leak internal error details back to the caller
        print(f"DynamoDB error: {e}")
        return _response(500, {"message": "internal server error"})
