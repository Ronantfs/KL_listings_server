import json
import os
import re
from datetime import date, timedelta

from shared.http_utils import build_response
from shared.config import CINEMAS, ROUTE_TYPES
from routes.get_listings import get_listings
from routes.get_image_listings import get_image_listings
from routes.get_pan_cinema_listings import handle_pan_cinema_listings_route


def _as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


# ===== MAIN HANDLER =====
def lambda_handler(event, context):
    print("Lambda triggered with event:", json.dumps(event))

    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
        or ""
    ).upper()

    qs_single = event.get("queryStringParameters") or {}
    qs_multi = event.get("multiValueQueryStringParameters") or {}

    if method == "OPTIONS":
        print("OPTIONS request received")
        return build_response(200, {"message": "CORS preflight OK"})

    if method != "GET":
        print("Unsupported HTTP method:", method)
        return build_response(405, {"error": f"Unsupported method: {method}"})

    route_type = (qs_single.get("route_type") or "").strip()
    if route_type not in ROUTE_TYPES:
        return build_response(400, {"error": "Invalid 'route_type' parameter"})

    if route_type == "pan_cinema_listings":
        return handle_pan_cinema_listings_route(qs_single)

    raw_cinemas = qs_multi.get("cinemas", None)
    if raw_cinemas is None:
        raw_cinemas = qs_single.get("cinemas")
    cinemas = _as_list(raw_cinemas)

    raw_dates = qs_multi.get("dates", None)
    if raw_dates is None:
        raw_dates = qs_single.get("dates")
    dates = _as_list(raw_dates)

    if not cinemas or any(c not in CINEMAS for c in cinemas):
        print("Invalid or missing cinemas param:", cinemas)
        return build_response(400, {"error": "Missing or invalid 'cinemas' parameter"})

    if not dates or not all(
        isinstance(d, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", d) for d in dates
    ):
        print("Invalid or missing dates param:", dates)
        return build_response(400, {"error": "Missing or invalid 'dates' parameter"})

    if route_type == "listings":
        print("Processing standard listings for cinemas:", cinemas)
        server_response_data = get_listings(cinemas, dates)
    else:
        print("Processing visual listings for cinemas:", cinemas)
        server_response_data = get_image_listings(cinemas, dates)

    return build_response(200, server_response_data)


# ===== LOCAL TESTING =====
if __name__ == "__main__":

    def _resolve_date(d):
        try:
            return (date.today() + timedelta(days=int(d))).isoformat()
        except ValueError:
            return d  # already an ISO date string

    def _q_params_to_test_event(route_type, cinemas=None, dates=None, film_id=None):
        qs = {"route_type": route_type}
        if cinemas:
            qs["cinemas"] = cinemas
        if dates:
            qs["dates"] = [_resolve_date(d) for d in dates]
        if film_id:
            qs["id"] = film_id
        return {"httpMethod": "GET", "queryStringParameters": qs}

    route_type = os.getenv("ROUTE_TYPE", "listings")
    cinemas_raw = _as_list(os.getenv("CINEMAS", "all"))
    cinemas = CINEMAS if cinemas_raw == ["all"] else cinemas_raw
    dates = _as_list(os.getenv("DATES") or "0,1")
    film_id = os.getenv("FILM_ID") or None

    event = _q_params_to_test_event(route_type, cinemas or None, dates or None, film_id=film_id)
    print(f"\n=== Testing route: {route_type} ===")
    response = lambda_handler(event, context=None)
    print(json.dumps(response, indent=2))
