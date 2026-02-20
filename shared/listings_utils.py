import json

from shared.config import s3, LISTING_BUCKET, get_cinemas_active_listings_path


def _get_cinemas_raw_listings(cinemas: list[str]) -> dict:
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
            }
        except Exception as e:
            cinema_listings[cinema] = {
                "error": f"Failed to load listings for {cinema}: {str(e)}"
            }

    return cinema_listings


def _redact_listings_fields(listings_with_good_images: dict) -> dict:
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
    filtered_all = {}
    for cinema, listings in listings_by_cinema.items():
        if not isinstance(listings, dict):
            continue
        filtered_listings = _filter_listings_by_dates(listings, dates)
        if filtered_listings:
            filtered_all[cinema] = filtered_listings
    return filtered_all
