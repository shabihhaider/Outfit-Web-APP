"""
engine/weather_api.py
WeatherAPI.com Current Weather integration.

Single responsibility: fetch the current temperature at a given lat/lon.
Location fallback logic belongs in the Flask layer, not here.

API endpoint:
  GET http://api.weatherapi.com/v1/current.json?key={key}&q={lat},{lon}

Response field used: current.temp_c (already in Celsius, no unit conversion needed).

Setup:
  1. Sign up at weatherapi.com → copy your API key (free tier, 1M calls/month).
  2. Create D:/FYP/.env and add:  WEATHERAPI_KEY=your_key_here
  3. pip install requests python-dotenv
"""

from __future__ import annotations

import logging
import os

from engine.models import WeatherAPIError

logger = logging.getLogger(__name__)

# Request timeout in seconds — keeps recommendation latency bounded
_REQUEST_TIMEOUT = 5

_WEATHERAPI_URL = "http://api.weatherapi.com/v1/current.json"


def _load_api_key() -> str:
    """
    Load the WeatherAPI key from the environment.
    Tries os.environ first; falls back to .env file via python-dotenv.

    Raises:
        WeatherAPIError: If no key is found in the environment or .env file.
    """
    key = os.environ.get("WEATHERAPI_KEY")
    if key:
        return key

    try:
        from dotenv import load_dotenv  # type: ignore[import]
        load_dotenv()
        key = os.environ.get("WEATHERAPI_KEY")
    except ImportError:
        pass

    if not key:
        raise WeatherAPIError(
            "WEATHERAPI_KEY not set. "
            "Add it to D:/FYP/.env or set it as an environment variable."
        )
    return key


def get_temperature_by_coords(lat: float, lon: float) -> float:
    """
    Fetch the current temperature (Celsius) at the given coordinates.

    Args:
        lat: Latitude  (e.g. 31.5204 for Lahore, 24.8607 for Karachi)
        lon: Longitude (e.g. 74.3587 for Lahore, 67.0011 for Karachi)

    Returns:
        Temperature in Celsius as a float.

    Raises:
        WeatherAPIError: On missing API key, network failure, timeout, or
                         unexpected response format.
    """
    import requests  # type: ignore[import]

    api_key = _load_api_key()

    params = {
        "key": api_key,
        "q":   f"{lat},{lon}",
    }

    try:
        response = requests.get(_WEATHERAPI_URL, params=params, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise WeatherAPIError(
            f"WeatherAPI request timed out after {_REQUEST_TIMEOUT}s"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise WeatherAPIError(f"WeatherAPI request failed: {exc}") from exc

    try:
        data = response.json()
        temp = float(data["current"]["temp_c"])
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherAPIError(
            f"Unexpected WeatherAPI response format: {exc}\n"
            f"Response: {response.text[:200]}"
        ) from exc

    return temp
