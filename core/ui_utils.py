import sys
import os
import time
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from i18n import CLI_HELP

_active_status = None
_last_update_time = 0

console = Console()

SUBCOMMAND_HELP = {
    "analyze": {
        "title_en": " CIPHERDNA - ANALYZE COMMAND ",
        "title_pt": " CIPHERDNA - COMANDO ANALYZE ",
        "usage": "cypherdna analyze <password_or_email> [OPTIONS]",
        "desc_en": "Dissects a password into DNA tokens (NAME, YEAR, NUMBER...), computes entropy, estimates crack time across GPUs, checks HIBP leak exposure, and generates mutated wordlists using Custom Tokens.",
        "desc_pt": "Disseca uma senha em tokens DNA (NAME, YEAR, NUMBER...), calcula entropia, estima tempo de quebra via GPU, checa vazamentos no HIBP e gera wordlists mutadas usando Custom Tokens.",
        "examples_en": [
            ("cypherdna analyze xbox360.kabuto", "Dissects password & generates custom token wordlist"),
            ("cypherdna analyze Admin123! -e", "Analyzes password and exports forensic PDF report"),
            ("cypherdna analyze target@email.com", "Checks email address exposure against leak databases")
        ],
        "examples_pt": [
            ("cypherdna analyze xbox360.kabuto", "Disseca senha e gera wordlist de tokens customizados"),
            ("cypherdna analyze Admin123! -e", "Analisa senha e exporta relatório forense em PDF"),
            ("cypherdna analyze target@email.com", "Verifica exposição do e-mail em bancos de vazamentos")
        ],
        "options_en": [
            ("-e, --export", "Export detailed forensic PDF report"),
            ("-y, --year", "Include year variations (-100 to +100) during mutation"),
            ("-n, --name", "Include name variations during mutation"),
            ("-p, --password", "Force password DNA analysis mode"),
            ("-m, --email", "Force email breach exposure audit mode")
        ],
        "options_pt": [
            ("-e, --export", "Exportar relatório forense detalhado em PDF"),
            ("-y, --year", "Incluir variações de anos (-100 a +100) durante mutação"),
            ("-n, --name", "Incluir variações de nomes durante mutação"),
            ("-p, --password", "Forçar modo de análise de DNA de senha"),
            ("-m, --email", "Forçar modo de auditoria de vazamento de e-mail")
        ]
    },
    "generator": {
        "title_en": " CIPHERDNA - GENERATOR COMMAND ",
        "title_pt": " CIPHERDNA - COMANDO GENERATOR ",
        "usage": "cypherdna generator <inputs...> [OPTIONS]",
        "desc_en": "Generates a targeted, realistic wordlist using personal data inputs (names, dates, custom tokens) based on structural pattern scoring.",
        "desc_pt": "Gera uma wordlist direcionada e realista usando dados pessoais (nomes, datas, tokens customizados) baseando-se em pontuação de padrões estruturais.",
        "examples_en": [
            ("cypherdna generator xbox kabuto 2024 -L -S", "Generates wordlist with Leet Speak (-L) and Symbols (-S)"),
            ("cypherdna generator banana -c", "Generates all 2^N binary casing combinations (banana, bAnana, baNana...)"),
            ("cypherdna generator admin 2025 -N 10000 -o out.txt", "Limits output to 10k passwords and saves to out.txt"),
            ("cypherdna generator Gustavo -R", "Applies Strategic Ranking (-R)"),
            ("cypherdna generator target 2024 -P | hashcat ...", "Pipes output directly to STDOUT (silent mode for Hashcat/John)")
        ],
        "examples_pt": [
            ("cypherdna generator xbox kabuto 2024 -L -S", "Gera wordlist com Leet Speak (-L) e Símbolos (-S)"),
            ("cypherdna generator banana -c", "Gera todas as 2^N combinações de maiúsculas/minúsculas (banana, bAnana, baNana...)"),
            ("cypherdna generator admin 2025 -N 10000 -o out.txt", "Limita saída em 10 mil senhas e salva em out.txt"),
            ("cypherdna generator Gustavo -R", "Aplica Ranking Estratégico (-R)"),
            ("cypherdna generator target 2024 -P | hashcat ...", "Redireciona saída para STDOUT (modo silencioso para Hashcat/John)")
        ],
        "options_en": [
            ("-N, --number <int>", "Limit maximum generated passwords (e.g. -N 50000)"),
            ("-o, --output <file>", "Specify output filename (saved in output/wordlists/)"),
            ("-c, --case", "Enable full binary casing permutations (all 2^N upper/lower combinations, e.g. banana, bAnana, baNana...)"),
            ("-L, --leet", "Enable dynamic Leet Speak mutations (a->4, e->3, o->0...)"),
            ("-S, --symbol", "Enable symbol mutations (!, @, #, $...)"),
            ("-R, --rank", "Apply custom Strategic Ranking created with 'ranker'"),
            ("-T, --trainer <file>", "Specify a trainer dataset from trainer_data/"),
            ("-V, --validate [file]", "Benchmark generated wordlist after creation"),
            ("-P, --pipe, --stdout", "Output directly to STDOUT (silent mode for Hashcat/John piping)")
        ],
        "options_pt": [
            ("-N, --number <int>", "Limita quantidade máxima de senhas geradas (ex: -N 50000)"),
            ("-o, --output <file>", "Especifica o nome do arquivo de saída (salvo em output/wordlists/)"),
            ("-c, --case", "Ativa permutações completas de maiúsculas/minúsculas (todas as 2^N combinações, ex: banana, bAnana, baNana...)"),
            ("-L, --leet", "Ativa mutações dinâmicas de Leet Speak (a->4, e->3, o->0...)"),
            ("-S, --symbol", "Ativa mutações com símbolos (!, @, #, $...)"),
            ("-R, --rank", "Aplica Ranking Estratégico customizado criado com 'ranker'"),
            ("-T, --trainer <file>", "Especifica dataset de treinamento de trainer_data/"),
            ("-V, --validate [file]", "Avalia a qualidade da wordlist gerada após a criação"),
            ("-P, --pipe, --stdout", "Envia saída diretamente para STDOUT (modo silencioso para Hashcat/John)")
        ]
    },
    "token": {
        "title_en": " CIPHERDNA - CUSTOM TOKEN MANAGER ",
        "title_pt": " CIPHERDNA - GERENCIADOR DE TOKENS CUSTOMIZADOS ",
        "usage": "cypherdna token [TOKEN_NAME] [OPTIONS]",
        "desc_en": "Creates and manages custom token wordlist categories (e.g., NARUTOCHARACTER, GAME, FOOTBALL) in custom_tokens/.",
        "desc_pt": "Cria e gerencia categorias de tokens customizados (ex: NARUTOCHARACTER, GAME, FOOTBALL) na pasta custom_tokens/.",
        "examples_en": [
            ("cypherdna token", "Lists all active custom tokens and wordlist counts"),
            ("cypherdna token -n", "Interactive wizard to create a new custom token"),
            ("cypherdna token GAME -a games.txt", "Adds a .txt wordlist file to the GAME custom token"),
            ("cypherdna token GAME -r games.txt", "Removes a specific wordlist file from the GAME token"),
            ("cypherdna token GAME -r", "Permanently deletes the entire GAME token folder")
        ],
        "examples_pt": [
            ("cypherdna token", "Lista todos os tokens customizados ativos e contagem de wordlists"),
            ("cypherdna token -n", "Assistente interativo para criar um novo token customizado"),
            ("cypherdna token GAME -a games.txt", "Adiciona um arquivo .txt ao token customizado GAME"),
            ("cypherdna token GAME -r games.txt", "Remove um arquivo de wordlist específico do token GAME"),
            ("cypherdna token GAME -r", "Deleta permanentemente a pasta inteira do token GAME")
        ],
        "options_en": [
            ("-n, --new", "Interactive wizard to create a new custom token folder"),
            ("-a, --add <path.txt>", "Add a .txt wordlist file to the specified custom token"),
            ("-r, --remove [file]", "Remove a specific wordlist or the entire token folder")
        ],
        "options_pt": [
            ("-n, --new", "Assistente interativo para criar uma nova pasta de token customizado"),
            ("-a, --add <path.txt>", "Adiciona um arquivo de wordlist .txt ao token especificado"),
            ("-r, --remove [file]", "Remove uma wordlist específica ou a pasta inteira do token")
        ]
    },
    "ranker": {
        "title_en": " CIPHERDNA - STRATEGIC RANKER ",
        "title_pt": " CIPHERDNA - RANKER ESTRATÉGICO ",
        "usage": "cypherdna ranker [OPTIONS]",
        "desc_en": "Manages DNA priority strategies (.dna files and active ranking) applied when running generator -R.",
        "desc_pt": "Gerencia estratégias de prioridade DNA (arquivos .dna e ranking ativo) aplicadas ao rodar generator -R.",
        "examples_en": [
            ("cypherdna ranker", "Opens interactive control panel and shows active ranking"),
            ("cypherdna ranker -L", "Lists active ranking, presets, and saved .dna strategies"),
            ("cypherdna ranker -C", "Builds a custom strategy, saves .dna on DONE, and activates it"),
            ("cypherdna ranker -P corporate", "Applies built-in preset (corporate | minimalist | hardcore)"),
            ("cypherdna ranker -I Naruto", "Loads and activates saved strategy Naruto.dna"),
            ("cypherdna ranker -E my_strat", "Exports active strategy to strategies/my_strat.dna"),
            ("cypherdna ranker -D Naruto", "Deletes custom strategy Naruto.dna (use -D all for all, or -D for menu)")
        ],
        "examples_pt": [
            ("cypherdna ranker", "Abre painel interativo e exibe o ranking ativo"),
            ("cypherdna ranker -L", "Lista ranking ativo, presets e estratégias .dna salvas"),
            ("cypherdna ranker -C", "Cria estratégia customizada, salva .dna no DONE e ativa"),
            ("cypherdna ranker -P corporate", "Aplica preset pronto (corporate | minimalist | hardcore)"),
            ("cypherdna ranker -I Naruto", "Carrega e ativa a estratégia salva Naruto.dna"),
            ("cypherdna ranker -E minha_strat", "Exporta a estratégia ativa para strategies/minha_strat.dna"),
            ("cypherdna ranker -D Naruto", "Apaga a estratégia Naruto.dna (use -D all para tudo, ou -D para menu)")
        ],
        "options_en": [
            ("-L, --list", "List active ranking, presets, and saved .dna strategies"),
            ("-C, --create, --custom", "Interactive builder (saves .dna file on DONE and activates)"),
            ("-P, --preset [name]", "Apply built-in preset (corporate, minimalist, hardcore)"),
            ("-I, --use, --import [name]", "Load and activate a saved .dna strategy"),
            ("-E, --export <file>", "Export active ranking to a .dna file in strategies/"),
            ("-D, --delete, --clear [target]", "Delete custom .dna strategy, 'active', or 'all'")
        ],
        "options_pt": [
            ("-L, --list", "Lista ranking ativo, presets e estratégias .dna salvas"),
            ("-C, --create, --custom", "Construtor interativo (salva arquivo .dna no DONE e ativa)"),
            ("-P, --preset [nome]", "Aplica modelo pronto (corporate, minimalist, hardcore)"),
            ("-I, --use, --import [nome]", "Carrega e ativa uma estratégia .dna salva"),
            ("-E, --export <arquivo>", "Exporta o ranking ativo para um arquivo .dna em strategies/"),
            ("-D, --delete, --clear [alvo]", "Apaga estratégia .dna customizada, 'active' ou 'all'")
        ]
    },
    "collect": {
        "title_en": " CIPHERDNA - COLLECT (PATTERN TRAINER) ",
        "title_pt": " CIPHERDNA - COLLECT (TREINADOR DE PADRÕES) ",
        "usage": "cypherdna collect [OPTIONS]",
        "desc_en": "Analyzes real-world wordlists (e.g. rockyou.txt) to extract structural patterns and build probabilistic scoring models used by the generator.",
        "desc_pt": "Analisa wordlists reais (ex: rockyou.txt) para extrair padrões estruturais e construir modelos de pontuação probabilística usados pelo generator.",
        "examples_en": [
            ("cypherdna collect -i rockyou.txt", "Parses rockyou.txt and saves pattern data to trainer_data/"),
            ("cypherdna collect -L", "Lists all stored pattern datasets"),
            ("cypherdna collect -P rockyou.json", "Prints token and pattern distribution for a dataset"),
            ("cypherdna collect -D rockyou.json", "Deletes a stored dataset")
        ],
        "examples_pt": [
            ("cypherdna collect -i rockyou.txt", "Analisa rockyou.txt e salva os dados de padrões em trainer_data/"),
            ("cypherdna collect -L", "Lista todos os conjuntos de padrões armazenados"),
            ("cypherdna collect -P rockyou.json", "Exibe distribuição de tokens e padrões de um conjunto"),
            ("cypherdna collect -D rockyou.json", "Deleta um conjunto de dados armazenado")
        ],
        "options_en": [
            ("-i, --input <file>", "Input wordlist file to parse and extract patterns from"),
            ("-L, --list", "List all datasets stored in trainer_data/"),
            ("-P, --print <file>", "Print token and pattern distribution for a dataset"),
            ("-D, --delete <file>", "Delete a specific dataset from trainer_data/")
        ],
        "options_pt": [
            ("-i, --input <file>", "Arquivo de wordlist para analisar e extrair padrões"),
            ("-L, --list", "Lista todos os conjuntos de dados em trainer_data/"),
            ("-P, --print <file>", "Exibe distribuição de tokens e padrões de um conjunto"),
            ("-D, --delete <file>", "Deleta um conjunto de dados específico de trainer_data/")
        ]
    },
    "comparator": {
        "title_en": " CIPHERDNA - WORDLIST COMPARATOR ",
        "title_pt": " CIPHERDNA - COMPARADOR DE WORDLISTS ",
        "usage": "cypherdna comparator <file1.txt> [file2.txt ...]",
        "desc_en": "Scores one or more wordlists using probabilistic pattern models, ranking structural realism and human-likeness.",
        "desc_pt": "Pontua uma ou mais wordlists usando modelos de padrões probabilísticos, classificando realismo estrutural e naturalidade humana.",
        "examples_en": [
            ("cypherdna comparator my_list.txt", "Scores my_list.txt against stored pattern datasets"),
            ("cypherdna comparator list1.txt list2.txt", "Compares multiple wordlists side-by-side")
        ],
        "examples_pt": [
            ("cypherdna comparator my_list.txt", "Pontua my_list.txt contra os datasets de padrões armazenados"),
            ("cypherdna comparator list1.txt list2.txt", "Compara múltiplas wordlists lado a lado")
        ],
        "options_en": [
            ("-f, --format <type>", "Export format: json | csv | html | none (default: none)"),
            ("-o, --output <name>", "Output filename base (default: benchmark_report)"),
            ("-OH, --output-html",  "Export report as HTML and open in browser")
        ],
        "options_pt": [
            ("-f, --format <tipo>", "Formato de exportação: json | csv | html | none (padrão: none)"),
            ("-o, --output <nome>", "Base do nome do arquivo de saída (padrão: benchmark_report)"),
            ("-OH, --output-html",  "Exporta relatório como HTML e abre no navegador")
        ]
    },
    "clear": {
        "title_en": " CIPHERDNA - CLEAN ENGINE ",
        "title_pt": " CIPHERDNA - MOTOR DE LIMPEZA ",
        "usage": "cypherdna clear [TARGET]",
        "desc_en": "Cleans generated wordlists (output/wordlists/), forensic PDF reports (output/reports/), or token caches.",
        "desc_pt": "Limpa wordlists geradas (output/wordlists/), relatórios PDF (output/reports/) ou caches de tokens.",
        "examples_en": [
            ("cypherdna clear wordlists", "Deletes all generated wordlists in output/wordlists/"),
            ("cypherdna clear reports", "Deletes all PDF reports in output/reports/"),
            ("cypherdna clear ranker", "Cleans all custom strategic rankings"),
            ("cypherdna clear all", "Cleans all generated assets and caches")
        ],
        "examples_pt": [
            ("cypherdna clear wordlists", "Deleta todas as wordlists geradas em output/wordlists/"),
            ("cypherdna clear reports", "Deleta todos os relatórios PDF em output/reports/"),
            ("cypherdna clear ranker", "Limpa todos os rankings estratégicos customizados"),
            ("cypherdna clear all", "Limpa todos os arquivos e caches gerados")
        ],
        "options_en": [
            ("wordlists", "Delete all generated wordlists in output/wordlists/"),
            ("reports", "Delete all generated PDF reports in output/reports/"),
            ("ranker", "Clear custom strategic rankings"),
            ("tokens", "Clear custom tokens and trained datasets"),
            ("all", "Clean all generated assets (wordlists, reports, caches)")
        ],
        "options_pt": [
            ("wordlists", "Deleta todas as wordlists geradas em output/wordlists/"),
            ("reports", "Deleta todos os relatórios PDF em output/reports/"),
            ("ranker", "Limpa rankings estratégicos customizados"),
            ("tokens", "Limpa tokens customizados e modelos treinados"),
            ("all", "Limpa todos os arquivos e caches gerados")
        ]
    },
    "status": {
        "title_en": " CIPHERDNA - SYSTEM STATUS ",
        "title_pt": " CIPHERDNA - STATUS DO SISTEMA ",
        "usage": "cypherdna status",
        "desc_en": "Displays active open-source status, module integrity, and environment configuration.",
        "desc_pt": "Exibe o status open-source ativo, integridade de módulos e configuração de ambiente.",
        "examples_en": [("cypherdna status", "Displays active system status")],
        "examples_pt": [("cypherdna status", "Exibe o status ativo do sistema")],
        "options_en": [],
        "options_pt": []
    },
    "doctor": {
        "title_en": " CIPHERDNA - SYSTEM DOCTOR ",
        "title_pt": " CIPHERDNA - MÉDICO DO SISTEMA ",
        "usage": "cypherdna doctor",
        "desc_en": "Performs diagnostic health checks on all internal directories, permissions, and dependencies.",
        "desc_pt": "Executa verificações de diagnóstico em todos os diretórios internos, permissões e dependências.",
        "examples_en": [("cypherdna doctor", "Runs complete diagnostic health check")],
        "examples_pt": [("cypherdna doctor", "Executa verificação diagnóstica completa")],
        "options_en": [],
        "options_pt": []
    },
    "dashboard": {
        "title_en": " CIPHERDNA - COMMAND DASHBOARD ",
        "title_pt": " CIPHERDNA - PAINEL DE COMANDO ",
        "usage": "cypherdna dashboard",
        "desc_en": "Displays an overview panel of all generated wordlists and PDF reports with sizes and creation dates.",
        "desc_pt": "Exibe um painel geral de todas as wordlists geradas e relatórios PDF com tamanhos e datas de criação.",
        "examples_en": [("cypherdna dashboard", "Displays asset overview dashboard")],
        "examples_pt": [("cypherdna dashboard", "Exibe o painel de visão geral dos relatórios e listas")],
        "options_en": [],
        "options_pt": []
    },
    "lang": {
        "title_en": " CIPHERDNA - LANGUAGE SETTINGS ",
        "title_pt": " CIPHERDNA - CONFIGURAÇÕES DE IDIOMA ",
        "usage": "cypherdna lang <pt|en>",
        "desc_en": "Sets the interface language permanently. After running this command, all output will use the selected language without needing any extra flag.",
        "desc_pt": "Define o idioma da interface de forma permanente. Após executar este comando, todo o output usará o idioma selecionado sem precisar de flags extras.",
        "examples_en": [
            ("cypherdna lang pt", "Switches all output to Portuguese permanently"),
            ("cypherdna lang en", "Switches all output to English permanently"),
            ("cypherdna lang",    "Shows currently active language")
        ],
        "examples_pt": [
            ("cypherdna lang pt", "Muda toda a saída para Português permanentemente"),
            ("cypherdna lang en", "Muda toda a saída para Inglês permanentemente"),
            ("cypherdna lang",    "Mostra o idioma ativo atualmente")
        ],
        "options_en": [],
        "options_pt": []
    },
    "api": {
        "title_en": " CIPHERDNA - HIBP API CONFIGURATION ",
        "title_pt": " CIPHERDNA - CONFIGURAÇÃO DE API HIBP ",
        "usage": "cypherdna api [KEY] [OPTIONS] | cypherdna set api [KEY]",
        "desc_en": "Configures and persists the HaveIBeenPwned API Key for real-time live email breach audits.",
        "desc_pt": "Configura e persiste a chave da API HaveIBeenPwned para auditorias de vazamento de e-mails em tempo real.",
        "examples_en": [
            ("cypherdna api <your_key>", "Persists your HIBP API key for all future sessions"),
            ("cypherdna api",           "Displays current key status and masked value"),
            ("cypherdna api --clear",   "Removes the saved key and falls back to free OSINT mode")
        ],
        "examples_pt": [
            ("cypherdna api <sua_chave>", "Salva sua chave HIBP permanentemente para todas as sessões"),
            ("cypherdna api",            "Exibe o status atual e a chave mascarada"),
            ("cypherdna api --clear",    "Remove a chave salva e volta para o modo OSINT gratuito")
        ],
        "options_en": [
            ("--clear", "Remove the persisted HIBP API key from disk")
        ],
        "options_pt": [
            ("--clear", "Remove a chave da API HIBP persistida em disco")
        ]
    }
}
SUBCOMMAND_HELP["idioma"] = SUBCOMMAND_HELP["lang"]
SUBCOMMAND_HELP["set-api"] = SUBCOMMAND_HELP["api"]

