"""
Mutação a partir do DNA de uma única senha já analisada (usado pelo comando 'analyze').

- Reaproveita as mutações do Gen.py (mutate_case, mutate_leet, mutate_nicknames).
- Expande cada token usando clusters de palavras fracas, wordlists temáticas,
  custom tokens e ranges de anos/datas.
"""

import os
import sys
import itertools
import shutil
from pathlib import Path
from rich.console import Console

from config import WORDLISTS_DIR, YOU_WORDLIST_DIR, CUSTOM_TOKENS_DIR, NAMES_DATASET_FILE
from Gen import mutate_leet, mutate_case, mutate_nicknames

console = Console()

def get_wordlists_dir():
    """Retorna o diretório das wordlists originais (para leitura)."""
    return WORDLISTS_DIR

def load_wordlists():
    """Carrega todas as wordlists da pasta com suporte a progresso automático."""
    from ui_utils import start_progress_status, update_progress_status, stop_progress_status
    from i18n import get_text
    is_pt = '-Pt' in sys.argv or '--portuguese' in sys.argv
    lang = "pt" if is_pt else "en"
    
    wordlists_dir = get_wordlists_dir()
    wordlists = {}
    
    if not os.path.exists(wordlists_dir):
        return {}
        
    files = [f for f in os.listdir(wordlists_dir) if f.endswith(".txt")]
    if not files:
        return {}
        
    total_size = sum(os.path.getsize(os.path.join(wordlists_dir, f)) for f in files)
    
    start_progress_status(console, get_text("mutation", "loading_db", lang))

    current_file_start_offset = 0
    for filename in files:
        filepath = os.path.join(wordlists_dir, filename)
        file_size = os.path.getsize(filepath)
        current_file_words = []
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            while True:
                line = f.readline()
                if not line:
                    break
                    
                update_progress_status(current_file_start_offset + f.tell(), total_size, get_text("mutation", "loading_file", lang, filename=filename))
                
                w = line.strip()
                if w: current_file_words.append(w)
        
        wordlists[filename] = current_file_words
        current_file_start_offset += file_size
    
    stop_progress_status()
    return wordlists

def generate_years(base_year):
    """Gera uma lista de anos (base - 100 até base + 100)."""
    years = []
    base_int = int(base_year)
    
    # Range de -100 a +100
    for y in range(base_int - 100, base_int + 101):
        # Validação simples para evitar anos absurdos (mantemos 1900 até futuro)
        if 1900 <= y <= 2200:
            years.append(str(y))
    return years

def get_output_filename(password):
    """Gera um caminho de arquivo seguro dentro de YOU_WORDLIST_DIR."""
    os.makedirs(YOU_WORDLIST_DIR, exist_ok=True)
    safe_password = "".join(c if c.isalnum() else "_" for c in password)
    base_name = f"analyzed_{safe_password}"
    output_file = os.path.join(YOU_WORDLIST_DIR, f"{base_name}.txt")
    
    counter = 2
    while os.path.exists(output_file):
        output_file = os.path.join(YOU_WORDLIST_DIR, f"{base_name}_{counter}.txt")
        counter += 1
        
    return output_file

def load_custom_tokens():
    """
    Carrega todas as categorias e palavras dos Custom Tokens (custom_tokens/).
    Retorna:
      categories: dict -> {"NARUTOCHARACTER": ["kabuto", "naruto", "sasuke", ...], ...}
      word_map: dict -> {"kabuto": "NARUTOCHARACTER", "naruto": "NARUTOCHARACTER", ...}
    """
    from config import CUSTOM_TOKENS_DIR
    categories = {}
    word_map = {}
    
    if os.path.exists(CUSTOM_TOKENS_DIR):
        for folder in os.listdir(CUSTOM_TOKENS_DIR):
            folder_path = os.path.join(CUSTOM_TOKENS_DIR, folder)
            if os.path.isdir(folder_path):
                category_name = folder.upper()
                words = []
                for fname in os.listdir(folder_path):
                    if fname.lower().endswith(".txt"):
                        fpath = os.path.join(folder_path, fname)
                        try:
                            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                                for line in f:
                                    w = line.strip()
                                    if w:
                                        words.append(w)
                                        word_map[w.lower()] = category_name
                        except Exception:
                            pass
                if words:
                    categories[category_name] = list(dict.fromkeys(words))
                    
    return categories, word_map

