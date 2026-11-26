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
PATTERN_PROB_WEIGHT = 100000        # Peso da probabilidade da assinatura completa de tipos (ex: NAME+YEAR)
TOKEN_PROB_WEIGHT = 500            # Peso da frequência unigrama de cada tipo de token individual
TRANSITION_PROB_WEIGHT = 1000      # Peso da probabilidade de transição bigrama entre tokens consecutivos

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
RANKER_TIER_EXACT_MATCH = 1000000000   # Tier 3: correspondência exata de tipos e comprimento
RANKER_TIER_EQUIV_MATCH = 500000000    # Tier 2: correspondência equivalente (ex: WORD ~ GAME)
RANKER_TIER_PREFIX_MATCH = 10000000    # Tier 1: correspondência de prefixo com tokens extras
RANKER_INDEX_DECAY = 5000000           # Decaimento por índice de prioridade na lista de padrões do usuário

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


def token_type_match_score(up, cp):
    """
    Equivalência inteligente de tipos do Ranker:
    2 = Exact Match (ex: GAME == GAME)
    1 = Equivalent Match (ex: WORD ~ GAME, NAME ~ WORD, YEAR ~ NUMBER)
    0 = No Match
    """
    up = up.upper()
    cp = cp.upper()
    if up == cp:
        return 2

    STANDARD_TYPES = {"NAME", "WORD", "YEAR", "NUMBER", "MONTH", "SYMBOL", "SEPARATOR", "DATE", "SEASON", "WEAK_WORD", "REPEATED", "KEY_WALK"}
    word_types = {"WORD", "NAME", "GAME", "WEAK_WORD", "SEASON"}
    num_types = {"NUMBER", "YEAR", "DATE", "KEY_WALK"}

    up_is_word = up in word_types or up not in STANDARD_TYPES
    cp_is_word = cp in word_types or cp not in STANDARD_TYPES
    if up_is_word and cp_is_word:
        return 1

    up_is_num = up in num_types
    cp_is_num = cp in num_types
    if up_is_num and cp_is_num:
        return 1

    return 0


def evaluate_pattern_match(user_pattern, candidate_signature):
    """
    Avalia a aderência de candidate_signature ao user_pattern do Ranker.
    Retorna:
    3 = Exact Match & Exact Length (ex: GAME+NUMBER == GAME+NUMBER, NAME+NUMBER == NAME+NUMBER)
    2 = Equivalent Match & Exact Length (ex: WORD+NUMBER para GAME+NUMBER)
    1 = Prefix Match com tokens extras (ex: GAME+NUMBER+WORD para GAME+NUMBER)
    0 = No Match
    """
    clean_user = user_pattern.upper().replace("@", "A").replace("0", "O").strip()
    u_parts = [p.strip() for p in clean_user.split("+") if p.strip() and p.strip() != "SEPARATOR"]
    c_parts = [p.strip() for p in candidate_signature.split("+") if p.strip() and p.strip() != "SEPARATOR"]

    if len(c_parts) < len(u_parts):
        return 0

    c_prefix = c_parts[:len(u_parts)]
    scores = [token_type_match_score(up, cp) for up, cp in zip(u_parts, c_prefix)]

    if any(s == 0 for s in scores):
        return 0

    is_exact_types = all(s == 2 for s in scores)
    is_exact_length = (len(c_parts) == len(u_parts))

    if is_exact_types and is_exact_length:
        return 3
    elif is_exact_length:
        return 2
    else:
        return 1


def pattern_signatures_match(user_pattern, candidate_signature):
    return evaluate_pattern_match(user_pattern, candidate_signature) > 0


