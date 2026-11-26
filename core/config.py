import os
import sys
import shutil

def get_base_dir():
    """
    Detecta o diretório base da aplicação e garante que seja gravável,
    com fallback para a home do usuário se não tiver permissão.
    """
    
    # 0. NUITKA ONEFILE - Preferred location
    nuitka_binary = os.environ.get('NUITKA_ONEFILE_BINARY')
    if nuitka_binary:
        path = os.path.dirname(os.path.abspath(nuitka_binary))
    else:
        # Detect project root relative to core/config.py
        root_from_file = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if os.path.exists(os.path.join(root_from_file, "data")):
            path = root_from_file
        else:
            path = os.getcwd()

    # Check for write permission in the detected path
    # If we can't write, we MUST use a fallback, otherwise setup_environment will cause a Segfault/Crash
    if not os.access(path, os.W_OK):
        path = os.path.join(os.path.expanduser("~"), ".cipherdna_pro")
    
    return path

# Valores de fallback usados se version.json estiver ausente ou corrompido
DEFAULT_VERSION = "3.5.1"
DEFAULT_META = {
    "version": DEFAULT_VERSION,
    "version_title": "Disaster Recovery Mode",
    "changelog_pt": ["Atuando em modo de segurança.", "Arquivos base ausentes ou corrompidos."],
    "changelog_en": ["Running in Safe Mode.", "Essential files missing or corrupted."]
}

# Global Paths
BASE_DIR = get_base_dir()
INTERNAL_RESOURCES = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Intelligence & Datasets (data/)
WORDLISTS_DIR = os.path.join(DATA_DIR, "wordlists")
TRAINER_DIR = os.path.join(DATA_DIR, "trainer_data")
STRATEGIES_DIR = os.path.join(DATA_DIR, "strategies")
CUSTOM_TOKENS_DIR = os.path.join(DATA_DIR, "custom_tokens")
NAMES_DATASET_FILE = os.path.join(DATA_DIR, "names_dataset.json")
BREACH_DATA_FILE = os.path.join(DATA_DIR, "breach_data.json")
RANKER_FILE = os.path.join(DATA_DIR, "ranker.json")
LANG_FILE   = os.path.join(DATA_DIR, ".cph_lang")
HIBP_KEY_FILE = os.path.join(DATA_DIR, ".cph_hibp")

# Output Directories (output/)
YOU_WORDLIST_DIR = os.path.join(OUTPUT_DIR, "wordlists")
REPORTS_DIR      = os.path.join(OUTPUT_DIR, "reports")
BENCHMARK_REPORTS_DIR = os.path.join(OUTPUT_DIR, "benchmark_reports")

def get_saved_lang() -> str:
    """Retorna o idioma salvo em disco ('pt' ou 'en'). Padrão: 'en'."""
    try:
        for p in [LANG_FILE, os.path.join(BASE_DIR, ".cph_lang")]:
            if os.path.exists(p):
                raw = open(p, "r", encoding="utf-8").read().strip().lower()
                if raw in ("pt", "en"):
                    return raw
    except Exception:
        pass
    return "en"

def set_saved_lang(lang: str) -> None:
    """Persiste o idioma preferido em disco."""
    try:
        with open(LANG_FILE, "w", encoding="utf-8") as f:
            f.write(lang.strip().lower())
    except Exception:
        pass


def get_saved_hibp_key() -> str:
    """Retorna a chave da API HIBP salva em disco ou em variável de ambiente."""
    env_key = os.environ.get("HIBP_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        for p in [HIBP_KEY_FILE, os.path.join(BASE_DIR, ".cph_hibp")]:
            if os.path.exists(p):
                val = open(p, "r", encoding="utf-8").read().strip()
                if val:
                    return val
    except Exception:
        pass
    return ""


def set_saved_hibp_key(key: str) -> None:
    """Persiste a chave da API HIBP em disco."""
    try:
        with open(HIBP_KEY_FILE, "w", encoding="utf-8") as f:
            f.write(key.strip())
    except Exception:
        pass


def remove_saved_hibp_key() -> bool:
    """Remove a chave da API HIBP persistida em disco."""
    removed = False
    for p in [HIBP_KEY_FILE, os.path.join(BASE_DIR, ".cph_hibp")]:
        try:
            if os.path.exists(p):
                os.remove(p)
                removed = True
        except Exception:
            pass
    return removed


def setup_environment():
    """
    Garante que TODA a estrutura exista fisicamente na pasta REAL do usuário.
    Copia os dados embutidos para fora se necessário.
    """
    # 1. Cria as pastas básicas
    folders = [
        BASE_DIR, DATA_DIR, OUTPUT_DIR,
        YOU_WORDLIST_DIR, REPORTS_DIR, BENCHMARK_REPORTS_DIR,
        WORDLISTS_DIR, TRAINER_DIR, STRATEGIES_DIR, CUSTOM_TOKENS_DIR
    ]
    for d in folders:
        try:
            if not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
        except Exception:
            pass

    # 2. Sincroniza dados internos para externos (O 'truque' para OneFile)
    is_frozen = (
        getattr(sys, 'frozen', False) or 
        hasattr(sys, 'nuitka_binary') or 
        os.environ.get('NUITKA_ONEFILE_BINARY') is not None or
        "__compiled__" in globals() or
        (os.path.basename(sys.executable).lower() not in ['python.exe', 'python', 'pythonw.exe', 'python3'])
    )
    if is_frozen:
        # Copia pastas de inteligência (apenas se estiverem vazias na pasta do usuário)
        for folder_name in ["wordlists", "trainer_data"]:
            source = os.path.join(INTERNAL_RESOURCES, folder_name)
            target = os.path.join(DATA_DIR, folder_name)
            
            if os.path.exists(source):
                try:
                    if not os.path.exists(target) or not os.listdir(target):
                        if os.path.exists(target): shutil.rmtree(target, ignore_errors=True)
                        shutil.copytree(source, target, dirs_exist_ok=True)
                except Exception:
                    pass

        # Copia arquivos JSON essenciais
        for f in ["version.json", "names_dataset.json"]:
            target = os.path.join(DATA_DIR, f)
            if not os.path.exists(target):
                source = os.path.join(INTERNAL_RESOURCES, f)
                if os.path.exists(source):
                    try:
                        shutil.copy2(source, target)
                    except Exception:
                        pass
                elif f == "version.json":
                    # Cria um version.json de emergência se nem no embutido ele estiver
                    import json
                    try:
                        with open(target, "w", encoding="utf-8") as temp_v:
                            json.dump(DEFAULT_META, temp_v)
                    except Exception:
                        pass

def load_version_data():
    """Lê a versão de forma segura sem crashar o programa."""
    import json
    for path in [os.path.join(DATA_DIR, "version.json"), os.path.join(BASE_DIR, "version.json")]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return DEFAULT_META

# Inicialização automática imediata ao importar o módulo
setup_environment()
