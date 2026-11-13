import math
import unittest

from empirical_completion import hac_mean, metric


class EmpiricalSyntheticTests(unittest.TestCase):
    def test_hac_constant_zero(self):
        v = hac_mean([0.0] * 20, 4)
        self.assertEqual(v["mean"], 0)
        self.assertEqual(v["hac_se"], 0)
        self.assertEqual(v["normal_approx_p"], 1)

    def test_hac_serial_dependence(self):
        series = [1.0] * 10 + [-1.0] * 10
        self.assertGreater(hac_mean(series, 4)["hac_se"], hac_mean(series, 0)["hac_se"])

    def test_price_metrics(self):
        v = metric([{"predicted_price": 105, "actual_price": 100},
                    {"predicted_price": 90, "actual_price": 100}])
        self.assertAlmostEqual(v["mape_pct"], 7.5)
        self.assertAlmostEqual(v["mae_points"], 7.5)
        self.assertAlmostEqual(v["rmse_points"], math.sqrt(62.5))


if __name__ == "__main__":
    unittest.main()
