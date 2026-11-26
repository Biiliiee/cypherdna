import re
import string
import os
import json
from dataclasses import dataclass, field
from datetime import datetime
from unidecode import unidecode
try:
    from config import CUSTOM_TOKENS_DIR, NAMES_DATASET_FILE, DATA_DIR
except ImportError:
    try:
        from core.config import CUSTOM_TOKENS_DIR, NAMES_DATASET_FILE, DATA_DIR
    except ImportError:
        CUSTOM_TOKENS_DIR = None
        NAMES_DATASET_FILE = None
        DATA_DIR = None


# =========================
# DATA STRUCTURES
# =========================

@dataclass
class Token:
    value: str
    token_type: str
    position: int  # ordem do token na lista
    meta: dict = field(default_factory=dict)


@dataclass
class DNAResult:
    raw: str
    normalized: str
    tokens: list[Token]
    pattern: str
    features: dict
    meta: dict = field(default_factory=dict)

    def has_type(self, t: str) -> bool:
        return any(token.token_type == t for token in self.tokens)


# =========================
# CONSTANTS
# =========================

CURRENT_YEAR = datetime.now().year


# =========================
# TOKENIZATION
# =========================

def tokenize(password: str) -> list[str]:
    """
    Quebra a senha em pedaços (tokens).
    Ex: "Gustavo2004!" -> ["Gustavo", "2004", "!"]
    Ex: "Ana_1999!!" -> ["Ana", "_", "1999", "!", "!"]
    """
    pattern = r"[A-Za-zÀ-ÿ]+|\d+|[^A-Za-zÀ-ÿ\d]"
    return re.findall(pattern, password)


# =========================
# TOKEN CLASSIFICATION
# =========================

# Optional dataset support for real names (Lazy Load)
NAMES_DATASET = None

def _lazy_load_names():
    global NAMES_DATASET
    if NAMES_DATASET is not None:
        return
    NAMES_DATASET = set()
    
    candidates = [
        NAMES_DATASET_FILE,
        os.path.join(DATA_DIR, "names_dataset.json"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "names_dataset.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "names_dataset.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "names_dataset.json")
    ]
    
    for fpath in candidates:
        if fpath and os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as _f:
                    _data = json.load(_f)
                    if isinstance(_data, list):
                        for n in _data:
                            if isinstance(n, str):
                                n_clean = n.strip().lower()
                                if n_clean:
                                    NAMES_DATASET.add(n_clean)
                                    NAMES_DATASET.add(unidecode(n_clean))
                if len(NAMES_DATASET) > 0:
                    break
            except Exception:
                pass

COMMON_WEAK_WORDS = {
    # Globais
    "password", "admin", "hello", "love", "master", "qwerty", 
    "root", "user", "pass", "test", "welcome", "123456", "default",
    # BR Clássicos da Cultura de Senha
    "senha", "mudar", "trocar", "sistema", "sucesso", "teste",
    "brasil", "deus", "amor", "jesus", "paz", "vida", "familia",
    "batata", "futebol", "flamengo", "corinthians", "palmeiras"
}

# Palavras de Dicionário corporativas
COMMON_DICTIONARY_WORDS = {
    "personal", "corporation", "oficial", "official", "brasil", "brazil", "negocios", "vendas",
    "marketing", "sucesso", "familia", "love", "vida", "life", "photo", "foto", "photography",
    "design", "fitness", "health", "saude", "viagem", "travel", "musica", "music", "art", "arte",
    "fashion", "estilo", "style", "digital", "tecnologia", "tech", "web", "online", "store", "loja"
}

# Sobrenomes BR Comuns
PORTUGUESE_SURNAMES = {
    "silva", "santos", "oliveira", "souza", "sousa", "rodrigues", "ferreira", "alves", "pereira",
    "lima", "gomes", "costa", "ribeiro", "martins", "carvalho", "almeida", "lopes", "soares",
    "fernandes", "vieira", "barbosa", "melo", "cardoso", "teixeira", "cabral", "nascimento", 
    "mendes", "araujo", "machado", "cunha", "borges", "moraes", "dias", "castro", "tavares", "monteiro"
}

# CACHE DE TOKENS CUSTOMIZADOS
_custom_tokens_cache = None # Ex: {"NARUTO": {"sasuke", "kakashi"}}

