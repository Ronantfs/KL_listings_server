from shared.listings_utils import (
    _get_cinemas_raw_listings,
    _filter_cinemas_listings_by_dates,
    _redact_listings_fields,
)
from routes.get_image_listings.utils import (
    _get_cinemas_good_images,
    _match_and_attach_images_to_listings,
)


def get_image_listings(cinemas: list[str], dates: list[str]) -> dict:
    listings_by_cinema = _get_cinemas_raw_listings(cinemas)
    print("Listings by cinema:", listings_by_cinema)
    listings_by_cinema_date_filtered = _filter_cinemas_listings_by_dates(
        listings_by_cinema, dates
    )
    print("Filtered listings by cinema:", listings_by_cinema_date_filtered)
    images_by_cinema = _get_cinemas_good_images(cinemas)
    print("Images by cinema:", images_by_cinema)
    listings_with_good_images = _match_and_attach_images_to_listings(
        listings_by_cinema_date_filtered, images_by_cinema, cinemas
    )
    print("Listings with good images:", listings_with_good_images)
    redacted_listings_with_good_images = _redact_listings_fields(
        listings_with_good_images
    )
    print("Redacted listings with good images:", redacted_listings_with_good_images)
    return redacted_listings_with_good_images
