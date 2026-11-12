"""Small invented fixture used only for unit tests, NOT for submitted dashboard data."""
import unittest
import pandas as pd
from data_pipeline import (parse_score, match_metrics, prepare_matches,
                           comeback_summary, competitiveness_summary,
                           rivalry_summary, select_matches)


def rows():
    # Ten real-shaped records, NOT real match results; app never loads these.
    result = []
    for i in range(10):
        d = ('MS' if i < 8 else 'MD')
        team1, team2 = ('Player A', 'Player B') if d == 'MS' else ('Pair A / Partner', 'Pair B / Partner')
        score = '16-21 21-15 21-18' if i % 2 == 0 else '21-15 17-21 21-19'
        result.append(dict(date=f'2025-04-{i+1:02}', discipline=d,
                           tournament='Test Cup', tier='HSBC BWF World Tour Super 500',
                           round='QF', team1=team1, team2=team2, winner=1, score=score))
    return pd.DataFrame(result)


class MetricsTest(unittest.TestCase):
    def test_parse_score(self):
        self.assertEqual(len(parse_score('21-18 20-22 21-19')), 3)
        self.assertIsNone(parse_score('21-15'))
        self.assertIsNone(parse_score('retired'))
        self.assertIsNone(parse_score('20-20 21-19'))

    def test_match_metric(self):
        m = match_metrics('15-21 21-16 21-17', 1)
        self.assertTrue(m['comeback'])
        self.assertTrue(m['deciding_game'])
        self.assertEqual(m['opening_loser'], 1)
        self.assertIsNone(match_metrics('15-21 15-21', 1))

    def test_aggregates(self):
        df, report = prepare_matches(rows())
        self.assertEqual(report['source_rows'], 10)
        self.assertEqual(report['score_valid_matches'], 10)
        self.assertEqual(len(competitiveness_summary(df)), 2)
        self.assertGreater(len(rivalry_summary(df, min_meetings=6)), 0)
        comeback = comeback_summary(df, min_opportunities=1)
        self.assertTrue((comeback['rate_pct'] >= 0).all())
        self.assertTrue((comeback['rate_pct'] <= 100).all())
        chosen = select_matches(df, [2025, 2025], ['MS','MD'],
                                ['HSBC BWF World Tour Super 500'],
                                {'type':'player','value':'Player A'})
        self.assertEqual(len(chosen), 8)
        pairid = df['rivalry_id'].iloc[0]
        self.assertEqual(len(select_matches(df,[2025,2025],['MS','MD'],
                          ['HSBC BWF World Tour Super 500'],
                          {'type':'rivalry','value':pairid})),8)


if __name__ == '__main__':
    unittest.main()