def _load_custom_tokens():
    global _custom_tokens_cache
    if _custom_tokens_cache is not None:
        return
    _custom_tokens_cache = {}
    if os.path.exists(CUSTOM_TOKENS_DIR):
        for folder in os.listdir(CUSTOM_TOKENS_DIR):
            path = os.path.join(CUSTOM_TOKENS_DIR, folder)
            if os.path.isdir(path):
                token_name = folder.upper()
                word_set = set()
                for f in os.listdir(path):
                    if f.lower().endswith(".txt"):
                        try:
                            with open(os.path.join(path, f), "r", encoding="utf-8", errors="ignore") as _file:
                                for line in _file:
                                    val = line.strip().lower()
                                    if val: word_set.add(val)
                        except Exception:
                            pass
                if word_set:
                    _custom_tokens_cache[token_name] = word_set

def is_year(token: str) -> bool:
    """
    Detecta se um token numérico é um ano realista.
    """
    if not token.isdigit():
        return False

    if len(token) != 4:
        return False

    year = int(token)
    return 1900 <= year <= (CURRENT_YEAR + 2)


def is_separator(token: str) -> bool:
    """
    Detecta separadores comuns.
    """
    separators = {"_", "-", ".", " "}
    return token in separators


def is_symbol(token: str) -> bool:
    """
    Detecta símbolos especiais (não alfanuméricos e não separadores).
    """
    if token.isalnum():
        return False
    if is_separator(token):
        return False
    return True

COMMON_STOP_WORDS = {
    "in", "on", "to", "is", "me", "the", "at", "an", "no", "do", "da", "de", 
    "di", "du", "my", "by", "or", "so", "if", "as", "it", "he", "we", "us", "am"
}

def is_name(token: str) -> bool:
    if not token.isalpha() or len(token) < 3:
        return False

    lower_token = token.lower()
    clean_token = unidecode(lower_token)

    if lower_token in COMMON_WEAK_WORDS or clean_token in COMMON_WEAK_WORDS:
        return False

    if lower_token in COMMON_DICTIONARY_WORDS or clean_token in COMMON_DICTIONARY_WORDS:
        return False

    if lower_token in COMMON_STOP_WORDS or clean_token in COMMON_STOP_WORDS:
        return False

    _lazy_load_names()
    # Aceita se for Nome próprio ou Sobrenome comum (com ou sem acentos)
    return (
        lower_token in NAMES_DATASET
        or clean_token in NAMES_DATASET
        or lower_token in PORTUGUESE_SURNAMES
        or clean_token in PORTUGUESE_SURNAMES
    )

def is_repeated(token: str) -> bool:
    """Detecta sequências de teclas idênticas preguiçosas (Ex: '111', 'aaaa', '!!!')."""
    return len(token) >= 3 and len(set(token)) == 1

def is_season(token: str) -> bool:
    """Detecta se o token é uma estação do ano."""
    seasons = {
        "primavera", "verao", "outono", "inverno",
        "spring", "summer", "autumn", "fall", "winter"
    }
    return unidecode(token).lower() in seasons

def is_weak_word(token: str) -> bool:
    """Detecta palavras extremamente vulneráveis corporativas ou comuns."""
    return unidecode(token).lower() in COMMON_WEAK_WORDS

def is_month(token: str) -> bool:
    """Verifica se o token é um mês escrito por extenso ou abreviado (PT/EN)."""
    months = {
        "janeiro", "fevereiro", "marco", "abril", "maio", "junho", 
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
        "jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez",
        "january", "february", "march", "april", "may", "june", 
        "july", "august", "september", "october", "november", "december",
        "aug", "sep", "oct", "nov", "dec"
    }
    return unidecode(token).lower() in months

def is_date(token: str) -> bool:
    """Verifica se a string de números é uma data de aniversário lógica (DDMMYYYY, DDMMYY ou DDMM - Padrão BR)."""
    if not token.isdigit():
        return False
    
    # Formatos 8 chars
    if len(token) == 8:
        # Padrão BR Absoluto: DD/MM/AAAA
        dd, mm, yyyy = int(token[:2]), int(token[2:4]), int(token[4:])
        if 1 <= dd <= 31 and 1 <= mm <= 12 and 1900 <= yyyy <= CURRENT_YEAR + 5:
            return True
            
        # Padrão ISO Backup: AAAA/MM/DD
        yyyy2, mm2, dd2 = int(token[:4]), int(token[4:6]), int(token[6:])
        if 1 <= dd2 <= 31 and 1 <= mm2 <= 12 and 1900 <= yyyy2 <= CURRENT_YEAR + 5:
            return True

    # Formatos 6 chars
    elif len(token) == 6:
        # Padrão BR: DD/MM/AA
        dd, mm = int(token[:2]), int(token[2:4])
        if 1 <= dd <= 31 and 1 <= mm <= 12:
            return True

    # Formatos 4 chars - Apenas Dia e Mês (Ex: 2512 para 25 de Dezembro)
    # Obs: A checagem de "YEAR" (ex: 2004) ocorre *antes* na pipeline de classificação.
    # Portanto, "2004" vira YEAR em vez de "Dia 20 Mês 4". O que cai aqui é real.
    elif len(token) == 4:
        dd, mm = int(token[:2]), int(token[2:])
        if 1 <= dd <= 31 and 1 <= mm <= 12:
            return True
            
    return False

