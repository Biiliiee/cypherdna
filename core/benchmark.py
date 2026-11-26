import os
import json
import csv
import math
import click
from dataclasses import dataclass, field
from collections import Counter
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
import webbrowser

from dna_parser import parse_password
from probabilistic_model import ProbabilisticModel

console = Console()

import sys
from config import setup_environment, WORDLISTS_DIR, REPORTS_DIR, YOU_WORDLIST_DIR
from i18n import BENCHMARK_TEXTS as TEXTS
from ui_utils import show_help_and_exit

setup_environment()

@dataclass
class WordlistMetrics:
    """Stores the evaluation metrics for a single wordlist."""
    name: str = ""
    total_passwords: int = 0
    total_tokens: int = 0
    average_score: float = 0.0
    std_deviation: float = 0.0
    
    token_frequencies: dict = field(default_factory=dict)
    pattern_frequencies: dict = field(default_factory=dict)
    top_pattern: str = ""
    top_passwords_dna: list = field(default_factory=list) # List of (password, score, dna_list)


class Benchmark:
    """
    Automatic Benchmark Engine.
    Evaluates generated wordlists against realistic probability models.
    """
    
    def __init__(self, model: ProbabilisticModel, is_pt: bool = False):
        self.model = model
        self.is_pt = is_pt
        self.results: dict[str, WordlistMetrics] = {}

    def _get_txt(self, key, **kwargs):
        """Helper for localized texts."""
        lang = "pt" if self.is_pt else "en"
        return TEXTS[lang].get(key, "").format(**kwargs)

    # ---------------------------------------------------------
    # 1️⃣ CÁLCULO DE SCORE INDIVIDUAL
    # ---------------------------------------------------------
    def get_token_forensic_weight(self, token_type: str) -> float:
        """
        Retorna o peso forense de previsibilidade humana de um token.
        Tokens críticos como WEAK_WORD e KEY_WALK possuem máxima previsibilidade.
        """
        SPECIAL_WEIGHTS = {
            "WEAK_WORD": 0.95,
            "KEY_WALK": 0.90,
            "REPEATED": 0.85,
            "YEAR": 0.75,
            "DATE": 0.70,
            "MONTH": 0.60,
        }
        if token_type in SPECIAL_WEIGHTS:
            return SPECIAL_WEIGHTS[token_type]

        p = self.model.get_token_probability(token_type)
        return p if p > 0 else 0.05

    def calculate_password_score(self, password: str) -> float:
        """
        Calcula o Score DNA de realismo/previsibilidade humana de uma senha.
        Senhas humanas (palavras comuns, datas, sequências) -> Score Alto (Realista).
        Senhas geradas por computador/aleatórias (alta fragmentação) -> Score Baixo (Sintético).
        """
        try:
            dna = parse_password(password)
        except Exception:
            return 0.0

        if not dna.tokens:
            return 0.0

        t_weights = [self.get_token_forensic_weight(t.token_type) for t in dna.tokens]
        avg_weight = sum(t_weights) / len(t_weights)

        # Probabilidade do padrão estrutural
        norm_pat = dna.pattern.replace("WEAK_WORD", "WORD").replace("KEY_WALK", "NUMBER")
        pat_prob = max(
            self.model.get_pattern_probability(dna.pattern),
            self.model.get_pattern_probability(norm_pat)
        )

        # Penalidade por fragmentação aleatória sintética (ex: xK9mQ2zL8 -> 6 blocos alternados)
        frag_factor = 1.0
        if len(dna.tokens) > 3:
            frag_factor = 1.0 / (1.0 + (len(dna.tokens) - 3) * 0.75)

        score = (avg_weight * (1.0 + pat_prob * 12.0)) * frag_factor
        return round(score, 5)

    # ---------------------------------------------------------
    # 2️⃣ AVALIAÇÃO DE LOTE (WORDLIST)
    # ---------------------------------------------------------
    def evaluate_wordlist(self, filepath: str):
        """
        Reads a wordlist, scores every password against the ProbabilisticModel,
        and aggregates standard metrics.
        """
        target_path = filepath
        if not os.path.exists(target_path):
            lookup = os.path.join(WORDLISTS_DIR, filepath)
            if os.path.exists(lookup):
                target_path = lookup
            else:
                lookup_out = os.path.join(YOU_WORDLIST_DIR, filepath)
                if os.path.exists(lookup_out):
                    target_path = lookup_out
                else:
                    console.print(self._get_txt("err_not_found", file=filepath))
                    return
            
        filename = os.path.basename(target_path)
        console.print(self._get_txt("evaluating", file=filename))
        
        n = 0
        mean = 0.0
        m2 = 0.0
        token_counter = Counter()
        pattern_counter = Counter()
        total_tokens = 0
        top_passwords = [] # List of (score, password, dna)
        
        from ui_utils import start_progress_status, update_progress_status, stop_progress_status
        file_size = os.path.getsize(target_path)
        eval_label = self._get_txt("evaluating", file="").strip()
        
        start_progress_status(console, f"{eval_label} {filename}")

        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            while True:
                line = f.readline()
                if not line:
                    break
                    
                update_progress_status(f.tell(), file_size, f"{eval_label} {filename}")
                
                pwd = line.strip()
                if not pwd:
                    continue
                    
                # Calculate Score
                score = self.calculate_password_score(pwd)
                
                # Iterative Mean and Variance (Welford's Algorithm)
                n += 1
                delta = score - mean
                mean += delta / n
                delta2 = score - mean
                m2 += delta * delta2
                
                # DNA Stats
                try:
                    dna = parse_password(pwd)
                    pattern_counter[dna.pattern] += 1
                    for token in dna.tokens:
                        token_counter[token.token_type] += 1
                        total_tokens += 1
                    
                    # Manter Top 3 senhas (mais realistas)
                    top_passwords.append((score, pwd, dna))
                    top_passwords.sort(key=lambda x: x[0], reverse=True)
                    top_passwords = top_passwords[:3]
                except Exception:
                    pass
                    
        stop_progress_status()

        # Aggregate Metrics
        if n == 0:
            return
            
        avg_score = mean
        variance = m2 / n
        std_dev = math.sqrt(variance)
        
        top_pattern = pattern_counter.most_common(1)[0][0] if pattern_counter else "UNKNOWN"
        
        
        # Calculate Human-like classification based on an arbitrary threshold or top pattern validity
        # Assuming a wordlist with score > 0.05 is decent in a real probabilistic sample
        is_human = avg_score > 0.05
        
        metrics = WordlistMetrics(
            name=filename,
            total_passwords=n,
            total_tokens=total_tokens,
            average_score=round(avg_score, 4),
            std_deviation=round(std_dev, 4),
            token_frequencies=dict(token_counter.most_common(10)),
            pattern_frequencies=dict(pattern_counter.most_common(5)),
            top_pattern=top_pattern,
            top_passwords_dna=[
                {
                    "password": p[1],
                    "score": p[0],
                    "tokens": [{"val": t.value, "type": t.token_type} for t in p[2].tokens]
                }
                for p in top_passwords
            ]
        )
        
        # Injetar o campo no tempo de analise caso precise para display 
        setattr(metrics, "is_human", is_human)
        self.results[filename] = metrics


    # ---------------------------------------------------------
    # 3️⃣ INTERFACE DE CONSULTA / IMPRESSÃO (Ranking)
    # ---------------------------------------------------------
    def print_report(self):
        """Prints a visual comparison table of evaluated wordlists."""
        if not self.results:
            return
            
        title_txt = self._get_txt('title')
        console.print(f"\n[bold white on red] {title_txt} [/bold white on red]\n")
        
        # Sort by best average score descending
        sorted_results = sorted(self.results.values(), key=lambda x: x.average_score, reverse=True)
        
        table = Table(title=self._get_txt("summary_title"), header_style="bold white", border_style="red")
        table.add_column("Rank", justify="center", style="bold red")
        table.add_column(self._get_txt("col_list"), style="white")
        table.add_column(self._get_txt("col_score"), justify="right", style="bold red")
        table.add_column("Std Dev", justify="right", style="dim")
        table.add_column(self._get_txt("col_pattern"), style="yellow")
        table.add_column(self._get_txt("col_class"), justify="center")
        
        for rank, metrics in enumerate(sorted_results, 1):
            class_label = getattr(metrics, "is_human", False)
            class_str = self._get_txt("class_human") if class_label else self._get_txt("class_unreal")
            
            table.add_row(
                f"#{rank}",
                metrics.name,
                f"{metrics.average_score:.4f}",
                f"{metrics.std_deviation:.4f}",
                metrics.top_pattern,
                class_str
            )
            
        console.print(table)


    # ---------------------------------------------------------
    # 4️⃣ EXPORTAÇÃO
    # ---------------------------------------------------------
    def export_report(self, format_type: str = "json", output_file: str = "benchmark_report"):
        """Exports the ranking and detailed metrics to JSON or CSV."""
        if not self.results:
            return
            
        sorted_results = sorted(self.results.values(), key=lambda x: x.average_score, reverse=True)
        # Prevent Directory Traversal
        output_file = os.path.basename(output_file)
        
        if format_type.lower() == "json":
            out_file = os.path.join(REPORTS_DIR, f"{output_file}.json")
            export_data = {
                "ranking": [
                    {
                        "rank": i+1,
                        "wordlist": m.name,
                        "average_score": m.average_score,
                        "std_deviation": m.std_deviation,
                        "total_passwords": m.total_passwords,
                        "top_pattern": m.top_pattern,
                        "pattern_frequencies": m.pattern_frequencies,
                        "token_frequencies": m.token_frequencies
                    } for i, m in enumerate(sorted_results)
                ]
            }
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=4)
                
            console.print(self._get_txt("export_success", file=out_file))
            
        elif format_type.lower() == "csv":
            out_file = os.path.join(REPORTS_DIR, f"{output_file}.csv")
            with open(out_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Rank", "Wordlist", "Avg_Score", "Std_Dev", "Total_Pwd", "Top_Pattern"])
                for i, m in enumerate(sorted_results):
                    writer.writerow([i+1, m.name, m.average_score, m.std_deviation, m.total_passwords, m.top_pattern])
                    
            console.print(self._get_txt("export_success", file=out_file))

        elif format_type.lower() == "html":
            out_file = os.path.join(REPORTS_DIR, f"{output_file}.html")
            
            cards_html = ""
            for i, m in enumerate(sorted_results):
                status_color = "#22c55e" if m.is_human else "#ff1f1f"
                if self.is_pt:
                    status_text = "HUMANO REALISTA" if m.is_human else "PADRÃO SINTÉTICO"
                else:
                    status_text = "HUMAN-LIKE" if m.is_human else "UNREALISTIC"
                
                # Gera HTML para as Top Senhas (Explorer)
                top_pwd_html = ""
                
                # Gera dados JSON seguros para os gráficos em JS
                t_lbls = json.dumps(list(m.token_frequencies.keys()))
                t_vals = json.dumps(list(m.token_frequencies.values()))
                p_lbls = json.dumps(list(m.pattern_frequencies.keys()))
                p_vals = json.dumps(list(m.pattern_frequencies.values()))
                for pwd_data in m.top_passwords_dna:
                    tokens_html = "".join([f'<span class="token-tag" data-type="{t["type"]}">{t["val"]}</span>' for t in pwd_data["tokens"]])
                    top_pwd_html += f"""
                    <div class="explorer-item">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; gap: 10px;">
                            <code style="color: #fff; font-size: 1rem; letter-spacing: 1px; word-break: break-all;">{pwd_data["password"]}</code>
                            <span style="color: var(--primary); font-size: 0.75rem; font-weight: 800; white-space: nowrap;">{pwd_data["score"]:.4f}</span>
                        </div>
                        <div class="token-row">
                            {tokens_html}
                        </div>
                    </div>
                    """

                cards_html += f"""
                <div class="card">
                    <div class="card-header">
                        <div>
                            <span class="rank">{"Rank de Análise" if self.is_pt else "Analysis Rank"} #{i+1}</span>
                            <h2>{m.name}</h2>
                        </div>
                        <span class="badge" style="background: {status_color}15; color: {status_color}; border: 1px solid {status_color}30;">{status_text}</span>
                    </div>

                    <div class="main-score-box">
                        <span class="metric-label">{"DNA Score Médio" if self.is_pt else "Average DNA Score"}</span>
                        <div class="score-val">{m.average_score:.4f}</div>
                    </div>

                    <div class="metrics-grid">
                        <div class="metric">
                            <span class="metric-label">{"Total de Senhas" if self.is_pt else "Total Passwords"}</span>
                            <div class="metric-val">{m.total_passwords}</div>
                        </div>
                        <div class="metric">
                            <span class="metric-label">{"Desvio Padrão" if self.is_pt else "Std Deviation"}</span>
                            <div class="metric-val">{m.std_deviation:.4f}</div>
                        </div>
                    </div>

                    <div class="pattern-box">
                        <span class="metric-label" style="color: rgba(255,255,255,0.4)">{"Padrão Estrutural Dominante" if self.is_pt else "Dominant Structural Pattern"}</span>
                        <div style="margin-top: 10px; font-weight: 600;">{m.top_pattern}</div>
                    </div>

                    <button class="explore-btn" onclick="toggleExplorer(this)">{"EXPLORAR ESTRUTURA DNA" if self.is_pt else "EXPLORE DNA STRUCTURE"}</button>
                    
                    <div class="explorer-section" style="display: none;">
                        <div style="height: 1px; background: rgba(255,255,255,0.05); margin: 20px 0;"></div>
                        
                        <!-- NOVO: DASHBOARD ANALYTICO DE GRÁFICOS -->
                        <div class="chart-container-row">
                            <div class="chart-box">
                                <h4>{"Frequência de Genes" if self.is_pt else "Gene Frequency"}</h4>
                                <div style="position: relative; height: 200px; width: 100%;">
                                    <canvas id="chart_t_{i}"></canvas>
                                </div>
                            </div>
                            <div class="chart-box">
                                <h4>{"Distribuição de Estruturas" if self.is_pt else "Structure Distribution"}</h4>
                                <div style="position: relative; height: 200px; width: 100%;">
                                    <canvas id="chart_p_{i}"></canvas>
                                </div>
                            </div>
                        </div>

                        <!-- SCRIPT INJETADO POR CARD -->
                        <script>
                            setTimeout(() => {{
                                new Chart(document.getElementById('chart_t_{i}'), {{
                                    type: 'doughnut',
                                    data: {{ labels: {t_lbls}, datasets: [{{ data: {t_vals}, backgroundColor: ['#ff1f1f', '#facc15', '#22c55e', '#4facfe', '#a855f7'], borderWidth: 0 }}] }},
                                    options: {{ 
                                        maintainAspectRatio: false,
                                        plugins: {{ legend: {{ position: 'bottom', labels: {{color: '#fff', font: {{size: 10}}, boxWidth: 15}} }} }}, 
                                        cutout: '70%' 
                                    }}
                                }});
                                new Chart(document.getElementById('chart_p_{i}'), {{
                                    type: 'bar',
                                    data: {{ labels: {p_lbls}, datasets: [{{ label: 'Occurrences', data: {p_vals}, backgroundColor: '#ff1f1f', borderRadius: 4 }}] }},
                                    options: {{ 
                                        indexAxis: 'y', 
                                        maintainAspectRatio: false,
                                        scales: {{ 
                                            x: {{ display: false }}, 
                                            y: {{ grid: {{ display: false }}, ticks: {{ color: '#a0a0a0', font: {{ size: 8 }}, autoSkip: false }} }} 
                                        }}, 
                                        plugins: {{ legend: {{display: false}} }} 
                                    }}
                                }});
                            }}, 100);
                        </script>
                        
                        <h4 style="font-size: 0.7rem; color: var(--dim-text); margin-bottom: 15px; text-transform: uppercase; letter-spacing: 2px;">{"Principais Candidatos" if self.is_pt else "Top Realistic Candidates"}</h4>
                        {top_pwd_html}
                    </div>
                </div>
                """

            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>CipherDNA - Intelligence Report</title>
                <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <style>
                    :root {{
                        --primary: #ff2a51;
                        --primary-glow: rgba(255, 42, 81, 0.45);
                        --secondary: #990022;
                        --bg: #030004;
                        --card-bg: rgba(13, 2, 6, 0.9);
                        --text: #ffffff;
                        --dim-text: #b8a6ac;
                    }}
                    * {{ box-sizing: border-box; }}
                    body {{
                        background-color: #030004;
                        background-image: 
                            radial-gradient(circle at 50% 5%, rgba(255, 30, 70, 0.22) 0%, transparent 45%),
                            radial-gradient(circle at 10% 20%, rgba(160, 10, 40, 0.15) 0%, transparent 35%),
                            radial-gradient(circle at 90% 30%, rgba(255, 40, 80, 0.12) 0%, transparent 40%),
                            radial-gradient(ellipse at 50% 100%, rgba(20, 0, 5, 0.8) 0%, #030004 100%);
                        background-attachment: fixed;
                        color: var(--text);
                        font-family: 'Outfit', sans-serif;
                        margin: 0;
                        padding: 60px 20px;
                        min-height: 100vh;
                        scroll-behavior: smooth;
                    }}
                    .container {{ max-width: 1300px; margin: 0 auto; }}
                    
                    /* HEADER - LIMPO & ESPACIAL (LETRAS BRANCAS, SEM GLOW) */
                    .header {{
                        text-align: center;
                        margin-bottom: 75px;
                        position: relative;
                        padding: 30px 20px 10px;
                    }}
                    
                    h1 {{
                        font-size: 4.2rem;
                        color: #ffffff;
                        background: none;
                        -webkit-text-fill-color: #ffffff;
                        margin: 10px 0 8px;
                        letter-spacing: -1px;
                        font-weight: 700;
                        position: relative;
                        z-index: 1;
                        text-shadow: none;
                        filter: none;
                    }}
                    .subtitle {{
                        color: #ffffff;
                        font-size: 0.85rem;
                        letter-spacing: 4px;
                        text-transform: uppercase;
                        font-weight: 600;
                        text-shadow: none;
                        position: relative;
                        z-index: 1;
                        margin-top: 4px;
                        display: inline-flex;
                        align-items: center;
                        gap: 15px;
                        opacity: 0.9;
                    }}
                    .subtitle::before, .subtitle::after {{
                        content: '';
                        display: inline-block;
                        width: 30px;
                        height: 1px;
                        background: linear-gradient(to right, transparent, rgba(255, 255, 255, 0.4));
                    }}
                    .subtitle::after {{
                        background: linear-gradient(to left, transparent, rgba(255, 255, 255, 0.4));
                    }}
                    
                    /* INTERACTION: Search Bar - Cosmic Glass Capsule */
                    .search-box {{
                        margin: 38px auto 0;
                        max-width: 520px;
                        position: relative;
                        z-index: 1;
                    }}
                    .search-box::before {{
                        content: '✦';
                        position: absolute;
                        left: 22px;
                        top: 50%;
                        transform: translateY(-50%);
                        color: rgba(255, 255, 255, 0.55);
                        font-size: 0.85rem;
                        pointer-events: none;
                        z-index: 2;
                    }}
                    .search-box input {{
                        width: 100%;
                        background: rgba(20, 4, 8, 0.6);
                        border: 1px solid rgba(255, 255, 255, 0.15);
                        padding: 16px 25px 16px 48px;
                        border-radius: 40px;
                        color: #ffffff;
                        font-size: 1.05rem;
                        font-family: inherit;
                        outline: none;
                        transition: all 0.3s ease;
                        backdrop-filter: blur(15px);
                        -webkit-backdrop-filter: blur(15px);
                        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.5);
                    }}
                    .search-box input::placeholder {{
                        color: rgba(255, 255, 255, 0.5);
                        font-weight: 300;
                        letter-spacing: 0.5px;
                    }}
                    .search-box input:hover {{
                        border-color: rgba(255, 255, 255, 0.3);
                        background: rgba(26, 6, 10, 0.75);
                    }}
                    .search-box input:focus {{
                        border-color: rgba(255, 255, 255, 0.6);
                        background: rgba(30, 8, 14, 0.85);
                        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
                    }}

                    /* NOVO: Estilos do Dashboard */
                    .chart-container-row {{
                        display: flex; gap: 20px; margin-bottom: 30px;
                        flex-wrap: wrap;
                    }}
                    .chart-box {{
                        flex: 1; min-width: 250px;
                        background: rgba(0,0,0,0.3); padding: 20px;
                        border-radius: 15px; border: 1px solid rgba(255,255,255,0.05);
                    }}
                    .chart-box h4 {{
                        font-size: 0.7rem; color: var(--dim-text); text-transform: uppercase; margin-top: 0; margin-bottom: 15px; letter-spacing: 1.5px;
                    }}

                    .grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                        gap: 30px;
                    }}
                    .card {{
                        background: var(--card-bg);
                        border: 1px solid rgba(255,255,255,0.05);
                        padding: 40px;
                        border-radius: 40px;
                        position: relative;
                        overflow: hidden;
                        transition: all 0.5s cubic-bezier(0.19, 1, 0.22, 1);
                        animation: fadeIn 0.8s ease-out forwards;
                    }}
                    @keyframes fadeIn {{
                        from {{ opacity: 0; transform: translateY(30px); }}
                        to {{ opacity: 1; transform: translateY(0); }}
                    }}

                    .card:hover {{
                        transform: translateY(-15px);
                        border-color: var(--primary-glow);
                        box-shadow: 0 30px 60px rgba(0,0,0,0.6), 0 0 20px rgba(255,31,31,0.1);
                    }}
                    .card::before {{
                        content: '';
                        position: absolute;
                        top: 0; left: 0; width: 100%; height: 5px;
                        background: linear-gradient(to right, var(--secondary), var(--primary));
                        opacity: 0.5;
                    }}

                    .card-header {{ display: flex; justify-content: space-between; align-items: center; gap: 15px; }}
                    .rank {{ color: var(--primary); font-weight: 700; font-size: 0.9rem; text-transform: uppercase; }}
                    .card h2 {{ font-size: 1.6rem; margin: 8px 0; word-break: break-all; flex: 1; }}
                    
                    .badge {{
                        padding: 6px 14px;
                        border-radius: 10px;
                        font-size: 0.75rem;
                        font-weight: 800;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                        white-space: nowrap;
                        display: inline-flex;
                        align-items: center;
                        height: fit-content;
                    }}

                    .main-score-box {{
                        margin: 30px 0;
                        background: rgba(255,255,255,0.02);
                        padding: 20px;
                        border-radius: 20px;
                        border: 1px dashed rgba(255,255,255,0.1);
                    }}
                    .score-val {{
                        font-size: 4rem;
                        font-weight: 800;
                        color: #fff;
                        margin: 0;
                        line-height: 1;
                        background: linear-gradient(135deg, #fff, #ff7e7e);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                    }}

                    .metrics-grid {{
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 20px;
                    }}
                    .metric {{ display: flex; flex-direction: column; gap: 5px; }}
                    .metric-label {{ color: var(--dim-text); font-size: 0.7rem; text-transform: uppercase; font-weight: 600; }}
                    .metric-val {{ font-size: 1.1rem; font-weight: 600; }}

                    .pattern-box {{
                        margin-top: 30px;
                        padding: 15px;
                        background: #000;
                        border-radius: 15px;
                        border: 1px solid rgba(255,31,31,0.2);
                        font-family: 'Courier New', monospace;
                        font-size: 0.9rem;
                        color: #ff7e7e;
                        word-break: break-all;
                        overflow-wrap: break-word;
                    }}

                    /* EXPLORER STYLES */
                    .explore-btn {{
                        width: 100%;
                        margin-top: 25px;
                        background: transparent;
                        border: 1px solid var(--primary);
                        color: var(--primary);
                        padding: 14px;
                        border-radius: 20px;
                        font-family: inherit;
                        font-weight: 700;
                        font-size: 0.8rem;
                        letter-spacing: 1px;
                        cursor: pointer;
                        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    }}
                    .explore-btn:hover {{
                        background: var(--primary);
                        color: #fff;
                        box-shadow: 0 0 20px var(--primary-glow);
                        transform: scale(1.02);
                    }}
                    .explorer-item {{
                        background: rgba(255,255,255,0.03);
                        padding: 18px;
                        border-radius: 20px;
                        margin-bottom: 15px;
                        border: 1px solid rgba(255,255,255,0.02);
                        transition: all 0.3s;
                    }}
                    .explorer-item:hover {{
                        background: rgba(255,255,255,0.06);
                        border-color: rgba(255,255,255,0.1);
                    }}
                    .token-row {{
                        display: flex;
                        flex-wrap: wrap;
                        gap: 8px;
                        margin-top: 12px;
                    }}
                    .token-tag {{
                        font-size: 0.65rem;
                        padding: 4px 10px;
                        border-radius: 8px;
                        background: rgba(0,0,0,0.3);
                        color: var(--dim-text);
                        border: 1px solid rgba(255,255,255,0.1);
                        font-weight: 600;
                        text-transform: uppercase;
                    }}
                    .token-tag[data-type="NAME"] {{ color: #4facfe; border-color: #4facfe66; }}
                    .token-tag[data-type="YEAR"] {{ color: #22c55e; border-color: #22c55e66; }}
                    .token-tag[data-type="KEY_WALK"] {{ color: #facc15; border-color: #facc1566; }}
                    .token-tag[data-type="WORD"] {{ color: #a855f7; border-color: #a855f766; }}
                    .token-tag[data-type="NUMBER"] {{ color: #fb923c; border-color: #fb923c66; }}


                    /* Responsive */
                    @media (max-width: 600px) {{
                        h1 {{ font-size: 2.5rem; }}
                        .grid {{ grid-template-columns: 1fr; }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">

                        <h1>{"Análise CipherDNA" if self.is_pt else "CipherDNA Analysis"}</h1>
                        <p class="subtitle">{"Inteligência Forense Avançada" if self.is_pt else "Advanced Forensic Intelligence"}</p>
                        
                        <div class="search-box">
                            <input type="text" id="searchInput" placeholder='{"Filtrar wordlists..." if self.is_pt else "Filter wordlists..."}' onkeyup="filterCards()">
                        </div>
                    </div>

                    <div class="grid" id="reportGrid">
                        {cards_html}
                    </div>

                </div>

                <script>
                    function filterCards() {{
                        const input = document.getElementById('searchInput');
                        const filter = input.value.toLowerCase();
                        const grid = document.getElementById('reportGrid');
                        const cards = grid.getElementsByClassName('card');

                        for (let i = 0; i < cards.length; i++) {{
                            const title = cards[i].getElementsByTagName('h2')[0].innerText.toLowerCase();
                            if (title.indexOf(filter) > -1) {{
                                cards[i].style.display = "";
                                cards[i].style.animation = "fadeIn 0.5s ease-out forwards";
                            }} else {{
                                cards[i].style.display = "none";
                            }}
                        }}
                    }}

                    function toggleExplorer(btn) {{
                        const section = btn.nextElementSibling;
                            if (section.style.display === "none") {{
                                section.style.display = "block";
                                section.style.animation = "fadeIn 0.4s ease-out forwards";
                                btn.innerText = '{"FECHAR EXPLORER" if self.is_pt else "CLOSE EXPLORER"}';
                                btn.style.background = "rgba(255, 31, 31, 0.1)";
                            }} else {{
                                section.style.display = "none";
                                btn.innerText = '{"EXPLORAR ESTRUTURA DNA" if self.is_pt else "EXPLORE DNA STRUCTURE"}';
                                btn.style.background = "transparent";
                            }}
                    }}
                </script>
            </body>
            </html>
            """
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            console.print(self._get_txt("export_success", file=out_file))


# ==========================================
# CLI MANUAL SUPPORT
# ==========================================
@click.command(add_help_option=False)
@click.option('-h', '--help', is_flag=True, is_eager=True, expose_value=False, callback=show_help_and_exit)
@click.argument("comparators", nargs=-1, required=True)
@click.option('-f', '--format', 'format_type', default='none',
              type=click.Choice(['json', 'csv', 'html', 'none']))
@click.option('-o', '--output', 'output_file', default='benchmark_report')
@click.option('-OH', '--output-html', is_flag=True)
@click.pass_context
def benchmark_cmd(ctx, comparators, format_type, output_file, output_html):
    """
    Manual Benchmark Analyzer for CipherDNA.
    Pass one or multiple wordlist files to compare and rank.
    Usage: cypherdna comparator file1.txt file2.txt
    """
    is_pt = ctx.obj.get('LANG_PT', False) if (ctx and ctx.obj) else False
    title = " CIPHERDNA - MANUAL BENCHMARK " if not is_pt else " CIPHERDNA - BENCHMARK MANUAL "
    console.print(f"\n[bold white on red] {title} [/bold white on red]\n")

    # 1. Start probability engine
    model = ProbabilisticModel()
    model.load_jsons()
    model.calculate_probabilities()
    
    # 2. Start evaluator
    bench = Benchmark(model, is_pt=is_pt)
    
    # Suporta tanto espaços quanto vírgulas:
    # cypherdna comparator a.txt b.txt   → comparators = ('a.txt', 'b.txt')
    # cypherdna comparator a.txt,b.txt   → comparators = ('a.txt,b.txt',)
    wordlist_list = []
    for item in comparators:
        # Se um dos itens contém vírgula, expande
        for part in item.split(","):
            part = part.strip().lstrip("=")
            if part:
                wordlist_list.append(part)
    
    for wordlist in wordlist_list:
        bench.evaluate_wordlist(wordlist)
    
    # 3. Present Results
    bench.print_report()
    
    # 4. Export if requested
    final_output = output_file
    final_format = format_type
    
    if output_html:
        final_format = "html"

    if final_format != 'none':
        bench.export_report(final_format, final_output)
        
        if output_html:
            report_path = os.path.join(REPORTS_DIR, f"{final_output}.html")
            if os.path.exists(report_path):
                msg = "Deseja abrir o relatório no navegador?" if is_pt else "Do you want to open the report in the browser?"
                if click.confirm(msg, default=True):
                    webbrowser.open(os.path.abspath(report_path))

if __name__ == "__main__":
    benchmark_cmd()