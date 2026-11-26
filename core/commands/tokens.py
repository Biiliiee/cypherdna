"""
CypherDNA Token Management Commands
- token: Manage custom tokens and wordlists
- tokens: List all custom tokens
"""

import os
import shutil
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm
import rich.box

from config import CUSTOM_TOKENS_DIR
from ui_utils import show_help_and_exit
from i18n import get_text

console = Console()


@click.command(name="token", add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.argument("name", required=False)
@click.option("-n", "--new", is_flag=True, help="Create a new custom token folder")
@click.option("-a", "--add", type=click.Path(exists=True), help="Add a wordlist (.txt) to the token")
@click.option("-r", "--remove", type=str, help="Remove a wordlist file or the entire token folder")
@click.pass_context
def token_cmd(ctx, name, new, add, remove):
    """Manual Tokenization: Manage custom tokens and wordlists."""
    lang = "pt" if (ctx.obj and ctx.obj.get('LANG_PT')) else "en"
    title = get_text("token", "title", lang)

    os.makedirs(CUSTOM_TOKENS_DIR, exist_ok=True)

    # 1. CREATE NEW TOKEN (--new)
    if new:
        console.print(f"\n[bold white on red] {title} [/bold white on red]\n")
        panel_title = "O que é um Token?" if lang == "pt" else "What is a Token?"
        panel_body = (
            "[white]Um [bold cyan]Token Customizado[/bold cyan] é uma categoria personalizada que você define.\n"
            "Exemplo: crie um token chamado [bold]ESPORTE[/bold] e adicione uma wordlist com\n"
            "palavras como [dim]futebol, basquete, tenis...[/dim]\n\n"
            "O motor CypherDNA reconhecerá essas palavras como tipo [bold cyan]ESPORTE[/bold cyan]\n"
            "em vez de um [dim]WORD[/dim] genérico, tornando a análise e geração mais inteligentes."
        ) if lang == "pt" else (
            "[white]A [bold cyan]Custom Token[/bold cyan] is a named category that you define.\n"
            "Example: create a token called [bold]SPORT[/bold] and add a wordlist with\n"
            "words like [dim]football, basketball, tennis...[/dim]\n\n"
            "The CypherDNA engine will then recognize those words as type [bold cyan]SPORT[/bold cyan]\n"
            "instead of generic [dim]WORD[/dim], making analysis and generation smarter."
        )
        console.print(Panel(
            panel_body,
            title=f"[bold yellow]{panel_title}[/bold yellow]",
            border_style="yellow",
            padding=(1, 2)
        ))

        t_name = console.input("\n[bold cyan]>[/bold cyan] Token name (e.g. SPORT, CITY, BRAND): ").strip().upper()
        if not t_name:
            console.print("[dim]Cancelled.[/dim]")
            return

        t_dir = os.path.join(CUSTOM_TOKENS_DIR, t_name)
        os.makedirs(t_dir, exist_ok=True)
        console.print(f"\n[green][+][/green] Token [bold cyan]{t_name}[/bold cyan] created successfully.\n")

        token_count = len([d for d in os.listdir(CUSTOM_TOKENS_DIR) if os.path.isdir(os.path.join(CUSTOM_TOKENS_DIR, d))])
        if token_count >= 3:
            console.print(f"[bold yellow][!] Performance Notice:[/bold yellow] You now have [bold]{token_count}[/bold] tokens. Many tokens can slow down [bold]collect[/bold] training and [bold]analyze[/bold]. Keep only what you actively use.\n")

        console.print("[white]Now, link a wordlist (.txt) to this token so the engine knows what words belong to it.[/white]")
        console.print("[dim]Each line of the .txt file = one word that will be recognized as this token.[/dim]\n")

        import_path = console.input(f"[bold cyan]>[/bold cyan] Path to your .txt wordlist (or press Enter to skip): ").strip().strip('"').strip("'")
        if import_path and os.path.exists(import_path):
            dest = os.path.join(t_dir, os.path.basename(import_path))
            shutil.copy2(import_path, dest)
            try:
                with open(dest, "r", encoding="utf-8", errors="ignore") as _f:
                    wcount = sum(1 for ln in _f if ln.strip())
            except Exception:
                wcount = "?"
            console.print(f"\n[green][+][/green] Wordlist [bold]{os.path.basename(import_path)}[/bold] linked to [bold cyan]{t_name}[/bold cyan] ([bold]{wcount}[/bold] words).\n")
            console.print(Panel(
                f"[white]The engine will now recognize every word in that file as type [bold cyan]{t_name}[/bold cyan].\n\n"
                f"[dim]Next steps:[/dim]\n"
                f" • Run [bold green]cypherdna analyze <word>[/bold green] to test the classification.\n"
                f" • Run [bold green]cypherdna collect -i <wordlist.txt>[/bold green] to train the AI with this context.\n"
                f" • Add more wordlists: [bold green]cypherdna token {t_name} -a <file.txt>[/bold green]",
                title="[bold green]Token Ready[/bold green]",
                border_style="green",
                padding=(1, 2)
            ))
        else:
            console.print(f"\n[dim]No wordlist added yet. You can add one later with:[/dim]")
            console.print(f"  [bold green]cypherdna token {t_name} -a <yourfile.txt>[/bold green]\n")
        return

    # 2. LIST ALL TOKENS
    if not name:
        console.print(f"\n[bold white on red] {title} [/bold white on red]\n")
        folders = [d for d in os.listdir(CUSTOM_TOKENS_DIR) if os.path.isdir(os.path.join(CUSTOM_TOKENS_DIR, d))]

        if not folders:
            console.print(Panel(
                "[white]No custom tokens found yet.\n\n"
                "Custom tokens let you teach CypherDNA to recognize specific categories of words\n"
                "(e.g. [cyan]SPORT[/cyan], [cyan]CITY[/cyan], [cyan]BRAND[/cyan]) that the engine wouldn't know by default.\n\n"
                "[dim]Get started:[/dim]\n"
                "  [bold green]cypherdna token -n[/bold green]              → Create your first token\n"
                "  [bold green]cypherdna token SPORT -a words.txt[/bold green] → Add a wordlist to a token",
                title="[bold yellow]No Tokens Yet[/bold yellow]",
                border_style="yellow",
                padding=(1, 2)
            ))
            return

        t_table = Table(box=rich.box.ROUNDED, border_style="bright_blue", show_lines=True)
        t_table.add_column(get_text("token", "col_token", lang), style="bold cyan", min_width=12)
        t_table.add_column(get_text("token", "col_files", lang), justify="center", min_width=10)
        t_table.add_column("Exemplos de Palavras" if lang == "pt" else "Sample Words", style="dim", min_width=30)

        for f in sorted(folders):
            f_path = os.path.join(CUSTOM_TOKENS_DIR, f)
            txt_files = [x for x in os.listdir(f_path) if x.lower().endswith(".txt")]
            count = len(txt_files)
            samples = []
            for tf in txt_files[:1]:
                try:
                    with open(os.path.join(f_path, tf), "r", encoding="utf-8", errors="ignore") as _fp:
                        for ln in _fp:
                            v = ln.strip()
                            if v:
                                samples.append(v)
                            if len(samples) >= 5:
                                break
                except Exception:
                    pass
            sample_str = ", ".join(samples[:5]) + ("..." if len(samples) >= 5 else "") if samples else "[dim]- empty -[/dim]"
            t_table.add_row(f.upper(), str(count), sample_str)

        console.print(t_table)

        ref_title = "Como Usar Tokens" if lang == "pt" else "How to Use Tokens"
        ref_body = (
            "[bold white]Referência Rápida:[/bold white]\n\n"
            "  [bold green]cypherdna token -n[/bold green]                   → Criar um novo token\n"
            "  [bold green]cypherdna token FISH[/bold green]                 → Inspecionar token e pré-visualizar palavras\n"
            "  [bold green]cypherdna token FISH -a mylist.txt[/bold green]   → Adicionar uma wordlist ao token\n"
            "  [bold green]cypherdna token FISH -r mylist.txt[/bold green]   → Remover uma wordlist do token\n"
            "  [bold green]cypherdna token FISH -r[/bold green]              → Deletar o token inteiro\n\n"
            "[dim]Após adicionar palavras, teste com:[/dim] [bold green]cypherdna analyze <palavra>[/bold green]\n"
            "[dim]Depois treine a IA com:[/dim]            [bold green]cypherdna collect -i <wordlist.txt>[/bold green]"
        ) if lang == "pt" else (
            "[bold white]Quick Reference:[/bold white]\n\n"
            "  [bold green]cypherdna token -n[/bold green]                   → Create a new token\n"
            "  [bold green]cypherdna token FISH[/bold green]                 → Inspect token & preview words\n"
            "  [bold green]cypherdna token FISH -a mylist.txt[/bold green]   → Add a wordlist to the token\n"
            "  [bold green]cypherdna token FISH -r mylist.txt[/bold green]   → Remove a wordlist from the token\n"
            "  [bold green]cypherdna token FISH -r[/bold green]              → Delete the entire token\n\n"
            "[dim]After adding words, test with:[/dim] [bold green]cypherdna analyze <word>[/bold green]\n"
            "[dim]Then train the AI with:[/dim]        [bold green]cypherdna collect -i <wordlist.txt>[/bold green]"
        )
        console.print(Panel(
            ref_body,
            title=f"[bold cyan]{ref_title}[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        ))
        return

    # 3. MANAGE SPECIFIC TOKEN
    t_name = os.path.basename(name).strip().upper()
    t_dir = os.path.abspath(os.path.join(CUSTOM_TOKENS_DIR, t_name))
    tokens_base = os.path.abspath(CUSTOM_TOKENS_DIR)
    try:
        is_valid_token_dir = (os.path.commonpath([t_dir, tokens_base]) == tokens_base)
    except ValueError:
        is_valid_token_dir = False

    if not is_valid_token_dir or not os.path.exists(t_dir):
        console.print(f"\n[red][!][/red] Token [bold]{t_name}[/bold] not found.")
        console.print(f"[dim]Create it with: [bold green]cypherdna token -n[/bold green] or list all tokens with [bold green]cypherdna tokens[/bold green][/dim]\n")
        return

    # ADD
    if add:
        dest = os.path.join(t_dir, os.path.basename(add))
        shutil.copy2(add, dest)
        try:
            with open(dest, "r", encoding="utf-8", errors="ignore") as _f:
                wcount = sum(1 for ln in _f if ln.strip())
        except Exception:
            wcount = "?"
        console.print(f"\n[green][+][/green] [bold]{os.path.basename(add)}[/bold] added to token [bold cyan]{t_name}[/bold cyan] ([bold]{wcount}[/bold] words).")
        console.print(f"[dim]The engine will now classify words from this list as [bold cyan]{t_name}[/bold cyan].[/dim]")
        console.print(f"[dim]Test it: [bold green]cypherdna analyze <word>[/bold green][/dim]\n")

        token_count = len([d for d in os.listdir(CUSTOM_TOKENS_DIR) if os.path.isdir(os.path.join(CUSTOM_TOKENS_DIR, d))])
        all_files = sum(len([ff for ff in os.listdir(os.path.join(CUSTOM_TOKENS_DIR, d)) if ff.endswith('.txt')]) for d in os.listdir(CUSTOM_TOKENS_DIR) if os.path.isdir(os.path.join(CUSTOM_TOKENS_DIR, d)))
        if token_count >= 3 or all_files >= 5:
            console.print(f"[bold yellow][!] Performance Notice:[/bold yellow] {token_count} tokens / {all_files} wordlist files total. Large libraries slow down [bold]collect[/bold] and [bold]analyze[/bold].\n")
        return

    # REMOVE
    if remove is not None:
        clean_remove = remove.strip()
        if clean_remove == "" or clean_remove.lower() == t_name.lower() or clean_remove.lower() == "all":
            console.print(f"\n[bold red][!] This will permanently delete the entire token [cyan]{t_name}[/cyan] and all its wordlists.[/bold red]")
            if Confirm.ask("Are you sure?"):
                shutil.rmtree(t_dir, ignore_errors=True)
                console.print(f"[red][-][/red] Token [bold cyan]{t_name}[/bold cyan] deleted.\n")
        else:
            # Bloqueia caminhos externos ou tentativas de path traversal
            if os.path.dirname(clean_remove).strip():
                console.print(f"[red][!][/red] Error: Only filenames within token [bold cyan]{t_name}[/bold cyan] can be removed. External paths are not allowed.\n")
                return

            file_target = os.path.basename(clean_remove)
            target_f = os.path.abspath(os.path.join(t_dir, file_target))
            try:
                is_safe_target = (os.path.commonpath([target_f, t_dir]) == t_dir)
            except ValueError:
                is_safe_target = False

            if is_safe_target and os.path.exists(target_f):
                if Confirm.ask(f"Remove [bold]{file_target}[/bold] from token [bold cyan]{t_name}[/bold cyan]?"):
                    os.remove(target_f)
                    console.print(f"[red][-][/red] [bold]{file_target}[/bold] removed from [bold cyan]{t_name}[/bold cyan].\n")
            else:
                console.print(f"[red][!][/red] File [bold]{file_target}[/bold] not found in token [bold cyan]{t_name}[/bold cyan].")
                files = [x for x in os.listdir(t_dir) if x.lower().endswith(".txt")]
                if files:
                    console.print(f"[dim]Available files: {', '.join(files)}[/dim]\n")
        return

    # INSPECT TOKEN
    console.print(f"\n[bold white on blue]  {t_name}  [/bold white on blue]\n")
    files = [x for x in os.listdir(t_dir) if x.lower().endswith(".txt")]

    if not files:
        console.print("[dim]  No wordlists linked to this token yet.[/dim]")
        console.print(f"  Add one with: [bold green]cypherdna token {t_name} -a <yourfile.txt>[/bold green]\n")
        return

    for f in sorted(files):
        f_path = os.path.join(t_dir, f)
        try:
            with open(f_path, "r", encoding="utf-8", errors="ignore") as _fp:
                words = [ln.strip() for ln in _fp if ln.strip()]
        except Exception:
            words = []
        wcount = len(words)
        preview = ", ".join(words[:8]) + ("..." if wcount > 8 else "")
        console.print(f"  [bold cyan]•[/bold cyan] [bold]{f}[/bold] [dim]({wcount} words)[/dim]")
        if preview:
            console.print(f"    [dim]Preview: {preview}[/dim]")

    console.print(Panel(
        f"[dim]Manage this token:[/dim]\n"
        f"  [bold green]cypherdna token {t_name} -a <file.txt>[/bold green]    → Add another wordlist\n"
        f"  [bold green]cypherdna token {t_name} -r <file.txt>[/bold green]    → Remove a specific wordlist\n"
        f"  [bold green]cypherdna token {t_name} -r[/bold green]               → Delete this entire token\n\n"
        f"[dim]Every word in these files is recognized as [bold cyan]{t_name}[/bold cyan] during analysis & generation.[/dim]",
        border_style="blue",
        padding=(1, 2)
    ))
    console.print("")


@click.command(name="tokens")
@click.pass_context
def tokens_all(ctx):
    """List all custom tokens (Alias for 'token')"""
    ctx.invoke(token_cmd)
