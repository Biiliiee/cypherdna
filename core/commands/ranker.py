"""
CypherDNA Ranker Command
- ranker: Manage custom strategic DNA priority rankings and .dna strategy files
"""

import os
import re
import json
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
import rich.box

from config import RANKER_FILE, STRATEGIES_DIR, CUSTOM_TOKENS_DIR
from ui_utils import format_pattern, get_preview_example, show_help_and_exit
from i18n import get_text

console = Console()

STANDARD_TOKENS = [
    "NAME", "WORD", "YEAR", "DATE", "MONTH",
    "NUMBER", "SYMBOL", "SEPARATOR", "REPEATED", "KEY_WALK"
]

PRESETS = {
    "corporate": {
        "patterns": ["NaME+YEAR", "NaME+SYMBOL+YEAR", "NaME+NUMBER", "NaME+YEAR+SYMBOL"],
        "desc_en": "Ideal for corporate credentials & Active Directory policies",
        "desc_pt": "Ideal para senhas corporativas e infraestrutura (Active Directory)"
    },
    "minimalist": {
        "patterns": ["NAME+YEAR", "YEAR+NAME", "NAME+NUMBER"],
        "desc_en": "Fast minimalist priority order with essential combinations",
        "desc_pt": "Estratégia minimalista e rápida com combinações essenciais"
    },
    "hardcore": {
        "patterns": ["N@ME+SYMBOL+YEAR", "W0RD+NUMBER+SYMBOL", "NaME+SEPARATOR+YEAR", "KEY_WALK+SYMBOL"],
        "desc_en": "Deep mutations combining leet speak, symbols and key walks",
        "desc_pt": "Mutações profundas combinando leet speak, símbolos e sequências de teclado"
    }
}


def _load_active_rankings():
    """Carrega a lista de padrões ativos em RANKER_FILE."""
    if not os.path.exists(RANKER_FILE):
        return []
    try:
        with open(RANKER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x).strip() for x in data if isinstance(x, str) and x.strip()]
    except Exception:
        pass
    return []


def _save_active_rankings(rankings):
    """Persiste os padrões ativos em RANKER_FILE."""
    os.makedirs(os.path.dirname(RANKER_FILE), exist_ok=True)
    with open(RANKER_FILE, "w", encoding="utf-8") as f:
        json.dump(rankings, f, indent=4)


def _list_dna_files():
    """Retorna os nomes dos arquivos .dna salvos em STRATEGIES_DIR."""
    os.makedirs(STRATEGIES_DIR, exist_ok=True)
    files = [f for f in os.listdir(STRATEGIES_DIR) if f.lower().endswith(".dna")]
    return sorted(files, key=str.lower)


