import json
import os
import re
from datetime import date, timedelta
from dotenv import load_dotenv
from modules.aws import set_s3_client, _generate_presigned_url
from modules.http import build_response


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

    Returns:
        dict: {
            cinema_name: [
                {
                    "name": "<filename>",  # used for filtering
                    "url": "<presigned_s3_url>"  # to attach later to listing
                },
                ...
            ]
        }
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
                    "MaxKeys": 1000,  # pagination limit
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

                # Continue if there are more keys
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

    Args:
        cinema_listings (dict): { listing_name: {...} }
        good_images (list[str]): list of image filenames (with extensions)

    Returns:
        dict: filtered { listing_name: {...} } with exact matches only
    """
    # Build a set of normalized image basenames (without extensions)
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

    Args:
        listings_by_cinema (dict): raw listings from _get_cinemas_raw_listings()
        images_by_cinema (dict): image data from _get_cinemas_good_images()
        cinemas (list[str]): list of cinema names

    Returns:
        dict: { cinema_name: { "listings": { <title>: <listing_with_image_url> } } }
    """
    listings_with_good_images = {}

    for cinema in cinemas:
        raw_cinema_listings = listings_by_cinema.get(cinema, {})
        images_info = images_by_cinema.get(cinema, [])

        # Create lookup: normalized image basename → presigned URL
        image_map = {
            os.path.splitext(img["name"])[0].lower(): img["url"]
            for img in images_info
            if isinstance(img, dict) and "name" in img and "url" in img
        }

        filtered_listings = {}
        for title, listing_data in raw_cinema_listings.items():
            norm_title = _normalize_name(title)
            if norm_title in image_map:
                # Add presigned URL to listing
                listing_data["image_url"] = image_map[norm_title]
                filtered_listings[title] = listing_data

        listings_with_good_images[cinema] = filtered_listings

    return listings_with_good_images


def _redact_listings_fields(listings_with_good_images: dict) -> dict:
    """
    Remove unwanted fields (e.g., 'image_to_download') from listings,
    and drop cinemas that have no listings remaining.

    Args:
        listings_with_good_images (dict):
            { cinema_name: { <title>: {listing_data} } }

    Returns:
        dict: cleaned structure with empty cinemas removed
               (format: { cinema_name: {"listings": {...}} })
    """
    FIELDS_TO_REMOVE = {
        "image_to_download",
        "isImageGood",
        "s3ImageURL",
    }  # extendable set

    redacted = {}

    for cinema, listings in listings_with_good_images.items():
        cleaned_listings = {}
        for title, data in listings.items():
            # skip if listing data isn't a dict
            if not isinstance(data, dict):
                continue

            # remove unwanted fields
            cleaned = {k: v for k, v in data.items() if k not in FIELDS_TO_REMOVE}

            # only keep listings that have content left
            if cleaned:
                cleaned_listings[title] = cleaned

        # only include cinema if it has any listings left
        if cleaned_listings:
            redacted[cinema] = {"listings": cleaned_listings}

    return redacted


########## get listing handlers:
def _filter_listings_by_dates(cinema_listings: dict, dates: list[str]) -> dict:
    """
    Filter listings for a given cinema to only include those
    where at least one 'when' entry matches a date in `dates`.

    Args:
        cinema_listings (dict): { listing_name: {..., 'when': [ {...}, ... ] } }
        dates (list[str]): list of date strings (format: YYYY-MM-DD)

    Returns:
        dict: filtered { listing_name: {...} } containing only listings
              with 'when' dates in the specified `dates`.
    """
    if not dates:
        return cinema_listings  # nothing to filter

    filtered = {}

    for title, listing_data in cinema_listings.items():
        when_entries = listing_data.get("when", [])
        if not isinstance(when_entries, list):
            continue  # malformed, skip

        # keep only 'when' entries with a date in the target list
        filtered_when = [w for w in when_entries if w.get("date") in dates]

        if filtered_when:
            # copy listing but replace its 'when' list with only relevant dates
            filtered_listing = listing_data.copy()
            filtered_listing["when"] = filtered_when
            filtered[title] = filtered_listing

    return filtered


def _filter_cinemas_listings_by_dates(
    listings_by_cinema: dict, dates: list[str]
) -> dict:
    """
    Apply _filter_listings_by_dates across all cinemas,
    remove cinemas that end up empty, and redact unwanted fields.

    Args:
        listings_by_cinema (dict): { cinema_name: { <title>: <listing_data> } }
        dates (list[str]): list of date strings

    Returns:
        dict: cleaned and filtered structure {
            cinema_name: { <title>: <listing_data_without_removed_fields> }
        }
    """
    filtered_all = {}

    for cinema, listings in listings_by_cinema.items():
        if not isinstance(listings, dict):
            continue

        filtered_listings = _filter_listings_by_dates(listings, dates)
        if filtered_listings:
            # Keep the same structure, no extra "listings" key
            filtered_all[cinema] = filtered_listings

    # # Redact fields like 'image_to_download' after filtering
    # redacted_filtered_all = _redact_listings(filtered_all)

    return filtered_all