def display_command_help(cmd_name, is_pt=False):
    """Exibe o manual detalhado e bonito de um subcomando específico usando Rich."""
    info = SUBCOMMAND_HELP.get(cmd_name)
    if not info:
        return False

    title = info['title_pt'] if is_pt else info['title_en']
    desc = info['desc_pt'] if is_pt else info['desc_en']

    console.print(f"\n[bold white on red] {title} [/bold white on red]\n")
    console.print(f"[white]{desc}[/white]\n")

    usage_label = "Uso" if is_pt else "Usage"
    console.print(f"[bold cyan]{usage_label}:[/bold cyan] [bold green]{info['usage']}[/bold green]\n")

    opts = info.get('options_pt' if is_pt else 'options_en', info.get('options', []))
    if opts:
        opt_table = Table(show_header=True, header_style="bold white", border_style="bright_blue", box=box.ROUNDED)
        opt_table.add_column("Flag / Opção" if is_pt else "Option / Flag", style="bold yellow", min_width=22)
        opt_table.add_column("Descrição" if is_pt else "Description", style="white", min_width=45)
        for opt, opt_desc in opts:
            opt_table.add_row(opt, opt_desc)
        console.print(Panel(opt_table, title="[bold white]OPÇÕES DISPONÍVEIS[/bold white]" if is_pt else "[bold white]AVAILABLE OPTIONS[/bold white]", border_style="bright_blue"))

    exs = info.get('examples_pt' if is_pt else 'examples_en', info.get('examples', []))
    if exs:
        ex_table = Table(show_header=False, box=None)
        ex_table.add_column("Cmd", style="bold green", min_width=42)
        ex_table.add_column("Explanation", style="dim white", min_width=35)
        for ex_cmd, ex_desc in exs:
            ex_table.add_row(ex_cmd, f"# {ex_desc}")
        console.print(Panel(ex_table, title="[bold white]EXEMPLOS DE USO[/bold white]" if is_pt else "[bold white]USAGE EXAMPLES[/bold white]", border_style="bright_green"))

    console.print()
    return True

