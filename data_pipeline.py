"""RallyScope: loading, quality checks, and research metrics.

Source: Sahil Motyar, bwf-match-data, GitHub; underlying match results © BWF.
AI-assisted code: generated with ChatGPT; review every function before submission.
"""
from __future__ import annotations

from pathlib import Path
import re
import pandas as pd
import numpy as np

REQUIRED_COLUMNS = {
    'date', 'discipline', 'tournament', 'tier', 'round', 'team1',
    'team2', 'winner', 'score',
}
DISCIPLINES = ('MS', 'WS', 'MD', 'WD', 'XD')
GAMES_RE = re.compile(r'^\d{1,2}-\d{1,2}(?: \d{1,2}-\d{1,2}){1,2}$')


def parse_score(raw: object) -> tuple[tuple[int, int], ...] | None:
    """Parse ordered games from team1's perspective; reject partial match scores.

    Examples: '21-15 17-21 21-16', '21-18, 21-17'.
    This checks plausible BWF scoring but not every rare historical exception.
    """
    if not isinstance(raw, str):
        return None
    text = re.sub(r'\s+', ' ', raw.replace(',', ' ')).strip()
    if not GAMES_RE.fullmatch(text):
        return None
    games = tuple(tuple(map(int, x.split('-'))) for x in text.split(' '))
    for a, b in games:
        if a == b or min(a, b) < 0 or max(a, b) > 30:
            return None
        # Standard 21-point rally scoring: win by two until 29-all, then 30-29.
        high, low = max(a, b), min(a, b)
        if high < 21 or (high - low < 2 and not (high == 30 and low == 29)):
            return None
    return games


def match_metrics(score: object, winner: object) -> dict | None:
    """Metrics only for matches with 2 or 3 valid completed games.

    Retirements/defaults and contradictory score/winner records are excluded.
    """
    games = parse_score(score)
    if not games or len(games) not in (2, 3):
        return None
    try:
        winner = int(winner)
    except (ValueError, TypeError):
        return None
    if winner not in (1, 2):
        return None
    wins1 = sum(a > b for a, b in games)
    wins2 = sum(b > a for a, b in games)
    if not ((winner == 1 and wins1 == 2 and wins2 <= 1) or
            (winner == 2 and wins2 == 2 and wins1 <= 1)):
        return None
    opening_loser = 1 if games[0][0] < games[0][1] else 2
    return {
        'deciding_game': len(games) == 3,
        'opening_loser': opening_loser,
        'comeback': winner == opening_loser,
        'avg_game_margin': float(np.mean([abs(a-b) for a, b in games])),
    }


