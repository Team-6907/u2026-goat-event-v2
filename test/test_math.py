# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from __future__ import annotations

import math
import unittest

from utils.math_util import erfinv


class TestMath(unittest.TestCase):
    def test_erfinv_round_trips_erf_for_representative_values(self) -> None:
        for value in (-0.999999, -0.9, -0.5, -0.1, 0.0, 0.1, 0.5, 0.9, 0.999999):
            with self.subTest(value=value):
                self.assertAlmostEqual(
                    math.erf(erfinv(value)),
                    value,
                    places=12,
                    msg=f"Expected erf(erfinv({value})) to round-trip back to {value}",
                )

    def test_erfinv_returns_expected_special_values(self) -> None:
        self.assertEqual(erfinv(0.0), 0.0, "Expected erfinv(0) to be exactly 0")
        self.assertEqual(
            erfinv(1.0), math.inf, "Expected erfinv(1) to be positive infinity"
        )
        self.assertEqual(
            erfinv(-1.0), -math.inf, "Expected erfinv(-1) to be negative infinity"
        )

    def test_erfinv_is_odd(self) -> None:
        for value in (0.1, 0.5, 0.9):
            with self.subTest(value=value):
                self.assertAlmostEqual(
                    erfinv(-value),
                    -erfinv(value),
                    places=12,
                    msg=f"Expected erfinv to be odd at {value}",
                )

    def test_erfinv_raises_outside_domain(self) -> None:
        for value in (-1.000001, 1.000001):
            with self.subTest(value=value):
                with self.assertRaises(
                    ValueError,
                    msg=f"Expected erfinv({value}) to reject values outside [-1, 1]",
                ):
                    erfinv(value)

    def test_erfinv_preserves_nan(self) -> None:
        result = erfinv(math.nan)
        self.assertTrue(math.isnan(result), "Expected erfinv(nan) to return nan")


if __name__ == "__main__":
    unittest.main()