def display_custom_help(is_pt=False):
    """Exibe o manual personalizado, formatado e visualmente hierárquico usando i18n."""
    from config import get_saved_lang
    lang = "pt" if is_pt else "en"
    texts = CLI_HELP[lang]

    # ── Header ────────────────────────────────────────────────────────────────
    active_lang = get_saved_lang()
    lang_badge = "[dim]PT[/dim]" if active_lang == "pt" else "[dim]EN[/dim]"

    console.print(f"\n[bold white on red] {texts['header']} [/bold white on red] {lang_badge}")
    console.print(f"[dim]{texts['version_tag']}[/dim]")
    console.print(f"[white]{texts['description']}[/white]\n")

    # ── Categorias de Comandos ───────────────────────────────────────────────
    categories = [
        (
            "ENGINE CORE (ANALYSIS & GENERATION)" if not is_pt else "MOTOR CORE (ANÁLISE & GERAÇÃO)",
            [
                ("cmd_analyze", "analyze <password_or_email>"),
                ("cmd_gen",     "generator <inputs...>"),
            ]
        ),
        (
            "CUSTOMIZATION & STRATEGY" if not is_pt else "CUSTOMIZAÇÃO & ESTRATÉGIAS",
            [
                ("cmd_token",   "token <NAME> [-n | -a <file> | -r]"),
                ("cmd_ranker",  "ranker [-L | -C | -P | -I | -D]"),
            ]
        ),
        (
            "PATTERN TRAINING & BENCHMARKING" if not is_pt else "TREINAMENTO DE PADRÕES & BENCHMARKING",
            [
                ("cmd_trainer", "collect -i <wordlist.txt>"),
                ("cmd_comparator", "comparator <file1.txt> [file2.txt]"),
            ]
        ),
        (
            "SYSTEM & MAINTENANCE" if not is_pt else "SISTEMA & MANUTENÇÃO",
            [
                ("cmd_status",  "status"),
                ("cmd_doctor",  "doctor"),
                ("cmd_dashboard", "dashboard"),
                ("cmd_clear",   "clear <wordlists|reports|all>"),
                ("cmd_lang",    "lang <pt|en>"),
                ("cmd_api",     "api [key] | --clear"),
            ]
        ),
    ]

    t = Table(
        show_header=True,
        header_style="bold white on dark_red",
        border_style="red",
        box=box.ROUNDED,
        expand=False,
        show_lines=False
    )
    t.add_column(texts.get('cmd_header', 'Command' if not is_pt else 'Comando'), style="bold cyan", min_width=22, no_wrap=True)
    t.add_column(texts['desc'], style="white", min_width=55)
    t.add_column(texts['usage'], style="dim green", min_width=38)

    for idx, (cat_title, items) in enumerate(categories):
        if idx > 0:
            t.add_row("", "", "")
        t.add_row(f"[bold yellow]-- {cat_title} --[/bold yellow]", "", "", style="dim")
        for key, usage in items:
            if key in texts:
                t.add_row(f"  {texts[key]}", texts[key + '_desc'], f"cypherdna {usage}")

    console.print(t)

    if is_pt:
        console.print("\n[dim]Use [bold white]cypherdna <comando> --help[/bold white] para detalhes de cada comando.[/dim]")
        console.print("[dim]Idioma: [bold white]cypherdna lang pt|en[/bold white] para mudar o idioma permanentemente.[/dim]\n")
    else:
        console.print("\n[dim]Use [bold white]cypherdna <command> --help[/bold white] for details on each command.[/dim]")
        console.print("[dim]Language: [bold white]cypherdna lang pt|en[/bold white] to change language permanently.[/dim]\n")

    console.print("")


