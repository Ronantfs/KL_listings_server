import json
import os
import re
from datetime import date, timedelta
from dotenv import load_dotenv
from aws import set_s3_client, _generate_presigned_url
from http_utils import build_response
import logging

# Basic logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Load environment variables from .env (for local dev)
load_dotenv()

# ===== CONFIGURATION =====
IMAGE_BUCKET = os.getenv("IMAGE_BUCKET", "kinoma-assets")
IMAGE_PREFIX = os.getenv("IMAGE_PREFIX", "cinema_listings_images")
LISTING_BUCKET = os.getenv("LISTING_BUCKET", "filmfynder")
LISTING_PREFIX = os.getenv("LISTING_PREFIX", "london/cinema-listings")
AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")
# Cinemas in S3
CINEMAS = [
    "barbican",
    "bfi_southbank",
    "castle",
    "close_up",
    "garden_cinema",
    "ica",
    "nickel",
    "prince_charles",
    "regent_street",
    "rio",
    "the_cinema_museum",
]

# types of data this server gets:
ROUTE_TYPES = ["listings", "visual_listings"]

s3 = set_s3_client(AWS_REGION)


# ===== HELPERS =====
def get_cinemas_image_folder_path(cinema: str) -> str:
    """
    Construct S3 folder path for a given cinemas listings images, selected as good.
    Folder contains image files only
    """
    cinemas_image_folder = f"{IMAGE_PREFIX}/{cinema}/good/"
    return cinemas_image_folder


def get_cinemas_active_listings_path(cinema: str) -> str:
    """
    Construct S3 folder path for a given cinemas active listings JSON.
    """
    cinemas_active_listings_json = f"{LISTING_PREFIX}/{cinema}/active_listings.json"
    return cinemas_active_listings_json


def _as_list(value):
    """
    Normalize query param into a list.
    - If already a list, return as-is.
    - If a non-empty string, split by comma.
    - Else return [].
    """
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


# ===== HANDLER UTILS =====
def _get_cinemas_raw_listings(cinemas: list[str]) -> dict:
    """
    Fetch all active listings JSONs from S3 for the given cinemas.

    Returns:
        dict: { cinema_name: <parsed active_listings.json> }
    """
    cinema_listings = {}

    for cinema in cinemas:
        cinema_json_key = get_cinemas_active_listings_path(cinema)
        try:
            response = s3.get_object(Bucket=LISTING_BUCKET, Key=cinema_json_key)
            listings_data = json.loads(response["Body"].read().decode("utf-8"))
            cinema_listings[cinema] = listings_data
        except s3.exceptions.NoSuchKey:
            cinema_listings[cinema] = {
                "error": f"No active listings found for {cinema}"
            }  # missing JSON
        except Exception as e:
            cinema_listings[cinema] = {
                "error": f"Failed to load listings for {cinema}: {str(e)}"
            }  # general error

    return cinema_listings


def _get_cinemas_good_images(cinemas: list[str], expires_in: int = 300) -> dict:
    """
    Fetch all 'good' images for each cinema from S3, returning both
    filenames (for matching) and presigned URLs (for frontend use).
    Handles pagination for >1000 objects per cinema.
    """
    cinemas_good_images = {}

    for cinema in cinemas:
        images_folder = get_cinemas_image_folder_path(cinema)
        all_images = []
        continuation_token = None

        try:
            while True:
                params = {
                    "Bucket": IMAGE_BUCKET,
                    "Prefix": images_folder,
                    "MaxKeys": 1000,
                }
                if continuation_token:
                    params["ContinuationToken"] = continuation_token

                response = s3.list_objects_v2(**params)
                contents = response.get("Contents", [])

                for obj in contents:
                    key = obj["Key"]
                    if key.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                        filename = os.path.basename(key)
                        presigned_url = _generate_presigned_url(
                            s3, IMAGE_BUCKET, key, expires_in=expires_in
                        )
                        all_images.append(
                            {
                                "name": filename,  # base name for matching
                                "url": presigned_url,  # for frontend download
                            }
                        )

                if response.get("IsTruncated"):
                    continuation_token = response.get("NextContinuationToken")
                else:
                    break

            cinemas_good_images[cinema] = all_images

        except Exception as e:
            cinemas_good_images[cinema] = {
                "error": f"Failed to fetch good images for {cinema}: {str(e)}"
            }

    return cinemas_good_images


