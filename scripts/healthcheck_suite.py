
import subprocess
import os
import sys
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# Caminho para o executável ou script (localizado na raiz do projeto)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(ROOT_DIR, "core")
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

CLI_SCRIPT = os.path.join(ROOT_DIR, "cli.py")
CLI_EXEC = [sys.executable, CLI_SCRIPT]

def run_test(name, args, expected_snippet=None):
    """Executa um comando e valida o resultado."""
    # Desativar cores do Rich para facilitar o matching de texto
    env = os.environ.copy()
    env["FORCE_COLOR"] = "0"
    env["TERM"] = "dumb"
    env["CPH_TEST_MODE"] = "true"

    full_cmd = CLI_EXEC + args
    console.print(f"[bold blue]Testing:[/] {' '.join(full_cmd)}")
    
    start_time = time.time()
    try:
        # Passamos múltiplos \n para pular todos os prompts interativos
        # timeout=30 garante que comandos com rede (HIBP, etc) não travem o test
        result = subprocess.run(
            full_cmd,
            input="\n\n\n\n",
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=60,
            env=env
        )
        duration = time.time() - start_time
        
        output = result.stdout + result.stderr
        success = (result.returncode == 0)
        
        # Validação extra de snippet se fornecido
        if expected_snippet and expected_snippet.lower() not in output.lower():
            success = False
            error_reason = f"Snippet '{expected_snippet}' not found."
        else:
            error_reason = f"Exit code: {result.returncode}" if not success else ""

        return {
            "name": name,
            "success": success,
            "duration": f"{duration:.2f}s",
            "reason": error_reason,
            "output_preview": output[-1000:] # Mais contexto no final
        }
    except Exception as e:
        return {
            "name": name,
            "success": False,
            "duration": "0s",
            "reason": str(e),
            "output_preview": "Exception occurred"
        }

def run_suite():
    console.print(Panel("[bold cyan]CYPHERDNA PRO - AUTOMATED HEALTHCHECK SUITE v1.0[/bold cyan]", border_style="cyan"))
    
    tests = [
        ("DRM/License Status", ["status"], "OPEN SOURCE"),
        ("DNA Parser Engine", ["analyze", "Admin123!"], "WEAK_WORD"),
        ("Wordlist Generator", ["generator", "xbox", "--number", "5"], "cypherdna"),
        ("Trainer Database", ["collect", "-L"], "Datasets"),
        ("Environment Health", ["doctor"], "DIAGN"),
        ("Token Manager", ["token", "--help"], "CUSTOM"),
        ("Strategic Ranker", ["ranker", "-L"], "RANK"),
    ]
    
    results = []
    for name, args, snippet in tests:
        res = run_test(name, args, snippet)
        results.append(res)
    
    # Gerar Tabela de Resultados
    table = Table(title="\n[bold white]Final Pipeline Report[/bold white]", border_style="dim")
    table.add_column("Module", style="cyan")
    table.add_column("Result", justify="center")
    table.add_column("Time", justify="right")
    table.add_column("Notes", style="dim")

    all_ok = True
    for r in results:
        status_icon = "[bold green]PASS[/bold green]" if r['success'] else "[bold red]FAIL[/bold red]"
        if not r['success']: all_ok = False
        table.add_row(r['name'], status_icon, r['duration'], r['reason'])

    console.print(table)
    
    if all_ok:
        console.print(Panel("[bold green]SYSTEM STATUS: CHUCHU BELEZA![/bold green]\nAll core modules are synchronized and stable.", border_style="green"))
    else:
        console.print(Panel("[bold red]SYSTEM STATUS: ANOMALY DETECTED![/bold red]\nOne or more modules returned an error. Check logs above.", border_style="red"))
        # Print failed outputs for debugging
        console.print("\n[bold yellow]Failed Test Details:[/bold yellow]")
        for r in results:
            if not r['success']:
                console.print(f"\n--- {r['name']} ---")
                console.print(f"Reason: {r['reason']}")
                console.print("Output (last 500 chars):")
                console.print(r['output_preview'])

if __name__ == "__main__":
    # Garante que as pastas básicas existem antes do teste
    from config import setup_environment
    setup_environment()
    
    run_suite()
