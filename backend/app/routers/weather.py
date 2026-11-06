import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import WEATHER_API_KEY
from app.database import get_db
from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("/{city}")
def weather(city: str, _: User = Depends(get_current_user)):
    if not WEATHER_API_KEY:
        raise HTTPException(503, "Weather integration is not configured")
    try:
        response = httpx.get("https://api.openweathermap.org/data/2.5/weather", params={"q": city[:100], "appid": WEATHER_API_KEY, "units": "metric"}, timeout=8)
        response.raise_for_status()
        data = response.json()
        return {"city": data.get("name"), "temperature_c": data.get("main", {}).get("temp"), "description": data.get("weather", [{}])[0].get("description")}
    except httpx.HTTPError as error:
        raise HTTPException(502, "Weather provider request failed") from error