def match_case(words_list, sample):
    """Aplica o padrão de maiúsculas/minúsculas do token original na lista de palavras."""
    if sample.isupper():
        return [w.upper() for w in words_list]
    elif sample.istitle():
        return [w.capitalize() for w in words_list]
    else:
        return [w.lower() for w in words_list]

# Semantic Weak Word Clusters (Cross-cultural forensics)
WEAK_WORD_CLUSTERS = {
    "admin": ["admin", "adm", "administrator", "administrador", "root", "user", "master"],
    "root": ["root", "toor", "admin", "superuser", "master", "user"],
    "senha": ["senha", "password", "pass", "mudar", "trocar", "padrao", "default", "123456"],
    "password": ["password", "senha", "pass", "admin", "default", "master", "123456"],
    "pass": ["pass", "password", "senha", "user", "admin", "123456"],
    "user": ["user", "usuario", "guest", "admin", "root", "client"],
    "master": ["master", "mestre", "chief", "leader", "admin", "root"],
    "welcome": ["welcome", "bemvindo", "hello", "ola", "start"],
    "default": ["default", "padrao", "admin", "root", "system"],
    "test": ["test", "teste", "testing", "dev", "demo", "temp"],
    "teste": ["teste", "test", "testing", "dev", "homolog", "demo"],
    "sistema": ["sistema", "system", "sucesso", "admin", "root"],
    "sucesso": ["sucesso", "sistema", "vitoria", "top", "brasil"],
    "brasil": ["brasil", "brazil", "futebol", "campeao", "verde", "amarelo"],
    "amor": ["amor", "love", "vida", "familia", "teamo", "paz"],
    "love": ["love", "amor", "life", "baby", "forever"],
    "vida": ["vida", "life", "viver", "amor", "luz", "paz"],
    "deus": ["deus", "jesus", "fe", "paz", "gloria", "cristo", "senhor"],
    "jesus": ["jesus", "cristo", "deus", "fe", "salvador", "senhor"],
    "familia": ["familia", "family", "amor", "uniao", "vida"],
    "futebol": ["futebol", "soccer", "gol", "flamengo", "corinthians", "palmeiras"],
    "flamengo": ["flamengo", "mengao", "rubronegro", "fla"],
    "corinthians": ["corinthians", "timao", "coringao", "sccp"],
    "palmeiras": ["palmeiras", "verdao", "alviverde", "palestra"]
}

def get_name_mutations(val, sample, use_name=False):
    """Gera variações forenses de nomes (apelidos, diminutivos, casing, leet, e dataset opcional)."""
    muts = [val]
    # Nicknames
    nicks = mutate_nicknames(val)
    muts.extend(match_case(list(nicks), sample))
    # Case variants
    muts.extend(list(mutate_case(val)))
    # Leet variants
    muts.extend(list(mutate_leet(val)))
    
    if use_name:
        common_names = [
            "lucas", "gabriel", "matheus", "felipe", "guilherme", "rodrigo", "bruno",
            "gustavo", "leonardo", "rafael", "danilo", "thiago", "marcelo", "fernando",
            "eduardo", "pedro", "joao", "caio", "diego", "vitor", "marcos", "andre",
            "ricardo", "alexandre", "carlos", "roberto", "antonio", "jose", "paulo",
            "juliana", "camila", "larissa", "amanda", "bruna", "leticia", "jessica",
            "mariana", "patricia", "aline", "beatriz", "fernanda", "carolina", "gabriela"
        ]
        muts.extend(match_case(common_names, sample))
    return list(dict.fromkeys(muts))

