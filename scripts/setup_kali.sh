#!/bin/bash
# =============================================================================
# CypherDNA — Linux/Kali Installer
# =============================================================================
# Installs CypherDNA and registers the 'cypherdna' command globally.
# Supports: Kali Linux, Ubuntu, Debian, Arch, Fedora
#
# Usage:
#   chmod +x setup_kali.sh
#   ./setup_kali.sh
# =============================================================================

set -e

# Mudar para a raiz do repositório
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${RED}${BOLD}╔══════════════════════════════════════════╗${NC}"
    echo -e "${RED}${BOLD}║   🧬 CYPHERDNA — Linux Installer         ║${NC}"
    echo -e "${RED}${BOLD}║   Advanced Password DNA Sequencing       ║${NC}"
    echo -e "${RED}${BOLD}╚══════════════════════════════════════════╝${NC}"
    echo ""
}

check_python() {
    echo -e "${CYAN}[*] Verificando Python...${NC}"
    if ! command -v python3 &>/dev/null; then
        echo -e "${RED}[!] Python 3 não encontrado. Instalando...${NC}"
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y python3 python3-pip
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm python python-pip
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y python3 python3-pip
        else
            echo -e "${RED}[!] Gerenciador de pacotes não reconhecido. Instale Python 3.10+ manualmente.${NC}"
            exit 1
        fi
    fi

    PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo -e "${GREEN}[✓] Python ${PYTHON_VER} encontrado.${NC}"
}

install_cypherdna() {
    echo -e "${CYAN}[*] Instalando CypherDNA...${NC}"

    # Verifica se pip está disponível
    if ! python3 -m pip --version &>/dev/null; then
        echo -e "${YELLOW}[!] pip não encontrado. Instalando pip...${NC}"
        curl -sS https://bootstrap.pypa.io/get-pip.py | python3
    fi

    # Instala o projeto em modo editável — registra o comando 'cypherdna'
    python3 -m pip install -e . --quiet

    echo -e "${GREEN}[✓] CypherDNA instalado com sucesso!${NC}"
}

verify_install() {
    echo -e "${CYAN}[*] Verificando instalação...${NC}"

    if command -v cypherdna &>/dev/null; then
        echo -e "${GREEN}[✓] Comando 'cypherdna' disponível globalmente!${NC}"
    else
        # Fallback: pode estar em ~/.local/bin (pip --user install)
        LOCAL_BIN="$HOME/.local/bin"
        if [ -f "$LOCAL_BIN/cypherdna" ]; then
            echo -e "${YELLOW}[!] Comando instalado em ~/.local/bin${NC}"
            echo -e "${YELLOW}    Adicione ao PATH com: echo 'export PATH=\$PATH:~/.local/bin' >> ~/.bashrc && source ~/.bashrc${NC}"
        else
            echo -e "${YELLOW}[!] Comando não encontrado no PATH. Tente reiniciar o terminal.${NC}"
        fi
    fi
}

print_usage() {
    echo ""
    echo -e "${BOLD}════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}  [✓] Instalação Concluída!${NC}"
    echo -e "${BOLD}════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BOLD}  Exemplos de uso:${NC}"
    echo -e "  ${CYAN}cypherdna --help${NC}"
    echo -e "  ${CYAN}cypherdna analyze 'xbox360.kabuto'${NC}"
    echo -e "  ${CYAN}cypherdna generator admin 2024 -L -S -N 50000${NC}"
    echo -e "  ${CYAN}cypherdna generator target 2024 --pipe | hashcat -m 0 hash.txt${NC}"
    echo -e "  ${CYAN}cypherdna token GAME -a games.txt${NC}"
    echo -e "  ${CYAN}cypherdna doctor${NC}"
    echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
print_header
check_python
install_cypherdna
verify_install
print_usage
