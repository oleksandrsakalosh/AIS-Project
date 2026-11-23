# Päťminútová ukážka: rezervácia tréningu

Špecifikácia **POC-BOOKING v0.1.1**, kontrakt **POC-BOOKING-API v0.1.1**. Ide o lokálny prototyp s fiktívnymi údajmi; nie o platby, notifikácie ani úplný informačný systém.

## Príprava

Postup inštalácie je v README. Pred prezentáciou zastavte server pomocou Ctrl+C, obnovte ukážkové údaje a server opäť spustite. Príkazy spúšťajte v `prototype/`:

```powershell
& .\.venv\Scripts\python.exe -m app.seed --reset-demo
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Otvorte http://127.0.0.1:8000. Heslo všetkých účtov je `Demo123!`. Reset zruší existujúce relácie; stránku obnovte. Termíny sa vytvárajú vzhľadom na čas resetu, pri ďalšom štarte sa samé neposúvajú.

## Scenár prezentácie

| Čas | Úkon | Očakávaný výsledok |
| --- | --- | --- |
| 0:00–0:40 | Prihláste sa ako `anna`; najprv môžete skúsiť nesprávne heslo. | Čitateľná chyba prihlásenia; po správnom hesle rozvrh a aktívne členstvo. |
| 0:40–1:30 | Pozrite Funkčný tréning: kapacita 3, voľné miesta 2. Kliknite **Rezervovať miesto**. | Potvrdenie rezervácie; voľné miesta 1; tlačidlo **Miesto je vaše** zabráni zbytočnému opakovaniu. Server chráni pravidlá aj bez tlačidla. |
| 1:30–2:00 | Otvorte **Moje rezervácie** a obnovte stránku. | Zobrazuje sa iba Annina rezervácia, nie Borisove záznamy. Dáta sú trvalé. |
| 2:00–2:40 | Zrušte rezerváciu, potom sa vráťte do rozvrhu. | Záznam zostane ako **ZRUŠENÁ**; počet voľných miest sa vráti na 2. Nová rezervácia dostane nové číslo. |
| 2:40–3:20 | Pozrite plný Kruhový tréning a sekciu **Minulé tréningy**. Odhláste sa; prihláste sa ako `dana`. | Plný a minulý tréning sa nedajú rezervovať. Dana vidí čakajúce členstvo a nemôže vytvoriť rezerváciu. |
| 3:20–4:10 | Prihláste sa ako `cyril`, otvorte **Moje rezervácie** a zrušte Zdravý chrbát. | Aj s expirovaným členstvom môže zrušiť vlastnú budúcu rezerváciu; novú vytvoriť nemôže. |
| 4:10–4:40 | Prihláste sa ako `trener`, otvorte rozvrh. | Rozvrh je iba na čítanie. Bez členstiev, vlastných rezervácií, účastníkov a správy tréningov. |
| 4:40–5:00 | Ukážte úzke zobrazenie pre telefón a odhláste sa. | Obsah sa prispôsobí šírke. Odhlásenie zneplatní prístup k chráneným údajom. |

## Dôkazy mimo päťminútovej prezentácie

**INC-01 · Registrácia a profil.** Na prihlasovacej stránke vyberte **Zaregistrujte sa**. Vytvorte si fiktívny účet s jedinečným používateľským menom, zobrazovaným menom a heslom s aspoň 12 znakmi. Prejdite na prihlásenie a prihláste sa ručne. V rozvrhu sa zobrazí **Nemáte evidované členstvo** a rezervovanie nebude dostupné. Otvorte **Môj profil**, uložte nové zobrazované meno a obnovte stránku. Používateľské meno aj uložené zobrazované meno zostanú viditeľné.

Zachovanie dát možno overiť zastavením a opätovným spustením servera bez resetu. Súbeh posledného miesta overujú automatické testy s nezávislými požiadavkami; rýchle klikanie v jednom prehliadači ho nedokazuje.

```powershell
& .\.venv\Scripts\python.exe -m pytest -q
node --test tests/mutations.test.mjs
```

Node je voliteľný iba pre tri JavaScript testy, aplikácia ho nepotrebuje. Prehľad SC-P01–SC-P20 a skutočné výsledky sú v `reports/validation.md`.

Pri neistom výsledku požiadavky aplikácia automaticky neposiela ďalší POST. Najprv obnoví aktuálny stav; ak obnova zlyhá, ďalšia rezervácia zostane zablokovaná až do úspešného obnovenia. Po zrušení môže oneskorený starý POST vytvoriť novú rezerváciu — je to schválené obmedzenie prototypu.