def start_progress_status(console_obj, label):
    """Inicia um status dinâmico com spinner."""
    global _active_status, _last_update_time
    if console_obj is None:
        console_obj = console
    if _active_status:
        _active_status.stop()

    _last_update_time = time.time()
    _active_status = console_obj.status(f" [bold cyan]>[/] [white]{label}[/white]", spinner="bouncingBar")
    _active_status.start()


def update_progress_status(current, total, label):
    """Atualiza a mensagem de status automaticamente com throttling de 0.1s."""
    global _active_status, _last_update_time
    if _active_status:
        now = time.time()
        if now - _last_update_time > 0.1:
            percent = (current / total) * 100 if total > 0 else 0
            _active_status.update(
                f" [bold cyan]>[/] [white]{label}[/white]: "
                f"[bold yellow]{percent:.0f}%[/bold yellow] "
                f"([dim]{current}/{total}[/dim])"
            )
            _last_update_time = now


def stop_progress_status():
    """Para o status e remove a linha do terminal."""
    global _active_status
    if _active_status:
        _active_status.stop()
        _active_status = None


def display_msg(label, text, level="info"):
    """Exibe mensagens em blocos profissionais e coloridos."""
    colors = {
        "info":    "bright_blue",
        "success": "bright_green",
        "warning": "yellow",
        "error":   "bright_red"
    }
    color = colors.get(level, "white")
    icons = {"info": "[i]", "success": "[+]", "warning": "[!]", "error": "[-]"}
    icon = icons.get(level, "*")

    prefix = f"[bold {color}]{icon} {label}[/bold {color}]"
    try:
        console.print(Panel(f"{text}", title=prefix, border_style=color, padding=(1, 2)))
    except UnicodeEncodeError:
        safe_icon = icons.get(level, "*")
        safe_prefix = f"[bold {color}]{safe_icon} {label}[/bold {color}]"
        console.print(Panel(f"{text}", title=safe_prefix, border_style=color, padding=(1, 2)))


