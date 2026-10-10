import os
import boto3
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError
from app.config import settings

dynamodb : Any = boto3.resource(
    "dynamodb",
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)
table = dynamodb.Table(settings.DYNAMODB_TABLE)

# ---------------------------------------------------------------------------
# Ticket Operations
# ---------------------------------------------------------------------------

def save_ticket(ticket_id: str, data: Dict[str, Any]) -> None:
    """Creates a new ticket record with geospatial GSI1 keys."""
    item = {
        "PK": f"TICKET#{ticket_id}",
        "SK": "METADATA",
        "ticket_id": ticket_id,
        **data,
    }
    table.put_item(Item=item)

def get_ticket(ticket_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a ticket record by ID."""
    try:
        response = table.get_item(Key={"PK": f"TICKET#{ticket_id}", "SK": "METADATA"})
        return response.get("Item")
    except ClientError as e:
        print(f"[DynamoDB Error] get_ticket: {e}")
        return None

def update_ticket_status(ticket_id: str, updates: Dict[str, Any]) -> None:
    """Updates status, OTP attributes, or audit results for a ticket."""
    expr_parts = []
    expr_names = {}
    expr_values = {}

    for idx, (k, v) in enumerate(updates.items()):
        alias_k = f"#f{idx}"
        alias_v = f":v{idx}"
        expr_parts.append(f"{alias_k} = {alias_v}")
        expr_names[alias_k] = k
        expr_values[alias_v] = v

    update_expression = "SET " + ", ".join(expr_parts)

    table.update_item(
        Key={"PK": f"TICKET#{ticket_id}", "SK": "METADATA"},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )

# ---------------------------------------------------------------------------
# Authority Discovery Cache
# ---------------------------------------------------------------------------

def get_authority_cache(city_slug: str) -> Optional[Dict[str, Any]]:
    """Checks DynamoDB for pre-discovered municipal authority data."""
    try:
        res = table.get_item(Key={"PK": f"AUTHORITY#{city_slug.lower()}", "SK": "METADATA"})
        return res.get("Item")
    except ClientError:
        return None

def save_authority_cache(city_slug: str, authority_data: Dict[str, Any]) -> None:
    """Saves discovered authority details to DynamoDB cache."""
    item = {
        "PK": f"AUTHORITY#{city_slug.lower()}",
        "SK": "METADATA",
        **authority_data,
    }
    table.put_item(Item=item)