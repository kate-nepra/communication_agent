# Manuál

Aplikace byla vyvíjena v jazyce Python `3.10` a je kompatibilní i s verzí `3.9`. Pro správné fungování projektu je nutné
nainstalovat všechny potřebné balíčky, to lze díky souboru `requirements.txt` provést jednoduše
příkazem `pip install -r requirements.txt`.

Zároveň je potřebný lokálně běžící MySQL server pro znalostní databázi zdrojů informací. Pokyny pro stažení a instalaci
jsou dostupné na [oficiálních stránkách MySQL](https://dev.mysql.com/downloads/mysql/). Pro lokální spuštění Weaviate
vektorové databáze je nutné mít nainstalovaný [Docker](https://www.docker.com/).

Tato aplikace je závislá na připojení k serveru s velkým jazykovým modelem, proto je nutné v konfiguracích správně
nastavit url adresu k serveru a API klíč, je-li pro model potřeba. Zároveň je nutné poskytnout API klíče pro LlamaCloud
a Cohere re-ranker.

Pro nastavení choulostivých údajů, jako jsou API klíče a přístup k databázi, je v projektu používán `.env` soubor, který
je potřeba vytvořit dle přiloženého `env.example`, který obsahuje:

```dotenv
LLAMA_CLOUD_API_KEY="<llx-key>"
OPENAI_API_KEY="<sk-key>"
LLAMA_API_KEY="<LL-key>"
LOCAL_API_KEY="local"
COHERE_APIKEY="<cohere-key>

DB_HOST=<host>
DB_USER=<user>
DB_PASSWORD=<password>
DATABASE=<db_name>
```

Dalším nastavením, které je potřeba provést, je obsah souboru `cfq/config.ini`. Mimo jiné jsou v tomto souboru nastaveny
cesty k složkám s PDF a souborům s daty pro inicializaci sběru dat, a právě zde jsou definované i url k API:

```ini
[API_INFOS]
LLAMA_URL = https://api.llama-api.com
OPENAI_URL = https://api.openai.com/v1
LOCAL_URL = http://localhost:8801/v1/
```

## Sběr dat

Prvním krokem je vytvoření SQL databáze, to lze provést příkazem:

```bash
python src/data_acquisition/sources_store/sources_db.py
```

Zároveň je potřeba mít spuštěnou vektorovou databázi:

```bash
docker-compose up -d
```

Prvotní zahájení sběru lze docílit instrukcí:

```bash
python src/data_acquisition/data_acquisition_manager.py
```

Následně je potřeba zahájit CRON operace, k čemuž je soubor `cron_files/cron_setup.sh`. Spustit ho lze např. takto:

```bash
bash cron_files/cron_setup.sh
```

## Webová aplikace

Není-li tak, je nutné spustit vektorovou databázi:

```bash
docker-compose up -d
```

Dialogovou aplikaci lze pak spustit následovně:

```bash
streamlit run src/app/production.py
```

Tím se v okně prohlížeče spustí dialogová aplikace, se kterou lze konverzovat. Možnosti spuštění a nastavení aplikace
jsou také popsány v přiloženém souboru `README.md`.
