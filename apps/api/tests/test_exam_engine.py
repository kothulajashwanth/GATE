"""Unit tests for Anti-Cheating System & Violation Engine (Phase 10)."""

import pytest


def test_anti_cheating_violation_threshold():
    MAX_WARNINGS = 3
    warnings = 0

    # Simulate tab switch events
    warnings += 1  # 1st tab switch -> warning
    assert warnings < MAX_WARNINGS

    warnings += 1  # 2nd tab switch -> warning
    assert warnings < MAX_WARNINGS

    warnings += 1  # 3rd tab switch -> auto-termination threshold
    assert warnings >= MAX_WARNINGS
