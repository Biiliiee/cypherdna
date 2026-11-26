import pytest
from crypto_utils import calculate_entropy, estimate_crack_time


class TestCryptoUtils:
    def test_calculate_entropy_empty(self):
        assert calculate_entropy("") == 0
        assert calculate_entropy(None) == 0

    def test_calculate_entropy_single_charset(self):
        # Digits only (pool 10)
        e_digits = calculate_entropy("123456")
        # 6 * log2(10) = 6 * 3.3219... = 19.93
        assert 19.8 <= e_digits <= 20.0

        # Lowercase only (pool 26)
        e_lower = calculate_entropy("abcdef")
        # 6 * log2(26) = 6 * 4.7004... = 28.20
        assert 28.0 <= e_lower <= 28.4

    def test_calculate_entropy_mixed(self):
        # Mixed: lower, upper, digit, symbol (pool 26 + 26 + 10 + 32 = 94)
        e_mixed = calculate_entropy("Admin123!")
        # 9 * log2(94) = 9 * 6.5545... = 58.99
        assert 58.8 <= e_mixed <= 59.2

    def test_estimate_crack_time_low_entropy(self):
        times = estimate_crack_time(15)
        assert times["rtx"] == "< 1 sec"
        assert times["pc"] == "< 1 sec"

    def test_estimate_crack_time_high_entropy(self):
        times = estimate_crack_time(80)
        assert "y" in times["rtx"] or ">" in times["rtx"]
        assert "y" in times["pc"] or ">" in times["pc"]

    def test_estimate_crack_time_overflow_protection(self):
        # Entropy > 300 must trigger safe overflow protection without crashing
        times_301 = estimate_crack_time(301)
        assert times_301 == {"rtx": "> 1000y", "pc": "> 1000y"}

        times_1000 = estimate_crack_time(1000)
        assert times_1000 == {"rtx": "> 1000y", "pc": "> 1000y"}

        times_huge = estimate_crack_time(5000)
        assert times_huge == {"rtx": "> 1000y", "pc": "> 1000y"}
