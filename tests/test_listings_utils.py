import json
from unittest.mock import patch, MagicMock

from shared.listings_utils import (
    _redact_listings_fields,
    _filter_listings_by_dates,
    _filter_cinemas_listings_by_dates,
    _get_cinemas_raw_listings,
)


# ===== _redact_listings_fields =====

def test_redact_removes_image_to_download():
    listings = {"bfi": {"Film A": {"title": "Film A", "image_to_download": "x"}}}
    result = _redact_listings_fields(listings)
    assert "image_to_download" not in result["bfi"]["Film A"]
    assert result["bfi"]["Film A"]["title"] == "Film A"


def test_redact_removes_is_image_good():
    listings = {"bfi": {"Film A": {"title": "Film A", "isImageGood": True}}}
    result = _redact_listings_fields(listings)
    assert "isImageGood" not in result["bfi"]["Film A"]


def test_redact_removes_s3_image_url():
    listings = {"bfi": {"Film A": {"title": "Film A", "s3ImageURL": "http://s3"}}}
    result = _redact_listings_fields(listings)
    assert "s3ImageURL" not in result["bfi"]["Film A"]


def test_redact_keeps_non_redacted_fields():
    listings = {"bfi": {"Film A": {"title": "Film A", "when": []}}}
    result = _redact_listings_fields(listings)
    assert result["bfi"]["Film A"] == {"title": "Film A", "when": []}


def test_redact_skips_non_dict_listings():
    listings = {"bfi": {"Film A": "not_a_dict"}}
    result = _redact_listings_fields(listings)
    assert "bfi" not in result  # Film A is skipped, so cinema becomes empty


def test_redact_skips_empty_cleaned_listing():
    listings = {"bfi": {"Film A": {"image_to_download": "x", "isImageGood": True}}}
    result = _redact_listings_fields(listings)
    # All fields redacted → Film A is empty → cinema is excluded
    assert "bfi" not in result


def test_redact_handles_empty_input():
    assert _redact_listings_fields({}) == {}


def test_redact_multiple_cinemas():
    listings = {
        "bfi": {"Film A": {"title": "A", "isImageGood": True}},
        "barbican": {"Film B": {"title": "B", "s3ImageURL": "http://s3"}},
    }
    result = _redact_listings_fields(listings)
    assert result["bfi"]["Film A"] == {"title": "A"}
    assert result["barbican"]["Film B"] == {"title": "B"}


# ===== _filter_listings_by_dates =====

def _listing_with_dates(*dates):
    return {"when": [{"date": d, "time": "18:00"} for d in dates]}


def test_filter_listings_by_dates_keeps_matching_entries():
    listings = {"Film A": _listing_with_dates("2024-01-15", "2024-01-16")}
    result = _filter_listings_by_dates(listings, ["2024-01-15"])
    assert len(result["Film A"]["when"]) == 1
    assert result["Film A"]["when"][0]["date"] == "2024-01-15"


def test_filter_listings_by_dates_excludes_non_matching():
    listings = {"Film A": _listing_with_dates("2024-01-20")}
    result = _filter_listings_by_dates(listings, ["2024-01-15"])
    assert "Film A" not in result


def test_filter_listings_by_dates_empty_dates_returns_all():
    listings = {"Film A": _listing_with_dates("2024-01-15")}
    result = _filter_listings_by_dates(listings, [])
    assert result == listings


def test_filter_listings_by_dates_skips_non_list_when():
    listings = {"Film A": {"when": "not_a_list"}}
    result = _filter_listings_by_dates(listings, ["2024-01-15"])
    assert "Film A" not in result


def test_filter_listings_by_dates_multiple_dates():
    listings = {
        "Film A": _listing_with_dates("2024-01-15"),
        "Film B": _listing_with_dates("2024-01-16"),
        "Film C": _listing_with_dates("2024-01-20"),
    }
    result = _filter_listings_by_dates(listings, ["2024-01-15", "2024-01-16"])
    assert "Film A" in result
    assert "Film B" in result
    assert "Film C" not in result


# ===== _filter_cinemas_listings_by_dates =====

def test_filter_cinemas_listings_by_dates_filters_each_cinema():
    listings_by_cinema = {
        "bfi": {"Film A": _listing_with_dates("2024-01-15")},
        "barbican": {"Film B": _listing_with_dates("2024-01-20")},
    }
    result = _filter_cinemas_listings_by_dates(listings_by_cinema, ["2024-01-15"])
    assert "bfi" in result
    assert "barbican" not in result  # no listings match the date


def test_filter_cinemas_listings_by_dates_skips_non_dict_cinema():
    listings_by_cinema = {
        "bfi": "not_a_dict",
        "barbican": {"Film B": _listing_with_dates("2024-01-15")},
    }
    result = _filter_cinemas_listings_by_dates(listings_by_cinema, ["2024-01-15"])
    assert "bfi" not in result
    assert "barbican" in result


def test_filter_cinemas_listings_by_dates_empty_input():
    result = _filter_cinemas_listings_by_dates({}, ["2024-01-15"])
    assert result == {}


# ===== _get_cinemas_raw_listings =====

def _make_s3_body(data: dict):
    body = MagicMock()
    body.read.return_value = json.dumps(data).encode("utf-8")
    return {"Body": body}


@patch("shared.listings_utils.s3")
def test_get_cinemas_raw_listings_returns_parsed_json(mock_s3):
    data = {"Film A": {"when": []}}
    mock_s3.get_object.return_value = _make_s3_body(data)

    result = _get_cinemas_raw_listings(["bfi_southbank"])

    assert result["bfi_southbank"] == data


@patch("shared.listings_utils.s3")
def test_get_cinemas_raw_listings_handles_general_exception(mock_s3):
    # NoSuchKey must be a real exception class so Python can use it in an except clause
    mock_s3.exceptions.NoSuchKey = type("NoSuchKey", (Exception,), {})
    mock_s3.get_object.side_effect = Exception("timeout")

    result = _get_cinemas_raw_listings(["bfi_southbank"])

    assert "error" in result["bfi_southbank"]
    assert "timeout" in result["bfi_southbank"]["error"]


@patch("shared.listings_utils.s3")
def test_get_cinemas_raw_listings_multiple_cinemas(mock_s3):
    def _side_effect(**kwargs):
        cinema = kwargs["Key"].split("/")[2]  # e.g. london/cinema-listings/bfi_southbank/...
        return _make_s3_body({f"Film from {cinema}": {}})

    mock_s3.get_object.side_effect = _side_effect

    result = _get_cinemas_raw_listings(["bfi_southbank", "barbican"])

    assert "bfi_southbank" in result
    assert "barbican" in result
