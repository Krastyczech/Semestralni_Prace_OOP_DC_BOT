# main.py - ČISTÁ VERZE

import json
import os
from discord.ext import commands
from discord.ext import tasks
from dotenv import load_dotenv
import discord
import asyncio

# LOKÁLNÍ IMPORT - TENTO UŽ TEĎ BUDE FUNGOVAT
from api_clients.air_quality_client import AirQualityClient
from api_clients.weather_client import WeatherClient

MONITORED_CITIES_FILE = "monitored_cities.json"

# WMO kódy pro nebezpečné počasí
SEVERE_CODES = {
    95: "Bouřka (mírná) ⛈️",
    96: "Bouřka se krupobitím ⛈️",
    99: "Silná bouřka s krupobitím ⛈️",
    65: "Silný déšť 🌧️",
    82: "Extrémní přeháňky 🌧️"
}


def load_cities():
    if os.path.exists(MONITORED_CITIES_FILE):
        with open(MONITORED_CITIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return ["Praha"]


monitored_cities = load_cities()


def save_cities():
    with open(MONITORED_CITIES_FILE, "w", encoding="utf-8") as f:
        json.dump(monitored_cities, f, ensure_ascii=False, indent=4)


# Načtení proměnných prostředí ze souboru .env
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Aktivace intents pro čtení obsahu zpráv
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Inicializace bota a klienta
aqi_client = AirQualityClient()  # Inicializace klienta (Zapouzdření API)
weather_client = WeatherClient()  # Inicializace klienta (Zapouzdření API)

last_alerts = {}  # Ukládá poslední alerty pro města


@tasks.loop(minutes=30)
async def weather_monitor_task():
    for city in monitored_cities:
        data, _ = await weather_client.get_weather_data(city)
        if not data:
            continue

        current = data['current']
        w_code = current.get('weather_code')

        # --- LOGIKA PROTI OPAKOVANÝM ALERTŮM ---
        # Pokud je aktuální kód stejný jako ten, co jsme nahlásili minule, město přeskočíme
        if last_alerts.get(city) == w_code:
            continue

        last_alerts[city] = w_code  # Aktualizujeme poslední alert

        # Pokud je zjištěno nebezpečné počasí
        if w_code in SEVERE_CODES:
            # Najdeme kanál 'alert' na všech serverech, kde bot je
            for guild in bot.guilds:
                channel = discord.utils.get(guild.text_channels, name="alert")
                if channel:
                    alert_msg = SEVERE_CODES[w_code]
                    await channel.send(f"🚨 **VAROVÁNÍ - {city}**: {alert_msg} ({current['temperature']}°C)")

        await asyncio.sleep(2)  # Šetříme API mezi jednotlivými městy


@bot.event
async def on_ready():
    # Spustí se při úspěšném připojení bota k Discordu.
    print(f'🤖 Bot je připojen jako: {bot.user.name}')


@bot.event
async def on_ready():
    print(f'🤖 {bot.user.name} je připojen a monitoruje počasí.')
    if not weather_monitor_task.is_running():
        weather_monitor_task.start()
# REAKTIVNÍ ČÁST: Příkaz pro komplexní Počasí (Standardizovaný název funkce)


@bot.command()
async def pocasi(ctx, *, city: str):
    """Reaktivní příkaz: Získá a zobrazí aktuální a historické počasí + AQI."""

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
    # Předpoklad: AQI je pro celé město (Praha, Brno atd.)
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


@bot.command(name="add")  # pridani mesta do monitoringu
async def add_city(ctx, *, city: str):
    city = city.strip().title()
    if city not in monitored_cities:
        monitored_cities.append(city)
        save_cities()
        await ctx.send(f"✅ Město **{city}** přidáno do monitoringu.")
    else:
        await ctx.send(f"Město {city} už v seznamu je.")


@bot.command(name="remove")  # odebrani mesta z monitoringu
async def remove_city(ctx, *, city: str):
    city = city.strip().title()
    if city in monitored_cities:
        monitored_cities.remove(city)
        save_cities()
        await ctx.send(f"🗑️ Město **{city}** odebráno.")
    else:
        await ctx.send(f"Město {city} v seznamu není.")


@bot.command(name="list")  # vypsani sledovanych mest
async def list_cities(ctx):
    cities_str = "\n".join(
        [f"• {c}" for c in monitored_cities]) or "Seznam je prázdný."
    await ctx.send(f"**Sledovaná města:**\n{cities_str}")

# REAKTIVNÍ ČÁST: Původní příkaz pro AQI


@bot.command()
async def aqi(ctx, *, city: str):
    """Původní příkaz, který by měl být nyní přesměrován na !pocasi."""
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