def safe_open(filepath):
    """Abre um arquivo de forma cross-platform (Windows, Mac, Linux)."""
    import subprocess
    try:
        if sys.platform.startswith("win"):
            os.startfile(filepath)
        elif sys.platform.startswith("darwin"):
            subprocess.run(["open", filepath], check=False)
        else:
            subprocess.run(["xdg-open", filepath], check=False)
    except Exception as e:
        return e
    return None


def show_help_and_exit(ctx, param, value):
    """Callback para interceptar o --help / -h e mostrar o menu de ajuda customizado."""
    if value and not ctx.resilient_parsing:
        from config import get_saved_lang
        saved_lang = get_saved_lang()
        is_pt = (
            '-Pt' in sys.argv or '--portuguese' in sys.argv
            or (ctx.obj and isinstance(ctx.obj, dict) and ctx.obj.get('LANG_PT', False))
            or saved_lang == 'pt'
        )

        invoked_cmd = ctx.info_name
        if invoked_cmd and invoked_cmd != "cli":
            if display_command_help(invoked_cmd, is_pt=is_pt):
                ctx.exit()

        display_custom_help(is_pt=is_pt)
        ctx.exit()


def format_pattern(pattern_str):
    """Highlight DNA tokens with special colors for strategic overrides."""
    from rich.text import Text
    t = Text()
    parts = pattern_str.split("+")
    for i, p in enumerate(parts):
        u_p = p.upper().strip()
        if "@" in p or "0" in p:
            style = "bold italic bright_cyan"
        elif any(c.islower() for c in p):
            style = "bold italic green_yellow"
        else:
            color = "white"
            if u_p in ["NAME", "WORD"]: color = "green"
            elif u_p in ["YEAR", "DATE", "MONTH"]: color = "yellow"
            elif u_p in ["NUMBER"]: color = "blue"
            elif u_p in ["SYMBOL", "SEPARATOR"]: color = "magenta"
            elif u_p in ["REPEATED", "KEY_WALK"]: color = "red"
            style = f"bold {color}"
        
        t.append(p, style=style)
        if i < len(parts) - 1:
            t.append("+", style="bold white")
    return t


