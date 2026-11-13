# RallyScope — Week 7 Functional Prototype

**Interactive Badminton Performance & Rivalry Analytics**  
NYU Information Visualization • Plotly Dash + Pandas • NYU-inspired purple palette

## Browser version

The `docs/` folder contains a GitHub Pages version of the same three-view dashboard. It runs in a browser without a Python server, reads the full CSV directly from the [credited source repository](https://github.com/SahilMotyar/bwf-match-data), and applies the same score-validity rules. The site supports year, discipline, and tier filters; hover details; and chart selections that update the other views. A network connection is required to load the source CSV. The Python Dash app below remains the local version used for development and in-class demonstration.

## What this prototype implements

The app loads the **full proposed BWF match dataset** after you run the download step, validates recorded score sequences, and displays three separate research views from the Week 5 proposal:

1. **Comeback Leaders (RQ1):** horizontal bars of comeback success rates after losing Game 1 (minimum 10 qualifying opportunities in the overview).
2. **Singles vs. Doubles Competitiveness (RQ2):** deciding-third-game rate for MS, WS, MD, WD, and XD; tooltips include game-point margins.
3. **Competitive Rivalries (RQ3):** bubble chart of rivalry parity vs. number of meetings, minimum 6 meetings; marker size represents the count of three-game meetings.

**Interactions:** Year, discipline, and tournament-tier filters affect all figures. Clicking a bar or bubble in *any* chart filters the same underlying match rows and updates all three charts. A button clears the selection. Tooltips show underlying counts. When a narrow selection has fewer than ten comeback opportunities, the app labels those contextual rates as exploratory instead of presenting them as established leaderboard rankings.

The code uses real source rows only. It **does not contain hardcoded or fake dashboard results**. Unit tests have fabricated mini-fixtures, isolated from the application.

## 1. Installation (macOS/Linux/Windows)

Use Python 3.10 or newer. In Terminal / PowerShell, open this project folder.

```bash
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If you already have a Python environment, you may omit the virtual environment commands.

## 2. Download the **full** dataset

```bash
python download_data.py
```

This saves `data/matches.csv` locally, **not a 10-row subset**. A manual download is also possible from:

https://github.com/SahilMotyar/bwf-match-data/blob/main/matches.csv

Click *Raw* / *Download raw file*, save it as `data/matches.csv`. The repository describes 105,147 source match records across all five disciplines. The analytics clean invalid/ambiguous completed-game scores; the loaded source count and excluded count are displayed on-screen and in the audit file.

**Important:** The dataset is licensed/attributed as described by the source repository. Match results belong to BWF; do not present RallyScope as an official BWF product.

## 3. Run the data audit and dashboard

```bash
python data_audit.py
python app.py
```

Open **http://127.0.0.1:8050** in your browser.

The audit creates `data_quality_report.json`, documenting total source rows, kept score-valid matches, excluded rows, years, disciplines, and tournaments. All source data is considered, but only valid two/three-game complete matches are used in these metrics. Blank, retired, defaulted, or inconsistent score records are excluded rather than guessed.

## 4. Confirm the Week 7 interactive demo

Test this with the **downloaded real dataset**:

1. Check that all three figures render and the source-row count is visible.
2. Hover over a comeback bar: confirm percentage, opportunities, and wins.
3. Click a comeback bar: the singles/doubles and rivalry charts should change; clear the selection.
4. Click a discipline bar (e.g. MD): the other charts should change; clear the selection.
5. Click a rivalry bubble: the other two figures should reflect that rivalry; clear the selection.
6. Narrow the year filter and select a tournament tier: all charts should respond.
7. Use **Clear chart selection** to return to the full filter context.

If a filter has too few qualifying head-to-head matches, the rivalries panel may display a plain-language empty-data message. That is preferable to inventing a result.

### Screenshots required for submission

Capture **two real screenshots after the dashboard is running**, saved in `screenshots/`:

- `01_full_dashboard.png`: all three views and the filter bar, showing the full selected real dataset.
- `02_linked_filtering.png`: after clicking one chart's mark, clearly showing updated values in the other charts and the selection status text.

Do not submit the included conceptual Week 5 wireframe as a prototype screenshot.

## 5. In-class peer feedback

The rubric requires an actual live demo and a short feedback log (≤½ page). Fill out `PEER_FEEDBACK_LOG.md` **after** the session. Do not make up peers or feedback.

## 6. Verify data code

```bash
python -m unittest discover -s tests -v
```

These test correctness of score parsing, comeback outcomes, aggregations, and cross-filtering on a **synthetic test fixture only**. The app itself needs a full CSV download. The results should not be copied into your submission as if they came from professional badminton matches.

## Source, adapted work, and AI assistance

- **Dataset**: Sahil Motyar, [BWF Badminton Match Results (2007–2026)](https://github.com/SahilMotyar/bwf-match-data); underlying results from the Badminton World Federation. The project is not affiliated with BWF.
- **Frameworks**: [Plotly Dash](https://dash.plotly.com/) and [Plotly Python](https://plotly.com/python/), with documented APIs used for graph event data, callbacks, and chart creation.
- **AI assistance**: ChatGPT helped draft and refine Python/Dash code, tests, and documentation. Review and understand all code before submission; your course requires you to be able to explain it.
- **Design ownership**: The selected research questions and Balanced Overview structure were chosen during the earlier course proposal process.

## Files

`app.py` — interactive dashboard and callback wiring  
`data_pipeline.py` — cleaning, field derivations, and analytics  
`download_data.py` — full dataset retrieval  
`data_audit.py` — report on data loading and cleaning  
`assets/style.css` — accessible, NYU-inspired styling  
`tests/test_data_pipeline.py` — reproducible unit tests  
`PEER_FEEDBACK_LOG.md` — half-page feedback form (fill only after session)  
`WEEK7_SUBMISSION_CHECKLIST.md` — rubric-specific final checks

## Known limitations and planned Week 8 improvements

This milestone prioritizes a **functional prototype**, not finished polish. Future work may include stronger color-vision and grayscale testing, refined small-sample confidence annotations, broader hover tooltips, performance optimizations, and structured usability testing with two peers × three tasks. The current basic linking uses one active selection at a time; multi-selection brushing and transitions can follow later.
