import aiohttp
import asyncio
from datetime import datetime, timedelta, date
# Import pro synchronní historická data (Meteostat)
from meteostat import Point, Daily
import pandas as pd


class WeatherClient:
    """
    Zapouzdřuje logiku pro komunikaci s Open-Meteo API (aktuální) a Meteostat (historické).
    Poskytuje aktuální i archivní data a zajišťuje robustní geokódování.
    """

    async def get_weather_data(self, city: str):
        """
        Získá aktuální a historická data pro dané město.
        """
        # 1. Geokódování
        result = await self._geocode_city(city)
        if result is None:
            return None, f"Chyba: Město '{city.title()}' nebylo nalezeno."

        lat, lon, validated_city_name = result

        # 2. Nastavení historického data
        today = datetime.now()
        historical_date = date(2024, 6, 15)  # Fixed date with likely data

        # 3. Asynchronní spuštění obou API/Klient volání
        current_task = self._fetch_current_weather(lat, lon)
        historical_task = asyncio.to_thread(self._fetch_historical_weather,
                                            lat, lon, historical_date)

        # Čekáme na dokončení obou úloh současně (konkurentně)
        current_data, historical_data = await asyncio.gather(current_task, historical_task)

        if current_data is None:
            return None, f"Nepodařilo se získat aktuální data o počasí pro {validated_city_name}."

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
        # Použijeme Open-Meteo Geocoding, které je spolehlivější než Nominatim
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

    # DŮLEŽITÉ: Tato funkce je SYNCHRONNÍ (chybí 'async'),
    # protože ji spouštíme přes asyncio.to_thread
    def _fetch_historical_weather(self, lat, lon, date: date):
        """Získá historickou max. denní teplotu pro dané datum z Meteostat (synchronní)."""
        print(
            f"Fetching historical weather for lat={lat}, lon={lon}, date={date}")
        try:
            point = Point(lat, lon)
            data = Daily(point, start=date, end=date).fetch()
            print(f"Data fetched, empty: {data.empty}")
            if data.empty:
                print("No historical data available")
                return None

            # data['tmax'] je Series, potřebujeme první hodnotu
            max_temp = data['tmax'].iloc[0]
            print(f"Max temp: {max_temp}")
            if pd.isna(max_temp):
                print("Max temp is NaN")
                return None

            return {
                "date": date.strftime('%Y-%m-%d'),
                "max_temp": float(max_temp)
            }
        except Exception as e:
            print(f"Chyba historického počasí (Meteostat): {e}")
            return None

    async def _fetch_current_weather(self, lat, lon):
        """Získá aktuální teplotu, srážky a počasí z Open-Meteo."""
        URL = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current=temperature_2m,precipitation,weather_code&timezone=auto"
        )
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(URL) as response:
                    data = await response.json()
                    if response.status != 200 or 'current' not in data:
                        return None

                    current = data['current']
                    weather_description = self._get_weather_description(
                        current.get('weather_code'))

                    return {
                        "temperature": current.get('temperature_2m'),
                        "precipitation": current.get('precipitation'),
                        "description": weather_description
                    }
            except aiohttp.ClientError as e:
                print(f"Chyba aktuálního počasí: {e}")
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
