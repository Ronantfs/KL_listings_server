import json

from shared.data_types import PanCinemaCleanedCompactedListings
from shared.config import s3, LISTING_BUCKET, PAN_CINEMA_LISTINGS_KEY
from shared.http_utils import build_response


def get_pan_cinema_listings() -> dict:
    try:
        response = s3.get_object(Bucket=LISTING_BUCKET, Key=PAN_CINEMA_LISTINGS_KEY)
        pan_cinema_listings: PanCinemaCleanedCompactedListings = json.loads(
            response["Body"].read().decode("utf-8")
        )
        return pan_cinema_listings
    except Exception as e:
        return {"error": f"Failed to load pan cinema listings: {str(e)}"}


def handle_pan_cinema_listings_route(qs_single: dict) -> dict:
    film_id_str = (qs_single.get("id") or "").strip()

    if film_id_str:
        print(f"pan_cinema_listings: specific film id requested: {film_id_str}")
        try:
            film_id = int(film_id_str)
        except ValueError:
            print(f"pan_cinema_listings: invalid id param (not an int): {film_id_str!r}")
            return build_response(400, {"error": "Invalid 'id' parameter: must be an integer"})

        all_listings = get_pan_cinema_listings()
        if "error" in all_listings:
            print(f"pan_cinema_listings: failed to load listings: {all_listings}")
            return build_response(500, all_listings)

        film_listings = all_listings.get(str(film_id))
        if film_listings is None:
            print(f"pan_cinema_listings: film id {film_id} not found — returning 404")
            return build_response(404, {"error": "Film Not showing on KL"})

        print(f"pan_cinema_listings: film id {film_id} found — returning CleanMatchedFilmsCinemaListings")
        return build_response(200, film_listings)
    else:
        print("pan_cinema_listings: no id param — returning all listings")
        return build_response(200, get_pan_cinema_listings())