def _normalize_name(name: str) -> str:
    """
    Normalize listing and image names for exact matching.
    Lowercase, strip, replace non-alphanumeric characters with underscores.
    """
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def _filter_cinema_listings_by_images(
    cinema_listings: dict, good_images: list[str]
) -> dict:
    """
    Filter a single cinema's listings to include only those
    whose normalized title exactly matches a 'good' image filename (without extension).
    """
    norm_image_basenames = {
        _normalize_name(os.path.splitext(img)[0])
        for img in good_images
        if isinstance(img, str)
    }

    filtered = {}
    for title, listing_data in cinema_listings.items():
        norm_title = _normalize_name(title)
        if norm_title in norm_image_basenames:
            filtered[title] = listing_data

    return filtered


def _match_and_attach_images_to_listings(
    listings_by_cinema: dict, images_by_cinema: dict, cinemas: list[str]
) -> dict:
    """
    Filter and enrich listings for each cinema by attaching matching presigned image URLs.
    """
    listings_with_good_images = {}

    for cinema in cinemas:
        raw_cinema_listings = listings_by_cinema.get(cinema, {})
        images_info = images_by_cinema.get(cinema, [])

        image_map = {
            os.path.splitext(img["name"])[0].lower(): img["url"]
            for img in images_info
            if isinstance(img, dict) and "name" in img and "url" in img
        }

        filtered_listings = {}
        for title, listing_data in raw_cinema_listings.items():
            norm_title = _normalize_name(title)
            if norm_title in image_map:
                listing_data["image_url"] = image_map[norm_title]
                filtered_listings[title] = listing_data

        listings_with_good_images[cinema] = filtered_listings

    return listings_with_good_images


def _redact_listings_fields(listings_with_good_images: dict) -> dict:
    """
    Remove unwanted fields and drop cinemas that have no listings remaining.
    """
    FIELDS_TO_REMOVE = {
        "image_to_download",
        "isImageGood",
        "s3ImageURL",
    }

    redacted = {}

    for cinema, listings in listings_with_good_images.items():
        cleaned_listings = {}
        for title, data in listings.items():
            if not isinstance(data, dict):
                continue
            cleaned = {k: v for k, v in data.items() if k not in FIELDS_TO_REMOVE}
            if cleaned:
                cleaned_listings[title] = cleaned
        if cleaned_listings:
            redacted[cinema] = cleaned_listings

    return redacted


def _filter_listings_by_dates(cinema_listings: dict, dates: list[str]) -> dict:
    """
    Filter listings for a given cinema to only include those
    where at least one 'when' entry matches a date in `dates`.
    """
    if not dates:
        return cinema_listings

    filtered = {}
    for title, listing_data in cinema_listings.items():
        when_entries = listing_data.get("when", [])
        if not isinstance(when_entries, list):
            continue

        filtered_when = [w for w in when_entries if w.get("date") in dates]
        if filtered_when:
            filtered_listing = listing_data.copy()
            filtered_listing["when"] = filtered_when
            filtered[title] = filtered_listing

    return filtered


def _filter_cinemas_listings_by_dates(
    listings_by_cinema: dict, dates: list[str]
) -> dict:
    """
    Apply _filter_listings_by_dates across all cinemas,
    remove cinemas that end up empty.
    """
    filtered_all = {}
    for cinema, listings in listings_by_cinema.items():
        if not isinstance(listings, dict):
            continue
        filtered_listings = _filter_listings_by_dates(listings, dates)
        if filtered_listings:
            filtered_all[cinema] = filtered_listings
    return filtered_all


# ===== ROUTE HANDLERS =====
def get_listings(cinemas: list[str], dates: list[str]) -> dict:
    listings_by_cinema = _get_cinemas_raw_listings(cinemas)
    logger.info("Listings by cinema: %s", listings_by_cinema)
    filtered_by_dates = _filter_cinemas_listings_by_dates(listings_by_cinema, dates)
    logger.info("Filtered listings by cinema: %s", filtered_by_dates)
    redacted_filtered = _redact_listings_fields(filtered_by_dates)
    logger.info("Redacted filtered listings: %s", redacted_filtered)
    return redacted_filtered