def calculate_ranker_boost(custom_rank, signature):
    """
    Calcula a pontuação de prioridade do Ranker personalizado.
    Tier 3 (Exact): ~1.000.000.000+
    Tier 2 (Equivalent): ~500.000.000+
    Tier 1 (Prefix/Extra): ~10.000.000+
    """
    if not custom_rank:
        return 0

    best_boost = 0
    for idx_rank, user_pattern in enumerate(custom_rank):
        m_quality = evaluate_pattern_match(user_pattern, signature)
        if m_quality > 0:
            if m_quality == 3:
                base_tier = RANKER_TIER_EXACT_MATCH
            elif m_quality == 2:
                base_tier = RANKER_TIER_EQUIV_MATCH
            else:
                base_tier = RANKER_TIER_PREFIX_MATCH
            boost = max(0, base_tier - (idx_rank * RANKER_INDEX_DECAY))
            if boost > best_boost:
                best_boost = boost
    return best_boost


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
        # 1. Verifica se o modelo já conhece nativamente esses tokens (se foi treinado com eles)
        native_types = ["NUMBER" if t == "KEY_WALK" else t for t in t_list]
        native_sig = "+".join(native_types)
        native_prob = model.get_pattern_probability(native_sig)

        has_custom = any(t not in STANDARD_TYPES for t in t_list)
        if has_custom and (native_prob > 0 or any(model.get_token_probability(t) > 0 for t in native_types if t not in STANDARD_TYPES)):
            # Modelo foi treinado com os tokens customizados! Trata com a identidade original criada
            trainer_types = native_types
            pattern_prob = native_prob
        else:
            # Fallback inteligente: modelo não conhece o token customizado -> trata como WORD
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

        trainer_base += int(pattern_prob * PATTERN_PROB_WEIGHT)

        prev_t = None
        for t in trainer_types:
            trainer_base += int(model.get_token_probability(t) * TOKEN_PROB_WEIGHT)
            if prev_t:
                trans = model.get_transition_probability(prev_t, t)
                if trans > 0:
                    trainer_base += int(trans * TRANSITION_PROB_WEIGHT)
            prev_t = t
    else:
        normalized_t = [t if t in ["NAME", "WORD", "YEAR", "NUMBER", "MONTH", "SYMBOL", "SEPARATOR"] else ("NUMBER" if t == "KEY_WALK" else "WORD") for t in t_list]
        prefix = tuple(normalized_t[:2])
        trainer_base = FALLBACK_BIGRAM_SCORES.get(prefix, FALLBACK_DEFAULT_SCORE)

    score = trainer_base

    # Penalidades comportamentais: APENAS quando não houver modelo estatístico ativo!
    if not model or not model.pattern_probabilities:
        if t_list and t_list[0] in ["SYMBOL", "SEPARATOR", "NUMBER"]:
            if t_list[0] == "NUMBER":
                score = int(score * NUMBER_PREFIX_PENALTY)
            else:
                score = int(score * SYMBOL_PREFIX_PENALTY)

        if "WORD" in t_set or "NAME" in t_set:
            first_word_idx = next((i for i, t in enumerate(t_list) if t in ["WORD", "NAME"]), -1)
            if first_word_idx > 0:
                score = int(score * WORD_NOT_FIRST_PENALTY)

        if t_set == {"NUMBER"}:
            score = int(score * ONLY_NUMBERS_PENALTY)

    # Penalidade contra poluição de pontuação múltipla
    if t_list.count("SEPARATOR") > 1 or t_list.count("SYMBOL") > 1 or t_list.count("NUMBER") > 2:
        score = int(score * EXCESSIVE_DELIMITERS_PENALTY)

    # Bonificação para ano no final da senha (comportamento humano padrão: ex: xbox2025)
    if "YEAR" in t_set and t_list[-1] == "YEAR":
        score += YEAR_SUFFIX_BONUS

    # Penalidade para anos sintéticos vs tokens reais fornecidos pelo usuário
    if token_metas and any(m.get("synthetic") for m in token_metas):
        score = int(score * SYNTHETIC_TOKEN_PENALTY)

    score += max(0, BASE_LENGTH_SCORE - (token_count * TOKEN_COUNT_PENALTY_WEIGHT))
    return max(0, score)


