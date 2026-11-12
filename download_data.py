"""Retrieve the full original CSV for local use. Run once before launching Dash."""
from pathlib import Path
from urllib.request import Request, urlopen
import shutil

URL = 'https://raw.githubusercontent.com/SahilMotyar/bwf-match-data/main/matches.csv'
DEST = Path(__file__).resolve().parent / 'data' / 'matches.csv'


def main():
    DEST.parent.mkdir(parents=True, exist_ok=True)
    req = Request(URL, headers={'User-Agent': 'RallyScope-academic-project/1.0'})
    try:
        with urlopen(req, timeout=90) as src, DEST.open('wb') as dst:
            shutil.copyfileobj(src, dst)
        if DEST.stat().st_size < 1000000:
            raise ValueError('Downloaded file appears incomplete; please try again.')
    except Exception:
        DEST.unlink(missing_ok=True)
        print('Download failed. Open the repository README and download matches.csv manually into data/.')
        print('https://github.com/SahilMotyar/bwf-match-data')
        raise
    print(f'Full dataset saved: {DEST} ({DEST.stat().st_size:,} bytes)')


if __name__ == '__main__':
    main()
