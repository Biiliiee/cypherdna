"""
CypherDNA — Build Script
Gera o executável standalone (cypherdna.exe) usando PyInstaller.

Usage:
    python build.py

Output:
    dist/cypherdna.exe   ← binário portátil, sem precisar de Python
"""

import os
import sys
import shutil
import subprocess

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.exists(ROOT_DIR):
    os.chdir(ROOT_DIR)

# ─── Configurações ────────────────────────────────────────────────────────────
APP_NAME    = "cypherdna"
ENTRY_POINT = "cli.py"
ICON_FILE   = os.path.join("assets", "icon.ico")

# Pastas de dados que serão embutidas no executável
DATA_INCLUDES = [
    ("data",               "data"),
]
# ──────────────────────────────────────────────────────────────────────────────


def clean_previous_build():
    """Remove artefatos de build anteriores para evitar conflitos."""
    for folder in ["build", "dist", f"{APP_NAME}.spec"]:
        if os.path.exists(folder):
            print(f"[*] Limpando: {folder}")
            if os.path.isdir(folder):
                shutil.rmtree(folder, ignore_errors=True)
            else:
                os.remove(folder)


def ensure_pyinstaller():
    """Garante que o PyInstaller está instalado."""
    try:
        import PyInstaller
    except ImportError:
        print("[*] Instalando PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)


def build():
    print("\n" + "=" * 55)
    print("   CYPHERDNA — BUILD SYSTEM")
    print("=" * 55 + "\n")

    clean_previous_build()
    ensure_pyinstaller()

    # ── Monta os --add-data flags ──────────────────────────────────────────
    separator = ";" if sys.platform == "win32" else ":"
    add_data_flags = []
    for src, dst in DATA_INCLUDES:
        if os.path.exists(src):
            add_data_flags += ["--add-data", f"{src}{separator}{dst}"]
        else:
            print(f"[!] Aviso: '{src}' não encontrado, será ignorado.")

    # ── Ícone ──────────────────────────────────────────────────────────────
    icon_flags = ["--icon", ICON_FILE] if os.path.exists(ICON_FILE) else []

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                   # Tudo num único .exe
        "--console",                   # Mantém o console (CLI tool)
        "--clean",                     # Limpa cache do PyInstaller
        "--paths=core",                # Inclui pasta core no sys.path do bundler
        f"--name={APP_NAME}",          # Nome do executável
        *icon_flags,                   # Ícone (se existir)
        *add_data_flags,               # Dados embutidos
        ENTRY_POINT,                   # Ponto de entrada
    ]

    print(f"[*] Compilando '{ENTRY_POINT}' -> dist/{APP_NAME}.exe ...")
    print("[!] Isso pode levar alguns minutos...\n")

    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = os.path.join("dist", f"{APP_NAME}.exe")
        size_mb = os.path.getsize(exe_path) / (1024 * 1024) if os.path.exists(exe_path) else 0

        print("\n" + "=" * 55)
        print(f"  [OK] Build completo!")
        print(f"  Executável: {exe_path}")
        print(f"  Tamanho:    {size_mb:.1f} MB")
        print("=" * 55)
        print("\n[>] Para usar sem instalar Python:")
        print(f"    .\\dist\\{APP_NAME}.exe analyze senha123")
        print(f"    .\\dist\\{APP_NAME}.exe generator admin 2024 -L -S\n")
    else:
        print("\n[ERRO] Build falhou. Verifique os erros acima.")
        sys.exit(1)


if __name__ == "__main__":
    build()
