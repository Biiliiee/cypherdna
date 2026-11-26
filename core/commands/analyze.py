"""
CypherDNA Analyze Command
- analyze: Analyze password DNA or email breach status
"""

import os
import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from config import TRAINER_DIR, REPORTS_DIR
from dna_parser import parse_password
from probabilistic_model import ProbabilisticModel
from benchmark import Benchmark
from crypto_utils import calculate_entropy, estimate_crack_time
from breach_engine import check_email_breach, check_pattern_exposure, check_password_breach
from reporter import generate_pdf_report, generate_email_pdf_report
from mutation_engine import mutate_dna, get_mutation_vectors
from ui_utils import display_msg, safe_open, show_help_and_exit
from i18n import get_text

import re

console = Console()

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,63}$"
)


def is_valid_email(text: str) -> bool:
    """Valida se uma string é genuinamente um endereço de e-mail (RFC simplificado)."""
    if not text or len(text) > 254:
        return False
    if any(c in text for c in (' ', '\t', '\n', '\r')):
        return False
    if text.count('@') != 1:
        return False
    local_part, domain_part = text.split('@')
    if not local_part or not domain_part:
        return False
    if local_part.startswith('.') or local_part.endswith('.'):
        return False
    if '..' in local_part or '..' in domain_part:
        return False
    return bool(EMAIL_REGEX.match(text))


