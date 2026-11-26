import pytest
from datetime import datetime
from dna_parser import (
    tokenize,
    is_year,
    is_name,
    is_date,
    is_repeated,
    is_month,
    is_season,
    is_weak_word,
    is_symbol,
    is_separator,
    classify_token,
    parse_password
)


class TestTokenize:
    def test_tokenize_normal(self):
        assert tokenize("Gustavo2004!") == ["Gustavo", "2004", "!"]
        assert tokenize("Admin123") == ["Admin", "123"]

    def test_tokenize_separators_and_symbols(self):
        assert tokenize("Ana_1999!!") == ["Ana", "_", "1999", "!", "!"]
        assert tokenize("root-pass.2025") == ["root", "-", "pass", ".", "2025"]

    def test_tokenize_accented(self):
        assert tokenize("João_2024") == ["João", "_", "2024"]
        assert tokenize("Açúcar123") == ["Açúcar", "123"]

    def test_tokenize_edge_cases(self):
        assert tokenize("") == []
        assert tokenize("!@#$%") == ["!", "@", "#", "$", "%"]
        assert tokenize("123456") == ["123456"]
        assert tokenize("     ") == [" ", " ", " ", " ", " "]


class TestClassifiers:
    def test_is_year_valid(self):
        current_year = datetime.now().year
        assert is_year("1900") is True
        assert is_year("1999") is True
        assert is_year("2024") is True
        assert is_year(str(current_year)) is True
        assert is_year(str(current_year + 2)) is True

    def test_is_year_edge_cases(self):
        current_year = datetime.now().year
        assert is_year("1899") is False
        assert is_year(str(current_year + 3)) is False
        assert is_year("99") is False
        assert is_year("20240") is False
        assert is_year("") is False
        assert is_year("abcd") is False
        assert is_year("!@#$") is False

    def test_is_name_normal(self):
        assert is_name("Gustavo") is True
        assert is_name("Maria") is True
        assert is_name("Carlos") is True
        assert is_name("Silva") is True

    def test_is_name_accented(self):
        assert is_name("José") is True
        assert is_name("João") is True
        assert is_name("Araújo") is True

    def test_is_name_exclusions_and_edge_cases(self):
        # Exclude weak words
        assert is_name("admin") is False
        assert is_name("password") is False
        assert is_name("senha") is False
        # Exclude stop words
        assert is_name("in") is False
        assert is_name("de") is False
        assert is_name("da") is False
        # Short strings or non-alpha
        assert is_name("") is False
        assert is_name("ab") is False
        assert is_name("123") is False
        assert is_name("!@#") is False

    def test_is_date_formats(self):
        current_year = datetime.now().year
        # DDMMYYYY (8 digits)
        assert is_date("25122000") is True
        assert is_date("01011990") is True
        # ISO YYYYMMDD (8 digits)
        assert is_date("20001225") is True
        # DDMMYY (6 digits)
        assert is_date("251299") is True
        assert is_date("150821") is True
        # DDMM (4 digits)
        assert is_date("2512") is True
        assert is_date("3101") is True

    def test_is_date_invalid_and_edge_cases(self):
        assert is_date("99999999") is False
        assert is_date("00000000") is False
        assert is_date("0000") is False
        assert is_date("123") is False
        assert is_date("") is False
        assert is_date("abcd1234") is False

    def test_is_repeated(self):
        assert is_repeated("111") is True
        assert is_repeated("aaaa") is True
        assert is_repeated("!!!") is True
        assert is_repeated("11") is False  # len < 3
        assert is_repeated("123") is False
        assert is_repeated("") is False

    def test_is_month(self):
        assert is_month("janeiro") is True
        assert is_month("jan") is True
        assert is_month("marco") is True
        assert is_month("março") is True
        assert is_month("march") is True
        assert is_month("december") is True
        assert is_month("dec") is True
        assert is_month("notamonth") is False
        assert is_month("") is False
        assert is_month("123") is False

    def test_is_season(self):
        assert is_season("primavera") is True
        assert is_season("verao") is True
        assert is_season("verão") is True
        assert is_season("summer") is True
        assert is_season("winter") is True
        assert is_season("inverno") is True
        assert is_season("banana") is False
        assert is_season("") is False

    def test_is_weak_word(self):
        assert is_weak_word("password") is True
        assert is_weak_word("admin") is True
        assert is_weak_word("senha") is True
        assert is_weak_word("flamengo") is True
        assert is_weak_word("secureunbreakablepass") is False
        assert is_weak_word("") is False


class TestParsePassword:
    def test_full_parse(self):
        result = parse_password("Admin123!")
        assert result.raw == "Admin123!"
        assert result.pattern in ("WEAK_WORD+KEY_WALK+SYMBOL", "WEAK_WORD+NUMBER+SYMBOL", "WORD+NUMBER+SYMBOL")
        assert len(result.tokens) >= 3
