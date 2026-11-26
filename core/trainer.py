#!/usr/bin/env python3
import click
import os
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from collections import Counter

from dna_parser import parse_password

console = Console()

import sys
from config import setup_environment, TRAINER_DIR
from i18n import TRAINER_TEXTS as TEXTS

setup_environment()

def get_lang(is_pt):
    """Retorna o dicionário de textos com base na flag de idioma."""
    return TEXTS["pt"] if is_pt else TEXTS["en"]


def ensure_trainer_dir():
    """Garante a existência da pasta interna de dados."""
    if not os.path.exists(TRAINER_DIR):
        os.makedirs(TRAINER_DIR)

# ==========================================
# WORKER MULTI-CORE (processamento paralelo)
# ==========================================
def process_chunk(kwargs):
    """Lê um pedaço bruto do arquivo em bytes, faz o parse e retorna os Contadores"""
    filepath = kwargs['filepath']
    start_byte = kwargs['start_byte']
    end_byte = kwargs['end_byte']

    from collections import Counter
    from dna_parser import parse_password

    t_counter = Counter()
    p_counter = Counter()
    tr_counter = Counter()
    n_counter = Counter() # N-Grams (sílabas/combinações char)
    
    total_pw = 0
    total_tok = 0

    with open(filepath, 'rb') as f:
        f.seek(start_byte)
        if start_byte > 0:
            f.readline() # pular até a próxima linha completa

        while f.tell() < end_byte:
            line = f.readline()
            if not line: break
            
            try:
                pwd = line.decode('utf-8', errors='ignore').strip()
                if not pwd: continue
                total_pw += 1
                
                # Aprende N-Grams (Padrões silábicos BR vs US)
                lower_pwd = pwd.lower()
                for i in range(len(lower_pwd)-1):
                    n_counter[lower_pwd[i:i+2]] += 1
                for i in range(len(lower_pwd)-2):
                    n_counter[lower_pwd[i:i+3]] += 1

                # Machine Learning do Padrão Estrutural
                dna = parse_password(pwd)
                p_counter[dna.pattern] += 1
                
                prev_tok = None
                for token in dna.tokens:
                    t_counter[token.token_type] += 1
                    total_tok += 1
                    if prev_tok:
                        tr_counter[f"{prev_tok}->{token.token_type}"] += 1
                    prev_tok = token.token_type
            except Exception:
                pass

    return {
        "token": dict(t_counter),
        "pattern": dict(p_counter),
        "transition": dict(tr_counter),
        "ngram": dict(n_counter),
        "total_pw": total_pw,
        "total_tok": total_tok
    }


from ui_utils import show_help_and_exit