def generate_wordlist(parsed_results, target_length=None, max_words=None, symbols=False, model=None, use_leet=False, use_nicknames=False, leak_mode=False, custom_rank=None, full_case=False):
    """
    Gera a wordlist combinatória com scoring e fila de prioridade (heap).
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

    # REGRA DE OURO DOS SÍMBOLOS: Símbolos e pontuações SÓ são permitidos com -S
    allowed_separators = ["", "_", "-", "."] if symbols else [""]
    allowed_symbols = COMMON_SYMBOLS if symbols else []
    user_casing_rule = None

    # Estima total de combinações
    n_tokens = len(token_objects)
    total_expected_combos = sum(
        math_perm(n_tokens, r) for r in range(1, min(5, n_tokens + 1))
    )
    current_combo_idx = 0

    start_progress_status(console, "Iniciando motor de permutação...")

    for r in range(1, min(5, n_tokens + 1)):
        if len(seen) >= MAX_SEEN_SIZE:
            break

        if custom_rank:
            min_rank_r = min(len(p.split("+")) for p in custom_rank)
            effective_r = (r + 1) if symbols else r
            if effective_r < min_rank_r:
                continue

        for combo in itertools.permutations(token_objects, r):
            current_combo_idx += 1
            if len(seen) >= MAX_SEEN_SIZE:
                break

            update_progress_status(current_combo_idx, total_expected_combos, "Generating combinations")

            types = [x[0] for x in combo]
            values = [x[1] for x in combo]
            boost_total = sum(x[2] for x in combo)
            token_metas = [x[3] for x in combo]
            pattern_signature = "+".join(types)

            # 1. NUNCA permitir mais de 1 ano/data na mesma combinação
            year_count = sum(1 for t in types if t in ("YEAR", "DATE"))
            if year_count > 1:
                continue

            # 2. Controle de anos sintéticos (injetados automaticamente)
            if not has_explicit_date:
                has_synth = any(m.get("synthetic") for m in token_metas)
                if has_synth:
                    # Não gerar senhas puramente sintéticas (só anos) quando usuário deu inputs
                    if all(m.get("synthetic") for m in token_metas):
                        continue
                    # Ano sintético só pode estar no início (prefixo) ou no fim (sufixo)
                    synth_idx = next(i for i, m in enumerate(token_metas) if m.get("synthetic"))
                    if synth_idx not in (0, r - 1):
                        continue
                    # Não criar permutações de 4 níveis se tiver ano sintético
                    if r > 3:
                        continue

            if sum(len(v) for v in values) > MAX_INTERNAL_LENGTH:
                continue

            base_score = calculate_score(types, r, values=values, model=model, token_metas=token_metas)
            if base_score <= 0:
                continue

            # Regras estratégicas de mutação a partir do ranker
            rank_leet_rules = [None] * r
            rank_case_rules = [None] * r
            is_strategic = False

            if custom_rank:
                for user_pattern in custom_rank:
                    if pattern_signatures_match(user_pattern, pattern_signature):
                        is_strategic = True
                        u_parts = user_pattern.split("+")
                        if len(u_parts) == r:
                            for i, up in enumerate(u_parts):
                                has_lower = any(c.islower() for c in up)
                                has_upper = any(c.isupper() for c in up)
                                if has_lower and has_upper:
                                    rank_case_rules[i] = "CAPITALIZE"
                                elif has_lower and not has_upper:
                                    rank_case_rules[i] = "LOWER"
                                else:
                                    rank_case_rules[i] = None
                                rank_leet_rules[i] = ("@" in up or "0" in up)
                        break

            component_variations = []
            for i, (t, v) in enumerate(zip(types, values)):
                forced_case = rank_case_rules[i] if is_strategic else user_casing_rule
                forced_leet = (rank_leet_rules[i] or use_leet) if is_strategic else use_leet

                if full_case:
                    vars_for_this = mutate_full_case(v)
                else:
                    vars_for_this = mutate_case(v, user_forced_case=forced_case)

                NON_LEET_TYPES = {"NUMBER", "YEAR", "DATE", "MONTH", "SYMBOL", "SEPARATOR", "KEY_WALK"}
                if forced_leet and t not in NON_LEET_TYPES and any(c.isalpha() for c in v):
                    vars_for_this.update(mutate_leet(v, allow_symbols=symbols))

                if t == "NAME" and use_nicknames and not (is_strategic and rank_case_rules[i]):
                    vars_for_this.update(mutate_nicknames(v))

                limit_per_token = 512 if full_case else (120 if (max_words and max_words > 2000) else (24 if r > 2 else 48))
                if len(vars_for_this) > limit_per_token:
                    vars_list = sorted(list(vars_for_this), key=len)[:limit_per_token]
                    vars_for_this = set(vars_list)

                component_variations.append(vars_for_this)

            for case_combo in itertools.product(*component_variations):
                if len(seen) >= MAX_SEEN_SIZE:
                    break

                # REGRA DE COERÊNCIA DE SEPARADORES:
                # Cada candidato usa um único separador consistente (ou nenhum, ou todo '_', ou todo '-', ou todo '.')
                # NUNCA misturar '-' com '_' ou '.' na mesma senha!
                if r == 1:
                    sep_combinations = [()]
                else:
                    sep_combinations = [(sep,) * (r - 1) for sep in allowed_separators]

                for seps in sep_combinations:
                    if len(seen) >= MAX_SEEN_SIZE:
                        break

                    base = ""
                    current_pattern_items = []
                    for i in range(r):
                        base += case_combo[i]
                        current_pattern_items.append(types[i])
                        if i < r - 1:
                            base += seps[i]
                            if seps[i]:
                                current_pattern_items.append("SEPARATOR")

                    if not valid_length(base, target_length):
                        continue

                    current_signature = "+".join(current_pattern_items)

                    # Bônus Cognitivo / Semântico
                    cognitive_bonus = 0
                    if is_osint and parsed_results:
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

                    if any(seps):
                        actual_base_score = calculate_score(current_pattern_items, len(current_pattern_items), values=None, model=model, token_metas=token_metas)
                    else:
                        actual_base_score = base_score

                    final_score = actual_base_score + (boost_total * 2) + cognitive_bonus
                    final_score += calculate_ranker_boost(custom_rank, current_signature)

                    if base not in seen:
                        seen.add(base)
                        if len(results_heap) < limit:
                            heapq.heappush(results_heap, (final_score, base))
                        elif final_score > results_heap[0][0]:
                            heapq.heapreplace(results_heap, (final_score, base))

                    # Injeção de Símbolos: ESTRITAMENTE quando symbols (-S) estiver ativo!
                    # Pontuação estrutural rigorosamente calculada contra a tabela probabilística ativa!
                    if symbols:
                        for sym in allowed_symbols:
                            # 1. Sufixo (ex: Xbox123!, Xbox123@)
                            candidate_end = base + sym
                            if valid_length(candidate_end, target_length) and candidate_end not in seen:
                                seen.add(candidate_end)
                                sym_types = list(current_pattern_items) + ["SYMBOL"]
                                sym_values = list(values) + [sym]
                                s_score = calculate_score(sym_types, len(sym_types), values=sym_values, model=model, token_metas=token_metas) + (boost_total * 2) + cognitive_bonus
                                s_score += calculate_ranker_boost(custom_rank, "+".join(sym_types))

                                if len(results_heap) < limit:
                                    heapq.heappush(results_heap, (s_score, candidate_end))
                                elif s_score > results_heap[0][0]:
                                    heapq.heapreplace(results_heap, (s_score, candidate_end))

                            # 2. Prefixo (ex: @Xbox123, !Xbox123)
                            candidate_start = sym + base
                            if valid_length(candidate_start, target_length) and candidate_start not in seen:
                                seen.add(candidate_start)
                                sym_types = ["SYMBOL"] + list(current_pattern_items)
                                sym_values = [sym] + list(values)
                                s_score = calculate_score(sym_types, len(sym_types), values=sym_values, model=model, token_metas=token_metas) + (boost_total * 2) + cognitive_bonus
                                s_score += calculate_ranker_boost(custom_rank, "+".join(sym_types))

                                if len(results_heap) < limit:
                                    heapq.heappush(results_heap, (s_score, candidate_start))
                                elif s_score > results_heap[0][0]:
                                    heapq.heapreplace(results_heap, (s_score, candidate_start))

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
