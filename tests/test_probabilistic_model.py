import pytest
from probabilistic_model import ProbabilisticModel


class TestProbabilisticModel:
    def test_calculate_probabilities_mathematical_accuracy(self):
        model = ProbabilisticModel()

        # Set up a small, mathematically controlled dataset
        # 100 total tokens: 40 NAME, 60 YEAR
        model.total_tokens_mapped = 100
        model._token_raw_counts = {
            "NAME": 40,
            "YEAR": 60
        }

        # 40 total passwords: 30 NAME+YEAR, 10 NAME+NUMBER
        model.total_passwords_analyzed = 40
        model._pattern_raw_counts = {
            "NAME+YEAR": 30,
            "NAME+NUMBER": 10
        }

        # Transitions: 25 NAME->YEAR out of 40 NAME occurrences
        model._transition_raw_counts = {
            "NAME->YEAR": 25
        }

        # Run mathematical probability distribution
        model.calculate_probabilities()

        # 1. Token Probabilities: P(token) = count / total_tokens
        # P(NAME) = 40 / 100 = 0.4000
        assert model.get_token_probability("NAME") == 0.4
        # P(YEAR) = 60 / 100 = 0.6000
        assert model.get_token_probability("YEAR") == 0.6
        # Unknown token returns 0.0
        assert model.get_token_probability("UNKNOWN") == 0.0

        # 2. Pattern Probabilities: P(pattern) = count / total_passwords
        # P(NAME+YEAR) = 30 / 40 = 0.7500
        assert model.get_pattern_probability("NAME+YEAR") == 0.75
        # P(NAME+NUMBER) = 10 / 40 = 0.2500
        assert model.get_pattern_probability("NAME+NUMBER") == 0.25
        # Unknown pattern returns 0.0
        assert model.get_pattern_probability("WORD+WORD") == 0.0

        # 3. Transition Probabilities (Markov Chain): P(Y|X) = count(X->Y) / count(X)
        # P(YEAR | NAME) = 25 / 40 = 0.6250
        assert model.get_transition_probability("NAME", "YEAR") == 0.625
        # Non-existing transition returns 0.0
        assert model.get_transition_probability("YEAR", "NAME") == 0.0

    def test_calculate_probabilities_zero_division_guard(self):
        model = ProbabilisticModel()
        model.total_tokens_mapped = 0
        model.total_passwords_analyzed = 0

        # Must not raise ZeroDivisionError
        model.calculate_probabilities()
        assert model.token_probabilities == {}
        assert model.pattern_probabilities == {}
        assert model.transition_probabilities == {}
