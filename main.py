# main.py
# TENTO IMPORT TEĎ BUDE FUNGOVAT
from api_clients.air_quality_client import AirQualityClient
import discord
from dotenv import load_dotenv
from discord.ext import commands
import sys
import os

# ZAJISTÍ, ŽE PYTHON NAJDE SLOŽKY API_CLIENTS a TASKS
# Přidá kořenový adresář projektu do cesty pro import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Načtení proměnných prostředí ze souboru .env
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Důležité: Aktivace intents pro čtení obsahu zpráv
intents = discord.Intents.default()
intents.message_content = True

# Inicializace bota a klienta jako globální proměnné (pro jednoduchost)
bot = commands.Bot(command_prefix='!', intents=intents)
aqi_client = AirQualityClient()  # Inicializace klienta


@bot.event
async def on_ready():
    """Spustí se při úspěšném připojení bota k Discordu."""
    print(f'🤖 Bot je připojen jako: {bot.user.name}')
    print('--------------------------------')


# REAKTIVNÍ ČÁST: Příkaz pro AQI
@bot.command(name='aqi')
async def aqi_command(ctx):
    """Reaktivní příkaz: Získá a zobrazí aktuální kvalitu ovzduší v Praze."""
    await ctx.send("Zjišťuji aktuální kvalitu ovzduší (AQI) pro Prahu...")

    # Používáme zapouzdřenou metodu klienta (jednoduché volání)
    aqi_value = await aqi_client.get_current_aqi("prague")

    if aqi_value is not None:
        # Příklad základní vizualizace AQI
        if aqi_value <= 50:
            status = "Dobrá (✅)"
        elif aqi_value <= 100:
            status = "Přijatelná (⚠️)"
        else:
            status = "Nebezpečná pro citlivé skupiny (❌)"

        embed = discord.Embed(
            title="💨 Kvalita Ovzduší v Praze",
            description=f"Aktuální Index Kvality Ovzduší (AQI) je: **{aqi_value}**",
            color=0x3498db
        )
        embed.add_field(name="Stav", value=status, inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send("Nepodařilo se získat data o AQI. Zkontrolujte API klíč nebo připojení.")


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
