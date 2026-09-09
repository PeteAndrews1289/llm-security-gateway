"""Wilson score confidence intervals for proportions.

The protocol (section 11) requires an interval on every reported rate, not a
bare percentage. The Wilson interval is used rather than the textbook normal
approximation because it behaves sensibly at the sample sizes here: it does not
run past 0 or 1, and it stays meaningful when a category scores 0/25 or 25/25,
where the normal approximation collapses to a zero-width interval and lies.
"""

import math


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple:
    """Return (low, high) for a proportion at ~95% confidence (z=1.96).

    `successes` events out of `n` trials. n=0 returns (0.0, 1.0): no data means
    no knowledge, which is the honest interval.
    """
    if n == 0:
        return (0.0, 1.0)

    p = successes / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    margin = (z * math.sqrt((p * (1 - p) + z2 / (4 * n)) / n)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def format_rate(successes: int, n: int) -> str:
    """A rate with its interval, for human-readable summaries."""
    if n == 0:
        return "n/a (0 trials)"
    p = successes / n
    low, high = wilson_interval(successes, n)
    return f"{successes}/{n} = {p:.0%}  (95% CI {low:.0%}-{high:.0%})"