def get_weak_word_mutations(val, sample):
    """Gera variações para palavras fracas (clusters semânticos, casing e leet)."""
    val_lower = val.lower()
    muts = [val]
    for k, siblings in WEAK_WORD_CLUSTERS.items():
        if k in val_lower:
            muts.extend(match_case(siblings, sample))
    muts.extend(list(mutate_case(val)))
    muts.extend(list(mutate_leet(val)))
    return list(dict.fromkeys(muts))

def get_word_mutations(val, sample):
    """Gera variações para palavras genéricas de dicionário (casing e leet speak)."""
    muts = [val]
    if len(val) >= 2:
        muts.extend(list(mutate_case(val)))
        muts.extend(list(mutate_leet(val)))
    return list(dict.fromkeys(muts))

def get_year_mutations(val, use_year=False):
    """Gera variações de anos (smart range +/- 5 anos + 2 dígitos, ou +/- 100 com -y)."""
    base_int = int(val)
    muts = [val]
    if use_year:
        for y in range(base_int - 100, base_int + 101):
            if 1900 <= y <= 2200:
                muts.append(str(y))
    else:
        for y in range(base_int - 5, base_int + 6):
            if 1900 <= y <= 2200:
                muts.append(str(y))
        short = val[-2:]
        muts.append(short)
        short_int = int(short)
        for s in range(short_int - 2, short_int + 3):
            if 0 <= s <= 99:
                muts.append(f"{s:02d}")
    return list(dict.fromkeys(muts))

def get_keywalk_mutations(val):
    """Gera sequências numéricas e variações de digitação sequencial."""
    val_lower = val.lower()
    muts = [val]
    if val.isdigit():
        seq_numeric = [
            "123", "1234", "12345", "123456", "321", "4321", "0123", "111", "000", "12", "01"
        ]
        for s in seq_numeric:
            if s != val:
                muts.append(s)
    elif val_lower in ["qwerty", "asdfgh", "zxcvbn", "qwert", "asdf", "zxcv"]:
        seq_alpha = ["qwerty", "qwert", "qwertyuiop", "asdfgh", "zxcvbn", "123456"]
        for s in seq_alpha:
            if s != val_lower:
                muts.append(s)
    return list(dict.fromkeys(muts))

def get_number_mutations(val):
    """Gera variações de números comuns (sufixos, 0-padding, etc.)."""
    muts = [val]
    if len(val) <= 3 and val.isdigit():
        candidates = [
            val, f"{int(val):02d}", f"{int(val)+1}", f"{max(0, int(val)-1)}",
            "1", "12", "123", "01", "007", "777", "69", "99"
        ]
        for c in candidates:
            muts.append(str(c))
    return list(dict.fromkeys(muts))

def get_symbol_mutations(val):
    """Gera variações dos símbolos mais frequentes em senhas."""
    muts = [val]
    common_syms = ["!", "@", "#", "$", "*", "?", "_", ".", "!!"]
    for s in common_syms:
        if s != val:
            muts.append(s)
    return list(dict.fromkeys(muts))

