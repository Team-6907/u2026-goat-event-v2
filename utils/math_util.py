# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from __future__ import annotations

from math import erf, exp, inf, isnan, log, sqrt

_SQRT_PI: float = sqrt(3.141592653589793)
_WinitzkiA: float = 0.147


def erfinv(value: float) -> float:
    if isnan(value):
        return value

    if value < -1.0 or value > 1.0:
        raise ValueError(f"erfinv is only defined on [-1, 1], got {value}")

    if value == -1.0:
        return -inf
    if value == 1.0:
        return inf
    if value == 0.0:
        return 0.0

    sign = 1.0
    normalizedValue = value
    if normalizedValue < 0.0:
        sign = -1.0
        normalizedValue = -normalizedValue

    # Winitzki's approximation provides a good closed-form initial guess.
    logTerm = log(1.0 - normalizedValue * normalizedValue)
    firstTerm = 2.0 / (3.141592653589793 * _WinitzkiA) + logTerm / 2.0
    result = sign * sqrt(sqrt(firstTerm * firstTerm - logTerm / _WinitzkiA) - firstTerm)

    # Halley's method converges quickly for erf because its derivatives are simple.
    for _ in range(4):
        error = erf(result) - value
        derivative = 2.0 / _SQRT_PI * exp(-(result * result))
        secondDerivative = -2.0 * result * derivative
        denominator = 2.0 * derivative * derivative - error * secondDerivative
        if denominator == 0.0:
            break
        result -= 2.0 * error * derivative / denominator

    return result
