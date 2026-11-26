#!/usr/bin/env python3
"""
Gerador de wordlists por combinação ranqueada de tokens.

- Funções de mutação: mutate_case, mutate_full_case, mutate_leet, mutate_nicknames.
- calculate_score() pontua cada combinação de tokens usando as probabilidades
  do modelo treinado (Markov) ou, na falta dele, um fallback heurístico.
- generate_wordlist() testa as permutações e mantém só as N melhores num heap,
  pra não precisar guardar tudo em memória.
"""

import itertools
import unicodedata
import heapq

ALLOWED_LENGTHS = [8, 10, 12]
DEFAULT_MAX_WORDS = 10000
MAX_INTERNAL_LENGTH = 20

COMMON_SEPARATORS = ["", "_", "-", "."]
COMMON_SYMBOLS = ["!", "@", "#", "$"]

# ==============================================================================
# PESOS E CONSTANTES DO MOTOR DE SCORING E RANKING HEURÍSTICO
# ==============================================================================

# Multiplicadores de probabilidade estatística (Modelo de Markov / Trainer)
PATTERN_PROB_WEIGHT = 1000000       # Peso da probabilidade da assinatura completa de tipos (ex: NAME+YEAR)
TRAINED_PATTERN_TIER_BONUS = 10000  # Garante que padrões presentes no modelo vencem combinações inéditas (P=0)
TOKEN_PROB_WEIGHT = 500             # Peso da frequência unigrama média dos tokens
TRANSITION_PROB_WEIGHT = 1000       # Peso da probabilidade média de transição bigrama (Markov)

# Fallback heurístico quando nenhum modelo estatístico está carregado
FALLBACK_DEFAULT_SCORE = 80        # Pontuação base padrão para combinações não mapeadas no fallback
FALLBACK_BIGRAM_SCORES = {
    ("NAME", "YEAR"): 300,
    ("NAME", "NUMBER"): 260,
    ("WORD", "YEAR"): 220,
    ("WORD", "NUMBER"): 210,
    ("NAME", "MONTH"): 280,
    ("WORD", "MONTH"): 240,
    ("NAME", "NAME"): 170,
    ("WORD", "WORD"): 150,
    ("NAME", "WORD"): 150,
    ("YEAR", "NAME"): 200,
    ("NUMBER", "NAME"): 200,
    ("MONTH", "NAME"): 180,
}

# Penalidades estruturais e comportamentais (aplicadas quando sem modelo estatístico)
NUMBER_PREFIX_PENALTY = 0.1        # Senhas raramente começam com dígitos isolados quando há palavras
SYMBOL_PREFIX_PENALTY = 0.05       # Senhas raramente começam com símbolos ou separadores
WORD_NOT_FIRST_PENALTY = 0.05      # Penalidade quando a palavra/nome não está na primeira posição
ONLY_NUMBERS_PENALTY = 0.1         # Penalidade se a senha for composta exclusivamente por números
EXCESSIVE_DELIMITERS_PENALTY = 0.1 # Penalidade contra poluição de pontuação múltipla (>1 separador, >1 símbolo ou >2 números)

# Bonificações e ajustes de tamanho
YEAR_SUFFIX_BONUS = 20             # Bônus para ano posicionado no final da senha (hábito humano comum: ex: target2024)
SYNTHETIC_TOKEN_PENALTY = 0.5      # Penalidade de 50% para combinações contendo anos/tokens sintéticos injetados
BASE_LENGTH_SCORE = 50             # Pontuação máxima de base proporcional ao número de tokens
TOKEN_COUNT_PENALTY_WEIGHT = 8     # Penalidade por token adicional para privilegiar combinações concisas

# Prioridades do Ranker customizado (--rank)
RANKER_TIER_EXACT_MATCH = 1000000000   # Base da regra #1; regras descem por RANKER_INDEX_DECAY preservando #1 > #2 > #3
RANKER_TIER_EQUIV_MATCH = 500000000    # Referência legada de equivalência
RANKER_TIER_PREFIX_MATCH = 10000000    # Tier de prefixo com tokens extras (abaixo de Exact/Equiv)
RANKER_INDEX_DECAY = 5000000           # Degrau entre regras consecutivas do Ranker
RANKER_EXACT_QUAL_BONUS = 2000000      # Dentro da mesma regra, Exact (m=3) vence Equivalent (m=2)
RANKER_EQUIV_QUAL_BONUS = 1000000

LEET_MAP = {
    'a': ['4', '@', 'A'],
    'e': ['3', 'E'],
    'i': ['1', '!', 'I'],
    'o': ['0', 'O'],
    's': ['5', '$', 'S'],
    't': ['7', 'T'],
    'b': ['8', '6'],
    'g': ['9', '6'],
    'l': ['1', '|'],
    'z': ['2']
}


def mutate_case(word, user_forced_case=None):
    """
    Motor de variação de maiúsculas/minúsculas baseado em tendências humanas.
    """
    if word.isdigit():
        return {word}

    variants = {word, word.lower(), word.upper(), word.capitalize()}

    if user_forced_case:
        if user_forced_case == "LOWER":
            return {word.lower()}
        if user_forced_case == "UPPER":
            return {word.upper()}
        if user_forced_case == "CAPITALIZE":
            return {word.capitalize()}

    # 1. Toggle Case (gUSTAVO)
    if len(word) > 1:
        variants.add(word[0].lower() + word[1:].upper())

    # 2. Alternating Case (GuStAvO)
    alt = "".join([c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(word)])
    variants.add(alt)

    # 3. End Capital (gustavO)
    if len(word) > 1:
        variants.add(word[:-1].lower() + word[-1].upper())

    return variants


def mutate_full_case(word, max_combos=512):
    """
    Motor de variação completa de maiúsculas/minúsculas (-c / --case).
    Gera todas as combinações binárias 2^N possíveis de maiúsculas e minúsculas
    para a palavra (ex: banana -> banana, Banana, bAnana, baNana, banAna, etc.).
    """
    if word.isdigit():
        return {word}

    char_options = [(c.lower(), c.upper()) if c.isalpha() else (c,) for c in word]
    total_possibilities = 1
    for opts in char_options:
        total_possibilities *= len(opts)

    if total_possibilities <= max_combos:
        return {"".join(p) for p in itertools.product(*char_options)}
    else:
        variants = {word, word.lower(), word.upper(), word.capitalize()}
        if len(word) > 1:
            variants.add(word[0].lower() + word[1:].upper())
            variants.add(word[:-1].lower() + word[-1].upper())
        alt = "".join([c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(word)])
        variants.add(alt)

        for i in range(len(word)):
            if word[i].isalpha():
                v = word.lower()
                variants.add(v[:i] + v[i].upper() + v[i+1:])
                v_up = word.upper()
                variants.add(v_up[:i] + v_up[i].lower() + v_up[i+1:])

        head_len = min(7, len(word))
        head_options = [(c.lower(), c.upper()) if c.isalpha() else (c,) for c in word[:head_len]]
        tail = word[head_len:].lower()
        for head in itertools.product(*head_options):
            variants.add("".join(head) + tail)

        return variants


