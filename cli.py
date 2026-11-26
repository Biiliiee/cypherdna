#!/usr/bin/env python3
"""
CypherDNA - Main CLI Entrypoint
Advanced Password DNA Sequencing & Intelligence Core
"""

import sys
import os

# Garante acesso imediato aos módulos internos do core e subcomandos
CORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core")
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

import difflib
import click
from rich.console import Console
from rich.panel import Panel

from config import setup_environment, get_saved_lang, load_version_data, BASE_DIR, DATA_DIR
from ui_utils import display_custom_help, show_help_and_exit
from i18n import get_text

# Import modular commands
from commands.analyze import analyze
from commands.generator import generator
from commands.ranker import ranker
from commands.tokens import token_cmd, tokens_all
from commands.clear import clear_cmd
from commands.system import lang_cmd, status_cmd, doctor, dashboard, api_cmd, set_cmd
from trainer import collect as trainer_cmd
from benchmark import benchmark_cmd

console = Console()
setup_environment()


def check_whats_new(current_version, lang):
    """Detecta se é o primeiro boot de uma versão nova e exibe novidades."""
    v_track_path = os.path.join(DATA_DIR, ".cph_last_v")
    legacy_track_path = os.path.join(BASE_DIR, ".cph_last_v")

    last_v = "0.0.0"
    for p in [v_track_path, legacy_track_path]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    last_v = f.read().strip()
                break
            except Exception:
                pass

    if current_version != last_v:
        data = load_version_data()
        try:
            cl_key = "changelog_pt" if lang == "pt" else "changelog_en"
            changes = data.get(cl_key, [])
            if changes:
                title = get_text("whats_new", "title", lang, version=current_version)
                header = get_text("whats_new", "header", lang)
                msg = f"[bold white]{header}[/bold white]\n\n"
                for c in changes:
                    msg += f" • [green]{c}[/green]\n"

                console.print()
                console.print(Panel(msg, title=title, border_style="cyan", padding=(1, 2)))
                console.print(f" [dim]{get_text('whats_new', 'footer', lang)}[/dim] ")
                try:
                    input()
                except (EOFError, KeyboardInterrupt):
                    pass
        except Exception:
            pass

        with open(v_track_path, "w", encoding="utf-8") as f:
            f.write(current_version)


class CypherdnaCLIGroup(click.Group):
    """Custom Click Group with Rich error formatting and fuzzy command suggestions."""

    def resolve_command(self, ctx, args):
        cmd_name = args[0]
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            is_pt = (get_saved_lang() == 'pt')
            all_cmds = self.list_commands(ctx)
            matches = difflib.get_close_matches(cmd_name, all_cmds, n=3, cutoff=0.4)

            if is_pt:
                err_title = "Comando Não Encontrado"
                msg = f"O comando '[bold yellow]{cmd_name}[/bold yellow]' não foi reconhecido."
                if matches:
                    suggestion = f"\n\n [bold white]Você quis dizer:[/bold white] [bold cyan]cypherdna {matches[0]}[/bold cyan]?"
                    if len(matches) > 1:
                        other_matches = ", ".join(f"[cyan]cypherdna {m}[/cyan]" for m in matches[1:])
                        suggestion += f"\n[dim]Outras opções semelhantes: {other_matches}[/dim]"
                else:
                    suggestion = "\n\n[dim]Use [bold white]cypherdna --help[/bold white] para ver a lista de comandos.[/dim]"
            else:
                err_title = "Command Not Found"
                msg = f"The command '[bold yellow]{cmd_name}[/bold yellow]' was not recognized."
                if matches:
                    suggestion = f"\n\n [bold white]Did you mean:[/bold white] [bold cyan]cypherdna {matches[0]}[/bold cyan]?"
                    if len(matches) > 1:
                        other_matches = ", ".join(f"[cyan]cypherdna {m}[/cyan]" for m in matches[1:])
                        suggestion += f"\n[dim]Other close matches: {other_matches}[/dim]"
                else:
                    suggestion = "\n\n[dim]Use [bold white]cypherdna --help[/bold white] to view available commands.[/dim]"

            console.print("\n", Panel(
                f"{msg}{suggestion}",
                title=f"[bold red] ❌ {err_title} [/bold red]",
                border_style="red",
                width=62
            ), "\n")
            sys.exit(1)

    def main(self, *args, **kwargs):
        try:
            return super().main(*args, **kwargs)
        except click.ClickException as e:
            is_pt = (get_saved_lang() == 'pt')
            title = "Erro de Sintaxe" if is_pt else "Syntax Error"
            console.print("\n", Panel(
                f"[white]{e.format_message()}[/white]",
                title=f"[bold red] ❌ {title} [/bold red]",
                border_style="red",
                width=62
            ), "\n")
            sys.exit(e.exit_code)


@click.group(cls=CypherdnaCLIGroup, invoke_without_command=True, add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.option('-v', '--verbose', is_flag=True, help="Enable verbose logging / debug mode.")
@click.pass_context
def cli(ctx, verbose):
    """CypherDNA - Intelligent Wordlist Generator"""
    ctx.ensure_object(dict)
    saved_lang = get_saved_lang()
    is_pt = (saved_lang == 'pt')
    ctx.obj['LANG_PT'] = is_pt
    lang = "pt" if is_pt else "en"

    is_completion = any(k.endswith('_COMPLETE') for k in os.environ)

    if ctx.invoked_subcommand is None and not is_completion:
        v_data = load_version_data()
        curr_v = v_data.get("version", "0.0.0")
        check_whats_new(curr_v, lang)

    ctx.obj['VERBOSE'] = verbose

    if ctx.invoked_subcommand is None:
        display_custom_help(is_pt=is_pt)


# Command Registrations
cli.add_command(analyze, name="analyze")
cli.add_command(generator, name="generator")
cli.add_command(ranker, name="ranker")
cli.add_command(token_cmd, name="token")
cli.add_command(tokens_all, name="tokens")
cli.add_command(clear_cmd, name="clear")
cli.add_command(status_cmd, name="status")
cli.add_command(doctor, name="doctor")
cli.add_command(dashboard, name="dashboard")
cli.add_command(lang_cmd, name="lang")
cli.add_command(lang_cmd, name="idioma")
cli.add_command(api_cmd, name="api")
cli.add_command(api_cmd, name="set-api")
cli.add_command(set_cmd, name="set")
cli.add_command(trainer_cmd, name="collect")
cli.add_command(benchmark_cmd, name="comparator")


if __name__ == "__main__":
    is_pt = '-Pt' in sys.argv or '--portuguese' in sys.argv
    lang = "pt" if is_pt else "en"

    try:
        cli(prog_name="cypherdna")
    except KeyboardInterrupt:
        console.print(get_text("system", "cancelled", lang))
        sys.exit(0)
    except Exception as e:
        if "--verbose" in sys.argv or "-v" in sys.argv:
            console.print_exception()
        else:
            console.print(f"{get_text('system', 'fatal_error', lang)} {e}")
            console.print(get_text("system", "verbose_hint", lang))
        sys.exit(1)
