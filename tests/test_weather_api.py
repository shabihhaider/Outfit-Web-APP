"""
tests/test_weather_api.py
Tests for the WeatherAPI.com weather integration.
All HTTP calls are mocked — no real network requests are made.

Run: pytest tests/test_weather_api.py -v
"""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import pytest

from engine.models import WeatherAPIError, WeatherLocationError


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _mock_response(temp_celsius: float) -> MagicMock:
    """Build a mock requests.Response returning the WeatherAPI.com format."""
    mock = MagicMock()
    mock.json.return_value = {"current": {"temp_c": temp_celsius}}
    mock.raise_for_status = MagicMock()
    mock.text = f'{{"current": {{"temp_c": {temp_celsius}}}}}'
    return mock


# ─── get_temperature_by_coords tests ──────────────────────────────────────────

class TestGetTemperatureByCoords:

    def test_success_returns_temperature(self):
        """A valid API response returns the temperature as a float."""
        from engine.weather_api import get_temperature_by_coords

        with patch.dict(os.environ, {"WEATHERAPI_KEY": "test-key"}), \
             patch("requests.get", return_value=_mock_response(38.5)):
            result = get_temperature_by_coords(31.5204, 74.3587)

        assert abs(result - 38.5) < 1e-6

    def test_success_calls_correct_endpoint(self):
        """Verifies the request uses the correct URL, key param, and q=lat,lon format."""
        from engine.weather_api import get_temperature_by_coords, _WEATHERAPI_URL

        with patch.dict(os.environ, {"WEATHERAPI_KEY": "test-key"}), \
             patch("requests.get", return_value=_mock_response(25.0)) as mock_get:
            get_temperature_by_coords(24.8607, 67.0011)  # Karachi

        args, kwargs = mock_get.call_args
        assert args[0] == _WEATHERAPI_URL
        assert kwargs["params"]["key"] == "test-key"
        assert kwargs["params"]["q"] == "24.8607,67.0011"

    def test_missing_api_key_raises_weather_api_error(self):
        """WeatherAPIError is raised when no API key is configured."""
        from engine.weather_api import get_temperature_by_coords

        with patch("engine.weather_api._load_api_key",
                   side_effect=WeatherAPIError("WEATHERAPI_KEY not set")):
            with pytest.raises(WeatherAPIError, match="WEATHERAPI_KEY"):
                get_temperature_by_coords(31.5204, 74.3587)

    def test_timeout_raises_weather_api_error(self):
        """Network timeout raises WeatherAPIError."""
        import requests as req_lib
        from engine.weather_api import get_temperature_by_coords

        with patch.dict(os.environ, {"WEATHERAPI_KEY": "test-key"}), \
             patch("requests.get", side_effect=req_lib.exceptions.Timeout):
            with pytest.raises(WeatherAPIError, match="timed out"):
                get_temperature_by_coords(31.5204, 74.3587)

    def test_http_error_raises_weather_api_error(self):
        """Non-2xx HTTP response raises WeatherAPIError."""
        import requests as req_lib
        from engine.weather_api import get_temperature_by_coords

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req_lib.exceptions.HTTPError("403 Forbidden")

        with patch.dict(os.environ, {"WEATHERAPI_KEY": "bad-key"}), \
             patch("requests.get", return_value=mock_resp):
            with pytest.raises(WeatherAPIError):
                get_temperature_by_coords(31.5204, 74.3587)

    def test_malformed_response_raises_weather_api_error(self):
        """Response missing current.temp_c raises WeatherAPIError."""
        from engine.weather_api import get_temperature_by_coords

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"location": {"name": "Lahore"}}  # No "current" key
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = '{"location": {"name": "Lahore"}}'

        with patch.dict(os.environ, {"WEATHERAPI_KEY": "test-key"}), \
             patch("requests.get", return_value=mock_resp):
            with pytest.raises(WeatherAPIError):
                get_temperature_by_coords(31.5204, 74.3587)

    def test_works_for_any_city(self):
        """Works correctly for any Pakistani city — no hardcoded location bias."""
        from engine.weather_api import get_temperature_by_coords

        cities = [
            (24.8607, 67.0011, 33.0),   # Karachi
            (33.7215, 73.0433, 22.0),   # Islamabad
            (31.5497, 74.3436, 38.0),   # Lahore
            (25.3960, 68.3578, 40.0),   # Hyderabad
        ]
        for lat, lon, expected_temp in cities:
            with patch.dict(os.environ, {"WEATHERAPI_KEY": "test-key"}), \
                 patch("requests.get", return_value=_mock_response(expected_temp)):
                result = get_temperature_by_coords(lat, lon)
            assert abs(result - expected_temp) < 1e-6, f"Failed for coords ({lat}, {lon})"


# ─── Pipeline.get_temperature tests ───────────────────────────────────────────

class TestPipelineGetTemperature:

    def test_returns_temperature_when_coords_provided(self):
        """pipeline.get_temperature(lat, lon) delegates to get_temperature_by_coords."""
        from engine.pipeline import RecommendationPipeline

        with patch.object(RecommendationPipeline, "__init__", return_value=None), \
             patch("engine.pipeline.get_temperature_by_coords", return_value=38.5) as mock_fn:
            pipeline = RecommendationPipeline.__new__(RecommendationPipeline)
            result = pipeline.get_temperature(lat=31.5204, lon=74.3587)

        assert result == 38.5
        mock_fn.assert_called_once_with(31.5204, 74.3587)

    def test_raises_weather_location_error_when_lat_is_none(self):
        """Missing lat raises WeatherLocationError — no silent fallback."""
        from engine.pipeline import RecommendationPipeline

        with patch.object(RecommendationPipeline, "__init__", return_value=None):
            pipeline = RecommendationPipeline.__new__(RecommendationPipeline)
            with pytest.raises(WeatherLocationError):
                pipeline.get_temperature(lat=None, lon=74.3587)

    def test_raises_weather_location_error_when_lon_is_none(self):
        """Missing lon raises WeatherLocationError — no silent fallback."""
        from engine.pipeline import RecommendationPipeline

        with patch.object(RecommendationPipeline, "__init__", return_value=None):
            pipeline = RecommendationPipeline.__new__(RecommendationPipeline)
            with pytest.raises(WeatherLocationError):
                pipeline.get_temperature(lat=31.5204, lon=None)

    def test_raises_weather_location_error_when_both_none(self):
        """Missing both coords raises WeatherLocationError."""
        from engine.pipeline import RecommendationPipeline

        with patch.object(RecommendationPipeline, "__init__", return_value=None):
            pipeline = RecommendationPipeline.__new__(RecommendationPipeline)
            with pytest.raises(WeatherLocationError):
                pipeline.get_temperature(lat=None, lon=None)

    def test_propagates_weather_api_error(self):
        """If the API call fails, WeatherAPIError propagates to Flask for handling."""
        from engine.pipeline import RecommendationPipeline

        with patch.object(RecommendationPipeline, "__init__", return_value=None), \
             patch("engine.pipeline.get_temperature_by_coords",
                   side_effect=WeatherAPIError("timeout")):
            pipeline = RecommendationPipeline.__new__(RecommendationPipeline)
            with pytest.raises(WeatherAPIError):
                pipeline.get_temperature(lat=31.5204, lon=74.3587)
