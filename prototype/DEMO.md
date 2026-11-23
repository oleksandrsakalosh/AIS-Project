# Päťminútová ukážka: rezervácia tréningu

Špecifikácia **POC-BOOKING v0.1.1**, kontrakt **POC-BOOKING-API v0.1.1**. Ide o lokálny prototyp s fiktívnymi údajmi; nie o platby, notifikácie ani úplný informačný systém.

## Príprava

Postup inštalácie je v README. Pred prezentáciou zastavte server pomocou Ctrl+C, obnovte ukážkové údaje a server opäť spustite. Príkazy spúšťajte v `prototype/`:

```powershell
& .\.venv\Scripts\python.exe -m app.seed --reset-demo
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Otvorte http://127.0.0.1:8000. Heslo predpripravených účtov je `Demo123!`. Reset zruší existujúce relácie. Obnovte stránku. Termíny sa vytvárajú vzhľadom na čas resetu, pri ďalšom štarte sa samé neposúvajú.

## Scenár prezentácie

| Čas | Úkon | Očakávaný výsledok |
| --- | --- | --- |
| 0:00–0:40 | Prihláste sa ako `anna`; najprv môžete skúsiť nesprávne heslo. | Čitateľná chyba prihlásenia; po správnom hesle rozvrh a aktívne členstvo. |
| 0:40–1:30 | Pozrite Funkčný tréning: kapacita 3, voľné miesta 2. Kliknite **Rezervovať miesto**. | Potvrdenie rezervácie; voľné miesta 1; tlačidlo **Miesto je vaše** zabráni zbytočnému opakovaniu. Server chráni pravidlá aj bez tlačidla. |
| 1:30–2:00 | Otvorte **Moje rezervácie** a obnovte stránku. | Zobrazuje sa iba Annina rezervácia, nie Borisove záznamy. Dáta sú trvalé. |
| 2:00–2:40 | Zrušte rezerváciu, potom sa vráťte do rozvrhu. | Záznam zostane ako **ZRUŠENÁ**; počet voľných miest sa vráti na 2. Nová rezervácia dostane nové číslo. |
| 2:40–3:20 | Pozrite plný Kruhový tréning a sekciu **Minulé tréningy**. Odhláste sa; prihláste sa ako `dana`. | Plný a minulý tréning sa nedajú rezervovať. Dana vidí čakajúce členstvo a nemôže vytvoriť rezerváciu. |
| 3:20–4:10 | Prihláste sa ako `cyril`, otvorte **Moje rezervácie** a zrušte Zdravý chrbát. | Aj s expirovaným členstvom môže zrušiť vlastnú budúcu rezerváciu; novú vytvoriť nemôže. |
| 4:10–4:40 | Prihláste sa ako `trener`, otvorte rozvrh. | Spoločný rozvrh zobrazuje obsadenosť. Po resete odkaz **Moje tréningy** vysvetlí, že účet musí najprv prepojiť administrátor. |
| 4:40–5:00 | Ukážte úzke zobrazenie pre telefón a odhláste sa. | Obsah sa prispôsobí šírke. Odhlásenie zneplatní prístup k chráneným údajom. |

## Dôkazy mimo päťminútovej prezentácie

**INC-01 · Registrácia a profil.** Na prihlasovacej stránke vyberte **Zaregistrujte sa**. Vytvorte si fiktívny účet s jedinečným používateľským menom, zobrazovaným menom a heslom s aspoň 12 znakmi. Prejdite na prihlásenie a prihláste sa ručne. V rozvrhu sa zobrazí **Nemáte evidované členstvo** a rezervovanie nebude dostupné. Otvorte **Môj profil**, uložte nové zobrazované meno a obnovte stránku. Používateľské meno aj uložené zobrazované meno zostanú viditeľné.

**INC-02 · Účty zamestnancov.** Po inicializácii alebo resete spustite `& .\.venv\Scripts\python.exe -m app.bootstrap_admin` a zadajte fiktívne údaje prvého administrátora. Prihláste sa a v zamestnaneckom portáli vyberte **Spravovať účty**.

1. Vytvorte účet recepcie. Prihláste sa ním v druhom okne s oddelenou reláciou. Zobrazí sa rozvrh s obsadenosťou. Pri otvorení `/admin/accounts` vás aplikácia vráti na zamestnanecký portál.
2. V okne administrátora zmeňte tomuto účtu rolu na **Tréner** a uložte ju. V okne recepcie obnovte rozvrh. Aplikácia vyžiada nové prihlásenie, po ktorom sa zobrazí nová rola.
3. Deaktivujte a znovu aktivujte tento účet. Staré prihlásenie sa neobnoví. Účet s novým prihlásením opäť získa prístup.
4. Skúste deaktivovať posledného administrátora a klienta `boris` s budúcou potvrdenou rezerváciou. Obe požiadavky aplikácia odmietne a zobrazí konkrétny dôvod. [Overenie INC-02](reports/validation-inc-02.md)

**INC-03 · Katalóg centra.** Prihláste sa ako administrátor a vyberte **Spravovať katalóg**.

1. V časti **Športové priestory** vytvorte miestnosť **Ukážková sála**, premenujte ju a deaktivujte. Obnovte zoznam a skontrolujte stav **Neaktívna položka**. Rovnaký postup môžete vyskúšať aj pri aktivitách a tréneroch.
2. V časti **Tréneri** otvorte pri Marekovi Novákovi **Prepojenie účtu** a vyberte `trener`. Na čerstvých ukážkových dátach jeho budúce tréningy zabránia zrušeniu prepojenia aj deaktivácii položky. V časti **Účty** skúste deaktivovať `trener` alebo mu zmeniť rolu na recepciu. Aplikácia obe zmeny odmietne.
3. V časti **Aktivity** premenujte **Funkčný tréning**. V oddelenom okne sa prihláste ako `boris` a skontrolujte nový názov v **Rozvrhu** aj v **Mojich rezerváciách**. Číslo rezervácie zostane rovnaké. Tlačidlo **Katalóg** sa klientovi nezobrazí. [Overenie INC-03](reports/validation-inc-03.md)

**INC-04 · Rozvrh trénera.** Podľa INC-03 prepojte účet `trener` s Marekom Novákom.

1. Prihláste sa ako `trener` a otvorte **Moje tréningy → Pridať tréning**. Vyberte existujúcu aktivitu a sálu, zadajte termín v Bratislave šesť dní po resete a kapacitu 2. Uložte tréning. Zobrazí sa aj v **Spoločnom rozvrhu**.
2. Skúste pridať ďalší tréning toho istého trénera v rovnakom čase. Aplikácia odmietne prekrytie. V oddelenom okne sa prihláste ako `anna` a nechajte nový tréning zobrazený v rozvrhu. V okne trénera posuňte jeho termín.
3. V okne klienta kliknite na **Rezervovať miesto** pri zobrazenom tréningu. Aplikácia obnoví údaje a vyžiada nové potvrdenie. Rezervujte aktualizovaný termín.
4. V okne trénera obnovte zoznam a upravte tréning. Termín, aktivita a priestor sa uzamknú. Uložte kapacitu 1 a skontrolujte plnú obsadenosť. Po zrušení rezervácie klientom sa miesto uvoľní a údaje o tréningu zostanú uzamknuté. [Overenie INC-04](reports/validation-inc-04.md)

Zachovanie dát možno overiť zastavením a opätovným spustením servera bez resetu. Súbeh posledného miesta overujú automatické testy s nezávislými požiadavkami; rýchle klikanie v jednom prehliadači ho nedokazuje.

```powershell
& .\.venv\Scripts\python.exe -m pytest -q tests
node --test tests/mutations.test.mjs tests/training-times.test.mjs
```

Node je potrebný iba na spustenie voliteľných testov JavaScriptu. Prehľad SC-P01–SC-P20 a skutočné výsledky sú v `reports/validation.md`.

Pri neistom výsledku požiadavky aplikácia automaticky neposiela ďalší POST. Najprv obnoví aktuálny stav; ak obnova zlyhá, ďalšia rezervácia zostane zablokovaná až do úspešného obnovenia. Po zrušení môže oneskorený starý POST vytvoriť novú rezerváciu — je to schválené obmedzenie prototypu.
