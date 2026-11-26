import pytest
from dna_parser import parse_password
from Gen import (
    calculate_score,
    token_type_match_score,
    evaluate_pattern_match,
    pattern_signatures_match,
    generate_wordlist
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


class TestRankerSymbolInjection:
    def test_middle_symbol_injection_and_capitalization_ranker(self):
        parsed = [parse_password("Gustavo"), parse_password("2024")]
        wordlist = generate_wordlist(
            parsed_results=parsed,
            max_words=20,
            symbols=True,
            custom_rank=["NaME+SYMBOL+YEAR"]
        )
        # Símbolo no meio com Capitalize (ex: Gustavo!2024) deve ser gerado e priorizado no topo
        assert "Gustavo!2024" in wordlist
        assert wordlist[:4] == ["Gustavo!2024", "Gustavo@2024", "Gustavo#2024", "Gustavo$2024"] or set(wordlist[:4]) == {
            "Gustavo!2024", "Gustavo@2024", "Gustavo#2024", "Gustavo$2024"
        }
        # Casing errado não deve ser promovido pela regra NaME+SYMBOL+YEAR
        assert "gUSTAVO!2024" not in wordlist[:4]

    def test_hardcore_leet_middle_symbol_without_explicit_leet_flag(self):
        parsed = [parse_password("Gustavo"), parse_password("2024")]
        wordlist = generate_wordlist(
            parsed_results=parsed,
            max_words=30,
            symbols=True,
            use_leet=False,
            custom_rank=["N@ME+SYMBOL+YEAR"]
        )
        # N@ME+SYMBOL+YEAR deve ativar leet automaticamente e priorizar Gust@vo!2024 no topo
        assert any("@" in w and "!" in w and w.endswith("2024") for w in wordlist[:10])
        assert "Gust@vo!2024" in wordlist[:8]

    def test_separator_rule_prioritizes_separated_candidate(self):
        parsed = [parse_password("Gustavo"), parse_password("2024")]
        wordlist = generate_wordlist(
            parsed_results=parsed,
            max_words=20,
            symbols=True,
            custom_rank=["NaME+SEPARATOR+YEAR"]
        )
        assert "Gustavo_2024" in wordlist[:4]

    def test_prefix_symbol_ranker_rule(self):
        parsed = [parse_password("Gustavo"), parse_password("2024")]
        wordlist = generate_wordlist(
            parsed_results=parsed,
            max_words=15,
            symbols=True,
            custom_rank=["SYMBOL+NaME+YEAR"]
        )
        assert set(wordlist[:4]) == {"!Gustavo2024", "@Gustavo2024", "#Gustavo2024", "$Gustavo2024"}

    def test_ranker_enforces_single_symbol_no_extra_separator_or_double_symbol(self):
        # 2 tokens com símbolo no fim: não pode misturar separador (_) com símbolo (!) no topo
        parsed_2 = [parse_password("Gustavo"), parse_password("2024")]
        wl_end = generate_wordlist(
            parsed_results=parsed_2,
            max_words=15,
            symbols=True,
            custom_rank=["NaME+YEAR+SYMBOL"]
        )
        assert set(wl_end[:4]) == {"Gustavo2024!", "Gustavo2024@", "Gustavo2024#", "Gustavo2024$"}
        assert "Gustavo_2024!" not in wl_end[:8]

        # 3 tokens com símbolo no meio: não pode adicionar '_' na segunda junção
        # Usando lowercase 'word' explícito e 'WORD' genérico para validar ambos
        parsed_3 = [parse_password("Gustavo"), parse_password("cobalt"), parse_password("2024")]
        wl_mid = generate_wordlist(
            parsed_results=parsed_3,
            max_words=20,
            symbols=True,
            custom_rank=["NaME+SYMBOL+word+YEAR"]
        )
        assert set(wl_mid[:4]) == {
            "Gustavo!cobalt2024", "Gustavo@cobalt2024", "Gustavo#cobalt2024", "Gustavo$cobalt2024"
        }
        assert all("_" not in w and "-" not in w and "." not in w for w in wl_mid[:4])

        # Quando input já traz um SYMBOL, regra de 1 símbolo não pode promover candidatos com 2 símbolos
        parsed_sym = [parse_password("Gustavo"), parse_password("&"), parse_password("2024")]
        wl_existing_sym = generate_wordlist(
            parsed_results=parsed_sym,
            max_words=20,
            symbols=True,
            custom_rank=["NaME+SYMBOL+YEAR"]
        )
        assert set(wl_existing_sym[:5]) == {
            "Gustavo&2024", "Gustavo!2024", "Gustavo@2024", "Gustavo#2024", "Gustavo$2024"
        }
        assert "Gustavo&2024!" not in wl_existing_sym[:6]
        assert "!Gustavo&2024" not in wl_existing_sym[:6]

    def test_single_separator_in_three_token_ranker_rule(self):
        parsed = [parse_password("Gustavo"), parse_password("cobalt"), parse_password("2024")]
        wl = generate_wordlist(
            parsed_results=parsed,
            max_words=20,
            symbols=True,
            custom_rank=["NaME+SEPARATOR+word+YEAR"]
        )
        assert set(wl[:3]) == {"Gustavo_cobalt2024", "Gustavo-cobalt2024", "Gustavo.cobalt2024"}
        assert "Gustavo_cobalt_2024" not in wl[:6]


class TestTwoPhaseRankerThenTrainedAI:
    def test_ranker_first_then_trained_ai_fills_rest_without_min_rank_r_block(self):
        from probabilistic_model import ProbabilisticModel

        model = ProbabilisticModel()
        model.pattern_probabilities = {
            "WORD+NUMBER": 0.45,
            "NAME+YEAR": 0.25,
            "WORD": 0.15,
        }
        model.token_probabilities = {
            "WORD": 0.40,
            "NUMBER": 0.30,
            "NAME": 0.20,
            "YEAR": 0.10,
        }
        model.transition_probabilities = {
            "WORD->NUMBER": 0.65,
            "NAME->YEAR": 0.55,
        }

        parsed = [
            parse_password("Gustavo"),
            parse_password("cobalt"),
            parse_password("2024"),
            parse_password("8472"),
        ]
        # Regra de 3 tokens: antes pulava r=1 e r=2 (WORD, WORD+NUMBER, NAME+YEAR);
        # agora Fase 1 gera a regra e Fase 2 usa o modelo treinado para preencher o resto.
        wl = generate_wordlist(
            parsed_results=parsed,
            max_words=40,
            symbols=False,
            model=model,
            custom_rank=["NaME+word+YEAR"]
        )

        assert wl[0] == "Gustavocobalt2024"
        # Padrões de alta probabilidade da IA devem aparecer logo após o Ranker
        assert "Cobalt8472" in wl or "cobalt8472" in wl
        assert "Gustavo2024" in wl
        # Formas naturais devem vencer variações exóticas (gUSTAVO / cOBALT) dentro da Fase 2
        idx_word_nat = min(wl.index(c) for c in ("Cobalt8472", "cobalt8472") if c in wl)
        idx_year_first = wl.index("20248472cobalt") if "20248472cobalt" in wl else len(wl)
        assert idx_word_nat < idx_year_first
        if "gUSTAVO2024" in wl:
            assert wl.index("Gustavo2024") < wl.index("gUSTAVO2024")


class TestSingleTokenHierarchy:
    """Testa que tokens r=1 (NUMBER, NAME, WORD, YEAR) sejam respeitados na hierarquia."""

    def test_ranker_single_token_rule_has_highest_priority(self):
        """Regra #0 'NUMBER' deve colocar 7493 (NUMBER) e 123 (KEY_WALK dígitos) ACIMA de NaME+SYMBOL+YEAR, sem sequestrar YEAR (2024)."""
        parsed = [parse_password("Gustavo"), parse_password("2024"), parse_password("123"), parse_password("7493")]
        wl = generate_wordlist(
            parsed_results=parsed,
            max_words=20,
            symbols=True,
            custom_rank=["NUMBER", "NaME+SYMBOL+YEAR"]
        )
        assert "7493" in wl
        assert "123" in wl
        idx_7493 = wl.index("7493")
        idx_123 = wl.index("123")
        first_sym = next(i for i, w in enumerate(wl) if "Gustavo" in w and any(s in w for s in "!@#$"))
        assert idx_7493 < idx_123 < first_sym, (
            f"7493 (#{idx_7493+1}) e 123 (#{idx_123+1}) deveriam aparecer antes de NaME+SYMBOL+YEAR (#{first_sym+1})"
        )
        # 2024 é YEAR (não NUMBER): não deve furar fila antes de NaME+SYMBOL+YEAR
        if "2024" in wl:
            assert wl.index("2024") > first_sym

    def test_single_number_no_penalty_in_fallback(self):
        """r=1 NUMBER sozinho não deve receber ONLY_NUMBERS_PENALTY nem NUMBER_PREFIX_PENALTY."""
        score_num = calculate_score(["NUMBER"], 1)
        score_name = calculate_score(["NAME"], 1)
        # Sem modelo, NUMBER sozinho deve ter score razoável (não esmagado por penalidades)
        assert score_num >= 80, f"NUMBER r=1 score ({score_num}) muito baixo — penalidade indevida"
        assert score_num > 0

    def test_year_uses_number_fallback_in_trained_model(self):
        """YEAR sozinho deve herdar probabilidade de NUMBER quando modelo não conhece YEAR."""
        from probabilistic_model import ProbabilisticModel
        model = ProbabilisticModel()
        model.pattern_probabilities = {"NUMBER": 0.16, "WORD": 0.28, "WORD+NUMBER": 0.26}
        model.token_probabilities = {"NUMBER": 0.30, "WORD": 0.40, "NAME": 0.20, "YEAR": 0.10}
        model.transition_probabilities = {}

        score_year = calculate_score(["YEAR"], 1, model=model)
        score_num = calculate_score(["NUMBER"], 1, model=model)
        # YEAR herda fallback descontado de NUMBER (fica no tier treinado, mas abaixo do NUMBER exato)
        assert score_year > 10000, f"YEAR r=1 com modelo ({score_year}) deveria entrar no tier treinado"
        assert score_num > score_year, f"NUMBER exato ({score_num}) deve vencer YEAR fallback ({score_year})"

    def test_ranker_single_token_word_above_second_rule(self):
        """Regra #0 'WORD' deve manter WORD/custom domain (cobalt, xbox) acima de regra #1 sem sequestrar NAME."""
        parsed = [parse_password("Gustavo"), parse_password("cobalt"), parse_password("xbox"), parse_password("2026")]
        wl = generate_wordlist(
            parsed_results=parsed,
            max_words=25,
            symbols=True,
            custom_rank=["WORD", "NaME+YEAR"]
        )
        first_combo_idx = next(i for i, w in enumerate(wl) if "2026" in w and len(w) > 4)
        idx_cobalt = min(i for i, w in enumerate(wl) if w.lower() == "cobalt")
        idx_xbox = min(i for i, w in enumerate(wl) if w.lower() == "xbox")
        assert idx_cobalt < first_combo_idx
        assert idx_xbox < first_combo_idx

    def test_minimalist_ranker_then_ai_word_before_word_number(self):
        """Caso Gustavo Luis cachorro 7493 2026: Ranker [NAME+YEAR, YEAR+NAME, NAME+NUMBER] -> AI WORD antes de WORD+NUMBER."""
        from probabilistic_model import ProbabilisticModel
        model = ProbabilisticModel()
        model.pattern_probabilities = {
            "WORD": 0.2843,
            "WORD+NUMBER": 0.2595,
            "NUMBER": 0.1598,
            "NAME+NUMBER": 0.0615,
            "NUMBER+WORD": 0.0323,
            "WORD+YEAR": 0.0161,
            "NUMBER+NAME": 0.0067,
            "NAME+YEAR": 0.0061,
            "NAME": 0.0028,
        }
        model.token_probabilities = {
            "WORD": 0.48, "NUMBER": 0.40, "NAME": 0.08, "YEAR": 0.02
        }
        model.transition_probabilities = {"WORD->NUMBER": 0.35, "NAME->YEAR": 0.15, "NAME->NUMBER": 0.45}

        parsed = [parse_password(x) for x in ("Gustavo", "Luis", "cachorro", "7493", "2026")]
        wl = generate_wordlist(
            parsed_results=parsed,
            max_words=150,
            symbols=True,
            model=model,
            custom_rank=["NAME+YEAR", "YEAR+NAME", "NAME+NUMBER"]
        )
        # 1. Ranker exatamente nessa ordem: NAME+YEAR -> YEAR+NAME -> NAME+NUMBER
        idx_name_year = wl.index("Gustavo2026")
        idx_year_name = wl.index("2026Gustavo")
        idx_name_num = wl.index("Gustavo7493")
        assert idx_name_year < idx_year_name < idx_name_num

        # 2. Cachorro (WORD 28.43%) vem logo após Ranker e ANTES de cachorro7493 (WORD+NUMBER 25.95%) e 7493 (NUMBER 15.98%)
        idx_word = min(wl.index(c) for c in ("cachorro", "Cachorro") if c in wl)
        idx_word_num = min(wl.index(c) for c in ("cachorro7493", "Cachorro7493") if c in wl)
        idx_num = wl.index("7493")
        idx_num_word = min(wl.index(c) for c in ("7493cachorro", "7493Cachorro") if c in wl)
        assert idx_name_num < idx_word < idx_word_num < idx_num < idx_num_word

    def test_key_walk_does_not_steal_name_number_probability(self):
        """NAME+KEY_WALK (0.23%) existente no modelo não deve usar probabilidade de NAME+NUMBER (6.15%)."""
        from probabilistic_model import ProbabilisticModel
        model = ProbabilisticModel()
        model.pattern_probabilities = {
            "NAME+NUMBER": 0.0615,
            "NAME": 0.0028,
            "NAME+KEY_WALK": 0.0023,
        }
        model.token_probabilities = {"NAME": 0.08, "NUMBER": 0.40, "KEY_WALK": 0.01}
        model.transition_probabilities = {}

        s_name_num = calculate_score(["NAME", "NUMBER"], 2, model=model)
        s_name = calculate_score(["NAME"], 1, model=model)
        s_name_kw = calculate_score(["NAME", "KEY_WALK"], 2, model=model)
        assert s_name_num > s_name > s_name_kw

    def test_ranker_multi_rule_exact_ownership_preserved(self):
        """Em [NaME+YEAR, NaME+SYMBOL+YEAR, NaME+NUMBER], NaME+NUMBER exato vai para regra #3, sem ser engolido por #1."""
        parsed = [parse_password("Gustavo"), parse_password("2026"), parse_password("7493")]
        wl = generate_wordlist(
            parsed_results=parsed,
            max_words=30,
            symbols=True,
            custom_rank=["NaME+YEAR", "NaME+SYMBOL+YEAR", "NaME+NUMBER"]
        )
        assert wl[0] == "Gustavo2026"
        first_sym = next(i for i, w in enumerate(wl) if w in ("Gustavo!2026", "Gustavo@2026", "Gustavo#2026", "Gustavo$2026"))
        idx_num = wl.index("Gustavo7493")
        assert first_sym < idx_num

    def test_ai_single_token_beats_unseen_long_frankensteins(self):
        """Padrões r=1 presentes na IA (ex: NAME 0.28%) devem vencer combinações 0% de 4-5 tokens e padrões menores."""
        from probabilistic_model import ProbabilisticModel
        model = ProbabilisticModel()
        model.pattern_probabilities = {
            "NUMBER": 0.1598,
            "NAME+NUMBER": 0.0615,
            "NUMBER+NAME": 0.0067,
            "NAME+YEAR": 0.0061,
            "NAME": 0.0028,
            "NAME+SEPARATOR+NAME": 0.0014,
            "NAME+SYMBOL": 0.0007,
        }
        model.token_probabilities = {
            "WORD": 0.48, "NUMBER": 0.40, "NAME": 0.08, "SEPARATOR": 0.03, "SYMBOL": 0.03, "YEAR": 0.02
        }
        model.transition_probabilities = {
            "YEAR->NAME": 0.20, "NAME->SEPARATOR": 0.35, "SEPARATOR->NAME": 0.30, "NAME->NUMBER": 0.50, "NUMBER->NAME": 0.25
        }

        s_name = calculate_score(["NAME"], 1, model=model)
        s_sep = calculate_score(["NAME", "SEPARATOR", "NAME"], 3, model=model)
        s_unseen_5 = calculate_score(["YEAR", "NAME", "SEPARATOR", "NAME", "NUMBER"], 5, model=model)
        assert s_name > s_sep > s_unseen_5

        parsed = [parse_password(x) for x in ("Gustavo", "Luis", "2026", "7493")]
        wl = generate_wordlist(parsed, max_words=80, symbols=True, model=model)
        assert "7493" == wl[0]
        assert "Gustavo" in wl
        assert "2026" in wl
        idx_gustavo = wl.index("Gustavo")
        idx_sep = next((i for i, w in enumerate(wl) if "_" in w or "-" in w or "." in w), len(wl))
        assert idx_gustavo < idx_sep

    def test_ai_phase2_includes_single_tokens_in_order(self):
        """Fase 2 (AI) deve incluir tokens r=1 na ordem de probabilidade do modelo."""
        from probabilistic_model import ProbabilisticModel
        model = ProbabilisticModel()
        model.pattern_probabilities = {
            "WORD+NUMBER": 0.45,
            "NAME+YEAR": 0.25,
            "WORD": 0.15,
            "NUMBER": 0.12,
            "NAME": 0.08,
        }
        model.token_probabilities = {
            "WORD": 0.40, "NUMBER": 0.30, "NAME": 0.20, "YEAR": 0.10,
        }
        model.transition_probabilities = {"WORD->NUMBER": 0.65, "NAME->YEAR": 0.55}

        parsed = [parse_password("Gustavo"), parse_password("cobalt"), parse_password("2024"), parse_password("8472")]
        wl = generate_wordlist(parsed, max_words=40, symbols=False, model=model)

        # Tokens r=1 devem estar presentes
        assert any(w.lower() == "cobalt" for w in wl), "WORD r=1 'cobalt' deveria estar na wordlist"
        assert any(w.lower() == "gustavo" for w in wl), "NAME r=1 'Gustavo' deveria estar na wordlist"
        assert "8472" in wl, "NUMBER r=1 '8472' deveria estar na wordlist"
        assert "2024" in wl, "YEAR r=1 '2024' deveria estar na wordlist"