# ===== ROUTE HANDLERS =====
def get_listings(cinemas: list[str], dates: list[str]) -> dict:
    """
    Fetch listings for the given cinemas and filter them
    to include only entries whose 'when' dates match the given dates.

    Args:
        cinemas (list[str]): cinemas to include
        dates (list[str]): list of target dates (YYYY-MM-DD)

    Returns:
        dict: { cinema_name: { "listings": { <title>: <filtered_listing> } } }
    """
    # Step 1: Get raw listings JSON for all cinemas
    listings_by_cinema = _get_cinemas_raw_listings(cinemas)

    # Step 2: Filter listings by matching 'when.date'
    filtered_by_dates = _filter_cinemas_listings_by_dates(listings_by_cinema, dates)

    # Step 3: Redact fields like 'image_to_download' for cleanliness
    redacted_filtered = _redact_listings_fields(filtered_by_dates)

    return redacted_filtered


def get_image_listings(cinemas: list[str], dates: list[str]) -> dict:
    """
    Combine active listings and 'good' images for each cinema,
    keeping only listings that have exactly matching images.
    Applies date filtering before redaction.
    Adds the matching presigned URL to each listing.
    """
    listings_by_cinema = _get_cinemas_raw_listings(cinemas)
    listings_by_cinema_date_filtered = _filter_cinemas_listings_by_dates(
        listings_by_cinema, dates
    )

    images_by_cinema = _get_cinemas_good_images(cinemas)

    listings_with_good_images = _match_and_attach_images_to_listings(
        listings_by_cinema_date_filtered, images_by_cinema, cinemas
    )

    redacted_listings_with_good_images = _redact_listings_fields(
        listings_with_good_images
    )
    return redacted_listings_with_good_images


# ===== MAIN HANDLER =====


def lambda_handler(event, context):

    print("Event:", json.dumps(event))

    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
        or ""
    ).upper()
    query = event.get("queryStringParameters") or {}

    if method == "OPTIONS":
        return build_response(200, {"message": "CORS preflight OK"})

    # === GET ===
    if method == "GET":
        route_type = query.get("route_type")
        if route_type not in ROUTE_TYPES:
            return build_response(400, {"error": "Invalid route_type parameter"})

        cinemas: list[str] = query.get("cinemas")
        if (
            not cinemas
            or not isinstance(cinemas, list)
            or any(c not in CINEMAS for c in cinemas)
        ):
            return build_response(
                400, {"error": "Missing or invalid 'cinema' parameter"}
            )

        dates: list[str] = query.get("dates")

        # === Dates are mandatory for all routes ===
        if (
            not dates
            or not isinstance(dates, list)
            or not all(
                isinstance(d, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", d)
                for d in dates
            )
        ):
            return build_response(
                500, {"error": "Missing or invalid 'dates' parameter"}
            )

        # === Listings ===
        if route_type == "listings":
            server_response_data = get_listings(cinemas, dates)

        # === Visual Listings ===
        elif route_type == "visual_listings":
            server_response_data = get_image_listings(cinemas, dates)

        return build_response(200, server_response_data)

    else:
        return build_response(405, {"error": f"Unsupported method: {method}"})


# ===== LOCAL TESTING =====
if __name__ == "__main__":

    # Generate today and tomorrow as date objects
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Generate lists of ISO-format date strings
    next_week_dates = [(today + timedelta(days=i)).isoformat() for i in range(1, 8)]
    next_30_dates = [(today + timedelta(days=i)).isoformat() for i in range(1, 31)]

    # Simple local test setup
    test_event_visual_listings = {
        "httpMethod": "GET",
        "queryStringParameters": {
            "route_type": "visual_listings",
            "cinemas": [
                "close_up",
                "ica",
                "nickel",
                "prince_charles",
                "bfi_southbank",
            ],  # all available cinemas
            "dates": next_30_dates,  # 30-day range
        },
    }

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
            ],  # all available cinemas
            "dates": [
                today.isoformat(),
                tomorrow.isoformat(),
            ],  # include today and tomorrow
        },
    }

    # Run the handler directly
    response = lambda_handler(test_event_listings, context=None)

    # Print formatted output
    print("\n=== Local Test Result ===")
    print(json.dumps(response, indent=2))
