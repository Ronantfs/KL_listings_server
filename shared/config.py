import os

from dotenv import load_dotenv

from shared.aws import set_s3_client

load_dotenv()

IMAGE_BUCKET = os.getenv("IMAGE_BUCKET", "kinoma-assets")
IMAGE_PREFIX = os.getenv("IMAGE_PREFIX", "cinema_listings_images")
LISTING_BUCKET = os.getenv("LISTING_BUCKET", "filmfynder")
LISTING_PREFIX = os.getenv("LISTING_PREFIX", "london/cinema-listings")
AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")

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
    "cine_lumiere",
    "arthouse_crouch_end",
]

ROUTE_TYPES = ["listings", "visual_listings", "pan_cinema_listings"]
PAN_CINEMA_LISTINGS_KEY = f"{LISTING_PREFIX}/all/pan_cinema_listings.json"

s3 = set_s3_client(AWS_REGION)


def get_cinemas_image_folder_path(cinema: str) -> str:
    return f"{IMAGE_PREFIX}/{cinema}/good/"


def get_cinemas_active_listings_path(cinema: str) -> str:
    return f"{LISTING_PREFIX}/{cinema}/active_listings.json"