@click.command(name="analyze", add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.argument("target_input")
@click.option("-y", "-Y", "--year", required=False, is_flag=True, help="Generate +/- 100 year variations for valid years")
@click.option("-n", "-N", "--name", required=False, is_flag=True, help="Mutate NAME tokens based on wordlists")
@click.option("-e", "-E", "--export", is_flag=True, help="Export a professional PDF forensic report")
@click.option("-p", "--password", is_flag=True, help="Force password DNA analysis mode")
@click.option("-m", "--email", is_flag=True, help="Force email breach exposure audit mode")
@click.pass_context
def analyze(ctx, target_input, year, name, export, password=False, email=False):
    """Analyze password DNA or Email Breach status"""
    is_pt = ctx.obj.get('LANG_PT', False) if ctx.obj else False
    lang = "pt" if is_pt else "en"

    # 0. DETECÇÃO DE TIPO (E-mail ou Senha)
    if password:
        is_email = False
    elif email:
        is_email = True
    else:
        is_email = is_valid_email(target_input.strip())

    if is_email:
        title = "AUDITORIA DE EXPOSIÇÃO DE E-MAIL" if is_pt else "EMAIL EXPOSURE AUDIT"
        display_msg(title, get_text("analyze", "checking_exposure", lang, target=target_input), level="info")

        result = check_email_breach(target_input)
        exposed = result.get("exposed", False)
        risk = result.get("risk", "CLEAN")
        stealers = result.get("stealers", [])
        hibp_breaches = result.get("hibp_breaches", [])
        total_services = result.get("total_services_exposed", 0)

        # 1. Painel de Diagnóstico Geral
        risk_color = "bright_red" if risk == "CRITICAL" else "bright_yellow" if risk in ("HIGH", "MEDIUM") else "bright_green"
        risk_label = "CRÍTICO" if risk == "CRITICAL" and is_pt else "ELEVADO" if risk in ("HIGH", "MEDIUM") and is_pt else "SEGURO" if is_pt else risk
        verdict = (
            f" [bold white]Conta:[/] [cyan]{target_input}[/]\n"
            f" [bold white]Nível de Ameaça:[/] [{risk_color} bold]{risk_label}[/{risk_color} bold]\n"
            f" [bold white]Máquinas Infectadas:[/] [yellow]{len(stealers)}[/] [dim]({total_services} serviços expostos)[/dim]\n"
            f" [bold white]Vazamentos Web HIBP:[/] [white]{len(hibp_breaches)}[/]"
        ) if is_pt else (
            f" [bold white]Account:[/] [cyan]{target_input}[/]\n"
            f" [bold white]Threat Level:[/] [{risk_color} bold]{risk_label}[/{risk_color} bold]\n"
            f" [bold white]Infected Hosts:[/] [yellow]{len(stealers)}[/] [dim]({total_services} services exposed)[/dim]\n"
            f" [bold white]Web Breaches (HIBP):[/bold white] [white]{len(hibp_breaches)}[/]"
        )
        console.print(Panel(verdict, title="[bold white] Diagnóstico Forense [/bold white]" if is_pt else "[bold white] Forensic Verdict [/bold white]", border_style=risk_color))

        # 2. Detalhes de Máquinas Infectadas (Hudson Rock OSINT)
        if stealers:
            stealer_table = Table(title="[bold red]Computadores Infectados por Malware Infostealer[/bold red]" if is_pt else "[bold red]Hosts Compromised by Infostealer Malware[/bold red]", box=None)
            stealer_table.add_column("Computador" if is_pt else "Host", style="bold white")
            stealer_table.add_column("Sistema Operacional" if is_pt else "Operating System", style="cyan")
            stealer_table.add_column("Data" if is_pt else "Date", style="yellow")
            stealer_table.add_column("Serviços" if is_pt else "Services", justify="right", style="bold magenta")
            stealer_table.add_column("Malware Identificado" if is_pt else "Malware Path", style="dim")

            for s in stealers:
                m_path = s.get("malware_path", "")
                if len(m_path) > 35: m_path = "..." + m_path[-32:]
                stealer_table.add_row(
                    s.get("computer_name", "Unknown"),
                    s.get("operating_system", "Unknown"),
                    s.get("date_compromised", "")[:10],
                    str(s.get("total_services", 0)),
                    m_path
                )
            console.print(Panel(stealer_table, border_style="red"))

        # 3. Detalhes de Vazamentos HIBP (se houver)
        if hibp_breaches:
            breach_table = Table(title="[bold yellow]Vazamentos Web Confirmados (HIBP)[/bold yellow]" if is_pt else "[bold yellow]Confirmed Web Breaches (HIBP)[/bold yellow]", box=None)
            breach_table.add_column("Incidente / Fonte" if is_pt else "Breach / Source", style="bold white")
            breach_table.add_column("Data" if is_pt else "Date", style="yellow")
            breach_table.add_column("Dados Vazados" if is_pt else "Compromised Data", style="dim")

            for b in hibp_breaches:
                dc = ", ".join(b.get("data_classes", []))
                if len(dc) > 40: dc = dc[:37] + "..."
                breach_table.add_row(b.get("name", "Unknown"), b.get("breach_date", "")[:10], dc)
            console.print(Panel(breach_table, border_style="yellow"))

        # 4. Informação sobre API HIBP (se não configurada)
        if not result.get("hibp_configured"):
            info_msg = (
                "[dim]A inteligência de infostealers operou ao vivo via Hudson Rock OSINT.\n"
                "Para correlacionar também com bases históricas web (Adobe, Canva, LinkedIn), configure sua chave HIBP:\n"
                "  [bold green]cypherdna api <sua_chave>[/bold green]  ou  [bold green]cypherdna set api <sua_chave>[/bold green]\n"
                "(A chave fica salva permanentemente no seu CypherDNA).[/dim]"
            ) if is_pt else (
                "[dim]Live infostealer threat intelligence was provided by Hudson Rock OSINT.\n"
                "To also cross-reference historical web dumps (Adobe, Canva, LinkedIn), configure your HIBP key:\n"
                "  [bold green]cypherdna api <your_key>[/bold green]  or  [bold green]cypherdna set api <your_key>[/bold green]\n"
                "(Your key will be permanently persisted in CypherDNA).[/dim]"
            )
            console.print(Panel(info_msg, title="[bold cyan]Inteligência HIBP[/bold cyan]" if is_pt else "[bold cyan]HIBP Intelligence[/bold cyan]", border_style="cyan"))

        # 5. Recomendações
        if exposed:
            display_msg("RECOMMENDATION" if not is_pt else "RECOMENDAÇÃO FORENSE",
                        get_text("analyze", "recommendation", lang), level="warning")
        else:
            display_msg("CLEAN RECORD" if not is_pt else "SEM VAZAMENTOS CONHECIDOS",
                        get_text("analyze", "clean_record", lang), level="success")

        # 6. Exportação de Relatório PDF (quando -e é passado)
        if export:
            clean_email_tag = target_input.replace("@", "_at_").replace(".", "_")
            report_name = f"Report_Email_{clean_email_tag}.pdf"
            report_path = os.path.join(REPORTS_DIR, report_name)

            console.print(f"\n [bold yellow][*][/bold yellow] " + get_text("analyze", "export_generating", lang))
            success = generate_email_pdf_report(
                email=target_input,
                breach_data=result,
                filename=report_path,
                is_pt=is_pt
            )
            if success:
                display_msg(get_text("analyze", "export_success_title", lang),
                            get_text("analyze", "export_success_msg", lang, path=report_path), level="success")
                confirm_msg = get_text("analyze", "prompt_open_report", lang)
                if click.confirm(confirm_msg, default=True):
                    err = safe_open(report_path)
                    if err:
                        display_msg("OPEN ERROR", str(err), level="error")
            else:
                display_msg("EXPORT ERROR", "Failed to generate email forensic PDF report.", level="error")

        return

    password = target_input
    # 1. Parsing Inicial
    dna = parse_password(password)

    # 2. Score e Inteligência
    model = ProbabilisticModel(data_folder=TRAINER_DIR)
    model.load_jsons(is_pt=is_pt)
    model.calculate_probabilities()
    bench = Benchmark(model, is_pt=is_pt)
    dna_score = bench.calculate_password_score(password)
    entropy_score = calculate_entropy(password)

    def fmt_num(n):
        return f"{n:,}".replace(",", ".") if is_pt else f"{n:,}"

    # 3. Inteligência Forense e Checagem Real (HIBP k-Anonymity)
    breach_info = check_pattern_exposure(dna.pattern)
    real_breach_count = check_password_breach(password)

    pattern_prob = model.get_pattern_probability(dna.pattern)
    norm_pattern = dna.pattern.replace("WEAK_WORD", "WORD").replace("KEY_WALK", "NUMBER")
    eff_pattern_prob = max(pattern_prob, model.get_pattern_probability(norm_pattern))
    prevalence = eff_pattern_prob * 100

    # UI: HEADER
    title = get_text("analyze", "forensic_dashboard", lang)
    console.print(f"\n[bold white on red] {title} [/bold white on red]\n")

    # GRID DE STATUS
    color = "bright_green" if dna_score > 0.3 else "bright_yellow" if dna_score > 0.1 else "bright_red"
    label_key = "score_label_high" if dna_score > 0.3 else "score_label_mid" if dna_score > 0.1 else "score_label_low"
    label = get_text("analyze", label_key, lang)

    score_panel = Panel(
        Text.assemble((f"{dna_score:.5f}\n", f"bold {color}"), (label, f"bold {color}")),
        title=get_text("analyze", "score_title", lang), border_style="bright_blue", expand=True
    )

    crack_times = estimate_crack_time(entropy_score)
    entropy_color = "bright_green" if entropy_score > 60 else "bright_yellow" if entropy_score > 40 else "red"

    entropy_panel = Panel(
        Text.assemble(
            (f"{int(entropy_score)} bits\n", f"bold {entropy_color}"),
            (f"PC: {crack_times['pc']} | RTX: {crack_times['rtx']}\n", "white"),
            (get_text("analyze", "machine_entropy", lang), "cyan")
        ),
        title=get_text("analyze", "complexity_title", lang), border_style="bright_blue", expand=True
    )

    # Superfície de Ataque Inteligente e Coerente com Vazamentos
    if real_breach_count > 0:
        threat_level = "CRÍTICA" if is_pt else "CRITICAL"
        threat_desc = (
            f"Vazada em {fmt_num(real_breach_count)} vazamentos conhecidos."
            if is_pt else
            f"Found in {fmt_num(real_breach_count)} known public breaches."
        )
        t_color = "bright_red"
    elif dna_score > 0.3 or (breach_info and breach_info.get("risk") in ("HIGH", "CRITICAL")):
        threat_level = get_text("analyze", "threat_high", lang)
        threat_desc = get_text("analyze", "threat_desc_high", lang)
        t_color = "bright_red"
    elif dna_score > 0.1:
        threat_level = get_text("analyze", "threat_mid", lang)
        threat_desc = get_text("analyze", "threat_desc_high", lang)
        t_color = "bright_yellow"
    else:
        threat_level = get_text("analyze", "threat_low", lang)
        threat_desc = get_text("analyze", "threat_desc_low", lang)
        t_color = "bright_green"

    surface_panel = Panel(
        Text.assemble((f"{threat_level}\n", f"bold {t_color}"), (threat_desc, f"dim {t_color}")),
        title=get_text("analyze", "attack_surface", lang), border_style=t_color, expand=True
    )

    top_grid = Table.grid(expand=True, padding=(0, 1))
    top_grid.add_column(ratio=1)
    top_grid.add_column(ratio=1)
    top_grid.add_column(ratio=2)
    top_grid.add_row(score_panel, entropy_panel, surface_panel)

    console.print(top_grid)

    # DNA ANATOMY TABLE
    table = Table(show_header=True, header_style="bold white", border_style="red", box=None)
    table.add_column("Type", width=15)
    table.add_column("Value", style="bold")
    table.add_column("Weight", justify="right")

    for token in dna.tokens:
        t_weight = bench.get_token_forensic_weight(token.token_type)
        table.add_row(token.token_type, token.value, f"{t_weight:.2f}")

    console.print(Panel(table, title=get_text("analyze", "anatomy_title", lang), border_style="red"))

    # VISUAL DNA STRAND
    heatmap_title = get_text("analyze", "heatmap_title", lang)
    console.print(f" [red]>[/] [white]{heatmap_title}[/white]")

    heatmap_line = Text()
    heatmap_line.append(f" {password}  ", style="bold white")

    for token in dna.tokens:
        t_weight = bench.get_token_forensic_weight(token.token_type)
        if t_weight >= 0.70:
            h_color = "red"
        elif t_weight >= 0.40:
            h_color = "yellow"
        elif t_weight >= 0.15:
            h_color = "blue"
        else:
            h_color = "green"

        blocks = "#" * len(token.value)
        heatmap_line.append(blocks, style=h_color)
        heatmap_line.append(" ", style="black")

    console.print(heatmap_line)

    legend_titles = get_text("analyze", "legend_titles", lang)
    legend = f" [dim]###[/] [red]{legend_titles[0]}[/] [dim]###[/] [yellow]{legend_titles[1]}[/] [dim]###[/] [blue]{legend_titles[2]}[/] [dim]###[/] [green]{legend_titles[3]}[/]"
    console.print(legend)

    if real_breach_count > 0:
        breach_alert = get_text("analyze", "real_breach_msg", lang, count=fmt_num(real_breach_count))
        console.print(Panel(breach_alert, border_style="bright_red", title=get_text("analyze", "real_breach_title", lang)))

    if breach_info:
        breach_title = get_text("analyze", "forensic_breach_title", lang)
        risk_color = "bold red" if breach_info["risk"] == "CRITICAL" else "bold yellow"

        breach_msg = Text.assemble(
            ("PATTERN MATCH: ", "dim"), (f"{dna.pattern}\n", "bold cyan"),
            ("LEAK COUNT: ", "dim"), (f"~{fmt_num(breach_info['count'])} occurrences\n", risk_color),
            ("RISK LEVEL: ", "dim"), (f"[{breach_info['risk']}]\n", risk_color),
            ("INTEL: ", "dim"), (breach_info['description'], "white")
        )
        console.print(Panel(breach_msg, title=breach_title, border_style="red" if breach_info["risk"] == "CRITICAL" else "yellow"))
    else:
        breach_title = get_text("analyze", "local_model_title", lang)
        if eff_pattern_prob > 0.001:
            breach_msg = get_text("analyze", "msg_detected_trained", lang, pattern=dna.pattern) + "\n" + get_text("analyze", "msg_attack_success", lang, prevalence=prevalence)
        else:
            breach_msg = get_text("analyze", "msg_not_found_top50", lang, pattern=dna.pattern)
        console.print(Panel(breach_msg, title=breach_title, border_style="bright_blue"))

    # Export Logic
    if export:
        report_name = f"Report_{password[:10]}.pdf".replace(" ", "_").replace("/", "").replace("\\", "")
        report_path = os.path.join(REPORTS_DIR, report_name)

        token_weights = {t.token_type: bench.get_token_forensic_weight(t.token_type) for t in dna.tokens}

        console.print(f"\n [bold yellow][*][/bold yellow] " + get_text("analyze", "export_generating", lang))
        success = generate_pdf_report(
            password=password,
            dna_score=dna_score,
            entropy=entropy_score,
            crack_times=crack_times,
            dna_result=dna,
            prevalence=prevalence,
            filename=report_path,
            is_pt=is_pt,
            token_weights=token_weights,
            real_breach_count=real_breach_count,
            breach_info=breach_info
        )
        if success:
            display_msg(get_text("analyze", "export_success_title", lang), get_text("analyze", "export_success_msg", lang, path=report_path), level="success")

            confirm_msg = get_text("analyze", "prompt_open_report", lang)
            if click.confirm(confirm_msg, default=True):
                err = safe_open(report_path)
                if err:
                    display_msg("OPEN ERROR", str(err), level="error")
        else:
            display_msg("EXPORT ERROR", "Failed to generate forensic PDF report.", level="error")

    # Mutation vectors detection & execution
    has_vectors, vectors = get_mutation_vectors(dna, password, use_year=year, use_name=name, is_pt=is_pt)
    mutation_file = None

    if has_vectors:
        console.print()
        console.print(get_text("mutation", "vectors_header", lang))
        for v_type, v_val, v_desc in vectors:
            console.print(f"  [bold cyan]•[/bold cyan] [bold white]{v_val}[/bold white] [dim]({v_type}):[/dim] [yellow]{v_desc}[/yellow]")

        if click.confirm(get_text("analyze", "prompt_mutation", lang), default=True):
            mutation_file = mutate_dna(dna, password, use_year=year, use_name=name, is_pt=is_pt)
    else:
        console.print(get_text("mutation", "no_vectors", lang))

    if mutation_file:
        msg_mut = get_text("analyze", "msg_mutated_saved", lang, file=mutation_file)
        prompt_mut = get_text("analyze", "prompt_open_mutations", lang)

        console.print(msg_mut)
        if click.confirm(prompt_mut, default=True):
            err = safe_open(mutation_file)
            if err:
                console.print(get_text("analyze", "err_open", lang, error=err))