def prepare_matches(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Load *all* source rows, validate attributes, and retain score-valid matches.

    Reports counts for transparency; never silently substitutes sample data.
    """
    missing = REQUIRED_COLUMNS.difference(raw.columns)
    if missing:
        raise ValueError(f'Dataset is missing required columns: {sorted(missing)}')
    df = raw.copy()
    source_rows = len(df)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['winner'] = pd.to_numeric(df['winner'], errors='coerce')
    for c in ('discipline', 'tournament', 'tier', 'round', 'team1', 'team2', 'score'):
        df[c] = df[c].astype('string').str.strip()
    df = df[df['date'].notna() & df['discipline'].isin(DISCIPLINES) &
            df['team1'].notna() & df['team2'].notna() &
            df['team1'].ne('') & df['team2'].ne('') &
            df['team1'].ne(df['team2'])].copy()
    structural_rows = len(df)
    derived = [match_metrics(s, w) for s, w in zip(df['score'], df['winner'])]
    valid = [x is not None for x in derived]
    df = df.loc[valid].copy().reset_index(drop=True)
    metrics = [x for x in derived if x is not None]
    if df.empty:
        raise ValueError('No valid completed best-of-three matches found in the dataset.')
    for key in ('deciding_game', 'opening_loser', 'comeback', 'avg_game_margin'):
        df[key] = [m[key] for m in metrics]
    df['year'] = df['date'].dt.year.astype(int)
    # A team is either one singles player or an entire named doubles pair.
    df['first_game_loser'] = np.where(df['opening_loser'].eq(1), df['team1'], df['team2'])
    df['winner_name'] = np.where(df['winner'].eq(1), df['team1'], df['team2'])
    df['side_a'] = np.where(df['team1'] <= df['team2'], df['team1'], df['team2'])
    df['side_b'] = np.where(df['team1'] <= df['team2'], df['team2'], df['team1'])
    df['side_a_won'] = df['winner_name'] == df['side_a']
    df['rivalry_id'] = df['discipline'] + '::' + df['side_a'] + '::' + df['side_b']
    report = {
        'source_rows': int(source_rows),
        'structurally_valid_rows': int(structural_rows),
        'score_valid_matches': int(len(df)),
        'excluded_rows': int(source_rows - len(df)),
        'years': f"{df['year'].min()}–{df['year'].max()}",
        'disciplines': sorted(df['discipline'].unique().tolist()),
        'tournaments': int(df['tournament'].nunique()),
        'notes': 'Retirements, defaults, unparseable scores, and scores conflicting with winner are excluded from analytic rates.',
    }
    return df, report


def load_matches(path: str | Path) -> tuple[pd.DataFrame, dict]:
    """Load full downloaded CSV. Raises clearly if it is unavailable."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f'Missing {path}. Run: python download_data.py')
    return prepare_matches(pd.read_csv(path, low_memory=False))


def select_matches(df: pd.DataFrame, years: list[int], disciplines: list[str],
                   tiers: list[str], selection: dict | None = None) -> pd.DataFrame:
    """Apply global filters plus a selection made in any chart."""
    out = df[df['year'].between(years[0], years[1]) &
             df['discipline'].isin(disciplines) & df['tier'].isin(tiers)]
    selection = selection or {}
    if selection.get('type') == 'player':
        player = selection['value']
        out = out[(out['team1'] == player) | (out['team2'] == player)]
    elif selection.get('type') == 'discipline':
        out = out[out['discipline'] == selection['value']]
    elif selection.get('type') == 'rivalry':
        out = out[out['rivalry_id'] == selection['value']]
    return out


def comeback_summary(df: pd.DataFrame, min_opportunities: int = 10) -> pd.DataFrame:
    """Successful recoveries divided by first-game-loss opportunities."""
    columns = ['competitor', 'opportunities', 'comeback_wins', 'rate_pct']
    if df.empty:
        return pd.DataFrame(columns=columns)
    by_player = (df.groupby('first_game_loser', observed=True)
                 .agg(opportunities=('comeback', 'size'), comeback_wins=('comeback', 'sum'))
                 .reset_index().rename(columns={'first_game_loser': 'competitor'}))
    by_player['rate_pct'] = 100 * by_player['comeback_wins'] / by_player['opportunities']
    return (by_player[by_player['opportunities'] >= min_opportunities]
            .sort_values(['rate_pct', 'opportunities'], ascending=[False, False])
            .reset_index(drop=True)[columns])


def competitiveness_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Rate of three-game matches and score-margin context by discipline."""
    columns = ['discipline', 'matches', 'deciding', 'rate_pct', 'avg_game_margin']
    if df.empty:
        return pd.DataFrame(columns=columns)
    summary = (df.groupby('discipline', observed=True)
               .agg(matches=('deciding_game', 'size'),
                    deciding=('deciding_game', 'sum'),
                    avg_game_margin=('avg_game_margin', 'mean')).reset_index())
    summary['rate_pct'] = 100 * summary['deciding'] / summary['matches']
    summary['discipline'] = pd.Categorical(summary['discipline'], DISCIPLINES, ordered=True)
    return summary.sort_values('discipline').reset_index(drop=True)[columns]


def rivalry_summary(df: pd.DataFrame, min_meetings: int = 6) -> pd.DataFrame:
    """Parity 100% is exactly 50/50; 0% means one side always wins."""
    columns = ['rivalry_id', 'discipline', 'side_a', 'side_b',
               'meetings', 'side_a_wins', 'deciding_games', 'parity_pct']
    if df.empty:
        return pd.DataFrame(columns=columns)
    summary = (df.groupby(['rivalry_id', 'discipline', 'side_a', 'side_b'], observed=True)
               .agg(meetings=('winner', 'size'),
                    side_a_wins=('side_a_won', 'sum'),
                    deciding_games=('deciding_game', 'sum')).reset_index())
    summary['parity_pct'] = 100 - 2 * abs(100 * summary['side_a_wins'] / summary['meetings'] - 50)
    return (summary[summary['meetings'] >= min_meetings]
            .sort_values(['parity_pct', 'meetings'], ascending=[False, False])
            .reset_index(drop=True)[columns])
