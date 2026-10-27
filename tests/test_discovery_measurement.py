"""Aggregate discovery reports must not invent non-branded traffic or recommendations.

Runs standalone with the Python standard library as well as in the main suite.
"""
from pathlib import Path
import importlib.util
import unittest

_spec = importlib.util.spec_from_file_location('discovery_report_under_test',
    Path(__file__).resolve().parents[1] / 'scripts/search_discovery_report.py')
report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(report)


class DiscoveryMeasurementTests(unittest.TestCase):
    def test_brand_tokens_and_missing_queries_stay_separate(self):
        rows = [dict(Query=query, Clicks=1, Impressions=10) for query in
                ('Cursiv AI', 'CursivAI', 'cursiv.us', 'Cursiv-Local', 'free local AI', 'cursive writing', '')]
        result = report.search_summary(rows)['groups']
        self.assertEqual(result['branded']['query_rows'], 4)
        self.assertEqual(result['non_branded']['query_rows'], 2)
        self.assertEqual(result['unknown']['query_rows'], 1)

    def test_click_rate_and_position_are_weighted_by_actual_counts(self):
        result = report.search_summary([
            dict(Query='local AI', Clicks='10', Impressions='100', Position='2'),
            dict(Query='offline LLM', Clicks='1', Impressions='10', Position='20'),
        ])['groups']['non_branded']
        self.assertAlmostEqual(result['ctr'], .1)
        self.assertAlmostEqual(result['average_position'], 400 / 110)

    def test_zero_impressions_are_unknown_rates_not_false_zero_rates(self):
        result = report.search_summary([dict(Query='local AI', Clicks=0, Impressions=0)])['groups']['non_branded']
        self.assertIsNone(result['ctr'])
        self.assertIsNone(result['average_position'])

    def test_other_exports_and_nonfinite_data_are_rejected(self):
        for rows in ([dict(Page='/', Clicks=1, Impressions=10)],
                     [dict(Query='local AI', Clicks='NaN', Impressions=10)],
                     [dict(Query='local AI', Clicks=0, Impressions=-1)]):
            with self.assertRaises(ValueError):
                report.search_summary(rows)

    def test_referrers_never_establish_branded_query_intent(self):
        result = report.referrals_summary([dict(Referrer='https://www.google.com/search', Count=5),
                                          dict(Referrer='chatgpt.com', Count=2),
                                          dict(Referrer='', Count=3)])
        self.assertEqual(result['channels'], dict(search_engine=5, ai_assistant=2, other_or_unknown=3))
        self.assertNotIn('non_branded', result)

    def test_unrelated_hosts_do_not_inherit_trusted_referrer_names(self):
        for host in ('google.com.evil.invalid', 'fakechatgpt.com', 'claude.ai.evil.invalid', 'developers.openai.com'):
            self.assertEqual(report.referral_channel(host), 'other_or_unknown')


if __name__ == '__main__':
    unittest.main()
