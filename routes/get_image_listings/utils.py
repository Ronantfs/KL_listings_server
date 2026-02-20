import os
import re

from shared.aws import _generate_presigned_url
from shared.config import s3, IMAGE_BUCKET, get_cinemas_image_folder_path


def _normalize_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def _get_cinemas_good_images(cinemas: list[str], expires_in: int = 300) -> dict:
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


def _filter_cinema_listings_by_images(
    cinema_listings: dict, good_images: list[str]
) -> dict:
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
    listings_with_good_images = {}

    for cinema in cinemas:
        raw_cinema_listings = listings_by_cinema.get(cinema, {})
        images_info = images_by_cinema.get(cinema, [])

        # Build a map using only the stem (no extension) and normalized
        image_map = {}
        for img in images_info:
            if not (isinstance(img, dict) and "name" in img and "url" in img):
                continue

            stem = os.path.splitext(img["name"])[0].lower()
            norm_stem = _normalize_name(stem)
            image_map[norm_stem] = img["url"]

        filtered_listings = {}
        for title, listing_data in raw_cinema_listings.items():
            norm_title = _normalize_name(title)

            # Direct match
            if norm_title in image_map:
                listing_data["image_url"] = image_map[norm_title]
                filtered_listings[title] = listing_data
                continue

            # Fallback: some images may contain extra suffixes like "_en"
            # Find any image whose normalized stem *starts with* the normalized title
            # e.g., "kung_fu_panda" matches "kung_fu_panda_en"
            for img_stem, url in image_map.items():
                if img_stem.startswith(norm_title):
                    listing_data["image_url"] = url
                    filtered_listings[title] = listing_data
                    break

        listings_with_good_images[cinema] = filtered_listings

    return listings_with_good_images