def mutate_leet(word, allow_symbols=False):
    """
    Gera variações de leet speak baseadas em popularidade (ex: a->4, e->3, o->0).
    Símbolos (@, $, !, |) só são incluídos se allow_symbols=True (-S).
    """
    variants = {word}
    word_low = word.lower()
    word_up = word.upper()

    # 1. Light Leet (Vogais mais comuns)
    vowels_map = {
        'a': '@' if allow_symbols else '4',
        'e': '3',
        'i': '!' if allow_symbols else '1',
        'o': '0',
        's': '$' if allow_symbols else '5'
    }
    v_word_low = "".join([vowels_map.get(c, c) for c in word_low])
    v_word_up = "".join([vowels_map.get(c.lower(), c.lower()).upper() if c.lower() in vowels_map else c for c in word_up])

    variants.add(v_word_low)
    variants.add(v_word_low.capitalize())
    variants.add(v_word_up)

    # 2. Full Leet Deep Exploration
    char_options = []
    for char in word_low:
        if char in LEET_MAP:
            opts = [char] + [x for x in LEET_MAP[char] if allow_symbols or x.isalnum()]
            char_options.append(opts)
        else:
            char_options.append([char])

    possibilities = 1
    for opts in char_options:
        possibilities *= len(opts)

    if possibilities <= 512:
        for combo in itertools.product(*char_options):
            new_word = "".join(combo)
            variants.add(new_word)
            variants.add(new_word.capitalize())
    else:
        v1_chars = [LEET_MAP[c][0] if c in LEET_MAP and (allow_symbols or LEET_MAP[c][0].isalnum()) else c for c in word_low]
        v1 = "".join(v1_chars)
        variants.update({v1, v1.capitalize(), v1.upper()})

    return variants


