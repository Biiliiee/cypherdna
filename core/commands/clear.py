"""
CypherDNA Clear Command
- clear: Clean wordlists, reports, custom tokens, ranker cache, or all
"""

import os
import shutil
import json
import click
from rich.console import Console

from config import (
    YOU_WORDLIST_DIR,
    REPORTS_DIR,
    CUSTOM_TOKENS_DIR,
    RANKER_FILE,
    TRAINER_DIR
)
from ui_utils import show_help_and_exit
from i18n import get_text

console = Console()


@click.command(name="clear", add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.argument(
    "target",
    type=click.Choice(["wordlists", "reports", "ranker", "tokens", "all"], case_sensitive=False)
)
@click.pass_context
def clear_cmd(ctx, target):
    """Clear wordlists, reports, custom tokens, ranker cache, or all"""
    is_pt = ctx.obj.get('LANG_PT', False) if ctx.obj else False
    lang = "pt" if is_pt else "en"
    target = target.lower()

    title = get_text("clear", "title", lang)
    console.print(f"\n[bold white on red] {title} [/bold white on red]\n")

    deleted_total = 0
    total_files_found = 0
    targets_to_clear = []

    if target == "wordlists":
        targets_to_clear.append(("wordlists", YOU_WORDLIST_DIR))
    elif target == "reports":
        targets_to_clear.append(("reports", REPORTS_DIR))
    elif target == "tokens":
        targets_to_clear.append(("tokens", CUSTOM_TOKENS_DIR))
    elif target == "ranker":
        targets_to_clear.append(("ranker", RANKER_FILE))
    elif target == "all":
        targets_to_clear.append(("wordlists", YOU_WORDLIST_DIR))
        targets_to_clear.append(("reports", REPORTS_DIR))
        targets_to_clear.append(("tokens", CUSTOM_TOKENS_DIR))
        targets_to_clear.append(("ranker", RANKER_FILE))

    # Verificar existência
    for name, path in targets_to_clear:
        if not os.path.exists(path):
            continue

        if name == "wordlists":
            files = [f for f in os.listdir(path) if f.lower().endswith(".txt")]
            total_files_found += len(files)
        elif name == "reports":
            files = os.listdir(path)
            total_files_found += len(files)
        elif name == "tokens":
            folders = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
            total_files_found += len(folders)
        elif name == "ranker":
            try:
                with open(path, "r", encoding="utf-8") as rf:
                    r_data = json.load(rf)
                    if len(r_data) > 0:
                        total_files_found += 1
            except Exception:
                pass

    if total_files_found == 0:
        msg_empty = get_text("clear", "msg_empty", lang)
        console.print(f" [bold red]>[/] [yellow]{msg_empty}[/yellow]\n")
        return

    # Confirmação
    if target in ("tokens", "all"):
        prompt = get_text("clear", "prompt_confirm_tokens", lang)
    else:
        prompt = get_text("clear", "prompt_confirm", lang)

    choice = console.input(prompt).strip().lower()

    if choice not in ("", "y", "yes", "s", "sim"):
        cancel_msg = get_text("clear", "msg_cancelled", lang)
        console.print(f"\n[yellow]{cancel_msg}[/yellow]\n")
        return

    # Executar limpeza
    for name, path in targets_to_clear:
        if not os.path.exists(path):
            continue

        if name == "wordlists":
            files = [f for f in os.listdir(path) if f.lower().endswith(".txt")]
            for file in files:
                try:
                    os.remove(os.path.join(path, file))
                    deleted_total += 1
                except Exception as e:
                    console.print(get_text("clear", "err_deleting", lang, file=file, error=e))

        elif name == "reports":
            files = os.listdir(path)
            for file in files:
                try:
                    os.remove(os.path.join(path, file))
                    deleted_total += 1
                except Exception as e:
                    console.print(get_text("clear", "err_deleting", lang, file=file, error=e))

        elif name == "tokens":
            folders = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
            for folder in folders:
                try:
                    shutil.rmtree(os.path.join(path, folder), ignore_errors=True)
                    deleted_total += 1
                except Exception as e:
                    console.print(get_text("clear", "err_deleting", lang, file=folder, error=e))

            if os.path.exists(TRAINER_DIR):
                tr_files = [f for f in os.listdir(TRAINER_DIR) if f.lower().endswith(".json")]
                for tr_file in tr_files:
                    try:
                        os.remove(os.path.join(TRAINER_DIR, tr_file))
                        deleted_total += 1
                    except Exception:
                        pass

            if os.path.exists(RANKER_FILE):
                try:
                    os.remove(RANKER_FILE)
                except Exception:
                    pass

        elif name == "ranker":
            try:
                os.remove(path)
                deleted_total += 1
            except Exception as e:
                console.print(get_text("clear", "err_deleting", lang, file="ranker.json", error=e))

    success_msg = get_text("clear", "success_msg", lang, count=deleted_total)
    console.print(f"\n [bold red]>[/] [bold green]{success_msg}[/bold green]\n")
