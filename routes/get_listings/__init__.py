from shared.listings_utils import (
    _get_cinemas_raw_listings,
    _filter_cinemas_listings_by_dates,
    _redact_listings_fields,
)


def get_listings(cinemas: list[str], dates: list[str]) -> dict:
    listings_by_cinema = _get_cinemas_raw_listings(cinemas)
    print("Listings by cinema:", listings_by_cinema)
    filtered_by_dates = _filter_cinemas_listings_by_dates(listings_by_cinema, dates)
    print("Filtered listings by cinema:", filtered_by_dates)
    redacted_filtered = _redact_listings_fields(filtered_by_dates)
    print("Redacted filtered listings:", redacted_filtered)
    return redacted_filtered