def mutate_nicknames(word):
    """
    Gera apelidos comuns e variações regionais brasileiras.
    Ex: Gustavo -> Gusta, Gu, Guxta, Gustinha, Gustazera.
    """
    variants = {word}
    word_low = word.lower()

    if len(word_low) <= 2:
        return variants

    # 1. Abreviações curtas e médias
    if len(word_low) >= 4:
        variants.add(word_low[:len(word_low) // 2])
        variants.add(word_low[:len(word_low) - 2])
        variants.add(word_low[:len(word_low) - 1])

    # 2. Variações Fonéticas e Gírias
    if 's' in word_low:
        variants.add(word_low.replace('s', 'x'))
        variants.add(word_low[:len(word_low) - 2].replace('s', 'x'))

    # 3. Diminutivos, Aumentativos e Sufixos BR
    root = word_low[:-1] if word_low[-1] in 'aeiou' else word_low
    suffixes = [
        "inho", "inha", "ao", "zao", "zinho", "zinha",
        "zera", "era", "zika", "ito", "ita", "top",
        "br", "01", "ofc", "oficial"
    ]

    for s in suffixes:
        variants.add(root + s)

    if word_low[-1] in 'oa':
        variants.add(word_low[:-1] + 'y')
        variants.add(word_low[:-1] + 'h')

    return variants


def normalize_text(text):
    return unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("ASCII")


STANDARD_DNA_TYPES = {
    "NAME", "WORD", "YEAR", "NUMBER", "MONTH", "SYMBOL",
    "SEPARATOR", "DATE", "SEASON", "WEAK_WORD", "REPEATED", "KEY_WALK"
}


def token_type_match_score(up, cp, strict_rank=False, is_digit_token=None):
    """
    Equivalência de tipos do Ranker:
    - Modo padrão (strict_rank=False):
      2 = Exact Match (ex: GAME == GAME)
      1 = Equivalent Match (ex: WORD ~ GAME, NAME ~ WORD, YEAR ~ NUMBER)
      0 = No Match
    - Modo estrito da Fase 1 (strict_rank=True):
      Não mistura NAME <-> WORD nem YEAR <-> NUMBER para não sequestrar padrões da IA;
      permite apenas custom tokens (ex: GAME) -> WORD e KEY_WALK numérico (ex: 123) -> NUMBER.
    """
    up = up.upper()
    cp = cp.upper()
    if up == cp:
        return 2

    if strict_rank:
        if up == "WORD" and cp not in STANDARD_DNA_TYPES:
            return 1
        if up == "NUMBER" and cp == "KEY_WALK" and (is_digit_token is True):
            return 1
        return 0

    word_types = {"WORD", "NAME", "GAME", "WEAK_WORD", "SEASON"}
    num_types = {"NUMBER", "YEAR", "DATE", "KEY_WALK"}

    up_is_word = up in word_types or up not in STANDARD_DNA_TYPES
    cp_is_word = cp in word_types or cp not in STANDARD_DNA_TYPES
    if up_is_word and cp_is_word:
        return 1

    up_is_num = up in num_types
    cp_is_num = cp in num_types
    if up_is_num and cp_is_num:
        return 1

    return 0


def _evaluate_rank_alignment_detail(user_pattern, candidate_signature, ignore_separators=False, strict_rank=False, digit_flags=None):
    """
    Compara alinhamento estrutural entre user_pattern e candidate_signature.
    Retorna (m_quality, sum_token_scores), onde m_quality é 3 (Exact), 2 (Equivalent), 1 (Prefix) ou 0.
    Quando ignore_separators=False, exige aderência estrita de SYMBOL e SEPARATOR.
    """
    clean_user = user_pattern.upper().replace("@", "A").replace("0", "O").strip()
    clean_cand = candidate_signature.upper().strip()

    raw_u = [p.strip() for p in clean_user.split("+") if p.strip()]
    raw_c = [p.strip() for p in clean_cand.split("+") if p.strip()]

    if ignore_separators:
        u_parts = [p for p in raw_u if p != "SEPARATOR"]
        c_parts = [p for p in raw_c if p != "SEPARATOR"]
        c_digits = [digit_flags[idx] for idx, p in enumerate(raw_c) if p != "SEPARATOR"] if digit_flags else None
    else:
        u_parts = raw_u
        c_parts = raw_c
        c_digits = list(digit_flags) if digit_flags else None

    if not u_parts or len(c_parts) < len(u_parts):
        return 0, 0

    c_prefix = c_parts[:len(u_parts)]
    scores = [
        token_type_match_score(
            up,
            cp,
            strict_rank=strict_rank,
            is_digit_token=(c_digits[idx] if c_digits and idx < len(c_digits) else None),
        )
        for idx, (up, cp) in enumerate(zip(u_parts, c_prefix))
    ]

    if any(s == 0 for s in scores):
        return 0, 0

    u_sym = sum(1 for p in raw_u if p == "SYMBOL")
    u_sep = sum(1 for p in raw_u if p == "SEPARATOR")
    c_sym = sum(1 for p in raw_c if p == "SYMBOL")
    c_sep = sum(1 for p in raw_c if p == "SEPARATOR")

    if not ignore_separators:
        # Se a regra pede SYMBOL ou SEPARATOR, não permitir adicionar delimitadores extras
        if (u_sym > 0 or u_sep > 0) and (c_sym != u_sym or c_sep != u_sep):
            return 0, 0
        # Se a regra não pede símbolos/separadores, não promover candidatos com múltiplos delimitadores no prefixo
        if u_sym == 0 and u_sep == 0 and (c_sym + c_sep) > 1:
            return 0, 0
    else:
        if u_sym > 0 and c_sym != u_sym:
            return 0, 0

    is_exact_types = all(s == 2 for s in scores)
    is_exact_length = (len(c_parts) == len(u_parts))
    detail_sum = sum(scores)

    if is_exact_types and is_exact_length:
        return 3, detail_sum
    elif is_exact_length:
        return 2, detail_sum
    else:
        return 1, detail_sum


def _evaluate_rank_alignment(user_pattern, candidate_signature, ignore_separators=False):
    m_quality, _ = _evaluate_rank_alignment_detail(user_pattern, candidate_signature, ignore_separators=ignore_separators)
    return m_quality


def evaluate_pattern_match(user_pattern, candidate_signature):
    """
    Avalia a aderência de candidate_signature ao user_pattern do Ranker.
    Retorna:
    3 = Exact Match & Exact Length (ex: GAME+NUMBER == GAME+NUMBER, NAME+SYMBOL+YEAR == NAME+SYMBOL+YEAR)
    2 = Equivalent Match & Exact Length (ex: WORD+NUMBER para GAME+NUMBER)
    1 = Prefix Match com tokens extras (ex: GAME+NUMBER+SYMBOL para GAME+NUMBER)
    0 = No Match
    """
    return _evaluate_rank_alignment(user_pattern, candidate_signature, ignore_separators=False)


def pattern_signatures_match(user_pattern, candidate_signature):
    return evaluate_pattern_match(user_pattern, candidate_signature) > 0


def _rank_boost_from_quality(m_quality, idx_rank, detail_score=0):
    """
    Calcula o boost do Ranker respeitando primeiro a ordem das regras (#1 > #2 > #3...),
    depois qualidade dentro da mesma regra (Exact > Equivalent), sempre acima da Fase 2.
    """
    if m_quality <= 0:
        return 0
    if m_quality >= 2:
        rule_base = max(100_000_000, RANKER_TIER_EXACT_MATCH - (idx_rank * RANKER_INDEX_DECAY))
        qual_bonus = RANKER_EXACT_QUAL_BONUS if m_quality == 3 else RANKER_EQUIV_QUAL_BONUS
        return rule_base + qual_bonus + (detail_score * 10_000)

    base_tier = max(2_000_000, RANKER_TIER_PREFIX_MATCH - (idx_rank * 200_000))
    return base_tier + (detail_score * 10_000)


def _select_best_rank_rule(candidates):
    """
    Seleciona a regra vencedora para um candidato dentre os matches válidos [(m_quality, idx_rank, detail_score, ...)].
    Prioriza maior m_quality (para um Exact em #3 não ser engolido por Equiv em #1) e desempata por menor idx_rank.
    """
    return max(candidates, key=lambda item: (item[0], -item[1], item[2]))


def calculate_ranker_boost(custom_rank, signature, min_quality=1, strict_rank=False, digit_flags=None):
    """
    Calcula a pontuação de prioridade do Ranker personalizado.
    Ordem primária: posição da regra na lista do usuário (#1 > #2 > #3...).
    Dentro da mesma regra: Exact (3) > Equivalent (2) > Prefix (1).
    """
    if not custom_rank:
        return 0

    matches = []
    for idx_rank, user_pattern in enumerate(custom_rank):
        m_quality, detail_score = _evaluate_rank_alignment_detail(
            user_pattern,
            signature,
            ignore_separators=False,
            strict_rank=strict_rank,
            digit_flags=digit_flags,
        )
        if m_quality >= min_quality:
            matches.append((m_quality, idx_rank, detail_score))
    if not matches:
        return 0
    best_q, best_idx, best_detail = _select_best_rank_rule(matches)
    return _rank_boost_from_quality(best_q, best_idx, detail_score=best_detail)


def valid_length(candidate, target_length):
    if len(candidate) > MAX_INTERNAL_LENGTH:
        return False
    if target_length in ALLOWED_LENGTHS:
        return len(candidate) == target_length
    return True


def calculate_score(types, token_count, values=None, model=None, token_metas=None):
    """
    Pontua uma combinação de tokens: usa as probabilidades do modelo treinado
    quando existem, senão aplica as penalidades/bônus heurísticos abaixo.
    """
    t_list = list(types)
    t_set = set(types)

    # 1. Regra Absoluta: NUNCA duplicar anos ou datas na mesma senha!
    year_count = sum(1 for t in t_list if t in ("YEAR", "DATE"))
    if year_count > 1:
        return 0

    # 2. Regra Absoluta: Rejeitar combinações puramente sintéticas (anos que o usuário não pediu)
    if token_metas and all(m.get("synthetic") for m in token_metas):
        return 0

    trainer_base = 0
    STANDARD_TYPES = {"NAME", "WORD", "YEAR", "NUMBER", "MONTH", "SYMBOL", "SEPARATOR", "DATE", "SEASON", "WEAK_WORD", "REPEATED", "KEY_WALK"}

    if model and (model.pattern_probabilities or model.token_probabilities):
        # 1. Consulta primeiro a assinatura exata (ex: NAME+KEY_WALK a 0.23% não deve virar NAME+NUMBER a 6.15%)
        exact_sig = "+".join(t_list)
        exact_prob = model.get_pattern_probability(exact_sig)
        has_custom = any(t not in STANDARD_TYPES for t in t_list)

        if exact_prob > 0 or (
            has_custom and any(model.get_token_probability(t) > 0 for t in t_list if t not in STANDARD_TYPES)
        ):
            trainer_types = list(t_list)
            pattern_prob = exact_prob
        else:
            # Fallback para tokens customizados desconhecidos (-> WORD) ou KEY_WALK sem padrão próprio (-> NUMBER)
            trainer_types = []
            for t in t_list:
                if t == "KEY_WALK":
                    trainer_types.append("NUMBER")
                elif t not in STANDARD_TYPES:
                    trainer_types.append("WORD")
                else:
                    trainer_types.append(t)
            trainer_sig = "+".join(trainer_types)
            pattern_prob = model.get_pattern_probability(trainer_sig)

            # Token numérico r=1 (YEAR/DATE/KEY_WALK) herda fallback descontado de NUMBER quando ausente como padrão solo
            if pattern_prob == 0 and len(t_list) == 1 and t_list[0] in ("YEAR", "DATE", "KEY_WALK"):
                num_solo_prob = model.get_pattern_probability("NUMBER")
                if num_solo_prob > 0:
                    pattern_prob = num_solo_prob * 0.3
            elif len(t_list) == 1 and t_list[0] == "KEY_WALK" and trainer_types == ["NUMBER"] and exact_prob == 0:
                # KEY_WALK r=1 sem entrada nativa fica descontado abaixo de NUMBER exato
                pattern_prob = pattern_prob * 0.3

        token_probs = [model.get_token_probability(t) for t in trainer_types]
        avg_token_prob = (sum(token_probs) / len(token_probs)) if token_probs else 0.0

        trans_probs = [
            model.get_transition_probability(trainer_types[i], trainer_types[i + 1])
            for i in range(len(trainer_types) - 1)
        ]
        avg_trans_prob = (sum(trans_probs) / len(trans_probs)) if trans_probs else 0.0

        if pattern_prob > 0:
            # Padrões realmente observados no dataset vencem sempre combinações inéditas (P=0)
            trainer_base += TRAINED_PATTERN_TIER_BONUS + int(pattern_prob * PATTERN_PROB_WEIGHT)
            trainer_base += int(avg_token_prob * 100) + int(avg_trans_prob * 100)
        else:
            # Sem padrão exato no modelo: usa média unigrama + Markov sem inflar por número de tokens
            if len(trainer_types) == 1:
                trainer_base += int(avg_token_prob * (TOKEN_PROB_WEIGHT + TRANSITION_PROB_WEIGHT * 0.5))
            else:
                trainer_base += int(avg_token_prob * TOKEN_PROB_WEIGHT) + int(avg_trans_prob * TRANSITION_PROB_WEIGHT)
    else:
        normalized_t = [t if t in ["NAME", "WORD", "YEAR", "NUMBER", "MONTH", "SYMBOL", "SEPARATOR"] else ("NUMBER" if t == "KEY_WALK" else "WORD") for t in t_list]
        prefix = tuple(normalized_t[:2])
        trainer_base = FALLBACK_BIGRAM_SCORES.get(prefix, FALLBACK_DEFAULT_SCORE)

    score = trainer_base

    # Penalidades comportamentais: APENAS quando não houver modelo estatístico ativo!
    if not model or not model.pattern_probabilities:
        # Penalidades de posição só se aplicam quando há mais de 1 token
        # (r=1 single-token é uma senha inteira, não tem "prefixo" errado)
        if len(t_list) > 1 and t_list[0] in ["SYMBOL", "SEPARATOR", "NUMBER"]:
            if t_list[0] == "NUMBER":
                score = int(score * NUMBER_PREFIX_PENALTY)
            else:
                score = int(score * SYMBOL_PREFIX_PENALTY)

        if len(t_list) > 1 and ("WORD" in t_set or "NAME" in t_set):
            first_word_idx = next((i for i, t in enumerate(t_list) if t in ["WORD", "NAME"]), -1)
            if first_word_idx > 0:
                score = int(score * WORD_NOT_FIRST_PENALTY)

        # Penaliza só-números APENAS no fallback heurístico e quando há mais de 1 token
        # (tokens r=1 como NUMBER ou YEAR sozinhos são senhas válidas: 123, 2024)
        if t_set == {"NUMBER"} and len(t_list) > 1:
            score = int(score * ONLY_NUMBERS_PENALTY)

    # Penalidade contra poluição de pontuação múltipla (SYMBOL + SEPARATOR acumulados ou repetidos)
    total_punct = t_list.count("SEPARATOR") + t_list.count("SYMBOL")
    has_trained_multi_punct = False
    if total_punct > 1 and model and model.pattern_probabilities:
        has_trained_multi_punct = (model.get_pattern_probability("+".join(t_list)) > 0)
    if (total_punct > 1 and not has_trained_multi_punct) or t_list.count("NUMBER") > 2:
        score = int(score * EXCESSIVE_DELIMITERS_PENALTY)

    # Bonificação para ano no final de senha composta (comportamento humano padrão: ex: xbox2025)
    if len(t_list) > 1 and "YEAR" in t_set and t_list[-1] == "YEAR":
        score += YEAR_SUFFIX_BONUS

    # Penalidade para anos sintéticos vs tokens reais fornecidos pelo usuário
    if token_metas and any(m.get("synthetic") for m in token_metas):
        score = int(score * SYNTHETIC_TOKEN_PENALTY)

    score += max(0, BASE_LENGTH_SCORE - (token_count * TOKEN_COUNT_PENALTY_WEIGHT))
    return max(0, score)


NON_LEET_TYPES = {"NUMBER", "YEAR", "DATE", "MONTH", "SYMBOL", "SEPARATOR", "KEY_WALK"}
LEET_CHARS = set("@04315$78926|")


def _parse_rank_token_rule(user_token):
    """Extrai regra de casing ('CAPITALIZE', 'LOWER', None) e flag de leet de um token do Ranker."""
    has_lower = any(c.islower() for c in user_token)
    has_upper = any(c.isupper() for c in user_token)
    if has_lower and has_upper:
        case_rule = "CAPITALIZE"
    elif has_lower and not has_upper:
        case_rule = "LOWER"
    else:
        case_rule = None
    needs_leet = ("@" in user_token or "0" in user_token)
    return case_rule, needs_leet


def _extract_required_sep_gaps(raw_parts, r, sym_pos):
    """
    Identifica em quais lacunas (0..r-2) o padrão do Ranker exige SEPARATOR explícito.
    Retorna frozenset com os índices das lacunas ou None se a posição de SEPARATOR for inválida.
    """
    if r <= 1:
        return None if any(p.upper() == "SEPARATOR" for p in raw_parts) else frozenset()

    req_gaps = set()
    non_sep_seen = 0
    cand_len = r + (1 if sym_pos is not None else 0)

    for idx_part, part in enumerate(raw_parts):
        up = part.upper()
        if up == "SEPARATOR":
            # SEPARATOR só é válido exatamente entre dois tokens (não no início/fim)
            if idx_part == 0 or idx_part == len(raw_parts) - 1:
                return None
            # Mapeia para a lacuna entre tokens-base (sym_pos no meio substitui a própria lacuna)
            if sym_pos is not None:
                # Posição imediatamente antes/depois do símbolo injetado não aceita separador duplicado
                if non_sep_seen == sym_pos or non_sep_seen - 1 == sym_pos:
                    return None
                base_gap = (non_sep_seen - 1) if non_sep_seen < sym_pos else (non_sep_seen - 2)
            else:
                base_gap = non_sep_seen - 1
            if base_gap < 0 or base_gap >= r - 1:
                return None
            req_gaps.add(base_gap)
        else:
            non_sep_seen += 1
            if non_sep_seen > cand_len:
                break

    return frozenset(req_gaps)


def _resolve_strategic_spec(custom_rank, base_types, sym_pos=None, min_quality=2, strict_rank=False, base_values=None):
    """
    Resolve a regra estratégica vencedora de custom_rank para base_types com símbolo opcional em sym_pos.
    Por padrão exige min_quality=2 (Exact ou Equivalent de tamanho compatível) para que
    combinações mais longas apenas de prefixo não furem a fila na frente da IA treinada.
    Retorna (user_pattern, token_rules_dict, required_sep_gaps, best_boost) ou None.
    """
    if not custom_rank:
        return None

    r = len(base_types)
    digit_flags_base = [bool(v.isdigit()) for v in base_values] if base_values else [False] * r
    if sym_pos is None:
        cand_types = list(base_types)
        cand_map = list(range(r))
        cand_digits = digit_flags_base
    else:
        cand_types = list(base_types[:sym_pos]) + ["SYMBOL"] + list(base_types[sym_pos:])
        cand_map = list(range(sym_pos)) + [None] + list(range(sym_pos, r))
        cand_digits = digit_flags_base[:sym_pos] + [False] + digit_flags_base[sym_pos:]

    cand_sig = "+".join(cand_types)
    matches = []

    for idx_rank, user_pattern in enumerate(custom_rank):
        raw_parts = [p.strip() for p in user_pattern.split("+") if p.strip()]
        has_sep_rule = any(p.upper() == "SEPARATOR" for p in raw_parts)
        req_gaps = _extract_required_sep_gaps(raw_parts, r, sym_pos)
        if has_sep_rule and req_gaps is None:
            continue

        m_quality, detail_score = _evaluate_rank_alignment_detail(
            user_pattern,
            cand_sig,
            ignore_separators=has_sep_rule,
            strict_rank=strict_rank,
            digit_flags=cand_digits,
        )
        if m_quality >= min_quality:
            sep_gaps = req_gaps if req_gaps is not None else frozenset()
            matches.append((m_quality, idx_rank, detail_score, user_pattern, sep_gaps))

    if not matches:
        return None

    best_q, best_idx, best_detail, best_pattern, best_sep_gaps = _select_best_rank_rule(matches)
    best_boost = _rank_boost_from_quality(best_q, best_idx, detail_score=best_detail)

    raw_parts = [p.strip() for p in best_pattern.split("+") if p.strip()]
    u_parts = [p for p in raw_parts if p.upper() != "SEPARATOR"]

    token_rules = {}
    for up, base_i in zip(u_parts, cand_map):
        if base_i is not None:
            case_rule, needs_leet = _parse_rank_token_rule(up)
            token_rules[base_i] = (case_rule, needs_leet, up)

    return best_pattern, token_rules, best_sep_gaps, best_boost


def _leet_substitution_distance(candidate, original):
    """Conta quantas posições alfanuméricas diferem (ignorando maiúsculas/minúsculas) da palavra base."""
    orig_low = original.lower()
    cand_low = candidate.lower()
    if len(cand_low) != len(orig_low):
        return abs(len(cand_low) - len(orig_low)) + 3
    return sum(1 for a, b in zip(cand_low, orig_low) if a != b)


def _variant_sort_key(word, original):
    """Ordena mutações priorizando formas humanas naturais antes de variações exóticas/leet pesado."""
    if word.isdigit():
        return (0, 0, len(word), word)
    if word == original.capitalize():
        return (0, 0, len(word), word)
    if word == original.lower():
        return (0, 1, len(word), word)
    if word == original:
        return (0, 2, len(word), word)
    if word == original.upper():
        return (0, 3, len(word), word)

    dist = _leet_substitution_distance(word, original)
    if dist == 0:
        # Casing exótico (gUSTAVO, GuStAvO, gustavO)
        return (2, 0, len(word), word)

    # Dentro do leet, formas com capitalização limpa (Gust@vo) vêm antes de casing misto aleatório (guST@vo)
    has_cap_shape = len(word) > 0 and (word[0].isupper() or not word[0].isalpha()) and not any(c.isupper() for c in word[1:])
    has_lower_shape = not any(c.isupper() for c in word)
    case_tier = 0 if has_cap_shape else (1 if has_lower_shape else 2)
    sym_tier = 0 if ("@" in word or "0" in word) else 1
    return (1, dist, case_tier, sym_tier, word)


def _build_token_variants(value, token_type, case_rule, force_leet, allow_symbols, full_case, allow_nicknames, limit_per_token):
    """Gera o conjunto controlado de variações de case, leet e apelidos para um token."""
    if full_case:
        vars_for_this = mutate_full_case(value)
    else:
        vars_for_this = mutate_case(value, user_forced_case=case_rule)

    if force_leet and token_type not in NON_LEET_TYPES and any(c.isalpha() for c in value):
        vars_for_this.update(mutate_leet(value, allow_symbols=allow_symbols))

    if token_type == "NAME" and allow_nicknames:
        vars_for_this.update(mutate_nicknames(value))

    vars_sorted = sorted(vars_for_this, key=lambda w: _variant_sort_key(w, value))
    if len(vars_sorted) > limit_per_token:
        vars_sorted = vars_sorted[:limit_per_token]

    return vars_sorted


def _build_candidate_with_symbol(case_combo, types, seps, sym, sym_pos):
    """Constrói a senha candidata e sua assinatura inserindo 'sym' na posição sym_pos (0..r)."""
    r = len(case_combo)
    parts_str = []
    sym_types = []

    if sym_pos == 0:
        parts_str.append(sym)
        sym_types.append("SYMBOL")

    for idx_t in range(r):
        parts_str.append(case_combo[idx_t])
        sym_types.append(types[idx_t])
        if idx_t < r - 1:
            if sym_pos == idx_t + 1:
                parts_str.append(sym)
                sym_types.append("SYMBOL")
            elif seps[idx_t]:
                parts_str.append(seps[idx_t])
                sym_types.append("SEPARATOR")

    if sym_pos == r:
        parts_str.append(sym)
        sym_types.append("SYMBOL")

    return "".join(parts_str), sym_types


def _compute_naturalness_bonus(case_combo, values, use_leet=False):
    """
    Pontua naturalidade das variações para que formas humanas (Gustavo, gustavo, GUSTAVO)
    e leet leve (Gust@vo) apareçam antes de variações artificiais (gUSTAVO, 9u$7@v0) na Fase 2.
    """
    bonus = 0
    for cand, orig in zip(case_combo, values):
        if orig.isdigit() or not any(c.isalpha() for c in orig):
            continue
        if cand == orig.capitalize() or cand == orig:
            bonus += 40
        elif cand == orig.lower():
            bonus += 35
        elif cand == orig.upper():
            bonus += 20
        elif any(ch in LEET_CHARS and ch not in orig for ch in cand):
            dist = _leet_substitution_distance(cand, orig)
            bonus += max(2, 16 - dist * 3) if use_leet else max(1, 10 - dist * 3)
        elif cand.lower() != orig.lower():
            bonus += 6
    return bonus


def _compute_rank_affinity_bonus(spec, case_combo, values, emitted_types):
    """Desempate fino no mesmo tier do Ranker para priorizar casing pedido (NaME/word), @/0 e formas limpas."""
    if not spec:
        return 0
    _, token_rules, req_sep_gaps, _ = spec
    bonus = 0
    if req_sep_gaps and "SEPARATOR" in emitted_types:
        bonus += 50
    for base_i, (c_rule, needs_leet, raw_up) in token_rules.items():
        cand_tok = case_combo[base_i]
        orig_tok = values[base_i]
        has_leet = any(ch in LEET_CHARS and ch not in orig_tok for ch in cand_tok)
        dist = _leet_substitution_distance(cand_tok, orig_tok)

        if any(c.isalpha() for c in cand_tok):
            if c_rule == "CAPITALIZE":
                inner_uppers = sum(1 for ch in cand_tok[1:] if ch.isupper())
                first_ok = cand_tok[0].isupper() or (not cand_tok[0].isalpha())
                if first_ok and inner_uppers == 0:
                    bonus += 35
                elif inner_uppers > 0:
                    bonus -= 30
                else:
                    bonus -= 20
            elif c_rule == "LOWER":
                bonus += 35 if not any(ch.isupper() for ch in cand_tok) else -25
            else:
                if cand_tok == orig_tok.capitalize() or cand_tok == orig_tok:
                    bonus += 15
                elif cand_tok == orig_tok.lower():
                    bonus += 14
                elif cand_tok == orig_tok.upper():
                    bonus += 8

        if needs_leet:
            if "@" in raw_up and "@" in cand_tok and "@" not in orig_tok:
                bonus += max(60, 100 - dist)
            elif "0" in raw_up and "0" in cand_tok and "0" not in orig_tok:
                bonus += max(60, 100 - dist)
            elif has_leet:
                bonus += max(20, 50 - dist)
        else:
            # Se a regra não pediu leet (@/0), formas limpas vencem leet e símbolos internos
            if not has_leet and cand_tok.lower() == orig_tok.lower():
                bonus += 45
            elif has_leet:
                has_sym_leet = any(not ch.isalnum() and ch not in orig_tok for ch in cand_tok)
                bonus -= (15 + dist * 2) if has_sym_leet else (5 + dist)
    return bonus


def _push_heap_candidate(results_heap, limit, seen, score, candidate):
    """Insere um candidato único na fila de prioridade mantendo no máximo 'limit' itens."""
    if candidate not in seen:
        seen.add(candidate)
        if len(results_heap) < limit:
            heapq.heappush(results_heap, (score, candidate))
        elif score > results_heap[0][0]:
            heapq.heapreplace(results_heap, (score, candidate))


def _build_phase_sep_tuples(r, symbols, req_sep_gaps=None):
    """
    Gera tuplas de separadores compatíveis para r tokens.
    - Para Fase 1 (Ranker): coloca separadores apenas nas lacunas exigidas por req_sep_gaps.
    - Para Fase 2 (IA/Fallback sem símbolo injetado): testa sem separador e separadores consistentes.
    """
    if r <= 1:
        return [()]

    if req_sep_gaps is not None:
        if not req_sep_gaps:
            return [("",) * (r - 1)]
        if not symbols:
            return []
        non_empty = [s for s in COMMON_SEPARATORS if s]
        tuples = []
        for sep in non_empty:
            tuples.append(tuple(sep if g in req_sep_gaps else "" for g in range(r - 1)))
        return tuples

    if not symbols:
        return [("",) * (r - 1)]

    tuples = [(sep,) * (r - 1) for sep in COMMON_SEPARATORS]
    # Para r >= 3 com -S, inclui 1 separador em uma única lacuna (ex: NAME+SEPARATOR+WORD+YEAR)
    if r >= 3:
        non_empty = [s for s in COMMON_SEPARATORS if s]
        for gap_idx in range(r - 1):
            for sep in non_empty:
                tuples.append(tuple(sep if g == gap_idx else "" for g in range(r - 1)))
    return tuples


def _build_emitted_signature_with_digits(types, seps, sym_pos, values):
    """Monta (sig, digit_flags) para alinhar KEY_WALK numérico com NUMBER na Fase 1."""
    r = len(types)
    sig = []
    digits = []
    if sym_pos == 0:
        sig.append("SYMBOL")
        digits.append(False)
    for idx_t in range(r):
        sig.append(types[idx_t])
        digits.append(bool(values[idx_t].isdigit()) if values else False)
        if idx_t < r - 1:
            if sym_pos == idx_t + 1:
                sig.append("SYMBOL")
                digits.append(False)
            elif seps[idx_t]:
                sig.append("SEPARATOR")
                digits.append(False)
    if sym_pos == r:
        sig.append("SYMBOL")
        digits.append(False)
    return sig, digits


def _build_emitted_signature(types, seps, sym_pos):
    """Monta a assinatura estrutural (lista de tipos) para uma combinação de separadores e sym_pos."""
    sig, _ = _build_emitted_signature_with_digits(types, seps, sym_pos, None)
    return sig


def _compute_cognitive_bonus(values, is_osint, parsed_results):
    """Calcula bônus semântico para combinações OSINT."""
    if not is_osint or not parsed_results:
        return 0
    cognitive_bonus = 0
    semantic_map = parsed_results[0].meta.get("semantic_pairs", {})
    entity_clusters = parsed_results[0].meta.get("entity_clusters", {})

    if semantic_map:
        for i_pair in range(len(values) - 1):
            pair_key = f"{values[i_pair].lower()}:{values[i_pair + 1]}"
            if pair_key in semantic_map:
                cognitive_bonus += 300

    if entity_clusters:
        active_clusters = []
        for val in values:
            val_low = val.lower()
            for c_name, words in entity_clusters.items():
                if val_low in words:
                    active_clusters.append(c_name)
                    break
        if len(active_clusters) >= 2 and len(set(active_clusters)) == 1:
            cognitive_bonus += 400
    return cognitive_bonus


def generate_wordlist(parsed_results, target_length=None, max_words=None, symbols=False, model=None, use_leet=False, use_nicknames=False, leak_mode=False, custom_rank=None, full_case=False):
    """
    Gera a wordlist combinatória em duas fases com fila de prioridade (heap):
    - Fase 1 (Ranker): gera primeiro as combinações que obedecem exatamente às regras do usuário.
    - Fase 2 (IA Treinada / Fallback): preenche o restante na ordem de probabilidade do modelo treinado.
    """
    from rich.console import Console
    from ui_utils import start_progress_status, update_progress_status, stop_progress_status

    console = Console()
    limit = max_words if max_words else DEFAULT_MAX_WORDS
    results_heap = []
    seen = set()
    MAX_SEEN_SIZE = max(limit * 8, 50000)

    token_objects = []
    has_explicit_date = False

    is_osint = any(res.raw == "osint_scan" for res in parsed_results)

    for res in parsed_results:
        for t in res.tokens:
            boost = 15 if is_osint else 10
            norm_val = normalize_text(t.value)
            token_objects.append((t.token_type, norm_val, boost, {"synthetic": False, **t.meta}))
            if t.token_type in ["DATE", "YEAR", "MONTH"]:
                has_explicit_date = True

    # Deduplicação dos tokens fornecidos
    unique_tokens = {}
    for obj in token_objects:
        key = (obj[0], obj[1])
        if key not in unique_tokens:
            unique_tokens[key] = obj
    token_objects = list(unique_tokens.values())

    allowed_symbols = COMMON_SYMBOLS if symbols else []
    n_tokens = len(token_objects)
    limit_per_token = 512 if full_case else (120 if (max_words and max_words > 2000) else 48)

    start_progress_status(console, "Planejando estruturas estratégicas e da IA...")

    # Planeja todas as permutações válidas (r = 1..4) e separa em Fase 1 (Ranker) e Fase 2 (IA/Fallback)
    phase1_tasks = []
    phase2_tasks = []
    combo_cache = {}
    variant_cache_phase2 = {}

    for r in range(1, min(5, n_tokens + 1)):
        for combo in itertools.permutations(token_objects, r):
            types = tuple(x[0] for x in combo)
            values = tuple(x[1] for x in combo)
            boost_total = sum(x[2] for x in combo)
            token_metas = tuple(x[3] for x in combo)

            # 1. NUNCA permitir mais de 1 ano/data na mesma combinação
            if sum(1 for t in types if t in ("YEAR", "DATE")) > 1:
                continue

            # 2. Controle de anos sintéticos (injetados automaticamente)
            if not has_explicit_date:
                has_synth = any(m.get("synthetic") for m in token_metas)
                if has_synth:
                    if all(m.get("synthetic") for m in token_metas):
                        continue
                    synth_idx = next(i for i, m in enumerate(token_metas) if m.get("synthetic"))
                    if synth_idx not in (0, r - 1) or r > 3:
                        continue

            if sum(len(v) for v in values) > MAX_INTERNAL_LENGTH:
                continue

            base_score = calculate_score(types, r, values=values, model=model, token_metas=token_metas)
            if base_score <= 0:
                continue

            cognitive_bonus = _compute_cognitive_bonus(values, is_osint, parsed_results)
            combo_key = (r, types, values)
            combo_info = (r, types, values, boost_total, token_metas, cognitive_bonus)
            combo_cache[combo_key] = combo_info

            active_positions = [None] + (list(range(r + 1)) if symbols else [])

            # Fase 1: tarefas que casam estritamente com as regras do Ranker (-R)
            if custom_rank:
                for pos in active_positions:
                    spec = _resolve_strategic_spec(
                        custom_rank, types, sym_pos=pos, min_quality=2, strict_rank=True, base_values=values
                    )
                    if spec is None:
                        continue
                    _, _, req_sep_gaps, _ = spec
                    sep_tuples = _build_phase_sep_tuples(r, symbols, req_sep_gaps=req_sep_gaps)
                    for seps in sep_tuples:
                        emitted_sig, emitted_digits = _build_emitted_signature_with_digits(types, seps, pos, values)
                        s_score = calculate_score(emitted_sig, len(emitted_sig), values=None, model=model, token_metas=token_metas)
                        if s_score <= 0:
                            continue
                        rank_boost = calculate_ranker_boost(
                            custom_rank, "+".join(emitted_sig), min_quality=2, strict_rank=True, digit_flags=emitted_digits
                        )
                        if rank_boost <= 0:
                            continue
                        phase1_tasks.append((rank_boost + s_score, combo_key, pos, seps, spec, rank_boost, s_score))

            # Fase 2: tarefas guiadas exclusivamente pela ordem probabilística do modelo treinado (ou fallback)
            for pos in active_positions:
                if pos is None:
                    sep_tuples = _build_phase_sep_tuples(r, symbols, req_sep_gaps=None)
                else:
                    # Quando -S injeta símbolo na junção/borda, não empilhar separadores extras
                    sep_tuples = [("",) * (r - 1)] if r > 1 else [()]

                for seps in sep_tuples:
                    emitted_sig = _build_emitted_signature(types, seps, pos)
                    ai_score = calculate_score(emitted_sig, len(emitted_sig), values=None, model=model, token_metas=token_metas)
                    if ai_score <= 0:
                        continue
                    phase2_tasks.append((ai_score + (boost_total * 2) + cognitive_bonus, combo_key, pos, seps, ai_score))

    phase1_tasks.sort(key=lambda item: item[0], reverse=True)
    phase2_tasks.sort(key=lambda item: item[0], reverse=True)

    total_tasks = max(1, len(phase1_tasks) + len(phase2_tasks))
    processed_tasks = 0

    # ==========================================================================
    # FASE 1: RANKER DO USUÁRIO (Ordem explícita das regras .dna)
    # ==========================================================================
    phase1_variants_cache = {}
    for _, combo_key, pos, seps, spec, rank_boost, base_struct_score in phase1_tasks:
        if len(seen) >= MAX_SEEN_SIZE:
            break
        processed_tasks += 1
        update_progress_status(processed_tasks, total_tasks, "Applying Ranker rules")

        r, types, values, boost_total, token_metas, cognitive_bonus = combo_cache[combo_key]
        _, token_rules, _, _ = spec

        token_lists = []
        for i in range(r):
            if i in token_rules:
                c_rule, l_rule, _ = token_rules[i]
                forced_case = c_rule
                forced_leet = bool(l_rule or use_leet)
                allow_nick = bool(use_nicknames and not c_rule)
            else:
                forced_case = None
                forced_leet = use_leet
                allow_nick = use_nicknames

            v_key = (values[i], types[i], forced_case, forced_leet, allow_nick)
            if v_key not in phase1_variants_cache:
                phase1_variants_cache[v_key] = _build_token_variants(
                    values[i], types[i], forced_case, forced_leet, symbols, full_case, allow_nick, limit_per_token
                )
            token_lists.append(phase1_variants_cache[v_key])

        emitted_sig = _build_emitted_signature(types, seps, pos)
        for case_combo in itertools.product(*token_lists):
            if len(seen) >= MAX_SEEN_SIZE:
                break
            affinity = _compute_rank_affinity_bonus(spec, case_combo, values, emitted_sig)
            final_score = base_struct_score + (boost_total * 2) + cognitive_bonus + rank_boost + affinity

            if pos is None:
                cand = "".join(
                    case_combo[idx_t] + (seps[idx_t] if idx_t < r - 1 else "")
                    for idx_t in range(r)
                )
                if valid_length(cand, target_length):
                    _push_heap_candidate(results_heap, limit, seen, final_score, cand)
            else:
                for sym in allowed_symbols:
                    cand, _ = _build_candidate_with_symbol(case_combo, types, seps, sym, pos)
                    if valid_length(cand, target_length):
                        _push_heap_candidate(results_heap, limit, seen, final_score, cand)

    # ==========================================================================
    # FASE 2: MODELO DE IA TREINADO (ou fallback heurístico se não houver dataset)
    # Reserva um orçamento dedicado após o Ranker para sempre completar o restante
    # ==========================================================================
    phase2_budget = max(MAX_SEEN_SIZE, len(seen) + MAX_SEEN_SIZE)
    max_nat_bonus_per_r = {r_k: r_k * 40 for r_k in range(1, 5)}
    ai_label = "Generating via AI model" if (model and (model.pattern_probabilities or model.token_probabilities)) else "Generating combinations"

    for task_priority, combo_key, pos, seps, ai_score in phase2_tasks:
        if len(seen) >= phase2_budget:
            break
        processed_tasks += 1
        update_progress_status(processed_tasks, total_tasks, ai_label)

        r, types, values, boost_total, token_metas, cognitive_bonus = combo_cache[combo_key]

        # Poda exata: se o heap já está cheio e nem o teto máximo global de naturalidade vence o pior item, encerra
        if len(results_heap) >= limit:
            if (task_priority + 160) <= results_heap[0][0]:
                break
            if (task_priority + max_nat_bonus_per_r.get(r, 160)) <= results_heap[0][0]:
                continue

        token_lists = []
        for i in range(r):
            v_key = (values[i], types[i], None, use_leet, use_nicknames)
            if v_key not in variant_cache_phase2:
                variant_cache_phase2[v_key] = _build_token_variants(
                    values[i], types[i], None, use_leet, symbols, full_case, use_nicknames, limit_per_token
                )
            token_lists.append(variant_cache_phase2[v_key])

        for case_combo in itertools.product(*token_lists):
            if len(seen) >= phase2_budget:
                break
            nat_bonus = _compute_naturalness_bonus(case_combo, values, use_leet=use_leet)
            final_score = ai_score + (boost_total * 2) + cognitive_bonus + nat_bonus

            if len(results_heap) >= limit and final_score <= results_heap[0][0]:
                continue

            if pos is None:
                cand = "".join(
                    case_combo[idx_t] + (seps[idx_t] if idx_t < r - 1 else "")
                    for idx_t in range(r)
                )
                if valid_length(cand, target_length):
                    _push_heap_candidate(results_heap, limit, seen, final_score, cand)
            else:
                for sym in allowed_symbols:
                    cand, _ = _build_candidate_with_symbol(case_combo, types, seps, sym, pos)
                    if valid_length(cand, target_length):
                        _push_heap_candidate(results_heap, limit, seen, final_score, cand)

    stop_progress_status()
    sorted_res = sorted(results_heap, key=lambda x: x[0], reverse=True)
    return [r[1] for r in sorted_res]


def math_perm(n, r):
    """Calcula n! / (n - r)! de forma eficiente."""
    import math
    try:
        return math.perm(n, r)
    except AttributeError:
        # Fallback para Python < 3.8 se aplicável
        res = 1
        for i in range(r):
            res *= (n - i)
        return res
