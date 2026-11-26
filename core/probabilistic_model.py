import os
import json
from datetime import datetime
from dataclasses import dataclass, field
from collections import Counter
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

# ==========================================
# TEXTOS BILÍNGUES (Inglês / Português)
# ==========================================
TEXTS = {
    "en": {
        "msg_loading": "Loading dataset: {file}",
        "msg_no_files": "[yellow]Warning: No JSON datasets found in '{folder}'. The model will return 0 probabilities.[/yellow]",
        "msg_processed": "[bold green]Successfully processed {count} JSON datasets.[/bold green]",
        "err_invalid_json": "[red]Error decoding JSON in {file}: {err}[/red]"
    },
    "pt": {
        "msg_loading": "Carregando dataset: {file}",
        "msg_no_files": "[yellow]Aviso: Nenhum dataset JSON encontrado na pasta '{folder}'. O modelo retornará probabilidades zeradas.[/yellow]",
        "msg_processed": "[bold green]Processado com sucesso {count} datasets JSON.[/bold green]",
        "err_invalid_json": "[red]Erro ao decodificar JSON em {file}: {err}[/red]"
    }
}

from config import TRAINER_DIR


def resolve_trainer_file(query: str = None, data_folder: str = TRAINER_DIR, is_pt: bool = False) -> str:
    """
    Resolves user trainer dataset input.
    - If query is None, empty, or 'SELECT_MENU', displays an interactive menu.
    - If query matches a file in data_folder, returns it.
    - If query is a short keyword (e.g. 'rockyou', 'cars'), searches for matching files
      and selects the most recently modified one.
    """
    if not os.path.exists(data_folder):
        return None

    all_files = [f for f in os.listdir(data_folder) if f.endswith('.json')]
    if not all_files:
        return None

    # Group files by base dataset name, picking the latest mtime for each unique dataset prefix
    # e.g. resultado_Cars_20260806_140106.json -> base "Cars"
    dataset_groups = {}
    for f in all_files:
        mtime = os.path.getmtime(os.path.join(data_folder, f))
        parts = f.replace("resultado_", "").replace(".json", "").split("_")
        base_name = parts[0] if parts else f
        if base_name not in dataset_groups or mtime > dataset_groups[base_name][0]:
            dataset_groups[base_name] = (mtime, f)

    # Sorted latest entries by base name
    latest_files = sorted(dataset_groups.values(), key=lambda x: x[0], reverse=True)

    def show_interactive_menu() -> str:
        console.print(Panel("[bold cyan]Datasets de Treinamento Disponíveis[/bold cyan]" if is_pt else "[bold cyan]Available Trainer Datasets[/bold cyan]", expand=False))
        
        for idx, (mtime, f_name) in enumerate(latest_files, 1):
            time_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            clean_name = f_name.replace("resultado_", "").replace(".json", "").split("_")[0]
            console.print(f"  [bold yellow][{idx}][/bold yellow] [bold white]{clean_name}[/bold white] [dim]({f_name} • {time_str})[/dim]")
            
        prompt_msg = "\n[bold green]Digite o número do dataset desejado[/bold green]" if is_pt else "\n[bold green]Enter dataset number[/bold green]"
        choice = Prompt.ask(prompt_msg, default="1")
        
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(latest_files):
                selected = latest_files[choice_idx][1]
                console.print(f"[bold green]✔ Dataset selecionado:[/bold green] [cyan]{selected}[/cyan]\n")
                return selected
        except Exception:
            pass
            
        selected = latest_files[0][1]
        console.print(f"[bold green]✔ Dataset selecionado (padrão):[/bold green] [cyan]{selected}[/cyan]\n")
        return selected

    if not query or str(query).upper() in ["SELECT_MENU", "MENU", "?", "TRUE", "NONE"]:
        return show_interactive_menu()

    raw_query = str(query).strip()

    # Exact filename match
    if os.path.exists(os.path.join(data_folder, raw_query)):
        return raw_query
        
    target = raw_query if raw_query.endswith(".json") else raw_query + ".json"
    if os.path.exists(os.path.join(data_folder, target)):
        return target

    # Fuzzy search across all files in data_folder
    q_lower = raw_query.lower()
    matching_files = []
    for f in all_files:
        if q_lower in f.lower():
            mtime = os.path.getmtime(os.path.join(data_folder, f))
            matching_files.append((mtime, f))

    if matching_files:
        matching_files.sort(key=lambda x: x[0], reverse=True)
        selected_file = matching_files[0][1]
        clean_label = selected_file.replace("resultado_", "").replace(".json", "").split("_")[0]
        console.print(f"[bold green]✔ Dataset encontrado para '{raw_query}':[/bold green] [cyan]{selected_file}[/cyan] [dim]({clean_label})[/dim]")
        return selected_file

    # If no match found, fall back to interactive menu
    console.print(f"[yellow][!] Dataset '{raw_query}' não encontrado. Escolha uma opção abaixo:[/yellow]" if is_pt else f"[yellow][!] Dataset '{raw_query}' not found. Select an option below:[/yellow]")
    return show_interactive_menu()