def get_mutation_vectors(dna, password, use_year=False, use_name=False, is_pt=False):
    """
    Identifica os vetores de mutação presentes no DNA.
    Retorna (has_vectors: bool, vectors: list[(token_type, value, description)]).
    """
    from i18n import get_text
    lang = "pt" if is_pt else "en"

    custom_categories, word_map = load_custom_tokens()
    wordlists = load_wordlists()
    wl_sets = {name: set(w.lower() for w in words) for name, words in wordlists.items()}

    vectors = []

    for token in dna.tokens:
        val_lower = token.value.lower()
        tok_type_upper = token.token_type.upper()

        # 1. Custom Tokens
        matched_cat = None
        if tok_type_upper in custom_categories:
            matched_cat = tok_type_upper
        elif val_lower in word_map:
            matched_cat = word_map[val_lower]

        if matched_cat and matched_cat in custom_categories:
            vectors.append((token.token_type, token.value, get_text("mutation", "vec_custom", lang, token_cat=matched_cat)))
            continue

        # 2. WORDLISTS GENÉRICAS (wordlists/)
        matching_words = []
        matching_files = []
        for wl_name, wl_words in wordlists.items():
            if val_lower in wl_sets[wl_name]:
                matching_words.extend(wl_words)
                matching_files.append(wl_name)

        if matching_words:
            wl_label = ", ".join(matching_files)
            vectors.append((token.token_type, token.value, get_text("mutation", "vec_wordlist", lang, wordlist=wl_label)))
            continue

        # 3. Years
        if token.token_type == "YEAR" or (token.token_type == "NUMBER" and len(token.value) == 4 and 1900 <= int(token.value) <= 2099):
            desc = get_text("mutation", "vec_year" if use_year else "vec_year_smart", lang)
            vectors.append((token.token_type, token.value, desc))
            continue

        # 4. Names
        if token.token_type == "NAME" or (use_name and token.value.isalpha() and len(token.value) >= 2):
            desc = get_text("mutation", "vec_name_dataset" if use_name else "vec_name", lang)
            vectors.append((token.token_type, token.value, desc))
            continue

        # 5. Weak Words
        if token.token_type == "WEAK_WORD":
            vectors.append((token.token_type, token.value, get_text("mutation", "vec_weak_word", lang)))
            continue

        # 6. Generic Words (length >= 2)
        if token.token_type == "WORD" and len(token.value) >= 2:
            vectors.append((token.token_type, token.value, get_text("mutation", "vec_word", lang)))
            continue

        # 7. Keywalks
        if token.token_type == "KEY_WALK":
            vectors.append((token.token_type, token.value, get_text("mutation", "vec_keywalk", lang)))
            continue

        # 8. Numbers (1-3 digits)
        if token.token_type == "NUMBER" and len(token.value) <= 3 and token.value.isdigit():
            vectors.append((token.token_type, token.value, get_text("mutation", "vec_number", lang)))
            continue

        # 9. Symbols
        if token.token_type == "SYMBOL":
            vectors.append((token.token_type, token.value, get_text("mutation", "vec_symbol", lang)))
            continue

    has_vectors = len(vectors) > 0
    return has_vectors, vectors

