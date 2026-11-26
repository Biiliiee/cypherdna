import pytest
from Gen import (
    calculate_score,
    token_type_match_score,
    evaluate_pattern_match,
    pattern_signatures_match
)


class TestGenScoringRules:
    def test_absolute_rule_never_duplicate_year_or_date(self):
        # Two YEAR tokens
        score_two_years = calculate_score(["NAME", "YEAR", "YEAR"], 3)
        assert score_two_years == 0

        # One YEAR and one DATE
        score_year_date = calculate_score(["NAME", "YEAR", "DATE"], 3)
        assert score_year_date == 0

        # Two DATE tokens
        score_two_dates = calculate_score(["DATE", "NAME", "DATE"], 3)
        assert score_two_dates == 0

        # Single YEAR is allowed
        score_single_year = calculate_score(["NAME", "YEAR"], 2)
        assert score_single_year > 0

    def test_absolute_rule_reject_purely_synthetic(self):
        # All tokens are synthetic -> must be rejected (score = 0)
        metas_all_synthetic = [{"synthetic": True}, {"synthetic": True}]
        score = calculate_score(["NAME", "YEAR"], 2, token_metas=metas_all_synthetic)
        assert score == 0

        # Partially synthetic (one user token + one synthetic year) -> allowed
        metas_mixed = [{"synthetic": False}, {"synthetic": True}]
        score_mixed = calculate_score(["NAME", "YEAR"], 2, token_metas=metas_mixed)
        assert score_mixed > 0

        # Fully user provided -> allowed
        metas_user = [{"synthetic": False}, {"synthetic": False}]
        score_user = calculate_score(["NAME", "YEAR"], 2, token_metas=metas_user)
        assert score_user > 0
        assert score_user > score_mixed

    def test_year_at_end_human_bonus(self):
        # NAME+YEAR should score higher than YEAR+NAME
        score_end = calculate_score(["NAME", "YEAR"], 2)
        score_start = calculate_score(["YEAR", "NAME"], 2)
        assert score_end > score_start


class TestPatternMatching:
    def test_token_type_match_score(self):
        # Exact match = 2
        assert token_type_match_score("GAME", "GAME") == 2
        assert token_type_match_score("NUMBER", "NUMBER") == 2
        assert token_type_match_score("NAME", "NAME") == 2

        # Equivalent match = 1 (word-like or number-like)
        assert token_type_match_score("WORD", "GAME") == 1
        assert token_type_match_score("NAME", "WORD") == 1
        assert token_type_match_score("YEAR", "NUMBER") == 1
        assert token_type_match_score("DATE", "NUMBER") == 1

        # No match = 0
        assert token_type_match_score("NAME", "NUMBER") == 0
        assert token_type_match_score("SYMBOL", "WORD") == 0
        assert token_type_match_score("YEAR", "SEPARATOR") == 0

    def test_evaluate_pattern_match(self):
        # Exact Match & Exact Length = 3
        assert evaluate_pattern_match("GAME+NUMBER", "GAME+NUMBER") == 3
        assert evaluate_pattern_match("NAME+YEAR", "NAME+YEAR") == 3

        # Equivalent Match & Exact Length = 2
        assert evaluate_pattern_match("GAME+NUMBER", "WORD+NUMBER") == 2
        assert evaluate_pattern_match("NAME+YEAR", "WORD+NUMBER") == 2

        # Prefix Match with extra tokens = 1
        assert evaluate_pattern_match("GAME+NUMBER", "GAME+NUMBER+SYMBOL") == 1
        assert evaluate_pattern_match("NAME+YEAR", "NAME+YEAR+WORD") == 1

        # No Match = 0
        assert evaluate_pattern_match("GAME+NUMBER", "SYMBOL+SYMBOL") == 0
        assert evaluate_pattern_match("NAME+YEAR", "YEAR+NAME") == 0
        assert evaluate_pattern_match("NAME+YEAR+SYMBOL", "NAME+YEAR") == 0  # Candidate shorter than user pattern

    def test_pattern_signatures_match(self):
        assert pattern_signatures_match("GAME+NUMBER", "GAME+NUMBER") is True
        assert pattern_signatures_match("GAME+NUMBER", "WORD+NUMBER") is True
        assert pattern_signatures_match("GAME+NUMBER", "SYMBOL+SYMBOL") is False