# ==========================================
# COMMAND: COLLECT
# ==========================================
@click.command(name="collect", add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.option('-i', '--input', 'input_src', required=False, type=str, help="Input wordlist file or string to parse.")
@click.option('-L', '--list', 'list_files', is_flag=True, help="List all JSON datasets in the internal folder.")
@click.option('-P', '--print', 'print_file', required=False, type=str, help="Print dataset content to terminal as a table.")
@click.option('-D', '--delete', 'delete_file', required=False, type=str, help="Delete a specific dataset from the folder.")
@click.pass_context
def collect(ctx, input_src, list_files, print_file, delete_file):
    is_pt = ctx.obj.get('LANG_PT', False)
    t = get_lang(is_pt)

    # Validate mutual exclusivity
    actions = sum([bool(input_src), bool(list_files), bool(print_file), bool(delete_file)])
    
    if actions > 1:
        console.print(f"[red]{t['err_conflict']}[/red]")
        return
    elif actions == 0:
        console.print(f"[red]{t['err_no_action']}[/red]")
        return

    # -------------------------
    # ACTION: LIST FILES (-L)
    # -------------------------
    if list_files:
        files = [f for f in os.listdir(TRAINER_DIR) if f.endswith(".json")]
        if not files:
            console.print(f"[yellow]{t['list_empty']}[/yellow]")
            return
            
        t_table = Table(title=t["list_title"], header_style="bold white", border_style="red")
        t_table.add_column(t["list_col_name"], style="bold red")
        t_table.add_column(t["list_col_date"], justify="right", style="white")
        
        for f in files:
            filepath = os.path.join(TRAINER_DIR, f)
            timestamp = os.path.getctime(filepath)
            dt_object = datetime.fromtimestamp(timestamp)
            t_table.add_row(f, dt_object.strftime("%Y-%m-%d %H:%M:%S"))
            
        console.print(t_table)
        return

    # -------------------------
    # ACTION: DELETE (-D)
    # -------------------------
    if delete_file:
        # Bloqueia caminhos externos ou tentativas de path traversal
        if os.path.dirname(delete_file).strip():
            err_path = (
                f"\n[bold red][!][/bold red] Erro: O flag [bold]-D[/bold] aceita apenas o nome do dataset dentro da pasta [dim]{TRAINER_DIR}[/dim]. Caminhos externos não são permitidos.\n"
                if is_pt else
                f"\n[bold red][!][/bold red] Error: The [bold]-D[/bold] flag only accepts dataset names inside the [dim]{TRAINER_DIR}[/dim] folder. External paths are not allowed.\n"
            )
            console.print(err_path)
            return

        clean_file = os.path.basename(delete_file).strip()
        if not clean_file.lower().endswith(".json"):
            clean_file += ".json"

        target_path = os.path.abspath(os.path.join(TRAINER_DIR, clean_file))
        trainer_abs = os.path.abspath(TRAINER_DIR)

        try:
            is_inside = (os.path.commonpath([target_path, trainer_abs]) == trainer_abs)
        except ValueError:
            is_inside = False

        if not is_inside or not os.path.exists(target_path):
            console.print(f"[red]{t['err_dataset_not_found'].format(file=clean_file)}[/red]")
            return

        confirm_q = (
            f"Tem certeza que deseja apagar o dataset '{clean_file}' permanentemente?"
            if is_pt else
            f"Are you sure you want to permanently delete dataset '{clean_file}'?"
        )
        if not click.confirm(f"\n[bold yellow][?][/bold yellow] {confirm_q}", default=False):
            cancel_msg = (
                f"[yellow]Operação cancelada.[/yellow] O dataset [bold]{clean_file}[/bold] não foi apagado.\n"
                if is_pt else
                f"[yellow]Operation cancelled.[/yellow] Dataset [bold]{clean_file}[/bold] was not deleted.\n"
            )
            console.print(cancel_msg)
            return

        try:
            os.remove(target_path)
            console.print(t['msg_deleted'].format(file=clean_file))
        except Exception as e:
            console.print(f"[bold red][!] Falha ao apagar arquivo: {e}[/bold red]")
        return

    # -------------------------
    # ACTION: PRINT (-P)
    # -------------------------
    if print_file:
        if os.path.dirname(print_file).strip():
            err_path = (
                f"\n[bold red][!][/bold red] Erro: O flag [bold]-P[/bold] aceita apenas o nome do dataset dentro da pasta [dim]{TRAINER_DIR}[/dim]. Caminhos externos não são permitidos.\n"
                if is_pt else
                f"\n[bold red][!][/bold red] Error: The [bold]-P[/bold] flag only accepts dataset names inside the [dim]{TRAINER_DIR}[/dim] folder. External paths are not allowed.\n"
            )
            console.print(err_path)
            return

        clean_print = os.path.basename(print_file).strip()
        if not clean_print.lower().endswith(".json"):
            clean_print += ".json"

        target_path = os.path.abspath(os.path.join(TRAINER_DIR, clean_print))
        trainer_abs = os.path.abspath(TRAINER_DIR)

        try:
            is_inside = (os.path.commonpath([target_path, trainer_abs]) == trainer_abs)
        except ValueError:
            is_inside = False

        if not is_inside or not os.path.exists(target_path):
            # Friendly error: explain what -P expects
            is_pt_local = ctx.obj.get('LANG_PT', False) if ctx and ctx.obj else False

            if is_pt_local:
                console.print(f"\n[bold red][!][/bold red] Dataset [bold]{print_file}[/bold] não encontrado em [dim]{TRAINER_DIR}[/dim].\n")
                console.print("[dim]O flag [/dim][bold]-P[/bold][dim] exibe um dataset JSON gerado pelo [/dim][bold]collect -i[/bold][dim], não um arquivo .txt.[/dim]\n")
                console.print("[dim]Para criar um dataset a partir de uma wordlist, use:[/dim]")
                console.print(f"  [bold green]cypherdna collect -i <wordlist.txt>[/bold green]\n")
            else:
                console.print(f"\n[bold red][!][/bold red] Dataset [bold]{print_file}[/bold] not found in [dim]{TRAINER_DIR}[/dim].\n")
                console.print("[dim]The [/dim][bold]-P[/bold][dim] flag prints a JSON dataset generated by [/dim][bold]collect -i[/bold][dim], not a .txt file.[/dim]\n")
                console.print("[dim]To create a dataset from a wordlist, run:[/dim]")
                console.print(f"  [bold green]cypherdna collect -i <wordlist.txt>[/bold green]\n")

            # List available datasets if any
            if os.path.exists(TRAINER_DIR):
                available = [f for f in os.listdir(TRAINER_DIR) if f.endswith(".json")]
                if available:
                    label = "Datasets disponíveis" if is_pt_local else "Available datasets"
                    console.print(f"[bold white]{label}:[/bold white] " + ", ".join(available) + "\n")
            return

            
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        t_table = Table(title=t["print_title"], header_style="bold white", border_style="red")
        t_table.add_column(t["print_col_type"], style="red")
        t_table.add_column(t["print_col_freq"], justify="right", style="white")
        
        tokens = data.get("token_frequencies", {})
        for tok_type, count in sorted(tokens.items(), key=lambda item: item[1], reverse=True):
            t_table.add_row(tok_type, str(count))
            
        console.print("\n")
        console.print(t_table)
        
        console.print(f"\n[bold yellow]{t['print_patterns']}[/bold yellow]")
        patterns = data.get("pattern_frequencies", {})
        for pat, count in patterns.items():
            console.print(f"- [magenta]{pat}[/magenta] ({count} occurrences)")
        return

    # -------------------------
    # ACTION: INPUT & PARSE (-i)
    # -------------------------
    if input_src:
        token_counter = Counter()
        pattern_counter = Counter()
        transition_counter = Counter()
        ngram_counter = Counter() # NOVO: Sílabas (N-Grams)
        total_tokens = 0
        total_passwords = 0
        
        title = t["cmd_collect"]
        console.print(f"\n[bold white on red] {title} [/bold white on red]\n")
        
        if os.path.exists(input_src):
            import concurrent.futures
            from multiprocessing import cpu_count
            
            file_size = os.path.getsize(input_src)
            num_workers = min(cpu_count(), 16) # Cap de segurança para RAM
            if num_workers < 1: num_workers = 1
            
            chunk_size = file_size // num_workers
            chunks = []
            for i in range(num_workers):
                start = i * chunk_size
                end = start + chunk_size if i < num_workers - 1 else file_size
                chunks.append({'filepath': input_src, 'start_byte': start, 'end_byte': end})

            try:
                with console.status(f"[bold cyan]Treinando modelo (núcleos: {num_workers})...\n[yellow]Analisando N-gramas e cadeias de Markov...", spinner="aesthetic"):
                    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
                        futures = [executor.submit(process_chunk, c) for c in chunks]
                        for future in concurrent.futures.as_completed(futures):
                            res = future.result()
                            token_counter.update(res["token"])
                            pattern_counter.update(res["pattern"])
                            transition_counter.update(res["transition"])
                            ngram_counter.update(res["ngram"])
                            total_passwords += res["total_pw"]
                            total_tokens += res["total_tok"]
            except MemoryError:
                console.print("\n[bold red][❌ MEMORY CRASH][/bold red] The training process ran out of RAM and was automatically cancelled.")
                console.print("[yellow]Tip:[/yellow] Try using a smaller wordlist, reduce the number of custom tokens, or free up system RAM before retrying.")
                return
            except Exception as _train_ex:
                if "MemoryError" in str(_train_ex) or "memory" in str(_train_ex).lower():
                    console.print("\n[bold red][❌ MEMORY CRASH][/bold red] Training process was killed due to memory overload.")
                    console.print("[yellow]Tip:[/yellow] Reduce wordlist size or remove unused custom tokens.")
                    return
                raise
        else:
            # Entrada de string direta pelo terminal
            pwd = input_src.strip()
            total_passwords += 1
            lower_pwd = pwd.lower()
            for i in range(len(lower_pwd)-1):
                ngram_counter[lower_pwd[i:i+2]] += 1
            for i in range(len(lower_pwd)-2):
                ngram_counter[lower_pwd[i:i+3]] += 1

            try:
                dna = parse_password(pwd)
                pattern_counter[dna.pattern] += 1
                
                prev_token_type = None
                for token in dna.tokens:
                    tok_t = token.token_type
                    token_counter[tok_t] += 1
                    total_tokens += 1
                    if prev_token_type:
                        transition_counter[f"{prev_token_type}->{tok_t}"] += 1
                    prev_token_type = tok_t
            except Exception:
                pass
                
        stats_data = {
            "metadata": {
                "total_passwords_analyzed": total_passwords,
                "total_tokens_mapped": total_tokens
            },
            "token_frequencies": dict(token_counter.most_common()),
            "pattern_frequencies": dict(pattern_counter.most_common(50)),
            "token_transitions": dict(transition_counter.most_common(100)),
            "ngram_frequencies": dict(ngram_counter.most_common(200)) # TOP 200 sílabas usadas
        }

        # Auto-save filename gen
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = os.path.basename(input_src).split('.')[0] if os.path.exists(input_src) else "string_input"
        output_filename = f"resultado_{safe_name}_{timestamp_str}.json"
        output_path = os.path.join(TRAINER_DIR, output_filename)

        with open(output_path, "w", encoding="utf-8") as out_f:
            json.dump(stats_data, out_f, indent=4)

        console.print(f"[bold green]" + t['msg_saved'].format(output=output_filename) + "[/bold green]")


if __name__ == "__main__":
    collect()
