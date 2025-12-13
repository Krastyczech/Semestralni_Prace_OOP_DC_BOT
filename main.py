# main.py - ČISTÁ VERZE

import os
from discord.ext import commands
from dotenv import load_dotenv
import discord

# LOKÁLNÍ IMPORT - TENTO UŽ TEĎ BUDE FUNGOVAT
from api_clients.air_quality_client import AirQualityClient
from api_clients.weather_client import WeatherClient


# Načtení proměnných prostředí ze souboru .env
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
# Ostatní nastavení z .env, pokud je potřebujeme hned:
# AQI_CLIENT_TOKEN je načten v AirQualityClient.py
# AQI_THRESHOLD = int(os.getenv('AQI_THRESHOLD'))


# Důležité: Aktivace intents pro čtení obsahu zpráv
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Inicializace bota a klienta
aqi_client = AirQualityClient()  # Inicializace klienta (Zapouzdření API)
weather_client = WeatherClient()  # Inicializace klienta (Zapouzdření API)


@bot.event
async def on_ready():
    # Spustí se při úspěšném připojení bota k Discordu.
    print(f'🤖 Bot je připojen jako: {bot.user.name}')

# REAKTIVNÍ ČÁST: Příkaz pro komplexní Počasí (Standardizovaný název funkce)


@bot.command()
async def pocasi(ctx, *, city: str):
    """Reaktivní příkaz: Získá a zobrazí aktuální a historické počasí + AQI."""

    # await ctx.send(f"Zpracovávám požadavek na komplexní data pro: **{city.title()}**...")

    # -------------------------------------------------------------------
    # 1. Získání Počasí (Aktuální + Historické)
    # -------------------------------------------------------------------
    weather_result, weather_error = await weather_client.get_weather_data(city)

    if weather_result is None:
        await ctx.send(f"❌ **{weather_error}** Prosím, zkontrolujte název města.")
        return

    validated_city = weather_result['city_name']
    current = weather_result['current']
    historical = weather_result['historical']

    current_temp = current['temperature']

    # -------------------------------------------------------------------
    # 2. Získání Kvality Ovzduší (AQI)
    # -------------------------------------------------------------------
    # Předpokládáme, že AQI je pro celé město (Praha, Brno atd.)
    aqi_value = await aqi_client.get_current_aqi(validated_city)

    if aqi_value is not None:
        aqi_status, color_hex = aqi_client.get_aqi_status(aqi_value)
    else:
        # Pokud AQI selže, použijeme default
        aqi_status = "Data o kvalitě vzduchu nejsou dostupná."
        color_hex = "#7f8c8d"  # Šedá

    # -------------------------------------------------------------------
    # 3. Formátování a Srovnání
    # -------------------------------------------------------------------

    # a) Historické srovnání
    historical_summary = ""
    if historical and historical['max_temp'] is not None:
        hist_temp = historical['max_temp']
        diff = current_temp - hist_temp

        diff_abs = abs(diff)
        diff_abs_formatted = f"{diff_abs:.1f}"

        if diff > 0:
            comparison = f"o **{diff_abs_formatted}°C více**"
        else:
            comparison = f"o **{diff_abs_formatted}°C méně**"

        historical_summary = (
            f", což je {comparison} než před rokem (tehdy **{hist_temp}°C**)."
        )
    else:
        historical_summary = ". Archivní data pro srovnání nejsou dostupná."

    # b) Generování finální věty
    response_sentence = (
        f"Ahoj! Dnes je v **{validated_city}** aktuální teplota **{current_temp}°C**"
        f"{historical_summary}"
    )

    # c) Generování embedu
    embed = discord.Embed(
        title=f"☀️ Aktuální Počasí a historie pro {validated_city}",
        description=response_sentence,
        color=int(color_hex.strip("#"), 16)  # Barva dle AQI
    )

    embed.add_field(name="Stav Počasí",
                    value=current['description'], inline=True)
    embed.add_field(name="Srážky (poslední hodina)",
                    value=f"{current['precipitation']} mm", inline=True)
    embed.add_field(name="Kvalita Ovzduší (AQI)",
                    value=aqi_status, inline=False)

    await ctx.send(embed=embed)


# REAKTIVNÍ ČÁST: Původní příkaz pro AQI
@bot.command()
async def aqi(ctx, *, city: str):
    """Původní příkaz, který by měl být nyní přesměrován na !pocasi."""
    # Můžete zde buď nechat původní logiku AQI, nebo:
    await ctx.send("Tento příkaz byl přesunut do !pocasi <město> pro komplexní odpověď.")

# Spuštění bota
if __name__ == "__main__":
    if DISCORD_TOKEN is None:
        print("CHYBA: Discord Token nebyl nalezen v souboru .env. Nelze spustit bota.")
    else:
        try:
            bot.run(DISCORD_TOKEN)
        except discord.errors.LoginFailure:
            print(
                "CHYBA: Neplatný Discord Token. Zkontrolujte, zda je token správně zadán v .env.")
