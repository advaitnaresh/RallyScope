"""Print/write transparent data-cleaning notes for the Week 7 prototype."""
from pathlib import Path
import json
from data_pipeline import load_matches

root = Path(__file__).resolve().parent
rows, report = load_matches(root / 'data' / 'matches.csv')
(root / 'data_quality_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
print('\nMatches per discipline:')
print(rows.groupby('discipline').size().to_string())
print('\nDerived numeric columns:')
print('year, deciding_game, comeback, avg_game_margin, rivalry parity (computed per pair)')
