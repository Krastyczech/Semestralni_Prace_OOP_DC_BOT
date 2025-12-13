# tests/test_clients.py

import pytest
import asyncio
from unittest.mock import MagicMock, patch

# Důležité: Import vašich tříd
from api_clients.air_quality_client import AirQualityClient
from api_clients.weather_client import WeatherClient

# Je nutné pro asynchronní testy v Pytestu
pytest_plugins = ('pytest_asyncio',)

# --- A) SYNCHRONNÍ TESTY (Logika AQI statusu) ---


def test_aqi_status_vyborna():
    """Testuje, zda AQI 45 správně odpovídá 'Dobrá'."""
    client = AirQualityClient()
    status, color = client.get_aqi_status(45)
    # Změna: Očekáváme VÁŠ text: "Dobrá" (AQI 45 spadá do <= 50)
    assert status == "Dobrá"
    assert color == "#00ff00"  # Ověříme i barvu podle Vašeho kódu


def test_aqi_status_spatna():
    """Testuje, zda AQI 180 správně odpovídá 'Nevhodná'."""
    client = AirQualityClient()
    status, color = client.get_aqi_status(180)
    # Změna: Očekáváme VÁŠ text: "Nevhodná" (AQI 180 spadá do <= 200)
    assert status == "Nevhodná"
    assert color == "#ff0000"  # Ověříme i barvu podle Vašeho kódu

# --- B) ASYNCHRONNÍ TEST S MOCKINGEM (Simulace Úspěšného API Toku) ---


# 1. Definice simulovaných (fejkových) dat pro všechny volané interní metody
MOCK_GEOCODE_SUCCESS = (50.08, 14.43, "MockMěsto")  # lat, lon, validated_name
MOCK_CURRENT_DATA_SUCCESS = {"temperature": 12.5,
                             "precipitation": 0.0, "description": "Polojasno ☁️"}
# Fejkové historické srovnání
MOCK_HISTORICAL_DATA_SUCCESS = {"date": "2020-12-13", "max_temp": 15.0}


@pytest.mark.asyncio
# Patchování interních metod klienta s nastavenými návratovými hodnotami (Mocking)
@patch('api_clients.weather_client.WeatherClient._fetch_historical_weather', return_value=MOCK_HISTORICAL_DATA_SUCCESS)
@patch('api_clients.weather_client.WeatherClient._fetch_current_weather', return_value=MOCK_CURRENT_DATA_SUCCESS)
@patch('api_clients.weather_client.WeatherClient._geocode_city', return_value=MOCK_GEOCODE_SUCCESS)
async def test_full_weather_data_success(mock_geocode, mock_current, mock_historical):
    """
    Testuje kompletní metodu get_weather_data() simulací úspěchu všech API volání.
    Tím prokážeme, že logika třídy funguje správně.
    """
    client = WeatherClient()

    # Voláme hlavní metodu, která volá mockované (simulované) sub-metody.
    result, error = await client.get_weather_data("Praha")

    # 1. Ověření, že nedošlo k chybě API/geokódování
    assert error is None
    assert result is not None

    # 2. Ověření, že se data správně poskládala do finálního slovníku
    assert result['city_name'] == "MockMěsto"
    assert result['current']['temperature'] == 12.5
    assert result['historical']['max_temp'] == 15.0

    # 3. Ověření, že byly skutečně volány interní metody
    mock_geocode.assert_called_once()
    mock_current.assert_called_once()
    mock_historical.assert_called_once()


@pytest.mark.asyncio
@patch('api_clients.weather_client.WeatherClient._geocode_city', return_value=None)
async def test_full_weather_data_geocode_failure(mock_geocode):
    """Testuje, zda kód správně ošetří selhání geokódování (město nenalezeno)."""
    client = WeatherClient()

    # Při selhání geokódování by se měl vrátit result=None a chybová zpráva
    result, error = await client.get_weather_data("NeznaméMěsto")

    # Ověření chybového stavu
    assert result is None
    assert "Město 'Neznaméměsto' nebylo nalezeno" in error
