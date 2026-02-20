from unittest.mock import patch

from routes.get_image_listings import get_image_listings

CINEMAS = ["bfi_southbank"]
DATES = ["2024-01-15"]


@patch("routes.get_image_listings._redact_listings_fields")
@patch("routes.get_image_listings._match_and_attach_images_to_listings")
@patch("routes.get_image_listings._get_cinemas_good_images")
@patch("routes.get_image_listings._filter_cinemas_listings_by_dates")
@patch("routes.get_image_listings._get_cinemas_raw_listings")
def test_get_image_listings_calls_pipeline_in_order(
    mock_raw, mock_filter, mock_images, mock_match, mock_redact
):
    mock_raw.return_value = {"bfi_southbank": {"Film A": {}}}
    mock_filter.return_value = {"bfi_southbank": {"Film A": {}}}
    mock_images.return_value = {"bfi_southbank": [{"name": "film_a.jpg", "url": "http://x"}]}
    mock_match.return_value = {"bfi_southbank": {"Film A": {"image_url": "http://x"}}}
    mock_redact.return_value = {"bfi_southbank": {"Film A": {}}}

    result = get_image_listings(CINEMAS, DATES)

    mock_raw.assert_called_once_with(CINEMAS)
    mock_filter.assert_called_once_with(mock_raw.return_value, DATES)
    mock_images.assert_called_once_with(CINEMAS)
    mock_match.assert_called_once_with(mock_filter.return_value, mock_images.return_value, CINEMAS)
    mock_redact.assert_called_once_with(mock_match.return_value)
    assert result == mock_redact.return_value


@patch("routes.get_image_listings._redact_listings_fields")
@patch("routes.get_image_listings._match_and_attach_images_to_listings")
@patch("routes.get_image_listings._get_cinemas_good_images")
@patch("routes.get_image_listings._filter_cinemas_listings_by_dates")
@patch("routes.get_image_listings._get_cinemas_raw_listings")
def test_get_image_listings_returns_redacted_result(
    mock_raw, mock_filter, mock_images, mock_match, mock_redact
):
    expected = {"bfi_southbank": {"Film B": {"title": "Film B"}}}
    mock_redact.return_value = expected

    result = get_image_listings(CINEMAS, DATES)

    assert result is expected


@patch("routes.get_image_listings._redact_listings_fields")
@patch("routes.get_image_listings._match_and_attach_images_to_listings")
@patch("routes.get_image_listings._get_cinemas_good_images")
@patch("routes.get_image_listings._filter_cinemas_listings_by_dates")
@patch("routes.get_image_listings._get_cinemas_raw_listings")
def test_get_image_listings_passes_multiple_cinemas_and_dates(
    mock_raw, mock_filter, mock_images, mock_match, mock_redact
):
    cinemas = ["bfi_southbank", "barbican"]
    dates = ["2024-01-15", "2024-01-16"]
    mock_raw.return_value = {}
    mock_filter.return_value = {}
    mock_images.return_value = {}
    mock_match.return_value = {}
    mock_redact.return_value = {}

    get_image_listings(cinemas, dates)

    mock_raw.assert_called_once_with(cinemas)
    mock_filter.assert_called_once_with({}, dates)
    mock_images.assert_called_once_with(cinemas)
    mock_match.assert_called_once_with({}, {}, cinemas)


@patch("routes.get_image_listings._redact_listings_fields")
@patch("routes.get_image_listings._match_and_attach_images_to_listings")
@patch("routes.get_image_listings._get_cinemas_good_images")
@patch("routes.get_image_listings._filter_cinemas_listings_by_dates")
@patch("routes.get_image_listings._get_cinemas_raw_listings")
def test_get_image_listings_empty_result_propagates(
    mock_raw, mock_filter, mock_images, mock_match, mock_redact
):
    mock_raw.return_value = {}
    mock_filter.return_value = {}
    mock_images.return_value = {}
    mock_match.return_value = {}
    mock_redact.return_value = {}

    result = get_image_listings(CINEMAS, DATES)

    assert result == {}
