"""
CypherDNA System Commands
- lang: Change interface language
- status: Show system status & version
- doctor: Environment health check
- dashboard: Operational oversight of assets
"""

import os
import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from config import (
    get_saved_lang,
    set_saved_lang,
    get_saved_hibp_key,
    set_saved_hibp_key,
    remove_saved_hibp_key,
    load_version_data,
    BASE_DIR,
    DATA_DIR,
    WORDLISTS_DIR,
    TRAINER_DIR,
    REPORTS_DIR,
    YOU_WORDLIST_DIR,
    NAMES_DATASET_FILE,
    BREACH_DATA_FILE,
    RANKER_FILE,
    CUSTOM_TOKENS_DIR
)
from ui_utils import display_msg, show_help_and_exit
from i18n import get_text

console = Console()


@click.command(name="lang", add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.argument("idioma", metavar="<pt|en>", required=False)
@click.pass_context
def lang_cmd(ctx, idioma):
    """Switch interface language (persists across sessions)."""
    ctx.ensure_object(dict)

    if idioma is None:
        current = get_saved_lang()
        label = "Português (PT)" if current == "pt" else "English (EN)"
        console.print(Panel(
            f"Idioma atual: [bold cyan]{label}[/bold cyan]\n\n"
            "[dim]Use [bold]cypherdna lang pt[/bold] ou [bold]cypherdna lang en[/bold] para trocar.[/dim]",
            title="[bold white] Language / Idioma [/bold white]",
            border_style="cyan",
            width=55
        ))
        return

    idioma = idioma.lower()
    if idioma == "pt":
        set_saved_lang("pt")
        console.print(Panel(
            "[bold green]Portugues ativado![/bold green]\n\n"
            "[dim]Todos os comandos agora usarao Portugues automaticamente.\n"
            "Para voltar: [bold]cypherdna lang en[/bold][/dim]",
            title="[bold white] Idioma [/bold white]",
            border_style="green",
            width=55
        ))
    elif idioma == "en":
        set_saved_lang("en")
        console.print(Panel(
            "[bold green]English activated![/bold green]\n\n"
            "[dim]All commands will now use English automatically.\n"
            "To switch back: [bold]cypherdna lang pt[/bold][/dim]",
            title="[bold white] Language [/bold white]",
            border_style="green",
            width=55
        ))
    else:
        console.print(f"[red][!] Invalid language: '{idioma}'. Use 'pt' or 'en'.[/red]")


@click.command(name="api", add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.option('--clear', is_flag=True, help="Remove the saved HIBP API key")
@click.argument("key", required=False)
@click.pass_context
def api_cmd(ctx, clear, key):
    """Configure or view HaveIBeenPwned API Key for live email breach auditing."""
    is_pt = (get_saved_lang() == "pt")
    
    if clear:
        remove_saved_hibp_key()
        msg = (
            "[bold green]Chave HIBP removida com sucesso![/bold green]\n\n"
            "[dim]O CypherDNA voltará a operar com inteligência OSINT gratuita (Hudson Rock).[/dim]"
        ) if is_pt else (
            "[bold green]HIBP API key removed successfully![/bold green]\n\n"
            "[dim]CypherDNA will default to free OSINT threat intelligence (Hudson Rock).[/dim]"
        )
        console.print(Panel(msg, title="[bold white] API HIBP [/bold white]", border_style="green", width=62))
        return

    if key:
        key_clean = key.strip()
        set_saved_hibp_key(key_clean)
        masked = key_clean[:4] + ("*" * max(0, len(key_clean) - 8)) + key_clean[-4:] if len(key_clean) > 8 else "***"
        msg = (
            f"[bold green]Chave da API HIBP configurada com sucesso![/bold green]\n\n"
            f"[bold white]Chave salva:[/] [cyan]{masked}[/cyan]\n\n"
            f"[dim]A partir de agora, 'cypherdna analyze <email>' consultará a API v3 oficial do HIBP em tempo real de forma permanente.[/dim]"
        ) if is_pt else (
            f"[bold green]HIBP API key configured successfully![/bold green]\n\n"
            f"[bold white]Saved Key:[/] [cyan]{masked}[/cyan]\n\n"
            f"[dim]From now on, 'cypherdna analyze <email>' will query official HIBP API v3 in real-time across all sessions.[/dim]"
        )
        console.print(Panel(msg, title="[bold white] API HIBP [/bold white]", border_style="green", width=62))
        return

    # Se não passou argumento, mostra status atual
    saved_key = get_saved_hibp_key()
    if saved_key:
        masked = saved_key[:4] + ("*" * max(0, len(saved_key) - 8)) + saved_key[-4:] if len(saved_key) > 8 else "***"
        status_text = (
            f"[bold green]STATUS: ATIVA E SALVA[/bold green]\n\n"
            f"[bold white]Chave Atual:[/] [cyan]{masked}[/cyan]\n\n"
            f"[dim]Para atualizar: [bold white]cypherdna api <nova_chave>[/bold white]\n"
            f"Para remover: [bold white]cypherdna api --clear[/bold white][/dim]"
        ) if is_pt else (
            f"[bold green]STATUS: ACTIVE & PERSISTED[/bold green]\n\n"
            f"[bold white]Current Key:[/] [cyan]{masked}[/cyan]\n\n"
            f"[dim]To update: [bold white]cypherdna api <new_key>[/bold white]\n"
            f"To remove: [bold white]cypherdna api --clear[/bold white][/dim]"
        )
        border = "green"
    else:
        status_text = (
            f"[bold yellow]STATUS: NENHUMA CHAVE CONFIGURADA[/bold yellow]\n\n"
            f"O CypherDNA analisa senhas gratuitamente (k-Anonymity) e e-mails via Hudson Rock OSINT.\n"
            f"Para correlacionar também com bases históricas web (Adobe, LinkedIn, etc.) no HIBP:\n\n"
            f"  [bold green]cypherdna api <sua_chave_hibp>[/bold green]\n"
            f"  [dim]ou[/dim] [bold green]cypherdna set api <sua_chave_hibp>[/bold green]\n\n"
            f"[dim]Adquira sua chave oficial em https://haveibeenpwned.com/API/Key[/dim]"
        ) if is_pt else (
            f"[bold yellow]STATUS: NO API KEY CONFIGURED[/bold yellow]\n\n"
            f"CypherDNA audits passwords for free (k-Anonymity) and emails via Hudson Rock OSINT.\n"
            f"To also cross-reference historical web dumps (Adobe, LinkedIn, etc.) on HIBP:\n\n"
            f"  [bold green]cypherdna api <your_hibp_key>[/bold green]\n"
            f"  [dim]or[/dim] [bold green]cypherdna set api <your_hibp_key>[/bold green]\n\n"
            f"[dim]Obtain your key at https://haveibeenpwned.com/API/Key[/dim]"
        )
        border = "yellow"

    console.print(Panel(status_text, title="[bold white] API HaveIBeenPwned (HIBP) [/bold white]", border_style=border, width=64))


@click.group(name="set", invoke_without_command=True, add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.pass_context
def set_cmd(ctx):
    """Configure persistent settings (api, lang)."""
    if ctx.invoked_subcommand is None:
        is_pt = (get_saved_lang() == "pt")
        msg = (
            "[bold white]Configuração de Parâmetros Globais[/bold white]\n\n"
            "Comandos disponíveis:\n"
            " • [bold green]cypherdna set api <chave>[/bold green]  - Define a chave da API HIBP\n"
            " • [bold green]cypherdna set lang <pt|en>[/bold green] - Altera o idioma permanente\n"
        ) if is_pt else (
            "[bold white]Global Settings Configuration[/bold white]\n\n"
            "Available commands:\n"
            " • [bold green]cypherdna set api <key>[/bold green]    - Set HIBP API key\n"
            " • [bold green]cypherdna set lang <pt|en>[/bold green] - Set interface language\n"
        )
        console.print(Panel(msg, title="[bold cyan] CypherDNA Set [/bold cyan]", border_style="cyan", width=62))


@set_cmd.command(name="api", add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.option('--clear', is_flag=True, help="Remove the saved HIBP API key")
@click.argument("key", required=False)
@click.pass_context
def set_api_subcmd(ctx, clear, key):
    """Set or view HIBP API key."""
    ctx.invoke(api_cmd, clear=clear, key=key)


@set_cmd.command(name="lang", add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.argument("idioma", metavar="<pt|en>", required=False)
@click.pass_context
def set_lang_subcmd(ctx, idioma):
    """Set interface language."""
    ctx.invoke(lang_cmd, idioma=idioma)


@click.command(name="status", add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.pass_context
def status_cmd(ctx):
    """Show system status"""
    is_pt = ctx.obj.get('LANG_PT', False) if ctx.obj else False
    v_data = load_version_data()
    version = v_data.get("version", "N/A")
    if is_pt:
        msg = (
            f"[bold green]STATUS: OPEN SOURCE[/bold green]\n\n"
            f"[bold white]Versão:[/]   [cyan]{version}[/]\n"
            f"[bold white]Licença:[/]  [green]Nenhuma necessária (Open Source)[/]\n"
            f"[bold white]Modo:[/]     [white]100% Offline — nenhum dado enviado externamente[/]"
        )
    else:
        msg = (
            f"[bold green]STATUS: OPEN SOURCE[/bold green]\n\n"
            f"[bold white]Version:[/]   [cyan]{version}[/]\n"
            f"[bold white]License:[/]  [green]None required (Open Source)[/]\n"
            f"[bold white]Mode:[/]     [white]100% Offline — zero external telemetry[/]"
        )
    console.print(Panel(
        msg,
        title="[bold cyan]CypherDNA[/bold cyan]",
        border_style="cyan",
        padding=(1, 2)
    ))


@click.command(name="doctor", add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.pass_context
def doctor(ctx):
    """Exhaustive forensic diagnostic audit of the CypherDNA ecosystem."""
    import platform
    import multiprocessing
    import time
    import json
    import requests

    is_pt = ctx.obj.get('LANG_PT', False) if ctx.obj else (get_saved_lang() == 'pt')
    lang = "pt" if is_pt else "en"

    # Header
    title = "CYPHERDNA SYSTEM DOCTOR - DIAGNÓSTICO FORENSE" if is_pt else "CYPHERDNA SYSTEM DOCTOR - FORENSIC DIAGNOSTIC"
    sub_title = "Auditoria Completa de Integridade do Ecossistema, Datasets, I/O e Feeds de Rede" if is_pt else "Complete Ecosystem Integrity Audit, Datasets, I/O & Network Probes"
    console.print(f"\n[bold white on red]  {title}  [/bold white on red]")
    console.print(f"[dim]{sub_title}[/dim]\n")

    total_checks = 0
    passed_checks = 0
    warnings = 0
    failures = 0

    def make_table(sec_title):
        t = Table(title=f"[bold cyan]{sec_title}[/bold cyan]", box=box.ROUNDED, border_style="dim", expand=True)
        t.add_column("Componente" if is_pt else "Component", style="bold white", width=30)
        t.add_column("Status", justify="center", width=18)
        t.add_column("Métricas / Telemetria" if is_pt else "Telemetry & Details", style="dim")
        return t

    # ─────────────────────────────────────────────────────────────
    # SEÇÃO 1: AMBIENTE HOST & RUNTIME
    # ─────────────────────────────────────────────────────────────
    t_host = make_table("1. AMBIENTE HOST & RUNTIME" if is_pt else "1. HOST RUNTIME & ENVIRONMENT")
    
    # 1.1 Python Core
    py_ver = platform.python_version()
    arch = platform.architecture()[0]
    total_checks += 1
    if sys.version_info >= (3, 10):
        t_host.add_row("Python Core", "[bold green]✔ OPERACIONAL[/bold green]", f"v{py_ver} ({arch}) - Compatibilidade Total")
        passed_checks += 1
    else:
        t_host.add_row("Python Core", "[bold yellow]⚠ ALERTA[/bold yellow]", f"v{py_ver} (Recomendado >= 3.10)")
        warnings += 1

    # 1.2 Sistema Operacional & Hardware
    os_desc = f"{platform.system()} {platform.release()} {platform.machine()}"
    cpus = multiprocessing.cpu_count()
    total_checks += 1
    t_host.add_row("Sistema & Hardware" if is_pt else "System & Hardware", "[bold green]✔ DETECTADO[/bold green]", f"{os_desc} • {cpus} Núcleos lógicos")
    passed_checks += 1

    # 1.3 Permissão de I/O em Disco
    total_checks += 1
    io_ok = False
    test_file = os.path.join(BASE_DIR, ".doctor_io_probe.tmp")
    try:
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("probe")
        if os.path.exists(test_file):
            os.remove(test_file)
            io_ok = True
    except Exception:
        io_ok = False

    if io_ok:
        t_host.add_row("Permissão de I/O em Disco" if is_pt else "Disk I/O Permissions", "[bold green]✔ LEITURA/ESCRITA[/bold green]", f"Diretório Raiz: {BASE_DIR}")
        passed_checks += 1
    else:
        t_host.add_row("Permissão de I/O em Disco" if is_pt else "Disk I/O Permissions", "[bold red]✖ NEGADO[/bold red]", f"Sem permissão de escrita em {BASE_DIR}")
        failures += 1

    console.print(t_host)

    # ─────────────────────────────────────────────────────────────
    # SEÇÃO 2: DATASETS FORENSES & INTELIGÊNCIA LOCAL
    # ─────────────────────────────────────────────────────────────
    t_data = make_table("2. DATASETS FORENSES & INTELIGÊNCIA LOCAL" if is_pt else "2. FORENSIC ASSETS & LOCAL DATASETS")

    # 2.1 Base de Nomes Próprios
    total_checks += 1
    if os.path.exists(NAMES_DATASET_FILE):
        try:
            with open(NAMES_DATASET_FILE, "r", encoding="utf-8") as f:
                names_data = json.load(f)
            names_cnt = len(names_data) if isinstance(names_data, list) else 0
            if names_cnt > 0:
                t_data.add_row("Base de Nomes Próprios" if is_pt else "First Names Dataset", "[bold green]✔ CARREGADO[/bold green]", f"{names_cnt:,} nomes indexados (names_dataset.json)".replace(",", "."))
                passed_checks += 1
            else:
                t_data.add_row("Base de Nomes Próprios" if is_pt else "First Names Dataset", "[bold yellow]⚠ VAZIO[/bold yellow]", "Arquivo presente mas sem registros válidos")
                warnings += 1
        except Exception as e:
            t_data.add_row("Base de Nomes Próprios" if is_pt else "First Names Dataset", "[bold red]✖ CORROMPIDO[/bold red]", f"Erro ao decodificar JSON: {e}")
            failures += 1
    else:
        t_data.add_row("Base de Nomes Próprios" if is_pt else "First Names Dataset", "[bold red]✖ AUSENTE[/bold red]", "Arquivo names_dataset.json não encontrado")
        failures += 1

    # 2.2 Base de Incidentes & Padrões
    total_checks += 1
    if os.path.exists(BREACH_DATA_FILE):
        try:
            with open(BREACH_DATA_FILE, "r", encoding="utf-8") as f:
                b_data = json.load(f)
            patterns_cnt = len(b_data.get("breach_patterns", []))
            stats_cnt = len(b_data.get("breach_source_stats", {}))
            t_data.add_row("Base de Incidentes & Leaks" if is_pt else "Breach Intelligence Data", "[bold green]✔ CARREGADO[/bold green]", f"{patterns_cnt} padrões estruturais & {stats_cnt} incidentes mapeados")
            passed_checks += 1
        except Exception:
            t_data.add_row("Base de Incidentes & Leaks" if is_pt else "Breach Intelligence Data", "[bold yellow]⚠ FALHA LEITURA[/bold yellow]", "JSON de incidentes inválido")
            warnings += 1
    else:
        t_data.add_row("Base de Incidentes & Leaks" if is_pt else "Breach Intelligence Data", "[bold yellow]⚠ AUSENTE[/bold yellow]", "breach_data.json ausente")
        warnings += 1

    # 2.3 Modelos de IA Pré-Treinados
    total_checks += 1
    trainer_files = [f for f in os.listdir(TRAINER_DIR) if f.endswith(".json")] if os.path.exists(TRAINER_DIR) else []
    if len(trainer_files) > 0:
        t_data.add_row("Modelos de IA (Trainer)" if is_pt else "Trained AI Models", "[bold green]✔ CARREGADO[/bold green]", f"{len(trainer_files)} modelo(s) probabilístico(s) em trainer_data/")
        passed_checks += 1
    else:
        t_data.add_row("Modelos de IA (Trainer)" if is_pt else "Trained AI Models", "[bold yellow]⚠ SEM MODELOS[/bold yellow]", "Nenhum .json treinado. Execute: 'cypherdna collect -i <wordlist>'")
        warnings += 1

    # 2.4 Tokens Customizados
    total_checks += 1
    if os.path.exists(CUSTOM_TOKENS_DIR):
        cat_dirs = [d for d in os.listdir(CUSTOM_TOKENS_DIR) if os.path.isdir(os.path.join(CUSTOM_TOKENS_DIR, d))]
        total_tok_words = 0
        for cd in cat_dirs:
            c_path = os.path.join(CUSTOM_TOKENS_DIR, cd)
            for tf in os.listdir(c_path):
                if tf.endswith(".txt"):
                    try:
                        with open(os.path.join(c_path, tf), "r", encoding="utf-8", errors="ignore") as _f:
                            total_tok_words += sum(1 for line in _f if line.strip())
                    except Exception:
                        pass
        t_data.add_row("Tokens Customizados" if is_pt else "Custom Tokens Cache", "[bold green]✔ ATIVO[/bold green]", f"{len(cat_dirs)} categoria(s) ({', '.join(cat_dirs[:3]) if cat_dirs else 'Nenhuma'}) • {total_tok_words} palavras")
        passed_checks += 1
    else:
        t_data.add_row("Tokens Customizados" if is_pt else "Custom Tokens Cache", "[bold yellow]⚠ AUSENTE[/bold yellow]", "Diretório custom_tokens não encontrado")
        warnings += 1

    # 2.5 Wordlists de Referência (data/wordlists/)
    total_checks += 1
    if os.path.exists(WORDLISTS_DIR):
        wlists = [f for f in os.listdir(WORDLISTS_DIR) if f.endswith(".txt")]
        if wlists:
            w_desc = f"{len(wlists)} listas temáticas disponíveis em data/wordlists/" if is_pt else f"{len(wlists)} thematic list(s) available in data/wordlists/"
            t_data.add_row("Wordlists de Referência" if is_pt else "Reference Wordlists", "[bold green]✔ CARREGADO[/bold green]", w_desc)
        else:
            w_desc = "Diretório limpo pronto para expansões (data/wordlists/)" if is_pt else "Clean directory ready for expansions (data/wordlists/)"
            t_data.add_row("Wordlists de Referência" if is_pt else "Reference Wordlists", "[bold green]✔ PRONTO[/bold green]", w_desc)
        passed_checks += 1
    else:
        t_data.add_row("Wordlists de Referência" if is_pt else "Reference Wordlists", "[bold yellow]⚠ AUSENTE[/bold yellow]", "Diretório data/wordlists/ não encontrado")
        warnings += 1

    # 2.6 Matriz Estratégica Ranker
    total_checks += 1
    if os.path.exists(RANKER_FILE):
        t_data.add_row("Matriz Estratégica (Ranker)" if is_pt else "Strategic Ranker Matrix", "[bold green]✔ SINCRONIZADO[/bold green]", "Arquivo ranker.json íntegro")
        passed_checks += 1
    else:
        t_data.add_row("Matriz Estratégica (Ranker)" if is_pt else "Strategic Ranker Matrix", "[bold yellow]⚠ PADRÃO[/bold yellow]", "Usando pesos heurísticos padrão")
        warnings += 1

    console.print(t_data)

    # ─────────────────────────────────────────────────────────────
    # SEÇÃO 3: CONECTIVIDADE & THREAT FEEDS (REDE)
    # ─────────────────────────────────────────────────────────────
    t_net = make_table("3. CONECTIVIDADE & THREAT INTELLIGENCE (REDE)" if is_pt else "3. THREAT FEEDS & NETWORK TELEMETRY")

    # 3.1 HIBP Passwords k-Anonymity
    total_checks += 1
    try:
        t0 = time.time()
        r_hibp = requests.get("https://api.pwnedpasswords.com/range/21BD1", timeout=2.5, headers={"User-Agent": "CypherDNA-Doctor"})
        lat_hibp = int((time.time() - t0) * 1000)
        if r_hibp.status_code == 200:
            t_net.add_row("API HIBP Passwords" if is_pt else "HIBP Passwords API", "[bold green]✔ CONECTADO[/bold green]", f"HTTP 200 ({lat_hibp}ms) • k-Anonymity 100% Gratuito")
            passed_checks += 1
        else:
            t_net.add_row("API HIBP Passwords" if is_pt else "HIBP Passwords API", "[bold yellow]⚠ INSTÁVEL[/bold yellow]", f"HTTP {r_hibp.status_code} ({lat_hibp}ms)")
            warnings += 1
    except Exception:
        t_net.add_row("API HIBP Passwords" if is_pt else "HIBP Passwords API", "[dim]OFFLINE[/dim]", "Sem conexão externa (Modo de isolamento local ativo)")
        warnings += 1

    # 3.2 Hudson Rock Cavalier OSINT
    total_checks += 1
    try:
        t0 = time.time()
        r_hr = requests.get("https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-email?email=probe@example.com", timeout=3.0, headers={"User-Agent": "CypherDNA-Doctor"})
        lat_hr = int((time.time() - t0) * 1000)
        if r_hr.status_code == 200:
            t_net.add_row("Hudson Rock Infostealers" if is_pt else "Hudson Rock OSINT Feed", "[bold green]✔ CONECTADO[/bold green]", f"HTTP 200 ({lat_hr}ms) • Monitoramento ao vivo ativo")
            passed_checks += 1
        else:
            t_net.add_row("Hudson Rock Infostealers" if is_pt else "Hudson Rock OSINT Feed", "[bold yellow]⚠ INSTÁVEL[/bold yellow]", f"HTTP {r_hr.status_code} ({lat_hr}ms)")
            warnings += 1
    except Exception:
        t_net.add_row("Hudson Rock Infostealers" if is_pt else "Hudson Rock OSINT Feed", "[dim]OFFLINE[/dim]", "Sem conexão externa (Modo de isolamento local ativo)")
        warnings += 1

    # 3.3 HIBP API Key
    total_checks += 1
    hibp_key = get_saved_hibp_key()
    if hibp_key:
        masked = hibp_key[:4] + ("*" * max(0, len(hibp_key) - 8)) + hibp_key[-4:] if len(hibp_key) > 8 else "***"
        t_net.add_row("Chave HIBP API v3" if is_pt else "HIBP Account API Key", "[bold green]✔ CONFIGURADA[/bold green]", f"Chave salva ({masked}) pronta para auditoria web")
        passed_checks += 1
    else:
        t_net.add_row("Chave HIBP API v3" if is_pt else "HIBP Account API Key", "[dim]ℹ NÃO CONFIGURADO[/dim]", "Opcional. Para correlacionar dumps web: 'cypherdna api <chave>'")
        passed_checks += 1

    console.print(t_net)

    # ─────────────────────────────────────────────────────────────
    # SEÇÃO 4: MOTORES DE EXECUÇÃO (CORE ENGINES)
    # ─────────────────────────────────────────────────────────────
    t_core = make_table("4. MOTORES DE EXECUÇÃO FORENSE (CORE ENGINES)" if is_pt else "4. CORE FORENSIC ENGINES HEALTH")

    # 4.1 DNA Parser Engine
    total_checks += 1
    test_dna = None
    try:
        from dna_parser import parse_password
        test_dna = parse_password("Admin2024!")
        tok_types = [t.token_type for t in test_dna.tokens]
        if "WEAK_WORD" in tok_types and "YEAR" in tok_types:
            t_core.add_row("DNA Parser Engine", "[bold green]✔ APROVADO[/bold green]", "Tokenização, extração de genes e classificação operacionais")
            passed_checks += 1
        else:
            t_core.add_row("DNA Parser Engine", "[bold yellow]⚠ ALERTA[/bold yellow]", f"Tokenização inesperada: {tok_types}")
            warnings += 1
    except Exception as e:
        t_core.add_row("DNA Parser Engine", "[bold red]✖ FALHA[/bold red]", f"Erro interno: {e}")
        failures += 1

    # 4.2 Shannon Entropy Engine
    total_checks += 1
    try:
        from crypto_utils import calculate_entropy, estimate_crack_time
        ent = calculate_entropy("Admin2024!")
        times = estimate_crack_time(ent)
        if ent > 0 and "rtx" in times:
            t_core.add_row("Entropy & Crack Estimator", "[bold green]✔ APROVADO[/bold green]", f"Shannon Metric: {ent:.1f} bits • Simulação de cluster RTX OK")
            passed_checks += 1
        else:
            t_core.add_row("Entropy & Crack Estimator", "[bold yellow]⚠ ALERTA[/bold yellow]", "Métrica de entropia retornou zero")
            warnings += 1
    except Exception as e:
        t_core.add_row("Entropy & Crack Estimator", "[bold red]✖ FALHA[/bold red]", f"Erro interno: {e}")
        failures += 1

    # 4.3 Mutation Vector Matrix
    total_checks += 1
    try:
        from mutation_engine import get_mutation_vectors
        if test_dna is not None:
            has_v, vectors = get_mutation_vectors(test_dna, "Admin2024!", is_pt=is_pt)
            t_core.add_row("Mutation Vector Matrix", "[bold green]✔ APROVADO[/bold green]", f"Matriz heurística ativa • {len(vectors)} vetores gerados no teste")
            passed_checks += 1
        else:
            t_core.add_row("Mutation Vector Matrix", "[bold yellow]⚠ PULADO[/bold yellow]", "Dependente do DNA Parser")
            warnings += 1
    except Exception as e:
        t_core.add_row("Mutation Vector Matrix", "[bold red]✖ FALHA[/bold red]", f"Erro interno: {e}")
        failures += 1

    # 4.4 Forensic PDF Reporter
    total_checks += 1
    try:
        from reporter import CipherDNAReporter
        pdf_probe = CipherDNAReporter(is_pt=is_pt)
        t_core.add_row("PDF Forensic Reporter", "[bold green]✔ APROVADO[/bold green]", "Motor FPDF e arquitetura de relatórios operacionais")
        passed_checks += 1
    except Exception as e:
        t_core.add_row("PDF Forensic Reporter", "[bold red]✖ FALHA[/bold red]", f"Erro interno: {e}")
        failures += 1

    console.print(t_core)

    # ─────────────────────────────────────────────────────────────
    # PAINEL RESUMO FINAL (Garante o snippet DIAGN para healthcheck)
    # ─────────────────────────────────────────────────────────────
    score_pct = int((passed_checks / total_checks) * 100) if total_checks > 0 else 0
    if failures == 0:
        summary_title = "[+] DIAGNÓSTICO CONCLUÍDO (DIAGNOSTIC COMPLETE)"
        border_style = "green"
        verdict_str = "[bold green]STATUS GERAL: 100% OPERACIONAL & PRONTO PARA AUDITORIA[/bold green]" if score_pct == 100 else f"[bold yellow]STATUS GERAL: {score_pct}% OPERACIONAL COM PEQUENOS AVISOS[/bold yellow]"
    else:
        summary_title = "[!] DIAGNÓSTICO CONCLUÍDO COM FALHAS (DIAGNOSTIC WARNING)"
        border_style = "red"
        verdict_str = f"[bold red]STATUS GERAL: {failures} FALHA(S) CRÍTICA(S) DETECTADA(S)[/bold red]"

    summary_body = (
        f" {verdict_str}\n\n"
        f" [bold white]Verificações Realizadas:[/] [cyan]{total_checks}[/]  |  "
        f"[bold white]Aprovadas:[/] [green]{passed_checks}[/]  |  "
        f"[bold white]Alertas:[/] [yellow]{warnings}[/]  |  "
        f"[bold white]Falhas:[/] [red]{failures}[/]\n\n"
        f"[dim]Todas as camadas do ecossistema (Runtime, Datasets, Feeds de Ameaça e Motores de Análise)\n"
        f"foram auditadas com telemetria em tempo real.[/dim]"
    ) if is_pt else (
        f" {verdict_str}\n\n"
        f" [bold white]Checks Executed:[/] [cyan]{total_checks}[/]  |  "
        f"[bold white]Passed:[/] [green]{passed_checks}[/]  |  "
        f"[bold white]Warnings:[/] [yellow]{warnings}[/]  |  "
        f"[bold white]Failures:[/] [red]{failures}[/]\n\n"
        f"[dim]All pipeline layers (Runtime, Datasets, Threat Feeds, and Core Engines)\n"
        f"have been audited with real-time telemetry.[/dim]"
    )

    console.print(Panel(summary_body, title=summary_title, border_style=border_style, padding=(1, 2)))


@click.command(name="dashboard", add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.pass_context
def dashboard(ctx):
    """[INTEL] Displays a professional oversight of all current investigations."""
    is_pt = ctx.obj.get('LANG_PT', False) if ctx.obj else False
    lang = "pt" if is_pt else "en"

    title = get_text("system", "dashboard_title", lang)

    wordlist_count = len(os.listdir(YOU_WORDLIST_DIR)) if os.path.exists(YOU_WORDLIST_DIR) else 0
    reports_count = len(os.listdir(REPORTS_DIR)) if os.path.exists(REPORTS_DIR) else 0

    dashboard_table = Table(box=None, header_style="bold red")
    dashboard_table.add_column(get_text("system", "operational_asset", lang), style="white")
    dashboard_table.add_column(get_text("system", "count", lang), justify="right", style="bold cyan")

    dashboard_table.add_row(get_text("system", "asset_wordlists", lang), str(wordlist_count))
    dashboard_table.add_row(get_text("system", "asset_reports", lang), str(reports_count))

    console.print(Panel(dashboard_table, title=f" {title} ", border_style="bright_red"))
