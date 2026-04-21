import requests
from datetime import datetime, timedelta

BEER_SHEVA_LAT = 31.2516
BEER_SHEVA_LON = 34.7915


def get_tomorrow_weather() -> dict | None:
    """Fetches tomorrow's weather for Beer Sheva using Open-Meteo (free, no API key)"""
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={BEER_SHEVA_LAT}&longitude={BEER_SHEVA_LON}"
            f"&daily=precipitation_sum,weathercode,temperature_2m_max,temperature_2m_min"
            f"&timezone=Asia/Jerusalem"
            f"&start_date={tomorrow}&end_date={tomorrow}"
        )
        response = requests.get(url, timeout=5)
        data = response.json()
        daily = data.get("daily", {})
        return {
            "date": tomorrow,
            "rain_mm": daily.get("precipitation_sum", [0])[0],
            "code": daily.get("weathercode", [0])[0],
            "temp_max": daily.get("temperature_2m_max", [0])[0],
            "temp_min": daily.get("temperature_2m_min", [0])[0],
        }
    except Exception:
        return None


def rain_expected(weather: dict) -> bool:
    if not weather:
        return False
    # WMO code >= 51 = drizzle/rain/storm; or precipitation > 0.5mm
    return weather["code"] >= 51 or weather["rain_mm"] > 0.5


def format_weather_alert(weather: dict) -> str:
    return (
        f"🌧️ מחר צפויים גשמים ({weather['rain_mm']}mm)\n"
        f"🌡️ {weather['temp_min']}°C - {weather['temp_max']}°C\n"
        f"אל תשכח מטריה! ☂️"
    )
