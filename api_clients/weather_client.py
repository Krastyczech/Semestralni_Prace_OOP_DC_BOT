import aiohttp
import asyncio
from datetime import datetime, timedelta, date


class WeatherClient:
    """
    Zapouzdřuje logiku pro komunikaci s Open-Meteo API (aktuální) a Meteostat (historické).
    Poskytuje aktuální i archivní data a zajišťuje robustní geokódování.
    """

    async def get_weather_data(self, city: str):
        """
        Získá aktuální a historická data pro dané město z Open-Meteo.
        """
        # 1. Geokódování
        result = await self._geocode_city(city)
        if result is None:
            return None, f"Chyba: Město '{city.title()}' nebylo nalezeno."

        lat, lon, validated_city_name = result

        # 2. Asynchronní příprava úloh (TADY BYLO TO POMÍCHANÉ)
        current_task = self._fetch_current_weather(lat, lon)
        historical_task = self._fetch_historical_weather_open_meteo(lat, lon)

        try:
            # 3. Spuštění obou úloh současně (konkurentně)
            current_data, historical_data = await asyncio.gather(current_task, historical_task)
        except Exception as e:
            print(f"Chyba při souběžném získávání dat: {e}")
            return None, "Nastala chyba při komunikaci s API."

        if current_data is None:
            return None, f"Nepodařilo se získat aktuální data o počasí pro {validated_city_name}."

        # 4. Vrácení finálních dat
        return {
            "city_name": validated_city_name,
            "current": current_data,
            "historical": historical_data
        }, None
    # ----------------------------------------------------
    # PRIVÁTNÍ METODY
    # ----------------------------------------------------

    async def _geocode_city(self, city: str):
        """Převádí název města na lat/lon a vrátí korektní název."""
        # Použity Open-Meteo Geocoding
        GEO_URL = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=cs&format=json"
        print(f"Geocoding city: {city}")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(GEO_URL) as response:
                    data = await response.json()
                    print(f"Geocoding data: {data}")

                    if not data or 'results' not in data or not data['results']:
                        print("No results")
                        return None

                    result = data['results'][0]
                    lat = result.get('latitude')
                    lon = result.get('longitude')
                    name = result.get('name')
                    print(f"Lat: {lat}, Lon: {lon}, Name: {name}")
                    return lat, lon, name

            except aiohttp.ClientError as e:
                print(f"Chyba Geokódování: {e}")
                return None

    async def _fetch_historical_weather_open_meteo(self, lat: float, lon: float) -> dict | None:
        """
        Získá maximální denní teplotu ze stejného data před 5 lety
        pomocí Open-Meteo Archive API (ERA5 Reanalysis).
        """
        try:
            # Určení data: před 1 rokem
            today = datetime.now()
            date_x_years_ago = today.date() - timedelta(days=365)

            # API endpoint pro historická data (Reanalysis)
            url = (
                f"https://archive-api.open-meteo.com/v1/era5?"
                f"latitude={lat}&longitude={lon}&start_date={date_x_years_ago}&end_date={date_x_years_ago}"
                f"&daily=temperature_2m_max&timezone=auto"
            )

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    # Kontrola HTTP statusu
                    response.raise_for_status()
                    data = await response.json()

            # Zpracování dat z Open-Meteo
            if data.get('daily', {}).get('time'):
                max_temp = data['daily']['temperature_2m_max'][0]
                return {
                    "date": date_x_years_ago.strftime("%Y-%m-%d"),
                    "max_temp": max_temp
                }

            return None
        except Exception as e:
            print(f"Chyba při stahování historických dat z Open-Meteo: {e}")
            return None

    async def _fetch_current_weather(self, lat: float, lon: float):
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=precipitation,temperature,weathercode"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()  # Tady se definuje to 'data'

                    cw = data.get("current", {})
                    return {
                        "temperature": cw.get("temperature"),
                        # Přidáno, výchozí 0.0 pokud není
                        "precipitation": cw.get("precipitation", 0.0),
                        # Důležité pro monitoring!
                        "weather_code": cw.get("weathercode"),
                        "description": self._get_weather_description(cw.get("weathercode", 0))
                    }
        except Exception as e:
            print(f"Chyba při fetchování aktuálního počasí: {e}")
            return None

    def _get_weather_description(self, code: int) -> str:
        """Převádí WMO kód na čitelný popis (zjednodušená verze)."""
        if code in [0, 1]:
            return "Jasno ☀️"
        if code in [2, 3]:
            return "Polojasno / Zataženo ☁️"
        if code in [51, 53, 55]:
            return "Mrholení 🌧️"
        if code in [61, 63, 65]:
            return "Déšť 🌧️"
        if code in [71, 73, 75]:
            return "Sněžení ❄️"
        if code in [80, 81, 82]:
            return "Přeháňky ⛈️"
        return "Neznámý jev ❓"
