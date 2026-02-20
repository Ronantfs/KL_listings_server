import json
from unittest.mock import patch, MagicMock

from routes.get_image_listings.utils import (
    _normalize_name,
    _filter_cinema_listings_by_images,
    _match_and_attach_images_to_listings,
    _get_cinemas_good_images,
)


# ===== _normalize_name =====

def test_normalize_name_lowercases():
    assert _normalize_name("Film Title") == "film_title"


def test_normalize_name_replaces_special_chars_with_underscore():
    assert _normalize_name("Film: A Story!") == "film_a_story"


def test_normalize_name_strips_leading_trailing_underscores():
    assert _normalize_name("  film  ") == "film"


def test_normalize_name_collapses_multiple_separators():
    assert _normalize_name("film---title") == "film_title"


def test_normalize_name_empty_string():
    assert _normalize_name("") == ""


def test_normalize_name_alphanumeric_unchanged():
    assert _normalize_name("kung fu panda") == "kung_fu_panda"


# ===== _filter_cinema_listings_by_images =====

def test_filter_cinema_listings_by_images_keeps_matching_titles():
    listings = {"Kung Fu Panda": {"when": []}, "Unknown Film": {"when": []}}
    good_images = ["kung_fu_panda.jpg"]

    result = _filter_cinema_listings_by_images(listings, good_images)

    assert "Kung Fu Panda" in result
    assert "Unknown Film" not in result


def test_filter_cinema_listings_by_images_no_matches_returns_empty():
    listings = {"Some Film": {"when": []}}
    good_images = ["other_film.jpg"]

    result = _filter_cinema_listings_by_images(listings, good_images)

    assert result == {}


def test_filter_cinema_listings_by_images_empty_listings():
    result = _filter_cinema_listings_by_images({}, ["film.jpg"])
    assert result == {}


def test_filter_cinema_listings_by_images_empty_images():
    listings = {"Film A": {"when": []}}
    result = _filter_cinema_listings_by_images(listings, [])
    assert result == {}


def test_filter_cinema_listings_by_images_ignores_non_string_images():
    listings = {"Film A": {"when": []}}
    result = _filter_cinema_listings_by_images(listings, [None, 123])
    assert result == {}


# ===== _match_and_attach_images_to_listings =====

def _make_image(name, url):
    return {"name": name, "url": url}


def test_match_attaches_image_url_on_direct_match():
    listings = {"bfi_southbank": {"Kung Fu Panda": {"when": []}}}
    images = {"bfi_southbank": [_make_image("Kung Fu Panda.jpg", "http://img")]}

    result = _match_and_attach_images_to_listings(listings, images, ["bfi_southbank"])

    assert result["bfi_southbank"]["Kung Fu Panda"]["image_url"] == "http://img"


def test_match_attaches_image_url_on_prefix_match():
    listings = {"bfi_southbank": {"Kung Fu Panda": {"when": []}}}
    images = {"bfi_southbank": [_make_image("kung_fu_panda_en.jpg", "http://img2")]}

    result = _match_and_attach_images_to_listings(listings, images, ["bfi_southbank"])

    assert result["bfi_southbank"]["Kung Fu Panda"]["image_url"] == "http://img2"


def test_match_excludes_listings_with_no_image():
    listings = {"bfi_southbank": {"Unknown Film": {"when": []}}}
    images = {"bfi_southbank": [_make_image("other_film.jpg", "http://img")]}

    result = _match_and_attach_images_to_listings(listings, images, ["bfi_southbank"])

    assert "Unknown Film" not in result.get("bfi_southbank", {})


def test_match_handles_missing_cinema_in_images():
    listings = {"bfi_southbank": {"Film A": {"when": []}}}
    images = {}  # no entry for bfi_southbank

    result = _match_and_attach_images_to_listings(listings, images, ["bfi_southbank"])

    assert result["bfi_southbank"] == {}


def test_match_handles_malformed_image_entries():
    listings = {"bfi_southbank": {"Film A": {"when": []}}}
    images = {"bfi_southbank": [{"bad": "entry"}, "not_a_dict"]}

    result = _match_and_attach_images_to_listings(listings, images, ["bfi_southbank"])

    assert result["bfi_southbank"] == {}


