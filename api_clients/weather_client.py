import aiohttp
import asyncio
from datetime import datetime, timedelta, date
# Import pro synchronní historická data (Meteostat)


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

        # 2. Asynchronní příprava úloh
        current_task = self._fetch_current_weather(lat, lon)
        # Nové: Voláme asynchronní Open-Meteo Archive API
        historical_task = self._fetch_historical_weather_open_meteo(lat, lon)

        # Předpokládáme, že AQI klient je inicializován v main.py a volán ZDE.
        # ALE: Pokud AQI data získáváte v main.py (viz Váš původní kód),
        # MUSÍME PŘEDAT AQI ZPĚT DO MAIN.PY.
        # Pro zjednodušení teď budeme počítat s tím, že AQI se získá v main.py,
        # tak jako v původní verzi, a zde se soustředíme jen na počasí.

        try:
            # 3. Spuštění obou úloh současně (konkurentně)
            # Tímto se zbavíme asyncio.to_thread!
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
