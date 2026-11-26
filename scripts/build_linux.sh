#!/bin/bash
# ============================================================
# CIPHERDNA PRO - LINUX BUILD SYSTEM v2.0 (NUITKA)
# ============================================================
set -e  # Parar imediatamente se qualquer comando falhar

# Mudar para a raiz do repositório
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"

APP_NAME="cypherdna"
ENTRY_POINT="cli.py"
DIST_DIR="CypherDNA_Linux_Build"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║    CIPHERDNA PRO - LINUX BUILD SYSTEM v2.0      ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── STEP 1: Verificar Python ──────────────────────────────
echo "[1/5] Verificando versão do Python..."
python3 --version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "      → Python $PYTHON_VERSION detectado."

# ── STEP 2: Instalar dependências do SISTEMA ──────────────
echo ""
echo "[2/5] Instalando dependências do sistema..."
sudo apt-get update -qq 2>/dev/null || true
sudo apt-get install -y \
    gcc g++ patchelf \
    python3-pip python3-dev \
    zlib1g-dev libmagic1 zip \
    --quiet 2>/dev/null || true
echo "      → Dependências do sistema OK."

# ── STEP 3: Instalar dependências Python ──────────────────
echo ""
echo "[3/5] Instalando bibliotecas Python..."
pip3 install -r requirements.txt --quiet --break-system-packages 2>/dev/null || \
pip3 install -r requirements.txt --quiet || true

# Garante Nuitka e ferramentas de build
pip3 install "nuitka>=2.0" zstandard ordered-set packaging --quiet --break-system-packages 2>/dev/null || \
pip3 install "nuitka>=2.0" zstandard ordered-set packaging --quiet || true
echo "      → Bibliotecas Python OK."

# ── STEP 4: Limpar builds anteriores ─────────────────────
echo ""
echo "[4/5] Limpando builds anteriores..."
rm -rf "$DIST_DIR"
rm -f "$APP_NAME"
rm -rf "cli.build" "cli.dist" "cli.onefile-build"
echo "      → Workspace limpo."

# ── STEP 5: COMPILAÇÃO NUITKA ────────────────────────────
echo ""
echo "[5/5] Iniciando compilação Nuitka..."
echo "      → LTO: DISABLED (compatibilidade máxima)"
echo "      → Modo: OneFile + Standalone"
echo "      → Isso pode levar 5-15 minutos..."
echo ""

python3 -m nuitka \
    --onefile \
    --standalone \
    --assume-yes-for-downloads \
    \
    `# ── Compatibilidade e Estabilidade ──` \
    --lto=no \
    --static-libpython=no \
    --python-flag=no_site \
    \
    `# ── Pacotes Python Essenciais ──` \
    --include-package=rich \
    --include-package=click \
    --include-package=requests \
    --include-package=bs4 \
    --include-package=unidecode \
    --include-package=fpdf \
    --include-package=PIL \
    --include-package=rsa \
    --include-package=packaging \
    --include-package=urllib \
    --include-package=email \
    --include-package=threading \
    --include-package=uuid \
    --include-package=ctypes \
    --include-package=zstandard \
    \
    `# ── Extração para pasta previsível ──` \
    --onefile-tempdir-spec="{CACHE_DIR}/CipherDNA_Runtime" \
    \
    `# ── Dados embutidos ──` \
    --include-data-dir=data=data \
    \
    `# ── Saída ──` \
    --output-filename="$APP_NAME" \
    --jobs=1 \
    --remove-output \
    "$ENTRY_POINT"

# ── RESULTADO ─────────────────────────────────────────────
echo ""
if [ -f "$APP_NAME" ]; then
    echo "╔══════════════════════════════════════════════════╗"
    echo "║               COMPILAÇÃO CONCLUÍDA!             ║"
    echo "╚══════════════════════════════════════════════════╝"

    # Cria pasta de distribuição
    mkdir -p "$DIST_DIR"
    mv "$APP_NAME" "$DIST_DIR/"
    chmod +x "$DIST_DIR/$APP_NAME"

    # Copia pasta de dados para distribuição
    [ -d data ] && cp -r data "$DIST_DIR/"

    # Cria diretórios padrão esperados pelo CipherDNA
    mkdir -p "$DIST_DIR/license"
    mkdir -p "$DIST_DIR/You_wordlist"
    mkdir -p "$DIST_DIR/benchmark_reports"

    # Cria README
    cat > "$DIST_DIR/README_LINUX.txt" << 'READMEEOF'
===========================================================
      CIPHERDNA PRO - OPERAÇÃO EM LINUX / KALI
===========================================================

COMO EXECUTAR (da pasta do executável):
  1. Abra o terminal DENTRO da pasta CypherDNA_Linux_Build/
  2. Dê permissão:  chmod +x cypherdna
  3. Execute:       ./cypherdna --help

IMPORTANTE: Sempre execute o binário de DENTRO da sua pasta.
Se você quiser usar de qualquer pasta, instale no sistema:

  sudo cp cypherdna /usr/local/bin/cypherdna
  cypherdna --help

===========================================================
READMEEOF

    # Teste rápido do binário gerado
    echo ""
    echo "[*] Testando o binário gerado..."
    if "$DIST_DIR/$APP_NAME" --help > /dev/null 2>&1 || \
       CPH_TEST_MODE=true "$DIST_DIR/$APP_NAME" --help > /dev/null 2>&1; then
        echo "    ✓ Binário respondeu com sucesso!"
    else
        EXIT_CODE=$?
        echo "    ⚠ Binário retornou código: $EXIT_CODE"
        echo "    → Isso pode ser normal se pedir licença na primeira execução."
    fi

    echo ""
    echo "  Binário: $DIST_DIR/$APP_NAME"
    BINSIZE=$(du -sh "$DIST_DIR/$APP_NAME" | cut -f1)
    echo "  Tamanho: $BINSIZE"
    echo ""
    echo "  Distribuição completa em: ./$DIST_DIR/"
    echo ""
else
    echo ""
    echo "╔══════════════════════════════════════════════════╗"
    echo "║              FALHA NA COMPILAÇÃO!               ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo ""
    echo "  Verifique os logs acima para identificar o erro."
    echo ""
    echo "  DICAS DE DEPURAÇÃO:"
    echo "  1. Rode novamente com: bash build_linux.sh 2>&1 | tee build.log"
    echo "  2. Verifique o arquivo build.log para mensagens de erro detalhadas."
    echo ""
    exit 1
fi