@dataclass
class ProbabilisticModel:
    """
    Calcula a probabilidade de cada tipo de token e de cada padrão estrutural
    a partir dos datasets JSON gerados pelo trainer.py (contagem -> frequência relativa).
    """
    
    # Target folder to pull datasets
    data_folder: str = TRAINER_DIR
    
    # Internal frequency accumulators (raw counts)
    total_passwords_analyzed: int = 0
    total_tokens_mapped: int = 0
    
    _token_raw_counts: Counter = field(default_factory=Counter)
    _pattern_raw_counts: Counter = field(default_factory=Counter)
    _transition_raw_counts: Counter = field(default_factory=Counter) # NOVO

    # Built Probability Mappings
    token_probabilities: dict = field(default_factory=dict)
    pattern_probabilities: dict = field(default_factory=dict)
    transition_probabilities: dict = field(default_factory=dict) # NOVO

    def _get_txt(self, key, is_pt=False, **kwargs):
        """Helper for localized Rich terminal prints."""
        lang = "pt" if is_pt else "en"
        return TEXTS[lang].get(key, "").format(**kwargs)

    # ---------------------------------------------------------
    # 1️⃣ LEITURA E ABSORÇÃO DOS DADOS
    # ---------------------------------------------------------
    def load_jsons(self, is_pt=False, specific_file: str = None):
        """
        Reads JSON statistic files. 
        If specific_file is provided, it resolves it (fuzzy search or menu) and ONLY loads that file.
        Otherwise, it loads ALL .json files in the folder.
        """
        if not os.path.exists(self.data_folder):
            console.print(self._get_txt("msg_no_files", is_pt=is_pt, folder=self.data_folder))
            return

        if specific_file:
            resolved = resolve_trainer_file(specific_file, data_folder=self.data_folder, is_pt=is_pt)
            json_files = [resolved] if resolved else []
        else:
            json_files = [f for f in os.listdir(self.data_folder) if f.endswith('.json')]
        
        if not json_files:
            console.print(self._get_txt("msg_no_files", is_pt=is_pt, folder=self.data_folder))
            return

        loaded_count = 0
        for j_file in json_files:
            filepath = os.path.join(self.data_folder, j_file)
            
            if not os.path.exists(filepath):
                if specific_file:
                    console.print(f"[red]Error:[/red] Trainer file '{j_file}' not found in '{self.data_folder}'.")
                continue
            
            # (Optional) Log the dataset being absorbed
            # console.print(self._get_txt("msg_loading", is_pt=is_pt, file=j_file))
            
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # 1. Aggregate Metadata
                    metadata = data.get("metadata", {})
                    self.total_passwords_analyzed += metadata.get("total_passwords_analyzed", 0)
                    self.total_tokens_mapped += metadata.get("total_tokens_mapped", 0)
                    
                    # 2. Aggregate Tokens
                    tokens = data.get("token_frequencies", {})
                    for tok_type, count in tokens.items():
                        self._token_raw_counts[tok_type] += count
                        
                    # 3. Aggregate Patterns
                    patterns = data.get("pattern_frequencies", {})
                    for pat_type, count in patterns.items():
                        self._pattern_raw_counts[pat_type] += count
                        
                    # 4. Aggregate Transitions (Markov)
                    transitions = data.get("token_transitions", {})
                    for trans_ext, count in transitions.items():
                        self._transition_raw_counts[trans_ext] += count
                    
                    loaded_count += 1
                        
            except json.JSONDecodeError as e:
                console.print(self._get_txt("err_invalid_json", is_pt=is_pt, file=j_file, err=str(e)))

        if loaded_count > 0:
            console.print(self._get_txt("msg_processed", is_pt=is_pt, count=loaded_count))


    # ---------------------------------------------------------
    # 2️⃣ CONSTRUÇÃO DA DISTRIBUIÇÃO MATEMÁTICA (Probabilidades)
    # ---------------------------------------------------------
    def calculate_probabilities(self):
        """
        Transforms raw frequencies into realistic floating-point probabilities (0.0 to 1.0).
        P(token) = token_occurrences / total_tokens
        P(pattern) = pattern_occurrences / total_passwords
        """
        
        # Guard clause against zero division models
        if self.total_tokens_mapped == 0 or self.total_passwords_analyzed == 0:
            return

        # Token Probability Distribution
        self.token_probabilities.clear()
        for tok_type, count in self._token_raw_counts.items():
            prob = count / self.total_tokens_mapped
            self.token_probabilities[tok_type] = round(prob, 4)

        # Pattern Probability Distribution
        self.pattern_probabilities.clear()
        for pat_type, count in self._pattern_raw_counts.items():
            prob = count / self.total_passwords_analyzed
            self.pattern_probabilities[pat_type] = round(prob, 4)

        # Transition Probability Distribution (Markov Chain)
        self.transition_probabilities.clear()
        for trans_ext, count in self._transition_raw_counts.items():
            # A probabilidade de Y sabendo que é X, P(Y|X) = Count(X->Y) / Count(X)
            try:
                base_token = trans_ext.split("->")[0]
                base_token_count = self._token_raw_counts.get(base_token, 0)
                if base_token_count > 0:
                    prob = count / base_token_count
                    self.transition_probabilities[trans_ext] = round(prob, 4)
            except Exception:
                pass


    # ---------------------------------------------------------
    # 3️⃣ INTERFACE E EXPOSIÇÃO PÚBLICA (Consultas)
    # ---------------------------------------------------------
    def get_token_probability(self, token_type: str) -> float:
        """
        Retorna a probabilidade matemática do Gen.py encontrar/utilizar este Token (ex: 'YEAR').
        Retorna 0.0 caso o token nunca tenha sido catalogado nos Datasets.
        """
        return self.token_probabilities.get(token_type.upper(), 0.0)

    def get_pattern_probability(self, pattern_signature: str) -> float:
        """
        Retorna a probabilidade matemática de uma determinada assinatura estrutural 
        (ex: 'NAME+YEAR+SYMBOL') ocorrer naturalmente baseada nos alvos.
        """
        return self.pattern_probabilities.get(pattern_signature.upper(), 0.0)

    def get_transition_probability(self, token_a: str, token_b: str) -> float:
        """
        [Cadeia de Markov] Retorna a probabilidade P(B|A): Qual a chance do Token B aparecer logo após o Token A?
        """
        return self.transition_probabilities.get(f"{token_a.upper()}->{token_b.upper()}", 0.0)

    def has_trained_data(self) -> bool:
        """Indica se há estatísticas reais carregadas de datasets do Trainer."""
        return bool(
            self.pattern_probabilities
            or self.token_probabilities
            or self.transition_probabilities
        )

    def print_top_tokens(self, limit: int = 5):
        """Prints the Top N most highly probable tokens observed."""
        console.print(f"\n[bold cyan]--- Top {limit} Most Probable Tokens ---[/bold cyan]")
        sorted_tokens = sorted(self.token_probabilities.items(), key=lambda x: x[1], reverse=True)
        for t_type, prob in sorted_tokens[:limit]:
            console.print(f"🔹 {t_type:<10} => {prob:.2%}")

    def print_top_patterns(self, limit: int = 5):
        """Prints the Top N most highly probable architectural patterns observed."""
        console.print(f"\n[bold magenta]--- Top {limit} Struct Patterns ---[/bold magenta]")
        sorted_patterns = sorted(self.pattern_probabilities.items(), key=lambda x: x[1], reverse=True)
        for pat, prob in sorted_patterns[:limit]:
            console.print(f"🔸 {pat:<20} => {prob:.2%}")


# ==========================================
# TESTE / EXEMPLO DE USO ISOLADO (Sandbox)
# ==========================================
if __name__ == "__main__":
    console.print("\n[bold cyan]🧪 Probabilistic Model Engine Sandbox[/bold cyan]\n")
    
    # 1. Instanciar apontando para a pasta local dos datasets do Trainer
    current_dir = os.path.dirname(__file__)
    target_dir = os.path.join(current_dir, "data", "trainer_data")
    if not os.path.exists(target_dir):
        target_dir = os.path.join(current_dir, "trainer_data")
    
    engine = ProbabilisticModel(data_folder=target_dir)
    
    # 2. Absorver todo o aprendizado JSON (Em PT-BR para teste)
    engine.load_jsons(is_pt=True)
    
    # 3. Rodar os cálculos de range matemático
    engine.calculate_probabilities()
    
    # 4. Validar e consumir as interfaces públicas
    engine.print_top_tokens()
    engine.print_top_patterns()
    
    # Exemplo: Como o Gen.py consumirá isso futuramente para pontuar um range
    # ex_score = base_score * engine.get_token_probability("NAME")
    print(f"\n> Example direct call P(YEAR) = {engine.get_token_probability('YEAR')}")