def test_match_processes_multiple_cinemas():
    listings = {
        "bfi_southbank": {"Film A": {"when": []}},
        "barbican": {"Film B": {"when": []}},
    }
    images = {
        "bfi_southbank": [_make_image("film_a.jpg", "http://a")],
        "barbican": [_make_image("film_b.jpg", "http://b")],
    }

    result = _match_and_attach_images_to_listings(
        listings, images, ["bfi_southbank", "barbican"]
    )

    assert result["bfi_southbank"]["Film A"]["image_url"] == "http://a"
    assert result["barbican"]["Film B"]["image_url"] == "http://b"


# ===== _get_cinemas_good_images =====

def _make_s3_list_response(keys, truncated=False):
    contents = [{"Key": k} for k in keys]
    return {
        "Contents": contents,
        "IsTruncated": truncated,
    }


@patch("routes.get_image_listings.utils._generate_presigned_url")
@patch("routes.get_image_listings.utils.s3")
def test_get_cinemas_good_images_returns_image_list(mock_s3, mock_presign):
    mock_s3.list_objects_v2.return_value = _make_s3_list_response(
        ["cinema_listings_images/bfi_southbank/good/film_a.jpg"]
    )
    mock_presign.return_value = "http://presigned"

    result = _get_cinemas_good_images(["bfi_southbank"])

    assert "bfi_southbank" in result
    images = result["bfi_southbank"]
    assert len(images) == 1
    assert images[0]["name"] == "film_a.jpg"
    assert images[0]["url"] == "http://presigned"


@patch("routes.get_image_listings.utils._generate_presigned_url")
@patch("routes.get_image_listings.utils.s3")
def test_get_cinemas_good_images_filters_non_image_files(mock_s3, mock_presign):
    mock_s3.list_objects_v2.return_value = _make_s3_list_response(
        [
            "cinema_listings_images/bfi_southbank/good/film_a.jpg",
            "cinema_listings_images/bfi_southbank/good/readme.txt",
        ]
    )
    mock_presign.return_value = "http://presigned"

    result = _get_cinemas_good_images(["bfi_southbank"])

    assert len(result["bfi_southbank"]) == 1
    assert result["bfi_southbank"][0]["name"] == "film_a.jpg"


@patch("routes.get_image_listings.utils._generate_presigned_url")
@patch("routes.get_image_listings.utils.s3")
def test_get_cinemas_good_images_handles_empty_bucket(mock_s3, mock_presign):
    mock_s3.list_objects_v2.return_value = {"Contents": [], "IsTruncated": False}

    result = _get_cinemas_good_images(["bfi_southbank"])

    assert result["bfi_southbank"] == []


@patch("routes.get_image_listings.utils._generate_presigned_url")
@patch("routes.get_image_listings.utils.s3")
def test_get_cinemas_good_images_returns_error_dict_on_exception(mock_s3, mock_presign):
    mock_s3.list_objects_v2.side_effect = Exception("S3 error")

    result = _get_cinemas_good_images(["bfi_southbank"])

    assert "error" in result["bfi_southbank"]


@patch("routes.get_image_listings.utils._generate_presigned_url")
@patch("routes.get_image_listings.utils.s3")
def test_get_cinemas_good_images_paginates(mock_s3, mock_presign):
    page1 = {
        "Contents": [{"Key": "cinema_listings_images/bfi_southbank/good/film_a.jpg"}],
        "IsTruncated": True,
        "NextContinuationToken": "token123",
    }
    page2 = {
        "Contents": [{"Key": "cinema_listings_images/bfi_southbank/good/film_b.png"}],
        "IsTruncated": False,
    }
    mock_s3.list_objects_v2.side_effect = [page1, page2]
    mock_presign.return_value = "http://presigned"

    result = _get_cinemas_good_images(["bfi_southbank"])

    assert len(result["bfi_southbank"]) == 2
    assert mock_s3.list_objects_v2.call_count == 2
