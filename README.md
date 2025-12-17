# Discord Weather Bot (Semestrální práce OOP)

Tento projekt je Discord bot zaměřený na poskytování informací o počasí a automatický monitoring nebezpečných meteorologických jevů. Aplikace je napsána v jazyce Python s důrazem na asynchronní programování a objektově orientovaný přístup.

## Hlavní funkce
* **Aktuální počasí:** Zobrazuje aktuální teplotu a slovní popis počasí pro libovolné město pomocí Open-Meteo API.
* **Historické srovnání:** Bot automaticky vyhledá a zobrazí maximální teplotu v daném městě přesně před **jedním rokem** pro srovnání s aktuálním stavem.
* **Proaktivní monitoring:** Automatická kontrola počasí ve městech ze seznamu každých 30 minut.
* **Inteligentní Alert systém:** Bot zasílá varování do kanálu `#alert` při zjištění nebezpečí (bouřky, silný déšť). Obsahuje ochranu proti spamu (nehlásí stejný jev opakovaně).
* **Persistence dat:** Seznam sledovaných měst se ukládá do souboru `monitored_cities.json`, díky čemuž bot neztratí data ani po restartu.

## Technické řešení
* **Asynchronní operace:** Využití knihoven `asyncio` a `aiohttp` pro paralelní dotazy na API (geokódování, aktuální data a historická data běží současně pomocí `asyncio.gather`).
* **Discord.ext.tasks:** Využití plánovaných úloh pro běh monitoringu na pozadí bez blokování hlavního vlákna bota.
* **Mocking & Testing:** Projekt obsahuje sadu testů v `pytest`, které simulují (mockují) API odpovědi i Discord kanály pro ověření logiky bez nutnosti reálného síťového připojení.

## Instalace a spuštění

1. **Klonování repozitáře:**
   ```bash
   git clone [https://github.com/Krastyczech/Semestralni_Prace_OOP_DC_BOT.git](https://github.com/Krastyczech/Semestralni_Prace_OOP_DC_BOT.git)
   cd Semestralni_Prace_OOP_DC_BOT

2. **Instalace potřebných knihoven:**
    ```bash
    pip install -r requirements.txt

3. **Nastavení:**
   * Do souboru `main.py` vložte svůj Discord Token (proměnná `TOKEN`).
   * Na svém Discord serveru vytvořte textový kanál s názvem `alert`.

4. **Spuštění**
    ```bash
    python main.py

**Používané příkazy**

!pocasi <město> – Detailní info o počasí (aktuální stav + srovnání s loňským rokem).

!add <město> – Přidá město do seznamu pro automatický monitoring nebezpečných jevů.

!remove <město> – Odebere město ze seznamu sledovaných míst.

!list – Zobrazí seznam všech aktuálně monitorovaných měst.



**Autor**

Jméno: Krastyczech

Předmět: Objektově orientované programování (OOP) 