def _read_dna_file(filepath):
    """Lê e valida um arquivo .dna, retornando lista de padrões ou None."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            cleaned = [str(x).strip() for x in data if isinstance(x, str) and x.strip()]
            if cleaned:
                return cleaned
    except Exception:
        pass
    return None


def _resolve_strategy_in_dir(raw_name):
    """
    Resolve um arquivo .dna estritamente dentro de STRATEGIES_DIR (case-insensitive).
    Retorna (caminho_absoluto, status) onde status é 'ok', 'traversal' ou 'not_found'.
    """
    clean = str(raw_name).strip().strip('"').strip("'")
    if not clean or os.path.dirname(clean).strip():
        return None, "traversal"

    target_name = os.path.basename(clean)
    if not target_name.lower().endswith(".dna"):
        target_name += ".dna"

    strategies_abs = os.path.abspath(STRATEGIES_DIR)
    exact_path = os.path.abspath(os.path.join(strategies_abs, target_name))
    try:
        if os.path.commonpath([exact_path, strategies_abs]) != strategies_abs:
            return None, "traversal"
    except ValueError:
        return None, "traversal"

    if os.path.isfile(exact_path):
        return exact_path, "ok"

    # Busca case-insensitive para compatibilidade Linux/macOS
    target_lower = target_name.lower()
    for fname in _list_dna_files():
        if fname.lower() == target_lower:
            return os.path.abspath(os.path.join(strategies_abs, fname)), "ok"

    return exact_path, "not_found"


def _sanitize_strategy_filename(raw_name):
    """Normaliza um nome informado pelo usuário para arquivo seguro '<nome>.dna' em STRATEGIES_DIR."""
    clean = str(raw_name).strip().strip('"').strip("'")
    if os.path.dirname(clean).strip():
        return None
    base = os.path.basename(clean)
    base = re.sub(r'[<>:"/\\|?*]', "_", base).strip(" .")
    if not base:
        return None
    if not base.lower().endswith(".dna"):
        base += ".dna"
    return base


def _next_default_strategy_name():
    """Gera o próximo nome padrão livre (ex: custom_1) em STRATEGIES_DIR."""
    existing = {f.lower() for f in _list_dna_files()}
    idx = 1
    while f"custom_{idx}.dna" in existing:
        idx += 1
    return f"custom_{idx}"


def _write_strategy_in_dir(filename, patterns):
    """Grava a estratégia em STRATEGIES_DIR/<filename>.dna e retorna o caminho."""
    os.makedirs(STRATEGIES_DIR, exist_ok=True)
    safe_name = _sanitize_strategy_filename(filename)
    if not safe_name:
        raise ValueError("Invalid strategy filename")
    strategies_abs = os.path.abspath(STRATEGIES_DIR)
    dest_path = os.path.abspath(os.path.join(strategies_abs, safe_name))
    if os.path.commonpath([dest_path, strategies_abs]) != strategies_abs:
        raise ValueError("Invalid strategy path")
    with open(dest_path, "w", encoding="utf-8") as f:
        json.dump(patterns, f, indent=4)
    return dest_path


def _rules_word(count, lang):
    """Retorna 'regra'/'regras' ou 'rule'/'rules' no singular/plural correto."""
    if lang == "pt":
        return "regra" if count == 1 else "regras"
    return "rule" if count == 1 else "rules"


def _confirm_action(prompt_markup, lang, default=False, danger=False):
    """Solicita confirmação usando Rich console.input para renderizar cores corretamente."""
    badge = "[bold red]\\[?][/bold red]" if danger else "[bold yellow]\\[?][/bold yellow]"
    if lang == "pt":
        choices = "[dim]\\[S/n]:[/dim]" if default else "[dim]\\[s/N]:[/dim]"
    else:
        choices = "[dim]\\[Y/n]:[/dim]" if default else "[dim]\\[y/N]:[/dim]"
    try:
        raw = console.input(f"{badge} [white]{prompt_markup}[/white] {choices} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print()
        return False
    if not raw:
        return default
    return raw in ("y", "yes", "s", "sim")


def _render_pattern_table(patterns, title, lang, numbered=True):
    """Exibe uma tabela Rich formatada com os padrões e exemplos."""
    console.print(f"[bold white]{title}[/bold white]")
    tbl = Table(box=rich.box.ROUNDED, header_style="bold magenta", border_style="cyan")
    tbl.add_column("#" if not numbered else get_text("ranker", "col_rank", lang), justify="center", style="bold yellow")
    tbl.add_column(get_text("ranker", "col_pattern", lang))
    tbl.add_column(get_text("ranker", "preview_label", lang), justify="left")

    for i, pat in enumerate(patterns, 1):
        rank_label = f"#{i}" if numbered else str(i)
        tbl.add_row(rank_label, format_pattern(pat), f"[dim white]{get_preview_example(pat)}[/dim white]")

    console.print(tbl)


def _handle_list(rankings, lang):
    """Exibe ranking ativo, presets internos e arquivos .dna salvos."""
    title = get_text("ranker", "title", lang)
    console.print(f"\n[bold white on red] {title} [/bold white on red]\n")

    if rankings:
        _render_pattern_table(rankings, get_text("ranker", "list_title", lang), lang, numbered=True)
        console.print()
    else:
        console.print(f" [dim]{get_text('ranker', 'empty', lang)}[/dim]\n")

    console.print(f"[bold white]{get_text('ranker', 'available_title', lang)}[/bold white]")
    list_table = Table(box=rich.box.ROUNDED, border_style="bright_blue")
    list_table.add_column("Type" if lang == "en" else "Tipo", justify="center", style="dim")
    list_table.add_column("Name" if lang == "en" else "Nome", style="bold cyan")
    list_table.add_column("Details" if lang == "en" else "Detalhes", style="white")

    desc_key = "desc_pt" if lang == "pt" else "desc_en"
    for p_name, p_info in PRESETS.items():
        cnt = len(p_info["patterns"])
        rules_str = f"{cnt} {_rules_word(cnt, lang)} - {p_info[desc_key]}"
        list_table.add_row("PRESET", p_name, f"[dim]{rules_str}[/dim]")

    dna_files = _list_dna_files()
    for fname in dna_files:
        fpath = os.path.join(STRATEGIES_DIR, fname)
        pats = _read_dna_file(fpath) or []
        cnt = len(pats)
        preview = ", ".join(pats[:2]) + ("..." if cnt > 2 else "")
        detail = f"{cnt} {_rules_word(cnt, lang)}" + (f" ({preview})" if preview else "")
        list_table.add_row("CUSTOM (.dna)", fname.rsplit(".", 1)[0], f"[dim]{detail}[/dim]")

    console.print(list_table)
    console.print(f"\n{get_text('ranker', 'quick_usage', lang)}\n")


def _handle_preset(preset_val, lang):
    """Seleciona (se __MENU__) e ativa imediatamente um preset interno."""
    keys = list(PRESETS.keys())
    desc_key = "desc_pt" if lang == "pt" else "desc_en"

    if preset_val == "__MENU__":
        lines = []
        for idx, k in enumerate(keys, 1):
            pats = ", ".join(PRESETS[k]["patterns"][:2])
            lines.append(f"  [bold yellow]\\[{idx}][/bold yellow] [bold cyan]{k}[/bold cyan] - [dim]{PRESETS[k][desc_key]} ({pats}...)[/dim]")
        lines.append(f"  [bold yellow]\\[0][/bold yellow] [dim]{'Cancelar' if lang == 'pt' else 'Cancel'}[/dim]")
        console.print(Panel("\n".join(lines), title=f"[bold cyan]{get_text('ranker', 'preset_menu_title', lang)}[/bold cyan]", border_style="cyan", expand=False))

        choice = Prompt.ask(get_text("ranker", "preset_menu_prompt", lang), default="0").strip()
        if choice.lower() in ("0", "", "q", "cancel", "cancelar", "sair", "exit", "quit"):
            return
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(keys):
                preset_val = keys[idx]
            else:
                console.print(get_text("ranker", "preset_error", lang, preset=choice))
                return
        else:
            preset_val = choice

    target = preset_val.strip().lower()
    if target not in PRESETS:
        console.print(get_text("ranker", "preset_error", lang, preset=preset_val))
        return

    patterns = list(PRESETS[target]["patterns"])
    _save_active_rankings(patterns)
    console.print(f"\n{get_text('ranker', 'preset_applied', lang, preset=target)}")
    _render_pattern_table(patterns, get_text("ranker", "strategy_label", lang), lang, numbered=True)
    console.print()


def _handle_import(import_val, lang):
    """Carrega e ativa uma estratégia .dna salva (ou redireciona caso seja nome de preset)."""
    if import_val != "__MENU__" and import_val.strip().lower() in PRESETS:
        _handle_preset(import_val, lang)
        return

    if import_val == "__MENU__":
        dna_files = _list_dna_files()
        if not dna_files:
            console.print(get_text("ranker", "err_no_strategies", lang))
            return

        lines = []
        for idx, fname in enumerate(dna_files, 1):
            pats = _read_dna_file(os.path.join(STRATEGIES_DIR, fname)) or []
            lines.append(f"  [bold yellow]\\[{idx}][/bold yellow] [bold cyan]{fname}[/bold cyan] [dim]({len(pats)} {_rules_word(len(pats), lang)})[/dim]")
        lines.append(f"  [bold yellow]\\[0][/bold yellow] [dim]{'Cancelar' if lang == 'pt' else 'Cancel'}[/dim]")
        console.print(Panel("\n".join(lines), title=f"[bold cyan]{get_text('ranker', 'import_menu_title', lang)}[/bold cyan]", border_style="cyan", expand=False))

        choice = Prompt.ask(get_text("ranker", "import_menu_prompt", lang), default="0").strip()
        if choice.lower() in ("0", "", "q", "cancel", "cancelar", "sair", "exit", "quit"):
            return
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(dna_files):
                import_val = dna_files[idx]
            else:
                console.print(get_text("ranker", "err_strategy_not_found", lang, name=choice))
                return
        else:
            import_val = choice

    clean_arg = import_val.strip().strip('"').strip("'")
    if os.path.dirname(clean_arg).strip():
        candidate_path = os.path.abspath(os.path.expanduser(clean_arg))
        if not candidate_path.lower().endswith(".dna") and not os.path.exists(candidate_path):
            candidate_path += ".dna"
    else:
        candidate_path, status = _resolve_strategy_in_dir(clean_arg)
        if status != "ok":
            console.print(get_text("ranker", "err_strategy_not_found", lang, name=clean_arg))
            return

    if not candidate_path or not os.path.isfile(candidate_path):
        console.print(get_text("ranker", "err_strategy_not_found", lang, name=clean_arg))
        return

    patterns = _read_dna_file(candidate_path)
    if not patterns:
        console.print(get_text("ranker", "err_invalid_dna_file", lang, path=os.path.basename(candidate_path)))
        return

    _save_active_rankings(patterns)
    console.print(f"\n{get_text('ranker', 'import_success', lang, path=os.path.basename(candidate_path))}")
    _render_pattern_table(patterns, get_text("ranker", "strategy_label", lang), lang, numbered=True)
    console.print()


def _handle_export(export_val, rankings, lang):
    """Exporta o ranking ativo atual para um arquivo .dna."""
    if not rankings:
        console.print(f"\n{get_text('ranker', 'err_empty_export', lang)}\n")
        return

    clean_arg = export_val.strip().strip('"').strip("'")
    if os.path.dirname(clean_arg).strip():
        dest_path = os.path.abspath(os.path.expanduser(clean_arg))
        if not dest_path.lower().endswith(".dna"):
            dest_path += ".dna"
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(rankings, f, indent=4)
        console.print(f"\n{get_text('ranker', 'export_success', lang, path=dest_path)}\n")
    else:
        try:
            dest_path = _write_strategy_in_dir(clean_arg, rankings)
            console.print(f"\n{get_text('ranker', 'export_success', lang, path=os.path.basename(dest_path))}\n")
        except Exception as e:
            err_lbl = "Erro" if lang == "pt" else "Error"
            console.print(f"[red][!] {err_lbl}: {e}[/red]")


def _delete_single_strategy(fpath, rankings, lang):
    """Apaga um arquivo .dna e limpa RANKER_FILE se o ranking ativo coincidir com ele."""
    fname = os.path.basename(fpath)
    deleted_patterns = _read_dna_file(fpath)
    os.remove(fpath)

    if rankings and deleted_patterns and rankings == deleted_patterns:
        _save_active_rankings([])
        console.print(get_text("ranker", "deleted_file_and_active", lang, name=fname))
    else:
        console.print(get_text("ranker", "deleted_file", lang, name=fname))


def _handle_delete(delete_val, rankings, lang):
    """Apaga estratégias .dna customizadas, ranking ativo, ou ambos."""
    dna_files = _list_dna_files()

    if delete_val == "__MENU__":
        if not rankings and not dna_files:
            console.print(f"\n{get_text('ranker', 'err_nothing_to_delete', lang)}\n")
            return

        lines = []
        for idx, fname in enumerate(dna_files, 1):
            pats = _read_dna_file(os.path.join(STRATEGIES_DIR, fname)) or []
            lines.append(f"  [bold yellow]\\[{idx}][/bold yellow] [bold cyan]{fname}[/bold cyan] [dim]({len(pats)} {_rules_word(len(pats), lang)})[/dim]")
        if rankings:
            lines.append(f"  [bold yellow]\\[A][/bold yellow] [white]{'Limpar apenas ranking ativo (manter arquivos .dna)' if lang == 'pt' else 'Clear active ranking only (keep .dna files)'}[/white]")
        if dna_files or rankings:
            lines.append(f"  [bold red]\\[ALL][/bold red] [white]{'Apagar TODAS estratégias .dna e limpar ranking ativo' if lang == 'pt' else 'Delete ALL custom .dna strategies & clear active ranking'}[/white]")
        lines.append(f"  [bold yellow]\\[0][/bold yellow] [dim]{'Cancelar' if lang == 'pt' else 'Cancel'}[/dim]")

        console.print(Panel("\n".join(lines), title=f"[bold red]{get_text('ranker', 'delete_menu_title', lang)}[/bold red]", border_style="red", expand=False))
        choice = Prompt.ask(get_text("ranker", "delete_menu_prompt", lang), default="0").strip()
        u_choice = choice.upper()

        if u_choice in ("0", "", "CANCEL", "CANCELAR"):
            console.print(get_text("ranker", "delete_cancelled", lang))
            return
        if u_choice in ("A", "ACTIVE", "ATIVO"):
            delete_val = "active"
        elif u_choice in ("ALL", "T", "TUDO"):
            delete_val = "all"
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(dna_files):
                delete_val = dna_files[idx]
            else:
                console.print(get_text("ranker", "err_strategy_not_found", lang, name=choice))
                return
        else:
            delete_val = choice

    u_val = delete_val.strip().upper()
    if u_val in ("ACTIVE", "ATIVO"):
        if not rankings:
            console.print(f"\n{get_text('ranker', 'err_nothing_to_delete', lang)}\n")
            return
        if _confirm_action(get_text('ranker', 'confirm_clear_active', lang), lang, default=False, danger=False):
            _save_active_rankings([])
            console.print(f"\n{get_text('ranker', 'cleared_active', lang)}\n")
        else:
            console.print(get_text("ranker", "delete_cancelled", lang))
        return

    if u_val in ("ALL", "TUDO"):
        if not rankings and not dna_files:
            console.print(f"\n{get_text('ranker', 'err_nothing_to_delete', lang)}\n")
            return
        if _confirm_action(get_text('ranker', 'confirm_delete_all', lang, count=len(dna_files)), lang, default=False, danger=True):
            deleted_count = 0
            for fname in dna_files:
                try:
                    os.remove(os.path.join(STRATEGIES_DIR, fname))
                    deleted_count += 1
                except Exception as e:
                    err_lbl = "Erro ao apagar" if lang == "pt" else "Error deleting"
                    console.print(f"[red][!] {err_lbl} {fname}: {e}[/red]")
            _save_active_rankings([])
            console.print(f"\n{get_text('ranker', 'deleted_all', lang, count=deleted_count)}\n")
        else:
            console.print(get_text("ranker", "delete_cancelled", lang))
        return

    target_path, status = _resolve_strategy_in_dir(delete_val)
    if status == "traversal":
        console.print(get_text("ranker", "err_path_traversal", lang, target=delete_val))
        return
    if status == "not_found" or not target_path or not os.path.isfile(target_path):
        console.print(get_text("ranker", "err_strategy_not_found", lang, name=delete_val))
        return

    fname = os.path.basename(target_path)
    if _confirm_action(get_text('ranker', 'confirm_delete_file', lang, name=fname), lang, default=False, danger=True):
        console.print()
        _delete_single_strategy(target_path, rankings, lang)
        console.print()
    else:
        console.print(get_text("ranker", "delete_cancelled", lang))


def _save_and_activate_builder_strategy(patterns, saved_filename, lang, suggested_name=None):
    """Persiste a estratégia criada como arquivo .dna em STRATEGIES_DIR e ativa em RANKER_FILE."""
    filename = saved_filename
    if not filename:
        default_name = suggested_name or _next_default_strategy_name()
        while True:
            raw_name = Prompt.ask(get_text("ranker", "prompt_save_name", lang), default=default_name).strip()
            safe = _sanitize_strategy_filename(raw_name)
            if safe:
                filename = safe
                break
            console.print(get_text("ranker", "err_path_traversal", lang, target=raw_name))

    dest_path = _write_strategy_in_dir(filename, patterns)
    _save_active_rankings(patterns)
    rel_display = os.path.join("strategies", os.path.basename(dest_path))
    console.print(f"\n{get_text('ranker', 'custom_finish', lang, path=rel_display)}\n")


def _handle_create(rankings, lang):
    """Construtor interativo passo a passo: salva arquivo .dna e ativa no Ranker ao finalizar com DONE."""
    if rankings:
        mode = Prompt.ask(get_text("ranker", "custom_mode_prompt", lang, count=len(rankings)), default="1").strip()
        if mode.lower() in ("0", "q", "cancel", "cancelar", "sair", "exit", "quit"):
            console.print(f"\n{get_text('ranker', 'custom_cancelled', lang)}\n")
            return
        new_rankings = rankings.copy() if mode == "2" else []
    else:
        new_rankings = []

    valid_tokens = list(STANDARD_TOKENS)
    custom_tokens_list = []
    if os.path.exists(CUSTOM_TOKENS_DIR):
        custom_tokens_list = sorted(
            d.upper() for d in os.listdir(CUSTOM_TOKENS_DIR)
            if os.path.isdir(os.path.join(CUSTOM_TOKENS_DIR, d))
        )
        valid_tokens.extend(custom_tokens_list)

    done_signals = {"DONE", "PRONTO", "FINISH"}
    cancel_signals = {"CANCEL", "CANCELAR", "EXIT", "QUIT", "SAIR", "ABORT"}
    undo_signals = {"UNDO", "DESFAZER", "BACK"}
    reset_signals = {"RESET", "REINICIAR", "CLEAR"}
    save_signals = ("SAVE", "SALVAR", "EXPORT")

    saved_dna_filename = None
    dirty_since_save = False

    while True:
        console.print("\n" + "-" * 64)
        console.print(f"[bold white on red] {get_text('ranker', 'title', lang)} [/bold white on red]\n")
        console.print(get_text("ranker", "custom_prompt", lang))
        if custom_tokens_list:
            console.print(get_text("ranker", "custom_custom_tokens", lang, tokens=", ".join(custom_tokens_list)))

        tips = get_text("ranker", "custom_tips", lang)
        if isinstance(tips, list):
            console.print(Panel("\n".join(tips), title="[yellow]DNA Guide[/yellow]", border_style="dim yellow"))

        if new_rankings:
            _render_pattern_table(
                new_rankings,
                "Estratégia em Construção:" if lang == "pt" else "Draft Strategy Stack:",
                lang,
                numbered=True
            )
        else:
            empty_txt = "(Nenhuma regra adicionada ainda)" if lang == "pt" else "(No rules added yet)"
            console.print(f"\n [dim]{empty_txt}[/dim]")

        entry = console.input(f"\n [bold cyan]{get_text('ranker', 'custom_step', lang, step=len(new_rankings) + 1)}[/bold cyan]").strip()
        if not entry:
            continue

        u_entry = entry.upper()

        if u_entry in done_signals:
            if not new_rankings:
                console.print(f"\n{get_text('ranker', 'custom_empty_abort', lang)}\n")
                return
            name_to_use = saved_dna_filename if (saved_dna_filename and not dirty_since_save) else None
            suggested = saved_dna_filename.rsplit(".", 1)[0] if saved_dna_filename else None
            _save_and_activate_builder_strategy(new_rankings, name_to_use, lang, suggested_name=suggested)
            return

        if u_entry in cancel_signals:
            if new_rankings and dirty_since_save:
                if _confirm_action(get_text('ranker', 'custom_confirm_save', lang), lang, default=True, danger=False):
                    suggested = saved_dna_filename.rsplit(".", 1)[0] if saved_dna_filename else None
                    _save_and_activate_builder_strategy(new_rankings, None, lang, suggested_name=suggested)
                    return
            console.print(f"\n{get_text('ranker', 'custom_cancelled', lang)}\n")
            return

        if u_entry in undo_signals:
            if new_rankings:
                new_rankings.pop()
                dirty_since_save = True
            continue

        if u_entry in reset_signals:
            new_rankings = []
            dirty_since_save = False
            saved_dna_filename = None
            continue

        if u_entry.startswith("DEL ") or u_entry.startswith("REMOVE "):
            idx_str = entry.split(None, 1)[1].strip().lstrip("#")
            if idx_str.isdigit():
                idx_rem = int(idx_str) - 1
                if 0 <= idx_rem < len(new_rankings):
                    new_rankings.pop(idx_rem)
                    dirty_since_save = True
                    continue
            console.print("[red][!][/red] Índice inválido." if lang == "pt" else "[red][!][/red] Invalid index.")
            continue

        cmd_head = u_entry.split(None, 1)[0]
        if cmd_head in save_signals:
            if not new_rankings:
                console.print(get_text("ranker", "err_empty_export", lang))
                continue
            parts_cmd = entry.split(None, 1)
            raw_name = parts_cmd[1].strip() if len(parts_cmd) > 1 else Prompt.ask(
                get_text("ranker", "prompt_save_name", lang),
                default=_next_default_strategy_name()
            ).strip()
            safe = _sanitize_strategy_filename(raw_name)
            if not safe:
                console.print(get_text("ranker", "err_path_traversal", lang, target=raw_name))
                continue
            try:
                _write_strategy_in_dir(safe, new_rankings)
                saved_dna_filename = safe
                dirty_since_save = False
                console.print(get_text("ranker", "export_success", lang, path=safe))
            except Exception as e:
                err_lbl = "Erro" if lang == "pt" else "Error"
                console.print(f"[red][!] {err_lbl}: {e}[/red]")
            continue

        parts = [p.strip() for p in entry.split("+")]
        if not parts or any(not p for p in parts):
            console.print(get_text("ranker", "err_invalid", lang))
            continue

        is_valid = all(p.upper().replace("@", "A").replace("0", "O") in valid_tokens for p in parts)
        if is_valid:
            normalized_entry = "+".join(parts)
            preview = get_preview_example(normalized_entry)
            console.print(f" [green][+][/green] {get_text('ranker', 'preview_label', lang)}: [bold white]{preview}[/bold white]")
            new_rankings.append(normalized_entry)
            dirty_since_save = True
        else:
            console.print(get_text("ranker", "err_invalid", lang))


@click.command(name="ranker", add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.option("-L", "--list", "--listing", "listing", is_flag=True, help="List active ranking, presets, and saved .dna strategies")
@click.option("-C", "--create", "--custom", "--customization", "customization", is_flag=True, help="Build a custom DNA strategy (.dna) interactively")
@click.option("-P", "--preset", is_flag=False, flag_value="__MENU__", default=None, type=str, help="Apply a built-in preset: corporate | minimalist | hardcore")
@click.option("-I", "--use", "--import", "import_target", is_flag=False, flag_value="__MENU__", default=None, type=str, help="Load and activate a saved .dna strategy")
@click.option("-E", "--export", type=str, default=None, help="Export active ranking to a .dna file")
@click.option("-D", "--delete", "--clear", "delete_target", is_flag=False, flag_value="__MENU__", default=None, type=str, help="Delete custom .dna strategy, 'active', or 'all'")
@click.pass_context
def ranker(ctx, listing, customization, preset, import_target, export, delete_target):
    """Manage custom strategic ranking for the generator."""
    is_pt = ctx.obj.get('LANG_PT', False) if ctx.obj else False
    lang = "pt" if is_pt else "en"

    # Valida se flags opcionais acabaram consumindo outra flag por erro de sintaxe (ex: ranker -D -L)
    for val in (preset, import_target, export, delete_target):
        if isinstance(val, str) and val != "__MENU__" and val.startswith("-"):
            console.print(f"\n{get_text('ranker', 'err_invalid_target', lang, target=val)}\n")
            return

    action_count = sum([
        bool(listing),
        bool(customization),
        preset is not None,
        import_target is not None,
        export is not None,
        delete_target is not None
    ])
    if action_count > 1:
        console.print(f"\n{get_text('ranker', 'err_conflict', lang)}\n")
        return

    rankings = _load_active_rankings()

    if listing:
        _handle_list(rankings, lang)
        return
    if preset is not None:
        _handle_preset(preset, lang)
        return
    if import_target is not None:
        _handle_import(import_target, lang)
        return
    if export is not None:
        _handle_export(export, rankings, lang)
        return
    if delete_target is not None:
        _handle_delete(delete_target, rankings, lang)
        return
    if customization:
        _handle_create(rankings, lang)
        return

    # Modo Interativo (executado quando nenhuma flag foi informada)
    console.print(f"\n[bold white on red] {get_text('ranker', 'title', lang)} [/bold white on red]\n")
    if rankings:
        _render_pattern_table(rankings, get_text("ranker", "list_title", lang), lang, numbered=True)
        console.print()
    else:
        console.print(f" [dim]{get_text('ranker', 'empty', lang)}[/dim]\n")

    menu_panel = Panel(
        get_text("ranker", "menu_items", lang),
        title=f"[bold cyan]{get_text('ranker', 'menu_title', lang)}[/bold cyan]",
        border_style="cyan",
        expand=False
    )
    console.print(menu_panel)
    opt = Prompt.ask(get_text("ranker", "menu_prompt", lang), default="0").strip()

    if opt == "1":
        _handle_list(rankings, lang)
    elif opt == "2":
        _handle_create(rankings, lang)
    elif opt == "3":
        _handle_preset("__MENU__", lang)
    elif opt == "4":
        _handle_import("__MENU__", lang)
    elif opt == "5":
        if not rankings:
            console.print(f"\n{get_text('ranker', 'err_empty_export', lang)}\n")
            return
        exp_name = Prompt.ask(get_text("ranker", "prompt_save_name", lang), default=_next_default_strategy_name())
        _handle_export(exp_name, rankings, lang)
    elif opt == "6":
        _handle_delete("__MENU__", rankings, lang)
