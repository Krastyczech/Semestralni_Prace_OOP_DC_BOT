import os
import aiohttp
from dotenv import load_dotenv

# Načtení klíčů z .env (pouze pro testování klienta)
load_dotenv()


class AirQualityClient:
    """
    Zapouzdřuje logiku pro komunikaci s WAQI API (World Air Quality Index).
    Stará se o volání API, parsování JSON a vracení srozumitelných dat.
    """

    # Základní URL pro API
    BASE_URL = "https://api.waqi.info/feed/"

    def __init__(self):
        """Inicializace klienta s API tokenem."""
        self.api_token = os.getenv('AQI_API_TOKEN')
        if not self.api_token:
            print("CHYBA: AQI_API_TOKEN není nastaven v .env. Klient bude nefunkční.")

    # ----------------------------------------------------
    # VEŘEJNÉ METODY (Interface - rozhraní pro zbytek bota)
    # ----------------------------------------------------

    async def get_current_aqi(self, city: str = "prague") -> int | None:
        """
        Hlavní metoda: Získá aktuální AQI (Air Quality Index) pro dané město.
        Vrací AQI jako celé číslo nebo None při chybě.
        """
        # Formátování URL pro volání
        full_url = f"{self.BASE_URL}{city}/?token={self.api_token}"

        # Použití aiohttp pro asynchronní HTTP volání
        async with aiohttp.ClientSession() as session:
            try:
                # Volání API (Skrytá složitost 1)
                async with session.get(full_url) as response:

                    # Kontrola HTTP kódu (Skrytá složitost 2)
                    if response.status != 200:
                        print(
                            f"Chyba API volání pro AQI: HTTP Status {response.status}")
                        return None

                    # Parsování JSON (Skrytá složitost 3)
                    data = await response.json()

                    # Kontrola statusu v JSON (Skrytá složitost 4)
                    if data.get('status') == 'ok':
                        # Parsování AQI hodnoty (Skrytá složitost 5)
                        aqi_value = data['data'].get('aqi')

                        # Kontrola, zda je hodnota číselná
                        if aqi_value is not None and isinstance(aqi_value, int):
                            return aqi_value

                        # V případě chyby v datech
                        print(
                            f"Chyba: AQI hodnota není číselná nebo chybí: {aqi_value}")
                        return None

                    print(
                        f"Chyba: Status v JSON není 'ok': {data.get('data')}")
                    return None

            except aiohttp.ClientError as e:
                print(f"Chyba připojení při volání AQI API: {e}")
                return None
            except Exception as e:
                print(f"Neočekávaná chyba při zpracování AQI dat: {e}")
                return None

    def get_aqi_status(self, aqi: int) -> tuple[str, str]:
        """
        Vrátí status kvality ovzduší a barvu pro embed na základě AQI hodnoty.
        """
        if aqi <= 50:
            return "Dobrá", "#00ff00"
        elif aqi <= 100:
            return "Uspokojivá", "#ffff00"
        elif aqi <= 150:
            return "Nevhodná pro citlivé skupiny", "#ff8000"
        elif aqi <= 200:
            return "Nevhodná", "#ff0000"
        elif aqi <= 300:
            return "Velmi nevhodná", "#800080"
        else:
            return "Nebezpečná", "#800000"

# ----------------------------------------------------
# PŘÍKLAD TESTOVÁNÍ FUNKČNOSTI (OOP Zásada: Základní test)
# ----------------------------------------------------
# if __name__ == "__main__":
#     import asyncio
#
#     async def test_aqi():
#         client = AirQualityClient()
#         aqi = await client.get_current_aqi("prague")
#         if aqi is not None:
#             print(f"Aktuální AQI pro Prahu: {aqi}")
#         else:
#             print("Nepodařilo se získat AQI.")
#
#     asyncio.run(test_aqi())
