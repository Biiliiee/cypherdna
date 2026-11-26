"""
CypherDNA Breach Intelligence Engine
- check_pattern_exposure: Checks structural DNA against common leak patterns
- check_password_breach: Real-time HIBP k-Anonymity check for exact password (100% free, zero cloud leak)
- check_email_breach: HIBP email check (live with HIBP_API_KEY or offline incident reference)
"""

import json
import os
import hashlib
import requests

try:
    from config import DATA_DIR, get_saved_hibp_key
    BREACH_FILE = os.path.join(DATA_DIR, "breach_data.json")
except Exception:
    try:
        from core.config import DATA_DIR, get_saved_hibp_key
        BREACH_FILE = os.path.join(DATA_DIR, "breach_data.json")
    except Exception:
        BREACH_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "breach_data.json")
        def get_saved_hibp_key():
            return os.environ.get("HIBP_API_KEY", "").strip()



def load_breach_data():
    if not os.path.exists(BREACH_FILE):
        return {"breach_patterns": [], "breach_source_stats": {}}

    try:
        with open(BREACH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"breach_patterns": [], "breach_source_stats": {}}


def check_pattern_exposure(pattern_signature):
    """
    Verifica se o padrão de DNA de uma senha já apareceu em grandes vazamentos.
    """
    data = load_breach_data()
    for item in data.get("breach_patterns", []):
        if item.get("pattern") == pattern_signature:
            return item
    return None


def check_password_breach(password):
    """
    Verifica se a senha exata já vazou usando a API HaveIBeenPwned (k-Anonymity).
    Privacidade total: a senha nunca sai do PC, apenas o prefixo de 5 caracteres do hash SHA-1.
    """
    if not password:
        return 0

    sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix = sha1_hash[:5]
    suffix = sha1_hash[5:]

    url = f"https://api.pwnedpasswords.com/range/{prefix}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return 0

        # O formato da resposta é 'SUFIXO:CONTAGEM'
        for line in response.text.splitlines():
            parts = line.split(':')
            if len(parts) == 2 and parts[0] == suffix:
                return int(parts[1])
    except Exception:
        pass

    return 0


def check_email_breach(email):
    """
    Verifica exposição forense de e-mail combinando:
    1. Hudson Rock Cavalier OSINT (Detecção de Infostealers e Máquinas Infectadas) - 100% Gratuito e em tempo real.
    2. HaveIBeenPwned API v3 (Grandes Vazamentos Web Históricos) - Ativo se HIBP_API_KEY estiver configurada.
    """
    email_clean = email.strip()
    sources = []
    stealers = []
    hibp_breaches = []
    total_services = 0
    hibp_error = None
    hibp_configured = False

    # 1. Inteligência de Infostealers (Hudson Rock Cavalier OSINT)
    try:
        hr_url = f"https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-email?email={email_clean}"
        hr_resp = requests.get(hr_url, timeout=7, headers={"User-Agent": "CypherDNA-OSINT-Probe"})
        if hr_resp.status_code == 200:
            hr_data = hr_resp.json()
            raw_stealers = hr_data.get("stealers", [])
            for s in raw_stealers:
                s_corp = s.get("total_corporate_services", 0)
                s_user = s.get("total_user_services", 0)
                total_services += (s_corp + s_user)
                c_name = s.get("computer_name", "Unknown Host")
                date_c = s.get("date_compromised", "")[:10]
                stealers.append({
                    "computer_name": c_name,
                    "operating_system": s.get("operating_system", "Unknown OS"),
                    "date_compromised": date_c,
                    "malware_path": s.get("malware_path", "").strip(),
                    "antiviruses": s.get("antiviruses", []),
                    "ip": s.get("ip", "Unknown"),
                    "total_services": s_corp + s_user,
                    "top_passwords": [p for p in s.get("top_passwords", []) if p],
                    "top_logins": [l for l in s.get("top_logins", []) if l]
                })
                sources.append(f"Infostealer: {c_name} ({date_c})")
    except Exception:
        pass

    # 2. HIBP API v3 (Grandes Vazamentos Web)
    api_key = get_saved_hibp_key()
    if api_key:
        hibp_configured = True
        headers = {
            "hibp-api-key": api_key,
            "user-agent": "CypherDNA-Forensic-Engine"
        }
        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email_clean}?truncateResponse=false"
        try:
            resp = requests.get(url, headers=headers, timeout=6)
            if resp.status_code == 200:
                breaches = resp.json()
                for b in breaches:
                    b_title = b.get("Title", b.get("Name", "Unknown Source"))
                    hibp_breaches.append({
                        "name": b_title,
                        "domain": b.get("Domain", ""),
                        "breach_date": b.get("BreachDate", ""),
                        "pwn_count": b.get("PwnCount", 0),
                        "data_classes": b.get("DataClasses", [])
                    })
                    sources.append(f"HIBP: {b_title}")
            elif resp.status_code == 404:
                # E-mail limpo no HIBP
                pass
            elif resp.status_code == 401:
                hibp_error = "API Key HIBP inválida ou expirada (HTTP 401)."
            elif resp.status_code == 429:
                hibp_error = "Limite de taxa HIBP excedido (Rate Limit HTTP 429)."
            else:
                hibp_error = f"Erro HIBP HTTP {resp.status_code}"
        except Exception as e:
            hibp_error = f"Falha de conexão HIBP: {str(e)}"

    exposed = (len(stealers) > 0) or (len(hibp_breaches) > 0)

    # Classificação de Risco Forense
    if len(stealers) > 0 and total_services >= 20:
        risk = "CRITICAL"
    elif len(stealers) > 0 or len(hibp_breaches) >= 3:
        risk = "HIGH"
    elif len(hibp_breaches) > 0:
        risk = "MEDIUM"
    else:
        risk = "CLEAN"

    data = load_breach_data()
    return {
        "email": email_clean,
        "exposed": exposed,
        "risk": risk,
        "sources": sources,
        "stealers": stealers,
        "hibp_breaches": hibp_breaches,
        "total_services_exposed": total_services,
        "hibp_configured": hibp_configured,
        "hibp_error": hibp_error,
        "offline_info": not exposed and not hibp_configured,
        "known_stats": data.get("breach_source_stats", {})
    }
