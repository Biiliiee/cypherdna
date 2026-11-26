"""
CypherDNA Generator Command
- generator: Generate targeted wordlists using personal data inputs
"""

import sys
import os
import json
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from config import RANKER_FILE, TRAINER_DIR, WORDLISTS_DIR, YOU_WORDLIST_DIR
from dna_parser import parse_password, DNAResult
from Gen import generate_wordlist
from probabilistic_model import ProbabilisticModel
from benchmark import Benchmark
from ui_utils import format_pattern, safe_open, show_help_and_exit
from i18n import get_text

console = Console()


def is_sensitive_directory(path: str) -> bool:
    """Verifica se o caminho pertence a diretórios sensíveis do sistema operacional."""
    try:
        norm = os.path.abspath(path).lower()
    except Exception:
        return True

    if sys.platform == "win32":
        sys_root = os.environ.get("SystemRoot", r"C:\Windows").lower()
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files").lower()
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)").lower()
        for protected in [sys_root, prog_files, prog_files_x86]:
            if protected and (norm == protected or norm.startswith(protected + os.sep)):
                return True
    else:
        sensitive_roots = ["/etc", "/boot", "/bin", "/sbin", "/usr/bin", "/usr/sbin", "/dev", "/proc", "/sys"]
        for s in sensitive_roots:
            if norm == s or norm.startswith(s + "/"):
                return True
    return False


