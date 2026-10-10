import os
import boto3
from typing import Optional, Dict, Any
from decimal import Decimal
from botocore.exceptions import ClientError
from app.config import settings

dynamodb : Any = boto3.resource(
    "dynamodb",
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)
table = dynamodb.Table(settings.DYNAMODB_TABLE)

def _convert_floats_to_decimals(obj: Any) -> Any:
    """Recursively converts Python float objects to Decimal for DynamoDB serialization."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: _convert_floats_to_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_floats_to_decimals(x) for x in obj]
    return obj

# ---------------------------------------------------------------------------
# Ticket Operations
# ---------------------------------------------------------------------------

def save_ticket(ticket_id: str, data: Dict[str, Any]) -> None:
    """Creates a new ticket record with geospatial GSI1 keys."""
    clean_data = _convert_floats_to_decimals(data)
    item = {
        "PK": f"TICKET#{ticket_id}",
        "SK": "METADATA",
        "ticket_id": ticket_id,
        **clean_data,
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
    clean_updates = _convert_floats_to_decimals(updates)
    expr_parts = []
    expr_names = {}
    expr_values = {}

    for idx, (k, v) in enumerate(clean_updates.items()):
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
    clean_data = _convert_floats_to_decimals(authority_data)
    item = {
        "PK": f"AUTHORITY#{city_slug.lower()}",
        "SK": "METADATA",
        **clean_data,
    }
    table.put_item(Item=item)