import unittest
from datetime import date

from run_timing_sensitivity import proxy, update_rows


class TimingSyntheticTests(unittest.TestCase):
    def test_new_york_dst_conversion(self):
        self.assertEqual(proxy(date(2022, 1, 3)).isoformat(), '2022-01-07T04:59:59+00:00')
        self.assertEqual(proxy(date(2022, 7, 3)).isoformat(), '2022-07-07T03:59:59+00:00')

    def test_later_missing_source_record_blocks(self):
        row = {'forecast_origin_id': 'F20220110', 'forecast_date': '2022-01-10',
               'forecast_cutoff_utc': '2022-01-10T12:00:00+00:00',
               'reasons': '', 'VIX': 12, 'VIX_date': '2022-01-03',
               'VIX_available_proxy_utc': '2022-01-06T04:59:59+00:00'}
        vix = {date(2022, 1, 3): 12.0, date(2022, 1, 4): None}
        out, _ = update_rows([row], ('VIX',), vix, {}, {'VIX_History.csv': 'synthetic'})
        self.assertIn('KNOWN_LATER_SOURCE_RECORD_MISSING_VIX', out[0]['reasons'])


if __name__ == '__main__':
    unittest.main()