def classify_token(token: str) -> tuple[str, dict]:
    """
    Classifica um token e retorna (tipo, meta).
    """
    meta = {}

    # Normaliza pra ajudar análise
    normalized = unidecode(token)
    meta["normalized"] = normalized

    # Identifica teclas repetidas idênticas (aaa, !!!, 0000)
    if is_repeated(token):
        return "REPEATED", meta

    # Identifica sequências de teclado (Keyboard Walks)
    if is_keyboard_walk(token):
        return "KEY_WALK", meta

    if is_year(token):
        return "YEAR", meta

    if is_date(token):
        return "DATE", meta

    if token.isdigit():
        return "NUMBER", meta

    if is_separator(token):
        return "SEPARATOR", meta

    if is_symbol(token):
        return "SYMBOL", meta
        
    # Token includes both digits and letters exclusively
    if token.isalnum() and not token.isalpha() and not token.isdigit():
        return "MIXED_ALNUM", meta

    # Checagem de custom tokens: prioridade alta, roda antes de NAME, WEAK_WORD, MONTH
    _load_custom_tokens()
    lower_val = token.lower()
    for c_type, c_words in _custom_tokens_cache.items():
        if lower_val in c_words:
            return c_type, meta

    if is_month(token):
        return "MONTH", meta

    if is_season(token):
        return "SEASON", meta

    if is_weak_word(token):
        return "WEAK_WORD", meta

    if is_name(token):
        return "NAME", meta

    if token.isalpha():
        return "WORD", meta

    return "UNKNOWN", meta

def is_keyboard_walk(token: str) -> bool:
    """
    Detecta padrões de teclas sequenciais no teclado (Keyboard Walks).
    Ex: qwerty, asdfgh, 123456, zxcvbn
    """
    walks = [
        "qwertyuiop", "asdfghjkl", "zxcvbnm",
        "1234567890", "0987654321",
        "qaz", "wsx", "edc", "rfv", "tgb", "yhn", "ujm", "ik,", "ol.", "p;/"
    ]
    
    t = token.lower()
    if len(t) < 3:
        return False
        
    for walk in walks:
        if t in walk:
            return True
            
    # Checagem adicional lógica: Sequências alfabéticas crescentes/decrescentes (abcd, dcba)
    if len(t) >= 4 and t.isalpha():
        is_seq_up = all(ord(t[i]) + 1 == ord(t[i+1]) for i in range(len(t)-1))
        is_seq_down = all(ord(t[i]) - 1 == ord(t[i+1]) for i in range(len(t)-1))
        if is_seq_up or is_seq_down:
            return True

    return False


# =========================
# PATTERN BUILDER
# =========================

def build_pattern(tokens: list[Token]) -> str:
    """
    Monta o padrão final da senha:
    NAME+YEAR+SYMBOL etc.
    """
    return "+".join([t.token_type for t in tokens])


# =========================
# FEATURES EXTRACTOR
# =========================

def extract_features(password: str) -> dict:
    """
    Extrai características úteis da senha.
    """
    return {
        "length": len(password),
        "has_upper": any(c.isupper() for c in password),
        "has_lower": any(c.islower() for c in password),
        "has_digit": any(c.isdigit() for c in password),
        "has_symbol": any(c in string.punctuation for c in password),
        "has_space": " " in password,
    }


# =========================
# MAIN PARSER
# =========================

def parse_password(password: str) -> DNAResult:
    """
    Função principal do módulo.
    """
    raw = password
    normalized = unidecode(password)

    raw_tokens = tokenize(password)

    tokens: list[Token] = []
    for i, tok in enumerate(raw_tokens):
        tok_type, meta = classify_token(tok)
        tokens.append(Token(value=tok, token_type=tok_type, position=i, meta=meta))

    pattern = build_pattern(tokens)
    features = extract_features(password)

    return DNAResult(
        raw=raw,
        normalized=normalized,
        tokens=tokens,
        pattern=pattern,
        features=features
    )





# =========================
# QUICK TEST
# =========================

if __name__ == "__main__":

    teste = "Admin123"
    result = parse_password(teste)
    print("=" * 50)
    print("RAW:", result.raw)
    print("NORMALIZED:", result.normalized)
    print("PATTERN:", result.pattern)
    print("FEATURES:", result.features)
    print("TOKENS:")
    for t in result.tokens:
        print(f"  [{t.position}] {t.value} -> {t.token_type}")
