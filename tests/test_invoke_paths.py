from unittest.mock import patch

import lambda_function

VALID_CINEMA = "bfi_southbank"
VALID_DATE = "2024-01-15"


def _event(method="GET", route_type=None, cinemas=None, dates=None):
    qs_single = {}
    qs_multi = {}
    if route_type is not None:
        qs_single["route_type"] = route_type
    if cinemas is not None:
        qs_multi["cinemas"] = cinemas
    if dates is not None:
        qs_multi["dates"] = dates
    return {
        "httpMethod": method,
        "queryStringParameters": qs_single,
        "multiValueQueryStringParameters": qs_multi,
    }

# --- OPTIONS ---

@patch("lambda_function.build_response")
@patch("lambda_function.get_pan_cinema_listings")
@patch("lambda_function.get_image_listings")
@patch("lambda_function.get_listings")
def test_options_calls_build_response_200(mock_listings, mock_image, mock_pan, mock_build):
    lambda_function.lambda_handler(_event(method="OPTIONS"), None)
    mock_build.assert_called_once_with(200, {"message": "CORS preflight OK"})
    mock_listings.assert_not_called()
    mock_image.assert_not_called()
    mock_pan.assert_not_called()


# --- Unsupported method ---

@patch("lambda_function.build_response")
@patch("lambda_function.get_pan_cinema_listings")
@patch("lambda_function.get_image_listings")
@patch("lambda_function.get_listings")
def test_post_calls_build_response_405(mock_listings, mock_image, mock_pan, mock_build):
    lambda_function.lambda_handler(_event(method="POST"), None)
    assert mock_build.call_args[0][0] == 405
    mock_listings.assert_not_called()
    mock_image.assert_not_called()
    mock_pan.assert_not_called()


# --- Invalid / missing route_type ---

@patch("lambda_function.build_response")
@patch("lambda_function.get_pan_cinema_listings")
@patch("lambda_function.get_image_listings")
@patch("lambda_function.get_listings")
def test_invalid_route_type_calls_build_response_400(mock_listings, mock_image, mock_pan, mock_build):
    lambda_function.lambda_handler(_event(route_type="not_a_route"), None)
    assert mock_build.call_args[0][0] == 400
    mock_listings.assert_not_called()
    mock_image.assert_not_called()
    mock_pan.assert_not_called()


# --- pan_cinema_listings ---

@patch("lambda_function.build_response")
@patch("lambda_function.get_pan_cinema_listings")
@patch("lambda_function.get_image_listings")
@patch("lambda_function.get_listings")
def test_pan_cinema_listings_calls_get_pan_cinema_listings(mock_listings, mock_image, mock_pan, mock_build):
    lambda_function.lambda_handler(_event(route_type="pan_cinema_listings"), None)
    mock_pan.assert_called_once_with()
    mock_listings.assert_not_called()
    mock_image.assert_not_called()
    assert mock_build.call_args[0][0] == 200


# --- listings ---

@patch("lambda_function.build_response")
@patch("lambda_function.get_pan_cinema_listings")
@patch("lambda_function.get_image_listings")
@patch("lambda_function.get_listings")
def test_listings_calls_get_listings_with_cinemas_and_dates(mock_listings, mock_image, mock_pan, mock_build):
    cinemas = [VALID_CINEMA]
    dates = [VALID_DATE]
    lambda_function.lambda_handler(_event(route_type="listings", cinemas=cinemas, dates=dates), None)
    mock_listings.assert_called_once_with(cinemas, dates)
    mock_image.assert_not_called()
    mock_pan.assert_not_called()
    assert mock_build.call_args[0][0] == 200


# --- visual_listings ---

@patch("lambda_function.build_response")
@patch("lambda_function.get_pan_cinema_listings")
@patch("lambda_function.get_image_listings")
@patch("lambda_function.get_listings")
def test_visual_listings_calls_get_image_listings_with_cinemas_and_dates(mock_listings, mock_image, mock_pan, mock_build):
    cinemas = [VALID_CINEMA]
    dates = [VALID_DATE]
    lambda_function.lambda_handler(_event(route_type="visual_listings", cinemas=cinemas, dates=dates), None)
    mock_image.assert_called_once_with(cinemas, dates)
    mock_listings.assert_not_called()
    mock_pan.assert_not_called()
    assert mock_build.call_args[0][0] == 200


# --- Bad cinemas / dates ---

@patch("lambda_function.build_response")
@patch("lambda_function.get_pan_cinema_listings")
@patch("lambda_function.get_image_listings")
@patch("lambda_function.get_listings")
def test_invalid_cinema_calls_build_response_400(mock_listings, mock_image, mock_pan, mock_build):
    lambda_function.lambda_handler(
        _event(route_type="listings", cinemas=["not_a_cinema"], dates=[VALID_DATE]), None
    )
    assert mock_build.call_args[0][0] == 400
    mock_listings.assert_not_called()
    mock_image.assert_not_called()
    mock_pan.assert_not_called()


@patch("lambda_function.build_response")
@patch("lambda_function.get_pan_cinema_listings")
@patch("lambda_function.get_image_listings")
@patch("lambda_function.get_listings")
def test_invalid_date_format_calls_build_response_400(mock_listings, mock_image, mock_pan, mock_build):
    lambda_function.lambda_handler(
        _event(route_type="listings", cinemas=[VALID_CINEMA], dates=["not-a-date"]), None
    )
    assert mock_build.call_args[0][0] == 400
    mock_listings.assert_not_called()
    mock_image.assert_not_called()
    mock_pan.assert_not_called()
