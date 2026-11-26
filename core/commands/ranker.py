"""
CypherDNA Ranker Command
- ranker: Manage custom strategic ranking for the generator
"""

import os
import json
import time
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


@click.command(name="ranker", add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.option("-L", "--listing", is_flag=True, help="List active strategic rankings")
@click.option("-C", "--customization", is_flag=True, help="Build your own strategic order interactively")
@click.option("-D", "--clear", is_flag=True, help="Delete all rankings")
@click.option("-P", "--preset", is_flag=False, flag_value="SELECT_MENU", type=str, help="Apply a template: corporate | minimalist | hardcore")
@click.option("-E", "--export", type=click.Path(), help="Export strategy to a .dna file")
@click.option("-I", "--import", "import_path", type=str, help="Import strategy (Preset name or .dna file)")
@click.pass_context
def ranker(ctx, listing, customization, clear, preset, export, import_path):
    """Manage custom strategic ranking for the generator."""
    is_pt = ctx.obj.get('LANG_PT', False) if ctx.obj else False
    lang = "pt" if is_pt else "en"

    # Load current rank
    rankings = []
    if os.path.exists(RANKER_FILE):
        try:
            with open(RANKER_FILE, "r", encoding="utf-8") as f:
                rankings = json.load(f)
        except Exception:
            rankings = []

    modified = False

    # --- HANDLE PRESET FLAG (-P) ---
    if preset:
        presets_dict = {
            "corporate": (["NaME+YEAR", "NaME+SYMBOL+YEAR", "NaME+NUMBER", "NaME+YEAR+SYMBOL"], "Ideal para senhas corporativas e infraestrutura (Active Directory)"),
            "minimalist": (["NAME+YEAR", "YEAR+NAME", "NAME+NUMBER"], "Estratégia minimalista com combinações essenciais"),
            "hardcore": (["N@ME+SYMBOL+YEAR", "W0RD+NUMBER+SYMBOL", "NaME+SEPARATOR+YEAR", "KEY_WALK+SYMBOL"], "Mutações profundas com leet speak e símbolos")
        }

        if str(preset).upper() in ["SELECT_MENU", "MENU", "?", "TRUE", "NONE"] or preset.lower() not in presets_dict:
            console.print(Panel("[bold cyan]Selecione um Preset Estratégico Pronto[/bold cyan]", expand=False))
            p_keys = list(presets_dict.keys())
            for idx, k in enumerate(p_keys, 1):
                desc = presets_dict[k][1]
                console.print(f"  [bold yellow][{idx}][/bold yellow] [bold white]{k}[/bold white] [dim]({desc})[/dim]")

            choice = Prompt.ask("\n[bold green]Digite o número do preset desejado[/bold green]", default="1")
            try:
                c_idx = int(choice) - 1
                if 0 <= c_idx < len(p_keys):
                    preset = p_keys[c_idx]
                else:
                    preset = p_keys[0]
            except Exception:
                preset = p_keys[0]

        import_path = preset

    # --- HANDLE IMPORT & PRESET (Unified) ---
    if import_path:
        presets = {
            "corporate": ["NaME+YEAR", "NaME+SYMBOL+YEAR", "NaME+NUMBER", "NaME+YEAR+SYMBOL"],
            "minimalist": ["NAME+YEAR", "YEAR+NAME", "NAME+NUMBER"],
            "hardcore": ["N@ME+SYMBOL+YEAR", "W0RD+NUMBER+SYMBOL", "NaME+SEPARATOR+YEAR", "KEY_WALK+SYMBOL"]
        }

        target_rankings = None
        display_name = import_path

        # 1. É um Preset?
        if import_path.lower() in presets:
            target_rankings = presets[import_path.lower()]
            display_name = f"{import_path} {get_text('ranker', 'preset_label', lang)}"
        else:
            # 2. É um arquivo? Procura na pasta strategies
            file_path = import_path
            if not os.path.isabs(file_path):
                file_path = os.path.join(STRATEGIES_DIR, file_path)
            if not file_path.lower().endswith(".dna"):
                file_path += ".dna"

            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        target_rankings = json.load(f)
                        display_name = os.path.basename(file_path)
                except Exception:
                    target_rankings = None
            else:
                console.print(get_text("ranker", "preset_error", lang))

        if target_rankings:
            console.print(f"\n{get_text('ranker', 'strategy_label', lang)} [bold cyan]{display_name}[/bold cyan]")
            preview_table = Table(box=rich.box.ROUNDED, border_style="cyan")
            preview_table.add_column("#", justify="center")
            preview_table.add_column(get_text("ranker", "col_pattern", lang))
            preview_table.add_column(get_text("ranker", "preview_label", lang))
            for idx, r in enumerate(target_rankings):
                preview_table.add_row(str(idx + 1), format_pattern(r), f"[dim]{get_preview_example(r)}[/dim]")
            console.print(preview_table)

            confirm = console.input(get_text("ranker", "import_confirm", lang)).strip().lower()
            if confirm in ["y", "s", "yes", "sim"]:
                rankings = target_rankings
                modified = True
                console.print(get_text("ranker", "import_success", lang, path=display_name))
            else:
                console.print(get_text("ranker", "import_aborted", lang))

    # --- HANDLE EXPORT ---
    if export:
        try:
            if not os.path.isabs(export):
                export = os.path.join(STRATEGIES_DIR, export)
            if not export.lower().endswith(".dna"):
                export += ".dna"

            with open(export, "w", encoding="utf-8") as f:
                json.dump(rankings, f, indent=4)
            console.print(get_text("ranker", "export_success", lang, path=os.path.basename(export)))
        except Exception as e:
            console.print(f"[red][!] Error: {e}[/red]")

    if clear:
        if rankings:
            rankings = []
            modified = True
            console.print(get_text("ranker", "cleared", lang))

    elif listing:
        title = get_text("ranker", "title", lang)
        console.print(f"\n[bold white on red] {title} [/bold white on red]\n")
        console.print(f"[bold white]{get_text('ranker', 'available_title', lang)}[/bold white]")

        list_table = Table(box=rich.box.ROUNDED, border_style="bright_blue")
        list_table.add_column("Type", justify="center", style="dim")
        list_table.add_column("Strategy Name", style="bold cyan")

        for p in ["corporate", "minimalist", "hardcore"]:
            list_table.add_row("PRESET", f"{p} {get_text('ranker', 'preset_label', lang)}")

        if os.path.exists(STRATEGIES_DIR):
            files = [f for f in os.listdir(STRATEGIES_DIR) if f.lower().endswith(".dna")]
            for f in sorted(files):
                list_table.add_row("FILE", f.replace(".dna", ""))

        console.print(list_table)
        console.print(f"\n[dim]Usage: ranker --import [name] | ranker --preset [name][/dim]\n")

    elif customization:
        new_rankings = rankings.copy()
        done_signals = ["DONE", "SAIR", "EXIT", "QUIT"]
        undo_signals = ["UNDO", "DESFAZER", "BACK"]
        reset_signals = ["RESET", "REINICIAR", "CLEAR"]
        save_signals = ["SAVE", "SALVAR", "EXPORT"]

        while True:
            console.print("\n" + "=" * 60)
            title = get_text("ranker", "title", lang)
            console.print(f"[bold white on red] {title} [/bold white on red]")
            console.print(get_text("ranker", "custom_prompt", lang))

            tips = get_text("ranker", "custom_tips", lang)
            if isinstance(tips, list):
                tips_text = "\n".join(tips)
                console.print(Panel(tips_text, title="[yellow]DNA Construction Guide[/yellow]", border_style="dim yellow"))

            if new_rankings:
                curr_table = Table(box=rich.box.SIMPLE, header_style="bold cyan")
                curr_table.add_column("#", justify="center")
                curr_table.add_column("Current Strategy Stack")
                curr_table.add_column(get_text("ranker", "preview_label", lang), justify="left")
                for i, r in enumerate(new_rankings):
                    curr_table.add_row(f"{i + 1}", format_pattern(r), f"[dim white]{get_preview_example(r)}[/dim white]")
                console.print(curr_table)
            else:
                console.print(f"\n [dim]({get_text('ranker', 'empty', lang)})[/dim]")

            entry = console.input(f"\n [bold cyan]{get_text('ranker', 'custom_step', lang, step=len(new_rankings) + 1)}[/bold cyan]").strip()
            u_entry = entry.upper()

            if u_entry in done_signals:
                break
            if u_entry in undo_signals:
                if new_rankings:
                    new_rankings.pop()
                continue
            if u_entry in reset_signals:
                new_rankings = []
                continue

            if any(u_entry.startswith(s) for s in save_signals):
                parts_cmd = entry.split(" ", 1)
                filename = ""
                if len(parts_cmd) > 1:
                    filename = parts_cmd[1].strip()
                else:
                    filename = console.input(get_text("ranker", "prompt_save_name", lang)).strip()

                if not filename:
                    continue

                if not filename.lower().endswith(".dna"):
                    filename += ".dna"
                path = os.path.join(STRATEGIES_DIR, filename)
                try:
                    with open(path, "w", encoding="utf-8") as sf:
                        json.dump(new_rankings, sf, indent=4)
                    console.print(get_text("ranker", "export_success", lang, path=filename))
                except Exception as e:
                    console.print(f"[red][!] Error: {e}[/red]")
                continue

            if not entry:
                continue

            valid_tokens = ["NAME", "WORD", "YEAR", "DATE", "MONTH", "NUMBER", "SYMBOL", "SEPARATOR", "REPEATED", "KEY_WALK"]

            if os.path.exists(CUSTOM_TOKENS_DIR):
                valid_tokens += [d.upper() for d in os.listdir(CUSTOM_TOKENS_DIR) if os.path.isdir(os.path.join(CUSTOM_TOKENS_DIR, d))]

            parts = entry.split("+")
            is_valid = True
            for p in parts:
                clean_p = p.upper().replace("@", "A").replace("0", "O").strip()
                if clean_p not in valid_tokens:
                    is_valid = False
                    break

            if is_valid:
                preview = get_preview_example(entry)
                console.print(f" [dim]↳ {get_text('ranker', 'preview_label', lang)} [bold white]{preview}[/bold white][/dim]")
                new_rankings.append(entry)
            else:
                console.print(get_text("ranker", "err_invalid", lang))
                time.sleep(2)

        if new_rankings != rankings:
            rankings = new_rankings
            modified = True
            console.print(f"\n{get_text('ranker', 'custom_finish', lang)}")

    if modified:
        with open(RANKER_FILE, "w", encoding="utf-8") as f:
            json.dump(rankings, f, indent=4)

    if (not any([listing, customization, clear, preset, export, import_path])) or modified:
        title = get_text("ranker", "title", lang)
        console.print(f"\n[bold white on red] {title} [/bold white on red]\n")

        if not rankings:
            console.print(f" [dim]{get_text('ranker', 'empty', lang)}[/dim]\n")
        else:
            console.print(f"[bold white]{get_text('ranker', 'list_title', lang)}[/bold white]")
            rank_table = Table(box=rich.box.DOUBLE_EDGE, header_style="bold magenta", border_style="red")
            rank_table.add_column(get_text("ranker", "col_rank", lang), justify="center", style="bold yellow")
            rank_table.add_column(get_text("ranker", "col_pattern", lang))
            rank_table.add_column(get_text("ranker", "preview_label", lang), justify="left")

            for i, r in enumerate(rankings):
                rank_table.add_row(f"#{i + 1}", format_pattern(r), f"[dim white]{get_preview_example(r)}[/dim white]")

            console.print(rank_table)
            console.print("")

        if not any([listing, customization, clear, preset, export, import_path]):
            menu_panel = Panel(
                "  [bold yellow][1][/bold yellow] 📋 Listar Presets & Estratégias (-L)\n"
                "  [bold yellow][2][/bold yellow] 🛠️ Criar Estratégia Customizada (-C)\n"
                "  [bold yellow][3][/bold yellow] 📦 Carregar Preset Pronto (-P)\n"
                "  [bold yellow][4][/bold yellow] 💾 Exportar Estratégia Atual (-E)\n"
                "  [bold yellow][5][/bold yellow] 🧹 Limpar / Resetar Ranking (-D)\n"
                "  [bold yellow][0][/bold yellow] 🚪 Sair",
                title="[bold cyan]Menu Interativo do Ranker[/bold cyan]",
                border_style="cyan"
            )
            console.print(menu_panel)
            opt = Prompt.ask("[bold green]Selecione uma opção[/bold green]", default="0")
            if opt == "1":
                ctx.invoke(ranker, listing=True)
            elif opt == "2":
                ctx.invoke(ranker, customization=True)
            elif opt == "3":
                ctx.invoke(ranker, preset="SELECT_MENU")
            elif opt == "4":
                exp_name = Prompt.ask("Nome do arquivo para exportar", default="minha_estrategia.dna")
                ctx.invoke(ranker, export=exp_name)
            elif opt == "5":
                ctx.invoke(ranker, clear=True)
