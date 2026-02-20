import json
from unittest.mock import patch, MagicMock

from routes.get_pan_cinema_listings import get_pan_cinema_listings, handle_pan_cinema_listings_route


def _make_s3_response(data: dict) -> dict:
    body = MagicMock()
    body.read.return_value = json.dumps(data).encode("utf-8")
    return {"Body": body}


def _make_qs(id_param=None) -> dict:
    qs = {}
    if id_param is not None:
        qs["id"] = id_param
    return qs


_FILM_ID = 12345
_FILM_LISTINGS = {"bfi_southbank": {"Film A": {}}, "barbican": {"Film A": {}}}
_ALL_LISTINGS = {
    str(_FILM_ID): _FILM_LISTINGS,
    "99999": {"barbican": {"Other Film": {}}},
}


@patch("routes.get_pan_cinema_listings.s3")
def test_get_pan_cinema_listings_returns_parsed_json(mock_s3):
    expected = {"bfi_southbank": {"Film A": {}}}
    mock_s3.get_object.return_value = _make_s3_response(expected)

    result = get_pan_cinema_listings()

    assert result == expected


@patch("routes.get_pan_cinema_listings.s3")
def test_get_pan_cinema_listings_calls_s3_with_correct_bucket_and_key(mock_s3):
    from shared.config import LISTING_BUCKET, PAN_CINEMA_LISTINGS_KEY

    mock_s3.get_object.return_value = _make_s3_response({})

    get_pan_cinema_listings()

    mock_s3.get_object.assert_called_once_with(
        Bucket=LISTING_BUCKET, Key=PAN_CINEMA_LISTINGS_KEY
    )


@patch("routes.get_pan_cinema_listings.s3")
def test_get_pan_cinema_listings_returns_error_dict_on_exception(mock_s3):
    mock_s3.get_object.side_effect = Exception("network error")

    result = get_pan_cinema_listings()

    assert "error" in result
    assert "network error" in result["error"]


@patch("routes.get_pan_cinema_listings.s3")
def test_get_pan_cinema_listings_error_dict_does_not_raise(mock_s3):
    mock_s3.get_object.side_effect = RuntimeError("boom")

    result = get_pan_cinema_listings()

    assert isinstance(result, dict)
    assert "error" in result


# ---------------------------------------------------------------------------
# lambda_handler integration — pan_cinema_listings route with/without id param
# ---------------------------------------------------------------------------


@patch("routes.get_pan_cinema_listings.get_pan_cinema_listings")
def test_pan_cinema_no_id_returns_all_listings(mock_get):
    """No id param → backwards-compatible: returns all listings."""
    mock_get.return_value = _ALL_LISTINGS

    response = handle_pan_cinema_listings_route(_make_qs())

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == _ALL_LISTINGS


@patch("routes.get_pan_cinema_listings.get_pan_cinema_listings")
def test_pan_cinema_valid_id_returns_film_cinema_listings(mock_get):
    """Valid id matching a key → returns CleanMatchedFilmsCinemaListings for that film."""
    mock_get.return_value = _ALL_LISTINGS

    response = handle_pan_cinema_listings_route(_make_qs(id_param=str(_FILM_ID)))

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == _FILM_LISTINGS


@patch("routes.get_pan_cinema_listings.get_pan_cinema_listings")
def test_pan_cinema_unknown_id_returns_404(mock_get):
    """Valid integer id with no matching key → 404 Film Not showing on KL."""
    mock_get.return_value = _ALL_LISTINGS

    response = handle_pan_cinema_listings_route(_make_qs(id_param="00000"))

    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert body["error"] == "Film Not showing on KL"


@patch("routes.get_pan_cinema_listings.get_pan_cinema_listings")
def test_pan_cinema_non_integer_id_returns_400(mock_get):
    """Non-integer id → 400 before S3 is ever called."""
    response = handle_pan_cinema_listings_route(_make_qs(id_param="not_an_int"))

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "id" in body["error"].lower()
    mock_get.assert_not_called()


@patch("routes.get_pan_cinema_listings.get_pan_cinema_listings")
def test_pan_cinema_s3_error_with_id_returns_500(mock_get):
    """S3 failure when id is provided → 500 with error body."""
    mock_get.return_value = {"error": "Failed to load pan cinema listings: network error"}

    response = handle_pan_cinema_listings_route(_make_qs(id_param=str(_FILM_ID)))

    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert "error" in body
