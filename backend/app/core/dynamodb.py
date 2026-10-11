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

def _convert_decimals_to_native(obj: Any) -> Any:
    """Recursively converts Decimal objects to float/int for JSON serialization."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    elif isinstance(obj, dict):
        return {k: _convert_decimals_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_decimals_to_native(x) for x in obj]
    return obj

# In-memory ticket cache to avoid repetitive full table scans
_TICKETS_CACHE: Dict[str, Dict[str, Any]] = {}
_LAST_SCAN_TIME: float = 0.0
_SCAN_TTL: float = 20.0  # seconds

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
    # Update cache
    native_item = _convert_decimals_to_native(item)
    _TICKETS_CACHE[ticket_id] = native_item

def get_ticket(ticket_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a ticket record by ID."""
    if ticket_id in _TICKETS_CACHE:
        return _TICKETS_CACHE[ticket_id]
    try:
        response = table.get_item(Key={"PK": f"TICKET#{ticket_id}", "SK": "METADATA"})
        item = response.get("Item")
        if item:
            native = _convert_decimals_to_native(item)
            _TICKETS_CACHE[ticket_id] = native
            return native
        return None
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
    # Update cache
    native_updates = _convert_decimals_to_native(updates)
    if ticket_id in _TICKETS_CACHE:
        _TICKETS_CACHE[ticket_id].update(native_updates)
    else:
        cached = get_ticket(ticket_id)
        if cached:
            cached.update(native_updates)
            _TICKETS_CACHE[ticket_id] = cached

def list_all_tickets(force_refresh: bool = False) -> list[Dict[str, Any]]:
    """Returns all ticket records, sorted by created_at descending."""
    import time
    from boto3.dynamodb.conditions import Attr

    global _LAST_SCAN_TIME, _TICKETS_CACHE

    now = time.time()
    if not force_refresh and _TICKETS_CACHE and (now - _LAST_SCAN_TIME < _SCAN_TTL):
        items = list(_TICKETS_CACHE.values())
        return _sort_tickets(items)

    try:
        res = table.scan(FilterExpression=Attr("PK").begins_with("TICKET#"))
        raw_items = res.get("Items", [])
        for raw in raw_items:
            native = _convert_decimals_to_native(raw)
            tid = native.get("ticket_id") or native.get("PK", "").replace("TICKET#", "")
            if tid:
                native["ticket_id"] = tid
                _TICKETS_CACHE[tid] = native
        _LAST_SCAN_TIME = now
    except Exception as e:
        print(f"[DynamoDB Scan Warning] list_all_tickets: {e}")

    items = list(_TICKETS_CACHE.values())
    return _sort_tickets(items)

def _sort_tickets(tickets: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    def _parse_time(t: Any) -> float:
        try:
            val = float(t.get("created_at") or 0)
            if val > 1e11:  # milliseconds
                val = val / 1000.0
            return val
        except Exception:
            return 0.0
    return sorted(tickets, key=_parse_time, reverse=True)

def find_ticket_by_token(token_or_id: str) -> Optional[Dict[str, Any]]:
    """Searches for a ticket by municipal_ref_id or ticket_id (case-insensitive)."""
    if not token_or_id:
        return None
    q = token_or_id.strip().lower()

    # Direct match on ticket_id
    ticket = get_ticket(token_or_id.strip())
    if ticket:
        return ticket

    # Search in all tickets
    all_tickets = list_all_tickets()
    for t in all_tickets:
        tid = str(t.get("ticket_id") or "").lower()
        ref = str(t.get("municipal_ref_id") or "").lower()
        field_ref = str(t.get("filed_fields", {}).get("reference_token") or "").lower()

        if q in (tid, ref, field_ref):
            return t
        # Match if q is subpart of token, e.g. '89102' in 'PMC-SW-2026-89102'
        if q and len(q) >= 4 and (q in ref or q in field_ref):
            return t

    return None

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