def mutate_dna(dna, password, use_year=False, use_name=False, is_pt=False):
    """
    Engine principal de mutação forense.
    Gera permutações direcionadas baseadas na anatomia genética (DNA) da senha:
    substituições semânticas por categorias de tokens customizados, wordlists,
    expansões de anos, apelidos de nomes, variações leet/casing em palavras fracas
    e progressões numéricas/símbolos.
    Retorna o caminho do arquivo gerado ou None.
    """
    from i18n import get_text
    lang = "pt" if is_pt else "en"

    custom_categories, word_map = load_custom_tokens()
    wordlists = load_wordlists()
    wl_sets = {name: set(w.lower() for w in words) for name, words in wordlists.items()}
    components = []
    has_mutation = False

    for token in dna.tokens:
        val_lower = token.value.lower()
        tok_type_upper = token.token_type.upper()

        # 1. CUSTOM TOKENS (Prioridade Máxima)
        matched_category = None
        if tok_type_upper in custom_categories:
            matched_category = tok_type_upper
        elif val_lower in word_map:
            matched_category = word_map[val_lower]

        if matched_category and matched_category in custom_categories:
            cat_words = custom_categories[matched_category]
            cased_words = match_case(cat_words, token.value)
            components.append(cased_words)
            has_mutation = True
            continue

        # 2. WORDLISTS GENÉRICAS (wordlists/)
        matching_words = []
        for wl_name, wl_words in wordlists.items():
            if val_lower in wl_sets[wl_name]:
                matching_words.extend(wl_words)

        if matching_words:
            unique_words = list(dict.fromkeys(matching_words))
            cased_words = match_case(unique_words, token.value)
            components.append(cased_words)
            has_mutation = True
            continue

        # 3. ANOS E DATAS (YEAR ou NUMBER de 4 dígitos entre 1900 e 2099)
        if token.token_type == "YEAR" or (token.token_type == "NUMBER" and len(token.value) == 4 and 1900 <= int(token.value) <= 2099):
            year_vars = get_year_mutations(token.value, use_year=use_year)
            if len(year_vars) > 1:
                components.append(year_vars)
                has_mutation = True
            else:
                components.append([token.value])
            continue

        # 4. NOMES (NAME ou use_name)
        if token.token_type == "NAME" or (use_name and token.value.isalpha() and len(token.value) >= 2):
            name_vars = get_name_mutations(token.value, token.value, use_name=use_name)
            if len(name_vars) > 1:
                components.append(name_vars)
                has_mutation = True
            else:
                components.append([token.value])
            continue

        # 5. WEAK WORDS
        if token.token_type == "WEAK_WORD":
            weak_vars = get_weak_word_mutations(token.value, token.value)
            if len(weak_vars) > 1:
                components.append(weak_vars)
                has_mutation = True
            else:
                components.append([token.value])
            continue

        # 6. WORDS GENÉRICAS (len >= 2)
        if token.token_type == "WORD" and len(token.value) >= 2:
            word_vars = get_word_mutations(token.value, token.value)
            if len(word_vars) > 1:
                components.append(word_vars)
                has_mutation = True
            else:
                components.append([token.value])
            continue

        # 7. KEY_WALK
        if token.token_type == "KEY_WALK":
            kw_vars = get_keywalk_mutations(token.value)
            if len(kw_vars) > 1:
                components.append(kw_vars)
                has_mutation = True
            else:
                components.append([token.value])
            continue

        # 8. NUMBER (1-3 dígitos)
        if token.token_type == "NUMBER" and len(token.value) <= 3 and token.value.isdigit():
            num_vars = get_number_mutations(token.value)
            if len(num_vars) > 1:
                components.append(num_vars)
                has_mutation = True
            else:
                components.append([token.value])
            continue

        # 9. SYMBOL
        if token.token_type == "SYMBOL":
            sym_vars = get_symbol_mutations(token.value)
            if len(sym_vars) > 1:
                components.append(sym_vars)
                has_mutation = True
            else:
                components.append([token.value])
            continue

        # 10. OUTROS TOKENS (Separadores, números longos, etc.)
        components.append([token.value])

    if has_mutation:
        # Prevent memory and disk explosion (Hard limit)
        MAX_COMBINATIONS = 50_000_000
        total_combinations = 1
        for comp in components:
            total_combinations *= len(comp)

        if total_combinations > MAX_COMBINATIONS:
            console.print(get_text("mutation", "warn_abort", lang, total=total_combinations, max=MAX_COMBINATIONS))
            return None

        output_file = get_output_filename(password)

        from ui_utils import start_progress_status, update_progress_status, stop_progress_status
        start_progress_status(console, get_text("mutation", "progress_cross", lang))

        count = 0
        CHUNK_SIZE = 50_000
        buffer_lines = []

        with open(output_file, "w", encoding="utf-8", buffering=8*1024*1024) as f:
            for combo in itertools.product(*components):
                buffer_lines.append("".join(combo) + "\n")
                count += 1
                if len(buffer_lines) >= CHUNK_SIZE:
                    f.writelines(buffer_lines)
                    buffer_lines.clear()
                    update_progress_status(count, total_combinations, get_text("mutation", "progress_mutating", lang))

            if buffer_lines:
                f.writelines(buffer_lines)
                buffer_lines.clear()

        stop_progress_status()
        console.print(get_text("mutation", "mutations_generated", lang, count=count))
        return output_file
    else:
        console.print(get_text("mutation", "msg_fail", lang))
        return None