def get_preview_example(pat_str):
    """Generates a realistic example of the pattern for UI feedback."""
    map_vals = {
        "NAME": "target", "WORD": "secret", "YEAR": "2024", "DATE": "25",
        "MONTH": "May", "NUMBER": "123", "SYMBOL": "!", "SEPARATOR": ".",
        "REPEATED": "111", "KEY_WALK": "qwerty"
    }
    parts = pat_str.split("+")
    results = []
    for p in parts:
        u_p = p.upper().strip()
        clean_token = u_p.replace("@", "A").replace("0", "O")
        base_raw = map_vals.get(clean_token)
        
        if not base_raw:
            from config import CUSTOM_TOKENS_DIR
            t_path = os.path.join(CUSTOM_TOKENS_DIR, clean_token)
            if os.path.exists(t_path):
                txt_fs = [f for f in os.listdir(t_path) if f.lower().endswith(".txt")]
                if txt_fs:
                    try:
                        with open(os.path.join(t_path, txt_fs[0]), "r", encoding="utf-8", errors="ignore") as _ex_f:
                            base_raw = _ex_f.readline().strip() or clean_token.lower()
                    except Exception:
                        base_raw = clean_token.lower()
                else:
                    base_raw = clean_token.lower()
            else:
                base_raw = "???"
        if any(c.islower() for c in p):
            base_raw = base_raw.capitalize()
        if "@" in p:
            base_raw = base_raw.replace("a", "@").replace("A", "@")
        if "0" in p:
            base_raw = base_raw.replace("o", "0").replace("O", "0")
        results.append(base_raw)
    return "".join(results)


