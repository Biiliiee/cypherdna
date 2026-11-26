#!/bin/bash
# ==============================================================
# CIPHERDNA - LINUX RUNNER (BASH EQUIVALENT TO .BAT)
# ==============================================================

# Verifica se o Python 3 está instalado
if ! command -v python3 &> /dev/null
then
    echo "[!] Erro: Python3 não encontrado. Por favor, instale o Python3."
    exit 1
fi

# Pega o diretório raiz do projeto (um nível acima de scripts/)
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
cd "$BASE_DIR"

# Verifica se o cli.py existe
if [ ! -f "cli.py" ]; then
    echo "[!] Erro: cli.py não encontrado no diretório $BASE_DIR"
    exit 1
fi

# Executa o CipherDNA passando todos os argumentos
python3 cli.py "$@"
