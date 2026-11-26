import os
import sys
from fpdf import FPDF
from datetime import datetime

class CipherDNAReporter(FPDF):
    def __init__(self, is_pt=False):
        super().__init__()
        self.is_pt = is_pt
        self.font_family_main = 'Helvetica'
        self.font_family_mono = 'Courier'

    def header(self):
        # Professional Header with Dark Obsidian & Blood Red Accent
        if self.page_no() == 1:
            # Page 1: Full Banner Header (Height: 40mm)
            self.set_fill_color(11, 15, 25) # Dark Obsidian #0B0F19
            self.rect(0, 0, 210, 40, 'F')
            
            # Blood Red Accent Bar (2mm)
            self.set_fill_color(220, 38, 38) # Crimson Red #DC2626
            self.rect(0, 38, 210, 2, 'F')
            
            # Title Badge
            self.set_y(6)
            self.set_font(self.font_family_main, 'B', 18)
            self.set_text_color(255, 255, 255)
            title = 'CYPHERDNA INTELLIGENCE REPORT' if not self.is_pt else 'RELATÓRIO DE INTELIGÊNCIA CYPHERDNA'
            self.cell(0, 7, title, ln=True, align='C')
            
            self.set_font(self.font_family_main, 'B', 9)
            self.set_text_color(220, 38, 38)
            sub_tag = '[ RESTRICTED // FORENSIC AUDIT ]' if not self.is_pt else '[ RESTRITO // AUDITORIA FORENSE ]'
            self.cell(0, 5, sub_tag, ln=True, align='C')
            
            self.set_font(self.font_family_main, 'I', 8)
            self.set_text_color(160, 175, 200)
            subtitle = 'Advanced Password DNA Sequencing & Structural Vulnerability Analysis'
            if self.is_pt: subtitle = 'Sequenciamento Avançado de DNA & Análise de Vulnerabilidade Estrutural'
            self.cell(0, 5, subtitle, ln=True, align='C')
        else:
            # Page 2+: Slim Header (Height: 14mm)
            self.set_fill_color(11, 15, 25)
            self.rect(0, 0, 210, 14, 'F')
            self.set_fill_color(220, 38, 38)
            self.rect(0, 13, 210, 1, 'F')
            
            self.set_y(3)
            self.set_font(self.font_family_main, 'B', 9)
            self.set_text_color(255, 255, 255)
            self.cell(100, 8, '  CYPHERDNA AUDIT REPORT', 0, 0, 'L')
            self.set_font(self.font_family_main, 'I', 8)
            self.set_text_color(160, 175, 200)
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.cell(90, 8, f'Audit Timestamp: {date_str}  ', 0, 0, 'R')

    def footer(self):
        self.set_y(-16)
        self.set_draw_color(203, 213, 225) # Light gray border
        self.set_line_width(0.4)
        self.line(10, self.get_y(), 200, self.get_y())
        
        self.set_y(-12)
        self.set_font(self.font_family_main, 'I', 8)
        self.set_text_color(100, 116, 139)
        
        page_label = 'Page' if not self.is_pt else 'Página'
        gen_label = 'CipherDNA Cyber-Forensics Core v3.5.1 | Restricted Access' if not self.is_pt else 'Núcleo Forense CipherDNA v3.5.1 | Acesso Restrito'
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.cell(60, 6, f'[{date_str}]', 0, 0, 'L')
        self.cell(70, 6, gen_label, 0, 0, 'C')
        self.cell(60, 6, f'{page_label} {self.page_no()} / {{nb}}', 0, 0, 'R')

    def draw_section_header(self, title):
        self.set_font(self.font_family_main, 'B', 10)
        self.set_text_color(15, 23, 42)
        self.set_fill_color(241, 245, 249) # Subtle slate fill
        
        box_y = self.get_y()
        self.rect(10, box_y, 190, 8, 'F')
        self.set_fill_color(220, 38, 38)
        self.rect(10, box_y, 3, 8, 'F') # Left accent
        
        self.set_xy(16, box_y + 1)
        self.cell(180, 6, title, ln=True)
        self.set_y(box_y + 11)

    def create_report(self, password, dna_score, entropy, crack_times, dna_result, prevalence, output_path, token_weights=None, real_breach_count=0, breach_info=None):
        is_pt = self.is_pt
        self.token_weights = token_weights or {}
        self.alias_nb_pages()
        self.add_page()
        self.set_auto_page_break(auto=True, margin=18)
        
        # Explicit start position for Page 1 below header banner
        self.set_y(46)
        
        # --- 1. TARGET AUDIT HEADER ---
        self.draw_section_header('1. TARGET & SYSTEM AUDIT SUMMARY' if not is_pt else '1. AUDITORIA DO ALVO & SISMÉTRICA')
        
        box_y = self.get_y()
        box_h = 36
        self.set_fill_color(248, 250, 252) # Light gray background
        self.set_draw_color(226, 232, 240)
        self.rect(10, box_y, 190, box_h, 'DF')
        
        audit_id = f"CPH-{abs(hash(password)) % 1000000:06d}"
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Line 1: Target String & Audit Ref ID
        self.set_xy(14, box_y + 3)
        self.set_font(self.font_family_main, 'B', 8)
        self.set_text_color(100, 116, 139)
        self.cell(32, 5, 'Target String:' if not is_pt else 'Cadeia Analisada:')
        
        self.set_font(self.font_family_mono, 'B', 10)
        self.set_text_color(15, 23, 42)
        self.cell(85, 5, f'"{password}"')
        
        self.set_font(self.font_family_main, 'B', 8)
        self.set_text_color(100, 116, 139)
        self.cell(25, 5, 'Audit Ref ID:', align='R')
        self.set_font(self.font_family_mono, 'B', 9)
        self.set_text_color(220, 38, 38)
        self.cell(38, 5, audit_id, ln=True, align='R')
        
        # Line 2: DNA Topology (Full line width to avoid overlaps)
        self.set_xy(14, box_y + 11)
        self.set_font(self.font_family_main, 'B', 8)
        self.set_text_color(100, 116, 139)
        self.cell(32, 5, 'DNA Topology:' if not is_pt else 'Topologia DNA:')
        
        self.set_font(self.font_family_mono, 'B', 9)
        self.set_text_color(30, 41, 59)
        self.cell(148, 5, dna_result.pattern, ln=True)
        
        # Line 3: Timestamp & Engine Core
        self.set_xy(14, box_y + 19)
        self.set_font(self.font_family_main, 'B', 8)
        self.set_text_color(100, 116, 139)
        self.cell(32, 5, 'Timestamp:')
        
        self.set_font(self.font_family_main, '', 8)
        self.set_text_color(30, 41, 59)
        self.cell(85, 5, timestamp_str)

        self.set_font(self.font_family_main, 'B', 8)
        self.set_text_color(100, 116, 139)
        self.cell(25, 5, 'Engine Core:', align='R')
        self.set_font(self.font_family_main, '', 8)
        self.set_text_color(30, 41, 59)
        self.cell(38, 5, 'CipherDNA Core v3.5.1', ln=True, align='R')

        # Line 4: Classification
        self.set_xy(14, box_y + 27)
        self.set_font(self.font_family_main, 'B', 8)
        self.set_text_color(100, 116, 139)
        self.cell(32, 5, 'Classification:' if not is_pt else 'Classificação:')
        
        self.set_font(self.font_family_main, 'B', 8)
        self.set_text_color(220, 38, 38)
        self.cell(148, 5, 'RESTRICTED AUDIT REPORT' if not is_pt else 'RELATÓRIO DE AUDITORIA RESTRITO', ln=True)
        
        self.set_y(box_y + box_h + 5)
        
        # --- 2. FORENSIC METRICS CARDS (3 CARDS) ---
        self.draw_section_header('2. FORENSIC METRICS & RISK MATRIX' if not is_pt else '2. MÉTRICAS FORENSES E MATRIZ DE RISCO')
        
        metrics_y = self.get_y()
        card_w = 60
        card_h = 36
        
        # CARD 1: REALISM SCORE
        score_color = (22, 163, 74) if dna_score >= 0.05 else (220, 38, 38)
        self.set_fill_color(252, 252, 253)
        self.set_draw_color(226, 232, 240)
        self.rect(10, metrics_y, card_w, card_h, 'DF')
        
        self.set_xy(10, metrics_y + 3)
        self.set_font(self.font_family_main, 'B', 7.5)
        self.set_text_color(100, 116, 139)
        self.cell(card_w, 4, 'REALISM FACTOR (DNA SCORE)' if not is_pt else 'FATOR DE REALISMO (DNA SCORE)', align='C', ln=True)
        
        self.set_x(10)
        self.set_font(self.font_family_main, 'B', 15)
        self.set_text_color(*score_color)
        self.cell(card_w, 12, f'{dna_score:.6f}', align='C', ln=True)
        
        verdict = "HUMAN-LIKE PROFILE" if dna_score >= 0.05 else "SYNTHETIC / UNREALISTIC"
        if is_pt: verdict = "PERFIL HUMANO REALISTA" if dna_score >= 0.05 else "SINTÉTICO / IRREAL"
        
        self.set_fill_color(*score_color)
        self.set_text_color(255, 255, 255)
        self.set_font(self.font_family_main, 'B', 7)
        badge_w = 50
        self.set_x(10 + (card_w - badge_w) / 2)
        self.cell(badge_w, 5, verdict, fill=True, align='C', ln=True)

        # CARD 2: ENTROPY & BRUTEFORCE
        self.set_xy(75, metrics_y)
        self.set_fill_color(252, 252, 253)
        self.set_draw_color(226, 232, 240)
        self.rect(75, metrics_y, card_w, card_h, 'DF')
        
        self.set_xy(75, metrics_y + 3)
        self.set_font(self.font_family_main, 'B', 7.5)
        self.set_text_color(100, 116, 139)
        self.cell(card_w, 4, 'SHANNON ENTROPY' if not is_pt else 'ENTROPIA DE SHANNON', align='C', ln=True)
        
        self.set_x(75)
        self.set_font(self.font_family_main, 'B', 15)
        entropy_rgb = (22, 163, 74) if entropy > 60 else (217, 119, 6) if entropy > 40 else (220, 38, 38)
        self.set_text_color(*entropy_rgb)
        self.cell(card_w, 12, f'{int(entropy)} Bits', align='C', ln=True)
        
        self.set_x(75)
        self.set_font(self.font_family_main, '', 7)
        self.set_text_color(71, 85, 105)
        gpu_str = crack_times.get('rtx', 'Instant')
        self.cell(card_w, 4, f"RTX Cluster: {gpu_str}", align='C', ln=True)
        self.set_x(75)
        cpu_str = crack_times.get('pc', 'Instant')
        self.cell(card_w, 4, f"CPU Core: {cpu_str}", align='C', ln=True)

        # CARD 3: LEAK EXPOSURE
        self.set_xy(140, metrics_y)
        self.set_fill_color(252, 252, 253)
        self.set_draw_color(226, 232, 240)
        self.rect(140, metrics_y, card_w, card_h, 'DF')
        
        self.set_xy(140, metrics_y + 3)
        self.set_font(self.font_family_main, 'B', 7.5)
        self.set_text_color(100, 116, 139)
        self.cell(card_w, 4, 'BREACH INTELLIGENCE (HIBP)' if not is_pt else 'INTELIGÊNCIA DE VAZAMENTOS', align='C', ln=True)
        
        self.set_x(140)
        self.set_font(self.font_family_main, 'B', 14)
        leak_color = (220, 38, 38) if real_breach_count > 0 else (22, 163, 74)
        self.set_text_color(*leak_color)
        formatted_breach = f"{real_breach_count:,}".replace(",", ".") if is_pt else f"{real_breach_count:,}"
        leak_text = formatted_breach if real_breach_count > 0 else ("CLEAN" if not is_pt else "SEGURO")
        self.cell(card_w, 12, leak_text, align='C', ln=True)
        
        leak_status = "CRITICAL COMPROMISE" if real_breach_count > 1000 else "EXPOSED IN LEAKS" if real_breach_count > 0 else "NO DIRECT LEAKS"
        if is_pt: leak_status = "VAZAMENTO CRÍTICO" if real_breach_count > 1000 else "EXPOSTO EM LEAKS" if real_breach_count > 0 else "SEM REGISTRO DE LEAK"
        
        self.set_fill_color(*leak_color)
        self.set_text_color(255, 255, 255)
        self.set_font(self.font_family_main, 'B', 7)
        self.set_x(140 + (card_w - badge_w) / 2)
        self.cell(badge_w, 5, leak_status, fill=True, align='C', ln=True)

        self.set_y(metrics_y + card_h + 5)

        # --- 3. GENE ANATOMY & SEQUENCING ---
        self.draw_section_header('3. GENE SEQUENCING & ANATOMY' if not is_pt else '3. SEQUENCIAMENTO E ANATOMIA DE GENES')
        
        # Table Header
        header_h = 6.5
        self.set_fill_color(30, 41, 59) # Dark slate #1E293B
        self.set_text_color(255, 255, 255)
        self.set_font(self.font_family_main, 'B', 8.5)
        
        col_w = [15, 55, 60, 30, 30]
        cols = ['Pos', 'Gene (Category)', 'Extracted Value', 'Prob Weight', 'Risk Impact']
        if is_pt: cols = ['Pos', 'Gene (Categoria)', 'Valor Detectado', 'Peso Prob.', 'Nível Risco']
        
        for i in range(len(cols)):
            self.cell(col_w[i], header_h, cols[i], 1, 0, 'C', True)
        self.ln()

        # Table Body
        self.set_font(self.font_family_mono, '', 8.5)
        fill = False
        
        for token in dna_result.tokens:
            self.set_fill_color(248, 250, 252) if fill else self.set_fill_color(255, 255, 255)
            weight = self.token_weights.get(token.token_type, 0.0)
            weight_str = f"{weight:.3f}"
            
            # Risk impact calculation per token
            if weight > 0.3:
                r_impact = "CRITICAL" if not is_pt else "ALTO"
                r_color = (220, 38, 38)
            elif weight > 0.05:
                r_impact = "MODERATE" if not is_pt else "MÉDIO"
                r_color = (217, 119, 6)
            else:
                r_impact = "LOW" if not is_pt else "BAIXO"
                r_color = (22, 163, 74)

            self.set_text_color(15, 23, 42)
            self.cell(col_w[0], 6, str(token.position), 1, 0, 'C', fill)
            
            self.set_font(self.font_family_main, 'B', 8.5)
            self.set_text_color(30, 41, 59)
            self.cell(col_w[1], 6, token.token_type, 1, 0, 'C', fill)
            
            self.set_font(self.font_family_mono, 'B', 8.5)
            self.set_text_color(15, 23, 42)
            self.cell(col_w[2], 6, token.value, 1, 0, 'C', fill)
            
            self.set_font(self.font_family_mono, '', 8.5)
            self.set_text_color(71, 85, 105)
            self.cell(col_w[3], 6, weight_str, 1, 0, 'C', fill)
            
            self.set_font(self.font_family_main, 'B', 8)
            self.set_text_color(*r_color)
            self.cell(col_w[4], 6, r_impact, 1, 1, 'C', fill)
            fill = not fill
            
        self.ln(4)

        # --- 4. THREAT ANALYSIS & REMEDIATION ---
        self.draw_section_header('4. THREAT VECTORS & RECOMMENDED REMEDIATION' if not is_pt else '4. VETORES DE AMEAÇA E RECOMENDAÇÕES')
        
        box_y = self.get_y()
        
        # Risk level determination
        if real_breach_count > 0 or prevalence > 5:
            box_border = (220, 38, 38)
            box_bg = (254, 242, 242)
            risk_label = "CRITICAL RISK (IMMEDIATE COMPROMISE)" if not is_pt else "RISCO CRÍTICO (COMPROMETIMENTO IMEDIATO)"
        elif dna_score > 0.05:
            box_border = (217, 119, 6)
            box_bg = (255, 251, 235)
            risk_label = "MODERATE RISK (OSINT & PATTERN MUTATION)" if not is_pt else "RISCO MÉDIO (SUSCETÍVEL A OSINT & MUTAÇÃO)"
        else:
            box_border = (22, 163, 74)
            box_bg = (240, 253, 244)
            risk_label = "LOW RISK (HIGH STRUCTURAL COMPLEXITY)" if not is_pt else "RISCO BAIXO (ALTA COMPLEXIDADE ESTRUTURAL)"

        # Real statistics string construction
        if real_breach_count > 0:
            formatted_count = f"{real_breach_count:,}".replace(",", ".") if is_pt else f"{real_breach_count:,}"
            exposure_stat_pt = f"A senha exata foi identificada em {formatted_count} vazamentos reais verificados (HIBP)."
            exposure_stat_en = f"The exact password has been identified in {formatted_count} verified data breaches (HIBP)."
        elif breach_info and breach_info.get("count"):
            count_val = breach_info["count"]
            formatted_count = f"{count_val:,}".replace(",", ".") if is_pt else f"{count_val:,}"
            exposure_stat_pt = f"A topologia '{dna_result.pattern}' possui ~{formatted_count} ocorrências registradas na base forense de vazamentos."
            exposure_stat_en = f"The topology '{dna_result.pattern}' has ~{formatted_count} recorded occurrences in the forensic breach database."
        elif prevalence > 0.0001:
            exposure_stat_pt = f"A topologia '{dna_result.pattern}' aparece em cerca de {prevalence:.4f}% dos perfis em vazamentos globais."
            exposure_stat_en = f"The topology '{dna_result.pattern}' matches approximately {prevalence:.4f}% of profiles in global breaches."
        else:
            exposure_stat_pt = f"A topologia '{dna_result.pattern}' possui incidência estatística isolada (padrão estrutural customizado/raro)."
            exposure_stat_en = f"The topology '{dna_result.pattern}' represents a rare or custom structural pattern."

        # Text construction
        if is_pt:
            vector_text = (
                f"{exposure_stat_pt}\n\n"
                f"Principais Vetores de Ataque:\n"
                f"- Ataques de Dicionário Direcionado (Regras Hashcat/John The Ripper)\n"
                f"- Permutações Sintéticas baseadas em Cadeias de Markov\n"
                f"- Ataques de Engenharia Social (OSINT) direcionados aos tokens identificados\n\n"
                f"Recomendações Forenses:\n"
                f"1. Aumente o comprimento da senha para pelo menos 16 caracteres.\n"
                f"2. Evite combinar nomes pessoais com anos ou caracteres especiais previsíveis ao final.\n"
                f"3. Substitua tokens previsíveis por sequências pseudo-aleatórias descentralizadas."
            )
        else:
            vector_text = (
                f"{exposure_stat_en}\n\n"
                f"Primary Attack Surface Vectors:\n"
                f"- Targeted Dictionary Attacks (Hashcat/John The Ripper Rule Engines)\n"
                f"- Synthetic Permutations based on Markov Chain probability models\n"
                f"- OSINT Social Engineering attacks targeting extracted name/date tokens\n\n"
                f"Forensic Hardening Recommendations:\n"
                f"1. Increase total string length to at least 16 characters.\n"
                f"2. Avoid positioning personal names adjacent to years or standard trailing symbols.\n"
                f"3. Replace structural tokens with decentralized pseudo-random character sequences."
            )

        # Dynamic box height
        self.set_font(self.font_family_main, '', 8.5)
        lines_count = len(vector_text.split('\n')) + 5
        box_h = lines_count * 4.2
        
        if self.get_y() + box_h > 270:
            self.add_page()
            box_y = self.get_y()
            
        self.set_fill_color(*box_bg)
        self.set_draw_color(*box_border)
        self.rect(10, box_y, 190, box_h, 'DF')
        
        # Left Accent Border (Thick line)
        self.set_fill_color(*box_border)
        self.rect(10, box_y, 3, box_h, 'F')
        
        self.set_xy(15, box_y + 2.5)
        self.set_font(self.font_family_main, 'B', 9)
        self.set_text_color(*box_border)
        self.cell(180, 5, f"STATUS DE AMEAÇA: {risk_label}" if is_pt else f"THREAT LEVEL: {risk_label}", ln=True)
        
        self.set_x(15)
        self.set_font(self.font_family_main, '', 8.5)
        self.set_text_color(30, 41, 59)
        self.multi_cell(180, 4.2, vector_text)

        try:
            self.output(output_path)
            return True
        except Exception as e:
            print(f"Error saving PDF: {e}")
            return False

    def create_email_report(self, email, breach_data, output_path):
        is_pt = self.is_pt
        self.alias_nb_pages()
        self.add_page()
        self.set_auto_page_break(auto=True, margin=18)
        self.set_y(46)

        # 1. TARGET SUMMARY
        self.draw_section_header('1. TARGET & SYSTEM AUDIT SUMMARY' if not is_pt else '1. AUDITORIA DO ALVO & SISMÉTRICA')
        
        self.set_font(self.font_family_main, 'B', 8.5)
        self.set_text_color(100, 116, 139)
        self.cell(40, 5, 'AUDITED ACCOUNT:' if not is_pt else 'CONTA AUDITADA:', 0, 0)
        self.set_font(self.font_family_mono, 'B', 9)
        self.set_text_color(15, 23, 42)
        self.cell(70, 5, email, 0, 0)

        self.set_font(self.font_family_main, 'B', 8.5)
        self.set_text_color(100, 116, 139)
        self.cell(35, 5, 'AUDIT SCOPE:' if not is_pt else 'ESCOPO:', 0, 0)
        self.set_font(self.font_family_main, '', 8.5)
        self.set_text_color(15, 23, 42)
        scope_str = 'OSINT Threat & Leaks' if not is_pt else 'Inteligência Threat & Leaks'
        self.cell(45, 5, scope_str, 0, 1)

        self.set_font(self.font_family_main, 'B', 8.5)
        self.set_text_color(100, 116, 139)
        self.cell(40, 5, 'TIMESTAMP:' if not is_pt else 'DATA / HORA:', 0, 0)
        self.set_font(self.font_family_mono, '', 8.5)
        self.set_text_color(15, 23, 42)
        self.cell(70, 5, datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"), 0, 0)

        self.set_font(self.font_family_main, 'B', 8.5)
        self.set_text_color(100, 116, 139)
        self.cell(35, 5, 'ENGINE CORE:' if not is_pt else 'MOTOR FORENSE:', 0, 0)
        self.set_font(self.font_family_main, '', 8.5)
        self.set_text_color(15, 23, 42)
        self.cell(45, 5, 'CypherDNA v3.5.1', 0, 1)

        self.ln(4)

        # 2. STATUS CARDS
        self.draw_section_header('2. FORENSIC STATUS & RISK MATRIX' if not is_pt else '2. STATUS FORENSE & MATRIZ DE RISCO')
        
        card_w = 60
        card_h = 32
        metrics_y = self.get_y()
        exposed = breach_data.get("exposed", False)
        risk = breach_data.get("risk", "CLEAN")
        stealers = breach_data.get("stealers", [])
        hibp_breaches = breach_data.get("hibp_breaches", [])
        total_services = breach_data.get("total_services_exposed", 0)

        # CARD 1: OVERALL VERDICT
        self.set_xy(10, metrics_y)
        self.set_fill_color(252, 252, 253)
        self.set_draw_color(226, 232, 240)
        self.rect(10, metrics_y, card_w, card_h, 'DF')
        
        self.set_xy(10, metrics_y + 3)
        self.set_font(self.font_family_main, 'B', 7.5)
        self.set_text_color(100, 116, 139)
        self.cell(card_w, 4, 'THREAT LEVEL' if not is_pt else 'NÍVEL DE AMEAÇA', align='C', ln=True)
        
        self.set_x(10)
        self.set_font(self.font_family_main, 'B', 15)
        if risk == "CRITICAL":
            r_rgb = (220, 38, 38)
            r_text = "CRÍTICO" if is_pt else "CRITICAL"
        elif risk in ("HIGH", "MEDIUM"):
            r_rgb = (217, 119, 6)
            r_text = "ELEVADO" if is_pt else "HIGH"
        else:
            r_rgb = (22, 163, 74)
            r_text = "SEGURO" if is_pt else "CLEAN"
            
        self.set_text_color(*r_rgb)
        self.cell(card_w, 12, r_text, align='C', ln=True)
        
        self.set_fill_color(*r_rgb)
        self.set_text_color(255, 255, 255)
        self.set_font(self.font_family_main, 'B', 7)
        badge_w = 50
        self.set_x(10 + (card_w - badge_w) / 2)
        verdict = "EXPOSIÇÃO CONFIRMADA" if exposed and is_pt else "BREACH CONFIRMED" if exposed else "SEM REGISTRO" if is_pt else "NO LEAKS FOUND"
        self.cell(badge_w, 5, verdict, fill=True, align='C', ln=True)

        # CARD 2: INFOSTEALER MALWARE
        self.set_xy(75, metrics_y)
        self.set_fill_color(252, 252, 253)
        self.set_draw_color(226, 232, 240)
        self.rect(75, metrics_y, card_w, card_h, 'DF')
        
        self.set_xy(75, metrics_y + 3)
        self.set_font(self.font_family_main, 'B', 7.5)
        self.set_text_color(100, 116, 139)
        self.cell(card_w, 4, 'INFOSTEALER MALWARE' if not is_pt else 'MALWARE INFOSTEALER', align='C', ln=True)
        
        self.set_x(75)
        self.set_font(self.font_family_main, 'B', 15)
        st_color = (220, 38, 38) if len(stealers) > 0 else (22, 163, 74)
        self.set_text_color(*st_color)
        st_count_text = f"{len(stealers)} Host(s)" if not is_pt else f"{len(stealers)} Máquina(s)"
        self.cell(card_w, 12, st_count_text, align='C', ln=True)
        
        self.set_x(75)
        self.set_font(self.font_family_main, '', 7)
        self.set_text_color(71, 85, 105)
        serv_text = f"{total_services} Exposed Services" if not is_pt else f"{total_services} Serviços Comprometidos"
        self.cell(card_w, 4, serv_text, align='C', ln=True)
        self.set_x(75)
        sub_info = "Hudson Rock Cavalier OSINT"
        self.cell(card_w, 4, sub_info, align='C', ln=True)

        # CARD 3: WEB LEAKS (HIBP)
        self.set_xy(140, metrics_y)
        self.set_fill_color(252, 252, 253)
        self.set_draw_color(226, 232, 240)
        self.rect(140, metrics_y, card_w, card_h, 'DF')
        
        self.set_xy(140, metrics_y + 3)
        self.set_font(self.font_family_main, 'B', 7.5)
        self.set_text_color(100, 116, 139)
        self.cell(card_w, 4, 'WEB BREACHES (HIBP)' if not is_pt else 'VAZAMENTOS WEB (HIBP)', align='C', ln=True)
        
        self.set_x(140)
        self.set_font(self.font_family_main, 'B', 15)
        hibp_color = (220, 38, 38) if len(hibp_breaches) > 0 else (22, 163, 74) if breach_data.get("hibp_configured") else (100, 116, 139)
        self.set_text_color(*hibp_color)
        hibp_text = f"{len(hibp_breaches)} Leaks" if breach_data.get("hibp_configured") else ("OFFLINE" if is_pt else "STANDBY")
        self.cell(card_w, 12, hibp_text, align='C', ln=True)
        
        self.set_fill_color(*hibp_color)
        self.set_text_color(255, 255, 255)
        self.set_font(self.font_family_main, 'B', 7)
        self.set_x(140 + (card_w - badge_w) / 2)
        hibp_status = "KEY ATIVA" if breach_data.get("hibp_configured") and is_pt else "KEY ACTIVE" if breach_data.get("hibp_configured") else "SEM CHAVE" if is_pt else "NO API KEY"
        self.cell(badge_w, 5, hibp_status, fill=True, align='C', ln=True)

        self.set_y(metrics_y + card_h + 5)

        # 3. INFOSTEALER DETAILS
        self.draw_section_header('3. INFECTED SYSTEMS & INFOSTEALER TELEMETRY' if not is_pt else '3. SISTEMAS INFECTADOS & TELEMETRIA INFOSTEALER')
        
        if stealers:
            self.set_fill_color(30, 41, 59)
            self.set_text_color(255, 255, 255)
            self.set_font(self.font_family_main, 'B', 8)
            col_w = [38, 37, 25, 60, 30]
            headers = ['COMPUTADOR / HOST', 'SISTEMA OPERACIONAL', 'DATA', 'CAMINHO DO MALWARE', 'SERVIÇOS'] if is_pt else ['COMPUTER / HOST', 'OPERATING SYSTEM', 'DATE', 'MALWARE PATH', 'SERVICES']
            for i, h in enumerate(headers):
                self.cell(col_w[i], 6, h, 0, 0, 'C' if i in (2, 4) else 'L', fill=True)
            self.ln()

            self.set_font(self.font_family_mono, '', 7.5)
            for idx, s in enumerate(stealers):
                fill = (idx % 2 == 1)
                self.set_fill_color(248, 250, 252) if fill else self.set_fill_color(255, 255, 255)
                self.set_text_color(15, 23, 42)
                
                c_name = s.get('computer_name', '')[:20]
                os_str = s.get('operating_system', '')[:20]
                date_str = s.get('date_compromised', '')[:10]
                m_path = s.get('malware_path', '')
                if len(m_path) > 35: m_path = "..." + m_path[-32:]
                srv_str = str(s.get('total_services', 0))

                self.cell(col_w[0], 5.5, f" {c_name}", 0, 0, 'L', fill=fill)
                self.cell(col_w[1], 5.5, f" {os_str}", 0, 0, 'L', fill=fill)
                self.cell(col_w[2], 5.5, date_str, 0, 0, 'C', fill=fill)
                self.cell(col_w[3], 5.5, f" {m_path}", 0, 0, 'L', fill=fill)
                self.cell(col_w[4], 5.5, srv_str, 0, 1, 'C', fill=fill)
            self.ln(3)
        else:
            self.set_font(self.font_family_main, 'I', 8.5)
            self.set_text_color(100, 116, 139)
            msg_clean = "Nenhum computador infectado por malware infostealer associado a este e-mail." if is_pt else "No computer infected with infostealer malware associated with this email."
            self.cell(190, 6, msg_clean, ln=True)
            self.ln(2)

        # 4. HIBP BREACHES DETAILS (If any)
        if hibp_breaches:
            self.draw_section_header('4. HISTORICAL WEB BREACHES (HIBP)' if not is_pt else '4. VAZAMENTOS WEB HISTÓRICOS (HIBP)')
            self.set_fill_color(30, 41, 59)
            self.set_text_color(255, 255, 255)
            self.set_font(self.font_family_main, 'B', 8)
            col_b = [50, 45, 30, 65]
            b_headers = ['INCIDENTE / FONTE', 'DOMÍNIO', 'DATA', 'DADOS COMPROMETIDOS'] if is_pt else ['BREACH SOURCE', 'DOMAIN', 'DATE', 'COMPROMISED DATA']
            for i, h in enumerate(b_headers):
                self.cell(col_b[i], 6, h, 0, 0, 'C' if i == 2 else 'L', fill=True)
            self.ln()

            self.set_font(self.font_family_mono, '', 7.5)
            for idx, b in enumerate(hibp_breaches):
                fill = (idx % 2 == 1)
                self.set_fill_color(248, 250, 252) if fill else self.set_fill_color(255, 255, 255)
                self.set_text_color(15, 23, 42)
                
                b_name = b.get('name', '')[:25]
                b_dom = b.get('domain', '')[:22]
                b_dt = b.get('breach_date', '')[:10]
                b_dc = ", ".join(b.get('data_classes', []))
                if len(b_dc) > 38: b_dc = b_dc[:35] + "..."

                self.cell(col_b[0], 5.5, f" {b_name}", 0, 0, 'L', fill=fill)
                self.cell(col_b[1], 5.5, f" {b_dom}", 0, 0, 'L', fill=fill)
                self.cell(col_b[2], 5.5, b_dt, 0, 0, 'C', fill=fill)
                self.cell(col_b[3], 5.5, f" {b_dc}", 0, 1, 'L', fill=fill)
            self.ln(3)

        # 5. FORENSIC RECOMMENDATIONS
        sec_num = '5' if hibp_breaches else '4'
        self.draw_section_header(f'{sec_num}. INCIDENT RESPONSE & MITIGATION ACTIONS' if not is_pt else f'{sec_num}. AÇÕES FORENSES DE RESPOSTA A INCIDENTES')
        
        box_y = self.get_y()
        self.set_fill_color(254, 242, 242) if exposed else self.set_fill_color(240, 253, 244)
        box_border = (220, 38, 38) if exposed else (22, 163, 74)
        self.set_draw_color(*box_border)
        
        recs = []
        if exposed:
            if is_pt:
                recs.append("1. REVOGAÇÃO IMEDIATA: Encerre todas as sessões ativas (Google, navegadores, bancos, e-mails).")
                recs.append("2. ROTAÇÃO DE SENHAS: Troque as senhas de todas as contas salvas nos navegadores das máquinas infectadas.")
                recs.append("3. HIGIENIZAÇÃO DE TERMINAL: Os computadores listados foram comprometidos por infostealers e exigem varredura completa.")
                recs.append("4. MFA/2FA FORTE: Ative autenticação de dois fatores com aplicativo autenticador ou chave física.")
            else:
                recs.append("1. IMMEDIATE REVOCATION: Terminate all active browser and cloud sessions (Google, banking, corporate).")
                recs.append("2. CREDENTIAL ROTATION: Reset passwords for all services stored in browsers on compromised machines.")
                recs.append("3. ENDPOINT SANITIZATION: The listed machines were infected with infostealers and require deep cleanup.")
                recs.append("4. ENFORCE MFA: Activate hardware or app-based two-factor authentication (avoid SMS).")
        else:
            if is_pt:
                recs.append("1. MONITORAMENTO: Nenhuma credencial associada a infostealers foi detectada.")
                recs.append("2. BOAS PRÁTICAS: Mantenha senhas complexas e verifique periodicamente sua integridade com CypherDNA.")
            else:
                recs.append("1. CONTINUOUS MONITORING: Zero infostealer infections detected for this identity.")
                recs.append("2. BEST PRACTICES: Maintain strong unique passwords and audit periodically.")

        rec_h = 8 + (len(recs) * 5)
        self.rect(10, box_y, 190, rec_h, 'DF')
        self.set_xy(15, box_y + 3)
        self.set_font(self.font_family_main, 'B', 8.5)
        self.set_text_color(*box_border)
        self.cell(180, 5, "PLANO DE RESPOSTA RECOMENDADO:" if is_pt else "RECOMMENDED INCIDENT ACTION PLAN:", ln=True)
        
        self.set_font(self.font_family_main, '', 8)
        self.set_text_color(30, 41, 59)
        for r in recs:
            self.set_x(15)
            self.cell(180, 4.5, r, ln=True)

        try:
            self.output(output_path)
            return True
        except Exception as e:
            print(f"Error saving Email PDF: {e}")
            return False

def generate_pdf_report(password, dna_score, entropy, crack_times, dna_result, prevalence, filename, is_pt=False, token_weights=None, real_breach_count=0, breach_info=None):
    pdf = CipherDNAReporter(is_pt=is_pt)
    return pdf.create_report(
        password, dna_score, entropy, crack_times, dna_result, prevalence, filename,
        token_weights=token_weights, real_breach_count=real_breach_count, breach_info=breach_info
    )

def generate_email_pdf_report(email, breach_data, filename, is_pt=False):
    pdf = CipherDNAReporter(is_pt=is_pt)
    return pdf.create_email_report(email, breach_data, filename)
