# Local MySQL Analytics Chatbot

A beginner-friendly analytics chatbot that translates plain-English questions into **read-only MySQL queries**, then shows the result in a browser. It uses [Ollama](https://ollama.com/) to run a free model locally—no API key or paid LLM required.

## Interface visual asset

The app includes `assets/eggplant-varieties.jpg`, a locally saved photograph of multiple eggplant varieties. Credit: [J.E. Fee, “Three Types of Eggplant,” via Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Three_Types_of_Eggplant.jpg), licensed [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/).

## Your plant-growth datasets

The CSV files you shared describe plant/genotype traits. They are joined conceptually through `GenotypeName`:

| Dataset file | Measures |
| --- | --- |
| `phy_fst.csv` | First physiological measurement: canopy temperature, SPAD, MSI, RWC, wax |
| `Phy_snd.csv` | Second physiological measurement: canopy temperature, SPAD, MSI, RWC, wax |
| `Root_fst.csv` | First root measurement: root length, lateral roots, root-to-shoot ratio |
| `Root_scd.csv` | Second root measurement: root length, lateral roots, root-to-shoot ratio |
| `plant_morpho.csv` | Categorical plant morphology and fruit traits |

The chatbot discovers the table and column names directly from MySQL. Ensure the MySQL table names and columns reflect the data you imported. If your tables have different names from the CSV files, that is fine—the displayed schema in the app is the source of truth.

## Questions you can ask

- `Show the first 20 rows from Root_fst`
- `What is the average RootLength in Root_fst?`
- `Compare average SPAD in phy_fst and Phy_snd`
- `Show all traits for GenotypeName 101`
- `Which genotypes have the largest R_S_Ratio in Root_scd?`
- `Count plants by FruitShape`
- `What is the average RootLength grouped by FruitShape?`
- `Join Root_fst and phy_fst on GenotypeName and show RootLength and SPAD`
- `For each FruitShape, show average RootLength and order it from highest to lowest`

The model receives table and column names, not your database credentials. The app only accepts one `SELECT` query and adds a 200-row cap. Create a MySQL account with **SELECT-only** access as the final safety layer.

Ask **one question per message**. For example, send `Show the first 10 rows from Root_fst`, wait for the result, then send `What is the average RootLength in Root_fst?`.

Use plain-English questions in the chat box, not SQL. For example, write `Show the first 10 rows from phy_fst` rather than `SELECT TOP 10 ...`. `TOP` is SQL Server syntax; MySQL uses `LIMIT`, and the app generates that safely for you.

## Charts, joins, and aggregates

Results containing a category (for example `FruitShape` or `GenotypeName`) and a numeric measure automatically show a chart. Choose the X-axis, measure, and bar/line type in **Graphical representation**. Single-row aggregate results show as metric cards.

The LLM prompt follows the **ART framework: Action, Role, Task**. It directs the model to use MySQL syntax, explicit `INNER JOIN`s, the shared `GenotypeName` key where relevant, and normal SQL aggregates such as `AVG`, `COUNT`, `MIN`, `MAX`, and `GROUP BY`.

Example join generated for a question about root length and SPAD:

```sql
SELECT rf.GenotypeName, rf.RootLength, pf.SPAD
FROM Root_fst AS rf
INNER JOIN phy_fst AS pf ON rf.GenotypeName = pf.GenotypeName
ORDER BY rf.GenotypeName
LIMIT 200;
```

## Voice input (free and local)

Use **Ask by voice** below the chat box and record an English question. As soon as recording finishes, the app transcribes it automatically, runs the question, and clears the recording so it is ready for the next one. The app uses the free, local `faster-whisper` speech-to-text model; it does not require an API key. The small `tiny.en` model downloads automatically the first time you transcribe a recording (about 75 MB). For more accurate transcription, set `WHISPER_MODEL=base.en` in `.env`; it is slower and larger.

After adding this feature, install the new dependency once:

```bash
python -m pip install -r requirements.txt
```

## Setup in VS Code

### 1. Install prerequisites

Install Python 3.11+ and MySQL. Install [Ollama](https://ollama.com/download), then in the VS Code terminal run:

```bash
ollama pull qwen2.5:3b
```

`qwen2.5:3b` is a good small starting model. On a more capable computer, `qwen2.5:7b` generally produces more reliable SQL.

### 2. Create a read-only MySQL user

In MySQL (replace `your_database` and choose a strong password):

```sql
CREATE USER 'analytics_reader'@'localhost' IDENTIFIED BY 'choose_a_strong_password';
GRANT SELECT ON your_database.* TO 'analytics_reader'@'localhost';
FLUSH PRIVILEGES;
```

### 3. Configure and install

In the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\Activate.ps1     # Windows PowerShell
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and enter your MySQL host, database name, username, and password. Do not commit `.env`.

### 4. Run

```bash
streamlit run app.py
```

Open the URL displayed in the terminal (usually `http://localhost:8501`).

## How it works

```text
Your question → Ollama local model → MySQL SELECT SQL → safety validation → MySQL → table in browser
```

## Suggested next milestones

1. Test the starter with two or three known questions and verify each displayed SQL query.
2. Add friendly descriptions such as "first" and "second" measurement stage if those terms have a precise experimental meaning.
3. Add conversation history and query logging once the basic queries are reliable.

## Important limitations

Small local models occasionally choose a wrong column or join. Always review the expandable SQL during early testing. This is an analytics assistant, not a replacement for database permissions: keep the MySQL account SELECT-only.