def get_image_listings(cinemas: list[str], dates: list[str]) -> dict:
    listings_by_cinema = _get_cinemas_raw_listings(cinemas)
    logger.info("Listings by cinema: %s", listings_by_cinema)
    listings_by_cinema_date_filtered = _filter_cinemas_listings_by_dates(
        listings_by_cinema, dates
    )
    logger.info("Filtered listings by cinema: %s", listings_by_cinema_date_filtered)
    images_by_cinema = _get_cinemas_good_images(cinemas)
    logger.info("Images by cinema: %s", images_by_cinema)
    listings_with_good_images = _match_and_attach_images_to_listings(
        listings_by_cinema_date_filtered, images_by_cinema, cinemas
    )
    logger.info("Listings with good images: %s", listings_with_good_images)
    redacted_listings_with_good_images = _redact_listings_fields(
        listings_with_good_images
    )
    logger.info(
        "Redacted listings with good images: %s", redacted_listings_with_good_images
    )
    return redacted_listings_with_good_images


# ===== MAIN HANDLER =====
def lambda_handler(event, context):
    logger.info("Lambda triggered with event: %s", json.dumps(event))

    # --- Detect method across HTTP API v2 / REST API v1 / tests ---
    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
        or ""
    ).upper()

    qs_single = event.get("queryStringParameters") or {}
    qs_multi = event.get("multiValueQueryStringParameters") or {}

    if method == "OPTIONS":
        logger.info("OPTIONS request received")
        return build_response(200, {"message": "CORS preflight OK"})

    if method != "GET":
        logger.warning("Unsupported HTTP method: %s", method)
        return build_response(405, {"error": f"Unsupported method: {method}"})

    route_type = (qs_single.get("route_type") or "").strip()
    if route_type not in ROUTE_TYPES:
        return build_response(400, {"error": "Invalid 'route_type' parameter"})

    # Handle both repeated keys and CSV
    raw_cinemas = qs_multi.get("cinemas", None)
    if raw_cinemas is None:
        raw_cinemas = qs_single.get("cinemas")
    cinemas = _as_list(raw_cinemas)

    raw_dates = qs_multi.get("dates", None)
    if raw_dates is None:
        raw_dates = qs_single.get("dates")
    dates = _as_list(raw_dates)

    # Validate params
    if not cinemas or any(c not in CINEMAS for c in cinemas):
        logger.warning("Invalid or missing cinemas param: %s", cinemas)
        return build_response(400, {"error": "Missing or invalid 'cinemas' parameter"})

    if not dates or not all(
        isinstance(d, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", d) for d in dates
    ):
        logger.warning("Invalid or missing dates param: %s", dates)
        return build_response(400, {"error": "Missing or invalid 'dates' parameter"})

    # Route handling
    if route_type == "listings":
        logger.info("Processing standard listings for cinemas: %s", cinemas)
        server_response_data = get_listings(cinemas, dates)
    else:
        logger.info("Processing visual listings for cinemas: %s", cinemas)
        server_response_data = get_image_listings(cinemas, dates)

    return build_response(200, server_response_data)


# ===== LOCAL TESTING =====
if __name__ == "__main__":

    today = date.today()
    tomorrow = today + timedelta(days=1)
    next_30_dates = [(today + timedelta(days=i)).isoformat() for i in range(1, 31)]

    test_event_listings = {
        "httpMethod": "GET",
        "queryStringParameters": {
            "route_type": "listings",
            "cinemas": [
                "close_up",
                "ica",
                "nickel",
                "prince_charles",
                "bfi_southbank",
            ],
            "dates": [
                today.isoformat(),
                tomorrow.isoformat(),
            ],
        },
    }

    test_event_visual_listings = {
        "httpMethod": "GET",
        "queryStringParameters": {
            "route_type": "visual_listings",
            "cinemas": [
                "bfi_southbank",
                "prince_charles",
                "rio",
                "ica",
            ],
            "dates": [
                today.isoformat(),
                tomorrow.isoformat(),
            ],
        },
    }

    response = lambda_handler(test_event_listings, context=None)
    print("\n=== Local Test Result ===")
    print(json.dumps(response, indent=2))
