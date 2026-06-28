"""Weather API scraper — match-day conditions data.

Fetches weather data from OpenWeatherMap or VisualCrossing for IPL
venue cities on match days.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from loguru import logger

from .base import BaseScraper


# Venue city coordinates for weather lookups
VENUE_COORDINATES = {
    "Chennai": (13.0827, 80.2707),
    "Mumbai": (19.0760, 72.8777),
    "Bengaluru": (12.9716, 77.5946),
    "Bangalore": (12.9716, 77.5946),
    "Kolkata": (22.5726, 88.3639),
    "Hyderabad": (17.3850, 78.4867),
    "Delhi": (28.6139, 77.2090),
    "New Delhi": (28.6139, 77.2090),
    "Jaipur": (26.9124, 75.7873),
    "Mohali": (30.7046, 76.7179),
    "Chandigarh": (30.7333, 76.7794),
    "Ahmedabad": (23.0225, 72.5714),
    "Lucknow": (26.8467, 80.9462),
    "Dharamsala": (32.2190, 76.3234),
    "Guwahati": (26.1445, 91.7362),
    "Visakhapatnam": (17.6868, 83.2185),
    "Pune": (18.5204, 73.8567),
    "Ranchi": (23.3441, 85.3096),
    "Indore": (22.7196, 75.8577),
    "Nagpur": (21.1458, 79.0882),
}


class WeatherScraper(BaseScraper):
    """Fetches weather data for match-day conditions."""

    SOURCE_NAME = "weather"

    def __init__(self, config, http_client):
        super().__init__(config, http_client)
        self.owm_key = os.getenv("OPENWEATHER_API_KEY", "")
        self.vc_key = os.getenv("VISUALCROSSING_API_KEY", "")

    # ------------------------------------------------------------------
    # Public Interface
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        return True

    async def fetch_weather_for_city(
        self,
        city: str,
        date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch weather data for a city.

        If date_str is None, fetches current weather.
        If date_str is provided (YYYY-MM-DD), fetches historical/forecast data.
        """
        # Try OpenWeatherMap first
        if self.owm_key:
            try:
                return await self._fetch_owm(city, date_str)
            except Exception as e:
                logger.warning("[Weather] OWM failed for {}: {}", city, e)

        # Fall back to VisualCrossing
        if self.vc_key:
            try:
                return await self._fetch_visualcrossing(city, date_str)
            except Exception as e:
                logger.warning("[Weather] VisualCrossing failed for {}: {}", city, e)

        logger.error("[Weather] No API keys configured or all APIs failed for {}", city)
        return {}

    async def fetch_match_conditions(
        self,
        venue_city: str,
        match_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch weather conditions for a match venue."""
        weather = await self.fetch_weather_for_city(venue_city, match_date)

        return {
            "temperature": weather.get("temperature"),
            "humidity": weather.get("humidity"),
            "weather_condition": weather.get("description", weather.get("weather_condition")),
            "wind_speed": weather.get("wind_speed"),
            "dew_probability": self._estimate_dew_probability(
                weather.get("temperature"),
                weather.get("humidity"),
                weather.get("dew_point"),
            ),
        }

    # ------------------------------------------------------------------
    # OpenWeatherMap
    # ------------------------------------------------------------------

    async def _fetch_owm(self, city: str, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Fetch from OpenWeatherMap API."""
        if date_str:
            # For historical data, use One Call API with timestamps
            coords = VENUE_COORDINATES.get(city)
            if coords:
                lat, lon = coords
                # Convert date to unix timestamp (approximate — noon local time)
                from datetime import datetime
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                timestamp = int(dt.timestamp())
                url = (
                    f"https://api.openweathermap.org/data/2.5/onecall/timemachine"
                    f"?lat={lat}&lon={lon}&dt={timestamp}&appid={self.owm_key}&units=metric"
                )
            else:
                url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.owm_key}&units=metric"
        else:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.owm_key}&units=metric"

        data = await self.fetch_json(url)
        return self._parse_owm_response(data)

    def _parse_owm_response(self, data: Dict) -> Dict[str, Any]:
        """Parse OpenWeatherMap response."""
        if "current" in data:
            current = data["current"]
            return {
                "temperature": current.get("temp"),
                "humidity": current.get("humidity"),
                "dew_point": current.get("dew_point"),
                "wind_speed": current.get("wind_speed"),
                "description": current.get("weather", [{}])[0].get("description", ""),
            }
        elif "main" in data:
            return {
                "temperature": data["main"].get("temp"),
                "humidity": data["main"].get("humidity"),
                "dew_point": data["main"].get("dew_point"),
                "wind_speed": data.get("wind", {}).get("speed"),
                "description": data.get("weather", [{}])[0].get("description", ""),
            }
        return {}

    # ------------------------------------------------------------------
    # VisualCrossing
    # ------------------------------------------------------------------

    async def _fetch_visualcrossing(self, city: str, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Fetch from VisualCrossing API."""
        date_part = f"/{date_str}" if date_str else ""
        url = (
            f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services"
            f"/timeline/{city}{date_part}"
            f"?unitGroup=metric&key={self.vc_key}&include=hours,current"
        )
        data = await self.fetch_json(url)
        return self._parse_vc_response(data)

    def _parse_vc_response(self, data: Dict) -> Dict[str, Any]:
        """Parse VisualCrossing response."""
        current = data.get("currentConditions", data.get("days", [{}])[0] if data.get("days") else {})
        return {
            "temperature": current.get("temp"),
            "humidity": current.get("humidity"),
            "dew_point": current.get("dew"),
            "wind_speed": current.get("windspeed"),
            "description": current.get("conditions", current.get("icon", "")),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_dew_probability(
        temp: Optional[float],
        humidity: Optional[float],
        dew_point: Optional[float],
    ) -> Optional[float]:
        """Estimate dew probability based on weather conditions.

        Higher probability when:
        - Temperature is moderate (20-30°C)
        - Humidity is high (>70%)
        - Dew point is close to temperature
        """
        if temp is None or humidity is None:
            return None

        score = 0.0
        if humidity > 80:
            score += 0.4
        elif humidity > 70:
            score += 0.2

        if dew_point and temp:
            gap = temp - dew_point
            if gap < 3:
                score += 0.4
            elif gap < 6:
                score += 0.2

        if temp and 20 <= temp <= 30:
            score += 0.2

        return min(score, 1.0)

    # Unused abstract methods (weather doesn't scrape match/player data)
    async def scrape_matches(self, season: int, **kwargs):
        return []

    async def scrape_match_detail(self, match_id: str, **kwargs):
        return {}