@click.command(name="generator", add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.argument("inputs", nargs=-1)
@click.option("-N", "--number", required=False, type=int, help="Wordlist size (how many passwords)")
@click.option("-o", "--output", required=False, type=str, help="Output file name")
@click.option("-S", "--symbol", required=False, is_flag=True, help="Enable symbol mutations")
@click.option("-c", "--case", is_flag=True, help="Enable full binary casing permutations (all 2^N upper/lower combinations, e.g., banana, bAnana, baNana...)")
@click.option("-T", "--trainer", is_flag=False, flag_value="SELECT_MENU", default=None, help="Especifica dataset de treinamento (ex: -T rockyou, -T cars ou apenas -T para menu interativo)")
@click.option("-L", "--leet", is_flag=True, help="Enable dynamic Leet Speak mutations")
@click.option("-V", "--validate", is_flag=False, flag_value="self", default=None, help="Executa o Benchmark. Aceita wordlists separadas por virgula (Ex: -V ou -V file1.txt,file2.txt).")
@click.option("-P", "--pipe", "--stdout", is_flag=True, help="Outputs passwords directly to STDOUT (Silent mode) for Hashcat/John the Ripper piping.")
@click.option("-R", "--rank", is_flag=True, help="Apply my custom Strategic Ranking from the 'ranker' command.")
@click.pass_context
def generator(ctx, inputs, number, output, symbol, trainer, leet, validate, pipe, rank, case=False, leak_reconstruct=False):
    """Generate a wordlist using personal inputs (names, dates, years, etc)."""
    is_pt = ctx.obj.get('LANG_PT', False) if ctx.obj else False
    lang = "pt" if is_pt else "en"

    # Load Ranker if requested
    active_rank_data = None
    if rank:
        if os.path.exists(RANKER_FILE):
            try:
                with open(RANKER_FILE, "r", encoding="utf-8") as rf:
                    active_rank_data = json.load(rf)
            except Exception:
                pass

    _from_osint = bool(ctx.obj.get('osint_tokens')) if ctx.obj else False
    osint_tokens = ctx.obj.get('osint_tokens', []) if ctx.obj else []
    parsed_results = []

    # 1. Process OSINT tokens if available
    if osint_tokens:
        parsed_results.append(DNAResult(
            raw="osint_scan",
            normalized="osint_scan",
            tokens=osint_tokens,
            pattern="+".join([t.token_type for t in osint_tokens]),
            features={}
        ))

    # 2. Process Manual Inputs
    sanitized_inputs = [str(x).strip()[:64] for x in inputs]
    for item in sanitized_inputs:
        if item:
            parsed_results.append(parse_password(item))

    if not parsed_results:
        if not pipe:
            if trainer:
                console.print(f"[bold yellow][!][/bold yellow] Para usar o dataset '[cyan]{trainer}[/cyan]', informe os termos/alvos desejados.\n  [dim]Exemplo: cypherdna generator admin 2024 -T {trainer}[/dim]")
            else:
                console.print("[bold red][!][/bold red] Nenhuma entrada (nome, palavra, ano) foi fornecida.\n  [dim]Exemplo: cypherdna generator xbox 360 naruto[/dim]")
        return

    if not _from_osint:
        if len(sanitized_inputs) > 5 and not pipe:
            console.print(get_text("generator", "warn_many_inputs", lang))

    # Carregar modelo probabilístico
    model = ProbabilisticModel(data_folder=TRAINER_DIR)
    model.load_jsons(is_pt=is_pt, specific_file=trainer)
    model.calculate_probabilities()

    if not pipe:
        title = get_text("generator", "title", lang)
        console.print(f"\n[bold white on red] {title} [/bold white on red]\n")

        # 1. Identificar tokens disponíveis com multiplicidade exata conforme Gen.py
        from collections import Counter
        standard_panel_types = {
            "NAME", "WORD", "YEAR", "NUMBER", "MONTH", "SYMBOL",
            "SEPARATOR", "DATE", "SEASON", "WEAK_WORD", "REPEATED", "KEY_WALK"
        }
        token_counts = Counter()
        seen_tok_keys = set()
        for res in parsed_results:
            for tok in res.tokens:
                tt = tok.token_type
                val_norm = tok.value.strip()
                tkey = (tt, val_norm)
                if tkey in seen_tok_keys:
                    continue
                seen_tok_keys.add(tkey)
                token_counts[tt] += 1
                if tt == "KEY_WALK" and val_norm.isdigit():
                    token_counts["NUMBER"] += 1
                elif tt not in standard_panel_types:
                    is_known_custom = (
                        model.get_token_probability(tt) > 0
                        and any(tt in p.split("+") for p in model.pattern_probabilities)
                    )
                    if not is_known_custom:
                        token_counts["WORD"] += 1

        total_non_delim = sum(cnt for k, cnt in token_counts.items() if k not in ("SYMBOL", "SEPARATOR"))

        def _can_panel_generate(pat_str):
            parts = [p for p in pat_str.split("+") if p]
            non_delims = [p for p in parts if p not in ("SYMBOL", "SEPARATOR")]
            if not non_delims or len(non_delims) > 4:
                return False
            # Gen.py rejeita >1 YEAR/DATE e separador sem 2+ tokens
            if sum(1 for p in non_delims if p in ("YEAR", "DATE")) > 1:
                return False
            sep_need = parts.count("SEPARATOR")
            sym_need = parts.count("SYMBOL")
            if sep_need > 0 and (not symbol and token_counts["SEPARATOR"] == 0 or len(non_delims) < 2):
                return False
            if sep_need > max(0, len(non_delims) - 1) and token_counts["SEPARATOR"] < sep_need:
                return False
            if sym_need > 0 and (not symbol and token_counts["SYMBOL"] < sym_need):
                return False
            if sym_need > 1 + token_counts["SYMBOL"]:
                return False
            # Se padrão termina com SEPARATOR isolado ou começa com SEPARATOR não gerado no Phase 2
            if parts[0] == "SEPARATOR" or parts[-1] == "SEPARATOR":
                return False
            need = Counter(non_delims)
            return all(token_counts[t] >= cnt for t, cnt in need.items())

        # 2. Buscar padrões prioritários (Fase 1: Ranker -> Fase 2: Modelo de IA treinado)
        top_strat = []
        seen_strat_pats = set()
        if rank and active_rank_data:
            for pat in active_rank_data:
                prob = model.get_pattern_probability(pat)
                top_strat.append((pat, prob, "RANKER"))
                seen_strat_pats.add(pat.upper())

        for pat, prob in sorted(model.pattern_probabilities.items(), key=lambda x: x[1], reverse=True):
            if pat.upper() not in seen_strat_pats and _can_panel_generate(pat):
                top_strat.append((pat, prob, "AI"))
                seen_strat_pats.add(pat.upper())
                if len([x for x in top_strat if x[2] == "AI"]) >= 5:
                    break

        # 3. Painel de Estratégia
        strat_table = Table(box=None, header_style="bold magenta")
        strat_table.add_column(get_text("generator", "col_pattern", lang), width=35)
        strat_table.add_column(get_text("generator", "col_prob", lang), justify="right")

        if top_strat:
            for pat, prob, source in top_strat:
                if source == "RANKER":
                    p_text = "[bold yellow]RANKER (1º)[/bold yellow]" if is_pt else "[bold yellow]RANKER (1st)[/bold yellow]"
                else:
                    ai_tag = "IA" if is_pt else "AI"
                    p_text = f"[bold cyan]{ai_tag}[/bold cyan] [bold white]{prob:.2%}[/bold white]" if rank else f"[bold white]{prob:.2%}[/bold white]"
                strat_table.add_row(format_pattern(pat), p_text)
        else:
            msg_fallback = get_text("generator", "msg_fallback", lang)
            strat_table.add_row(f"[dim]{msg_fallback}[/dim]", "0.00%")

        console.print(Panel(strat_table, title=get_text("generator", "strat_panel_title", lang), border_style="bright_blue"))

        # 4. Painel de Configurações Ativas
        config_text = Text()
        config_text.append(get_text("generator", "label_leet", lang), style="dim")
        config_text.append((get_text("generator", "status_enabled", lang) if leet else get_text("generator", "status_disabled", lang)) + "  ", style="bold green" if leet else "dim red")

        config_text.append(get_text("generator", "label_ranker", lang), style="dim")
        config_text.append((get_text("generator", "status_enabled", lang) if rank else get_text("generator", "status_disabled", lang)) + "  ", style="bold green" if rank else "dim red")

        config_text.append(get_text("generator", "label_case", lang), style="dim")
        config_text.append((get_text("generator", "status_enabled", lang) if case else get_text("generator", "status_disabled", lang)) + "  ", style="bold green" if case else "dim red")

        config_text.append(get_text("generator", "label_symbols", lang), style="dim")
        config_text.append((get_text("generator", "status_enabled", lang) if symbol else get_text("generator", "status_disabled", lang)) + "  ", style="bold green" if symbol else "dim red")

        config_text.append(get_text("generator", "label_payload", lang), style="dim")
        config_text.append(str(number or "10,000"), style="bold white")

        console.print(Panel(config_text, title=get_text("generator", "config_panel_title", lang), border_style="bright_red"))

        if rank and not active_rank_data:
            warn_empty_rank = (
                "[yellow][!][/yellow] Flag [bold]-R[/bold] ativa, mas nenhuma estratégia do Ranker está carregada. Use [bold]cypherdna ranker -C[/bold] ou [bold]-P corporate[/bold]."
                if is_pt else
                "[yellow][!][/yellow] Flag [bold]-R[/bold] is enabled, but no Ranker strategy is active. Use [bold]cypherdna ranker -C[/bold] or [bold]-P corporate[/bold]."
            )
            console.print(warn_empty_rank)
        elif rank and active_rank_data and not symbol and any("SYMBOL" in pat.upper() or "SEPARATOR" in pat.upper() for pat in active_rank_data):
            warn_sym_rank = (
                "[yellow][!][/yellow] Sua estratégia do Ranker usa [bold]SYMBOL/SEPARATOR[/bold], mas [bold]-S[/bold] está desabilitado. Adicione [bold]-S[/bold] para injetar símbolos."
                if is_pt else
                "[yellow][!][/yellow] Your active Ranker strategy uses [bold]SYMBOL/SEPARATOR[/bold], but [bold]-S[/bold] is disabled. Add [bold]-S[/bold] to inject symbols."
            )
            console.print(warn_sym_rank)

        console.print(get_text("generator", "msg_generating", lang))

    try:
        wordlist = generate_wordlist(
            parsed_results=parsed_results,
            max_words=number,
            symbols=symbol,
            model=model,
            use_leet=leet,
            leak_mode=leak_reconstruct,
            custom_rank=active_rank_data,
            full_case=case
        )
    except MemoryError:
        console.print("\n[bold red][❌ MEMORY CRASH][/bold red] The generator ran out of RAM and was automatically cancelled.")
        console.print("[yellow]Tip:[/yellow] Try fewer inputs, disable leet/symbol mutations, or remove unused custom tokens.")
        return
    except Exception as _gen_ex:
        if "MemoryError" in str(_gen_ex) or "memory" in str(_gen_ex).lower():
            console.print("\n[bold red][❌ MEMORY CRASH][/bold red] Generation process was killed due to memory overload.")
            console.print("[yellow]Tip:[/yellow] Reduce the number of inputs, tokens, or wordlist size.")
            return
        raise

    if not wordlist:
        if not pipe:
            console.print(get_text("generator", "err_no_words", lang))
        return

    if pipe:
        for w in wordlist:
            sys.stdout.write(w + "\n")
        sys.stdout.flush()
        return

    # ── Resolução do caminho e nome de saída ──────────────────
    user_dir = os.path.dirname(output).strip() if output else ""

    if not output or not user_dir:
        # Usuário passou apenas o nome do arquivo ou não passou nada (-o ausente)
        target_dir = YOU_WORDLIST_DIR
        raw_name = os.path.basename(output).strip() if output else "cypherdna.txt"
        if not raw_name:
            raw_name = "cypherdna.txt"
        if not raw_name.lower().endswith(".txt"):
            raw_name += ".txt"
        base_name = raw_name[:-4]
    else:
        # Usuário passou um caminho com diretório (absoluto ou relativo)
        expanded = os.path.expanduser(output.strip())
        abs_path = os.path.abspath(expanded)
        target_dir = os.path.dirname(abs_path)
        raw_name = os.path.basename(abs_path).strip()
        if not raw_name:
            raw_name = "cypherdna.txt"
        if not raw_name.lower().endswith(".txt"):
            raw_name += ".txt"
        base_name = raw_name[:-4]

        # Validação contra diretórios protegidos do sistema
        if is_sensitive_directory(target_dir):
            err_title = "Caminho Bloqueado" if is_pt else "Blocked Path"
            err_desc = (
                f"O caminho de destino '{target_dir}' pertence a um diretório protegido do sistema operacional."
                if is_pt else
                f"The target path '{target_dir}' belongs to a protected operating system directory."
            )
            console.print(f"\n[bold red]❌ {err_title}:[/bold red] {err_desc}\n")
            return

    # Garante a existência do diretório de destino
    try:
        os.makedirs(target_dir, exist_ok=True)
    except Exception as e:
        err_title = "Erro de Diretório" if is_pt else "Directory Error"
        err_desc = (
            f"Não foi possível criar ou acessar o diretório '{target_dir}'.\n[dim]Detalhes: {e}[/dim]"
            if is_pt else
            f"Could not create or access directory '{target_dir}'.\n[dim]Details: {e}[/dim]"
        )
        console.print(f"\n[bold red]❌ {err_title}:[/bold red] {err_desc}\n")
        return

    # Evita sobrescrever arquivo existente (ex: nome.txt -> nome_2.txt, nome_3.txt)
    safe_output_path = os.path.join(target_dir, f"{base_name}.txt")
    counter = 2
    while os.path.exists(safe_output_path):
        safe_output_path = os.path.join(target_dir, f"{base_name}_{counter}.txt")
        counter += 1

    # Gravação segura do arquivo
    try:
        with open(safe_output_path, "w", encoding="utf-8") as f:
            for w in wordlist:
                f.write(w + "\n")
    except Exception as e:
        err_title = "Erro de Gravação" if is_pt else "Write Error"
        err_desc = (
            f"Falha ao salvar a wordlist em '{safe_output_path}'.\n[dim]Detalhes: {e}[/dim]"
            if is_pt else
            f"Failed to save wordlist to '{safe_output_path}'.\n[dim]Details: {e}[/dim]"
        )
        console.print(f"\n[bold red]❌ {err_title}:[/bold red] {err_desc}\n")
        return

    # Painel final de sucesso
    final_msg = Text.assemble(
        (get_text("generator", "final_msg_success", lang, count=len(wordlist)), "bold green"),
        (get_text("generator", "final_msg_location", lang), "dim"), (safe_output_path, "bold cyan")
    )
    console.print(Panel(final_msg, border_style="bright_green", title=get_text("generator", "generation_complete", lang)))

    prompt = get_text("generator", "prompt_open", lang)
    choice = console.input(prompt).strip().lower()

    if choice in ("", "y", "yes", "s", "sim"):
        err = safe_open(safe_output_path)
        if err:
            console.print(get_text("generator", "err_opening", lang, error=err))

    # Benchmark automático (-V)
    if validate is not None:
        valid_title = get_text("generator", "valid_title", lang)
        console.print(f"[bold white on red] {valid_title} [/bold white on red]\n")
        model = ProbabilisticModel()
        model.load_jsons()
        model.calculate_probabilities()

        bench = Benchmark(model, is_pt=is_pt)
        bench.evaluate_wordlist(safe_output_path)

        cleaned_validate = validate.lstrip('=')
        target_str = cleaned_validate.lower().strip()
        if target_str not in ["", "self", "only", "true", "none"]:
            extra_lists = [w.strip() for w in cleaned_validate.split(",") if w.strip()]
            for extra_wl in extra_lists:
                if not os.path.isabs(extra_wl) and not os.path.exists(extra_wl):
                    lookup_path = os.path.join(WORDLISTS_DIR, extra_wl)
                    bench.evaluate_wordlist(lookup_path)
                else:
                    bench.evaluate_wordlist(extra_wl)

        bench.print_report()
