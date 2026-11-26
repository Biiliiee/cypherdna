#!/usr/bin/env python3
"""
CypherDNA Secret Vault - Servidor com Páginas Separadas:
- http://localhost:5000/login  -> Portal de Login do Desafiante (Seu Painel)
- http://localhost:5000/admin  -> Painel do Administrador / Vítima (Configurar Senha & Prêmio)
"""

import sys
import os
import json
import time
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import webbrowser

PORT = 5000
TARGET_DATA = {
    "username": "admin",
    "password": "xbox360",
    "secret_reward": "🏆 PARABÉNS! VOCÊ É O MESTRE DO CYPHERDNA! (Palavra Surpresa: CYPER_LEGEND_2026)",
    "attempts": 0,
    "last_attempt": "",
    "last_time": None,
    "cracked": False,
    "cracked_password": None,
    "unlocked_by_user": False,
    "history": []
}

# -------------------------------------------------------------------------
# HTML 1: PORTAL DE LOGIN DO DESAFIANTE (http://localhost:5000/login)
# -------------------------------------------------------------------------
LOGIN_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CypherDNA - Portal do Desafiante</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600;700&family=Inter:wght@300;400;600;700;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-deep: #060913;
            --bg-card: rgba(15, 23, 42, 0.85);
            --border-glow: rgba(56, 189, 248, 0.25);
            --cyan-glow: #06b6d4;
            --emerald-glow: #10b981;
            --rose-glow: #f43f5e;
            --gold-glow: #fbbf24;
            --text-main: #f8fafc;
            --text-dim: #94a3b8;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', sans-serif; }

        body {
            background-color: var(--bg-deep);
            background-image: 
                radial-gradient(circle at 30% 20%, rgba(6, 182, 212, 0.12) 0%, transparent 45%),
                radial-gradient(circle at 70% 80%, rgba(251, 191, 36, 0.08) 0%, transparent 45%),
                linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
            background-size: 100% 100%, 100% 100%, 40px 40px, 40px 40px;
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 2.5rem 1rem;
        }

        .header { text-align: center; margin-bottom: 2rem; }

        .logo-tag {
            display: inline-flex; align-items: center; gap: 0.5rem;
            background: rgba(6, 182, 212, 0.12);
            border: 1px solid rgba(6, 182, 212, 0.4);
            color: var(--cyan-glow);
            padding: 0.4rem 1.2rem; border-radius: 999px;
            font-size: 0.85rem; font-weight: 700;
            letter-spacing: 1px; text-transform: uppercase;
            margin-bottom: 0.75rem;
            box-shadow: 0 0 20px rgba(6, 182, 212, 0.25);
        }

        h1 {
            font-size: 2.3rem; font-weight: 900;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }

        p.subtitle { color: var(--text-dim); font-size: 0.95rem; }

        .container {
            width: 100%; max-width: 1050px;
            display: grid; grid-template-columns: 1fr 1fr; gap: 2rem;
        }

        @media (max-width: 850px) { .container { grid-template-columns: 1fr; } }

        .card {
            background: var(--bg-card); backdrop-filter: blur(16px);
            border: 1px solid var(--border-glow); border-radius: 16px;
            padding: 2rem; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.45);
            position: relative; overflow: hidden;
        }

        .card::before {
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, transparent, var(--cyan-glow), transparent);
        }

        .card-title {
            font-size: 1.2rem; font-weight: 700; display: flex; align-items: center;
            justify-content: space-between; margin-bottom: 1.5rem;
            padding-bottom: 0.75rem; border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }

        .form-group { margin-bottom: 1.25rem; }
        label { display: block; font-size: 0.85rem; font-weight: 600; color: var(--text-dim); margin-bottom: 0.5rem; text-transform: uppercase; }
        input {
            width: 100%; background: rgba(10, 15, 30, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 8px;
            padding: 0.85rem 1rem; color: #fff; font-size: 1rem;
            font-family: 'Fira Code', monospace; transition: all 0.2s ease;
        }
        input:focus { outline: none; border-color: var(--cyan-glow); box-shadow: 0 0 12px rgba(6, 182, 212, 0.3); }

        .btn {
            width: 100%; padding: 0.95rem; border: none; border-radius: 8px;
            font-weight: 700; font-size: 0.95rem; cursor: pointer;
            transition: all 0.2s ease; display: flex; align-items: center;
            justify-content: center; gap: 0.5rem; text-transform: uppercase;
        }

        .btn-gold {
            background: linear-gradient(135deg, var(--gold-glow), #d97706); color: #000;
            box-shadow: 0 4px 15px rgba(251, 191, 36, 0.3);
        }
        .btn-gold:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(251, 191, 36, 0.5); }
        .btn-danger { background: rgba(244, 63, 94, 0.15); border: 1px solid rgba(244, 63, 94, 0.3); color: var(--rose-glow); margin-top: 0.75rem; }

        .vault-box {
            display: none; background: linear-gradient(135deg, rgba(251, 191, 36, 0.18), rgba(16, 185, 129, 0.18));
            border: 2px solid var(--gold-glow); border-radius: 14px; padding: 1.5rem;
            text-align: center; margin-top: 1.5rem; box-shadow: 0 0 30px rgba(251, 191, 36, 0.25);
            animation: bounceIn 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        @keyframes bounceIn { 0% { transform: scale(0.8); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }

        .vault-title { color: var(--gold-glow); font-size: 1.35rem; font-weight: 900; margin-bottom: 0.5rem; }
        .vault-msg { font-family: 'Fira Code', monospace; font-size: 1.15rem; font-weight: 700; color: #fff; background: #040711; padding: 1rem; border-radius: 10px; border: 1px solid var(--gold-glow); margin-top: 0.75rem; word-break: break-all; }

        .stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
        .stat-box { background: rgba(0, 0, 0, 0.35); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 10px; padding: 1rem; text-align: center; }
        .stat-value { font-family: 'Fira Code', monospace; font-size: 1.8rem; font-weight: 700; color: var(--cyan-glow); }
        .stat-label { font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; margin-top: 0.25rem; }

        .terminal {
            background: #030712; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px;
            padding: 1rem; height: 200px; overflow-y: auto; font-family: 'Fira Code', monospace;
            font-size: 0.82rem; display: flex; flex-direction: column; gap: 0.35rem;
        }
        .terminal-line { display: flex; gap: 0.75rem; align-items: center; }
        .terminal-fail { color: var(--rose-glow); }
        .terminal-success { color: var(--emerald-glow); font-weight: 700; background: rgba(16, 185, 129, 0.1); padding: 0.2rem 0.5rem; border-radius: 4px; }
    </style>
</head>
<body>

    <div class="header">
        <div class="logo-tag">🔐 Portal do Desafiante</div>
        <h1>CypherDNA Secret Vault Login</h1>
        <p class="subtitle">Descubra a senha com as requisições do CypherDNA e digite aqui para obter a Palavra Surpresa!</p>
    </div>

    <div class="container">
        
        <!-- CARD DE LOGIN DO DESAFIANTE -->
        <div class="card">
            <div class="card-title">
                <span>🔑 Acesso ao Cofre</span>
                <span style="font-size: 0.8rem; color: var(--gold-glow); font-weight: 700;">ÁREA DO DESAFIANTE</span>
            </div>

            <p style="color: var(--text-dim); font-size: 0.9rem; margin-bottom: 1.25rem;">
                Assim que o script <code style="color:var(--cyan-glow)">crack_target.py</code> encontrar a senha, digite-a abaixo para desbloquear a palavra surpresa!
            </p>

            <form id="loginForm">
                <div class="form-group">
                    <label>Usuário</label>
                    <input type="text" id="loginUser" value="admin" required>
                </div>
                <div class="form-group">
                    <label>Senha Descoberta pelo CypherDNA</label>
                    <input type="password" id="loginPass" placeholder="Digite a senha descoberta..." required>
                </div>
                <button type="submit" class="btn btn-gold">
                    🔓 Destrancar Cofre Secreto
                </button>
            </form>

            <div id="vaultBox" class="vault-box">
                <div class="vault-title">🏆 PALAVRA SURPRESA DESTRANCADA!</div>
                <p style="color: var(--text-dim); font-size: 0.85rem;">Você descobriu a senha e liberou a Palavra Surpresa:</p>
                <div id="vaultMsgText" class="vault-msg">-</div>
            </div>
        </div>

        <!-- CARD DO MONITOR EM TEMPO REAL -->
        <div class="card">
            <div class="card-title">
                <span>📡 Monitor de Requisições de Login</span>
                <span style="font-family: 'Fira Code', monospace; font-size: 0.8rem; color: var(--cyan-glow);">HTTP /api/login</span>
            </div>

            <div class="stats-grid">
                <div class="stat-box">
                    <div id="valAttempts" class="stat-value">0</div>
                    <div class="stat-label">Tentativas Recebidas</div>
                </div>
                <div class="stat-box">
                    <div id="valLastPass" class="stat-value" style="font-size: 1.1rem; color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">-</div>
                    <div class="stat-label">Última Senha Testada</div>
                </div>
            </div>

            <label>Feed de Requisições do CypherDNA:</label>
            <div id="terminal" class="terminal">
                <div class="terminal-line" style="color: #64748b;">Aguardando requisições do CypherDNA...</div>
            </div>

            <button id="btnReset" class="btn btn-danger">
                🔄 Zerar Contador de Tentativas
            </button>
        </div>

    </div>

    <script>
        const loginForm = document.getElementById('loginForm');
        const loginUser = document.getElementById('loginUser');
        const loginPass = document.getElementById('loginPass');
        const vaultBox = document.getElementById('vaultBox');
        const vaultMsgText = document.getElementById('vaultMsgText');
        
        const btnReset = document.getElementById('btnReset');
        const valAttempts = document.getElementById('valAttempts');
        const valLastPass = document.getElementById('valLastPass');
        const terminal = document.getElementById('terminal');

        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: loginUser.value,
                    password: loginPass.value,
                    is_manual: true
                })
            });
            const data = await res.json();
            if (data.success) {
                vaultBox.style.display = 'block';
                vaultMsgText.textContent = data.secret_reward;
            } else {
                alert('❌ Senha Incorreta! O cofre continua trancado.');
                vaultBox.style.display = 'none';
            }
        });

        btnReset.addEventListener('click', async () => {
            await fetch('/api/reset', { method: 'POST' });
            terminal.innerHTML = '<div class="terminal-line" style="color: #64748b;">Contador zerado. Aguardando requisições...</div>';
            vaultBox.style.display = 'none';
            pollStats();
        });

        async function pollStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();

                valAttempts.textContent = data.attempts.toLocaleString();
                valLastPass.textContent = data.last_attempt || '-';

                if (data.unlocked_by_user && data.secret_reward) {
                    vaultBox.style.display = 'block';
                    vaultMsgText.textContent = data.secret_reward;
                }

                if (data.history && data.history.length > 0) {
                    terminal.innerHTML = data.history.map(item => {
                        const timeStr = new Date(item.time * 1000).toLocaleTimeString();
                        if (item.success) {
                            return `<div class="terminal-line terminal-success">
                                <span>[${timeStr}] 🔑 SUCESSO! Senha correta: <strong>${escapeHtml(item.password)}</strong></span>
                            </div>`;
                        } else {
                            return `<div class="terminal-line terminal-fail">
                                <span>[${timeStr}] ❌ Falha: "${escapeHtml(item.password)}" (401)</span>
                            </div>`;
                        }
                    }).join('');
                    terminal.scrollTop = terminal.scrollHeight;
                }
            } catch (err) {}
        }

        function escapeHtml(text) {
            return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }

        setInterval(pollStats, 800);
        pollStats();
    </script>
</body>
</html>
"""

# -------------------------------------------------------------------------
# HTML 2: PAINEL DO ADMINISTRADOR / VÍTIMA (http://localhost:5000/admin)
# -------------------------------------------------------------------------
ADMIN_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CypherDNA - Painel do Administrador</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600;700&family=Inter:wght@300;400;600;700;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-deep: #080c14;
            --bg-card: rgba(15, 23, 42, 0.85);
            --border-glow: rgba(16, 185, 129, 0.3);
            --emerald-glow: #10b981;
            --cyan-glow: #06b6d4;
            --text-main: #f8fafc;
            --text-dim: #94a3b8;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', sans-serif; }

        body {
            background-color: var(--bg-deep);
            background-image: 
                radial-gradient(circle at 50% 20%, rgba(16, 185, 129, 0.1) 0%, transparent 50%),
                linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
            background-size: 100% 100%, 40px 40px, 40px 40px;
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem 1rem;
        }

        .header { text-align: center; margin-bottom: 2rem; }

        .logo-tag {
            display: inline-flex; align-items: center; gap: 0.5rem;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.4);
            color: var(--emerald-glow);
            padding: 0.4rem 1.2rem; border-radius: 999px;
            font-size: 0.85rem; font-weight: 700;
            letter-spacing: 1px; text-transform: uppercase;
            margin-bottom: 0.75rem;
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.25);
        }

        h1 {
            font-size: 2.2rem; font-weight: 900;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }

        p.subtitle { color: var(--text-dim); font-size: 0.95rem; }

        .card {
            width: 100%; max-width: 600px;
            background: var(--bg-card); backdrop-filter: blur(16px);
            border: 1px solid var(--border-glow); border-radius: 16px;
            padding: 2.2rem; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
            position: relative; overflow: hidden;
        }

        .card::before {
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, transparent, var(--emerald-glow), transparent);
        }

        .card-title {
            font-size: 1.3rem; font-weight: 700; display: flex; align-items: center;
            justify-content: space-between; margin-bottom: 1.5rem;
            padding-bottom: 0.75rem; border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }

        .form-group { margin-bottom: 1.25rem; }
        label { display: block; font-size: 0.85rem; font-weight: 600; color: var(--text-dim); margin-bottom: 0.5rem; text-transform: uppercase; }
        
        input, textarea {
            width: 100%; background: rgba(10, 15, 30, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 8px;
            padding: 0.85rem 1rem; color: #fff; font-size: 1rem;
            font-family: 'Fira Code', monospace; transition: all 0.2s ease;
        }

        textarea { resize: vertical; min-height: 90px; }

        input:focus, textarea:focus { outline: none; border-color: var(--emerald-glow); box-shadow: 0 0 12px rgba(16, 185, 129, 0.3); }

        .btn-emerald {
            width: 100%; padding: 1rem; border: none; border-radius: 8px;
            font-weight: 700; font-size: 1rem; cursor: pointer;
            background: linear-gradient(135deg, var(--emerald-glow), #059669);
            color: #fff; text-transform: uppercase; letter-spacing: 0.5px;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3); transition: all 0.2s ease;
        }

        .btn-emerald:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(16, 185, 129, 0.5); }
    </style>
</head>
<body>

    <div class="header">
        <div class="logo-tag">⚙️ Painel do Administrador</div>
        <h1>Configuração da Vítima</h1>
        <p class="subtitle">Esconda a Senha Secreta e defina o Prêmio / Palavra Surpresa do Desafio!</p>
    </div>

    <div class="card">
        <div class="card-title">
            <span>🎯 Configurar Desafio</span>
            <span style="font-size: 0.8rem; color: var(--emerald-glow); font-weight: 700;">ÁREA RESTRITA</span>
        </div>

        <p style="color: var(--text-dim); font-size: 0.9rem; margin-bottom: 1.5rem;">
            Peça para seu amigo definir a <strong>Senha Secreta</strong> que o CypherDNA vai tentar adivinhar e a <strong>Palavra Surpresa</strong> que você desbloqueará no portal de login!
        </p>

        <form id="configForm">
            <div class="form-group">
                <label>Usuário Alvo</label>
                <input type="text" id="targetUser" value="admin" required>
            </div>
            <div class="form-group">
                <label>Senha Secreta Alvo (que o CypherDNA vai procurar)</label>
                <input type="text" id="targetPass" value="xbox360" required placeholder="Ex: xbox360, Gusta2026!...">
            </div>
            <div class="form-group">
                <label>Palavra / Mensagem Surpresa (Prêmio Escondido)</label>
                <textarea id="targetReward" required placeholder="Ex: Parabéns! A palavra surpresa é PIX_50_REAIS ou SEGREDOMAXIMO"></textarea>
            </div>
            <button type="submit" class="btn-emerald">
                🔒 Trancar Cofre com a Palavra Surpresa
            </button>
        </form>
    </div>

    <script>
        const configForm = document.getElementById('configForm');
        const targetUser = document.getElementById('targetUser');
        const targetPass = document.getElementById('targetPass');
        const targetReward = document.getElementById('targetReward');

        targetReward.value = "🏆 PARABÉNS! VOCÊ É O MESTRE DO CYPHERDNA! (Palavra Surpresa: CYPER_LEGEND_2026)";

        configForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const res = await fetch('/api/set-target', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: targetUser.value,
                    password: targetPass.value,
                    secret_reward: targetReward.value
                })
            });
            const data = await res.json();
            if (data.success) {
                alert('🔒 Cofre Configurado e Trancado com Sucesso!');
                window.location.href = '/login';
            }
        });
    </script>
</body>
</html>
"""

class TargetHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        # URL 1: Portal de Login do Desafiante (http://localhost:5000/ e http://localhost:5000/login)
        if parsed.path == '/' or parsed.path == '/login' or parsed.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(LOGIN_HTML.encode('utf-8'))
            return

        # URL 2: Painel do Administrador (http://localhost:5000/admin)
        if parsed.path == '/admin':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(ADMIN_HTML.encode('utf-8'))
            return
            
        if parsed.path == '/api/stats':
            self._send_json(200, {
                "username": TARGET_DATA["username"],
                "attempts": TARGET_DATA["attempts"],
                "last_attempt": TARGET_DATA["last_attempt"],
                "cracked": TARGET_DATA["cracked"],
                "cracked_password": TARGET_DATA["cracked_password"],
                "unlocked_by_user": TARGET_DATA["unlocked_by_user"],
                "secret_reward": TARGET_DATA["secret_reward"] if TARGET_DATA["unlocked_by_user"] else None,
                "history": TARGET_DATA["history"][-25:]
            })
            return

        self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8', errors='ignore')

        payload = {}
        if body:
            try:
                payload = json.loads(body)
            except Exception:
                payload = dict(urllib.parse.parse_qsl(body))

        if parsed.path == '/api/set-target':
            if "password" in payload:
                TARGET_DATA["password"] = payload["password"].strip()
                if "username" in payload and payload["username"].strip():
                    TARGET_DATA["username"] = payload["username"].strip()
                if "secret_reward" in payload and payload["secret_reward"].strip():
                    TARGET_DATA["secret_reward"] = payload["secret_reward"].strip()
                TARGET_DATA["attempts"] = 0
                TARGET_DATA["cracked"] = False
                TARGET_DATA["cracked_password"] = None
                TARGET_DATA["unlocked_by_user"] = False
                TARGET_DATA["history"] = []
                self._send_json(200, {"success": True})
            else:
                self._send_json(400, {"error": "Campo 'password' obrigatório"})
            return

        if parsed.path == '/api/reset':
            TARGET_DATA["attempts"] = 0
            TARGET_DATA["cracked"] = False
            TARGET_DATA["cracked_password"] = None
            TARGET_DATA["unlocked_by_user"] = False
            TARGET_DATA["history"] = []
            self._send_json(200, {"success": True})
            return

        if parsed.path == '/api/login' or parsed.path == '/login':
            tried_pass = payload.get("password", "")
            is_manual = payload.get("is_manual", False)

            if not is_manual:
                TARGET_DATA["attempts"] += 1
                TARGET_DATA["last_attempt"] = tried_pass

            now = time.time()
            is_correct = (tried_pass == TARGET_DATA["password"])

            if is_correct:
                TARGET_DATA["cracked"] = True
                TARGET_DATA["cracked_password"] = tried_pass
                if is_manual:
                    TARGET_DATA["unlocked_by_user"] = True

                TARGET_DATA["history"].append({
                    "time": now,
                    "password": tried_pass,
                    "success": True
                })
                self._send_json(200, {
                    "success": True,
                    "message": "Acesso Concedido!",
                    "secret_reward": TARGET_DATA["secret_reward"]
                })
            else:
                if not is_manual:
                    TARGET_DATA["history"].append({
                        "time": now,
                        "password": tried_pass,
                        "success": False
                    })
                self._send_json(401, {
                    "success": False,
                    "error": "Senha Incorreta"
                })
            return

        self._send_json(404, {"error": "Endpoint não encontrado"})

def start_server(port=PORT):
    server_address = ('', port)
    httpd = HTTPServer(server_address, TargetHTTPHandler)
    print("=" * 68)
    print(f" 👑 CYPHERDNA SECRET VAULT SERVER - ONLINE")
    print(f" 🔑 1. Portal de Login do Desafiante: http://localhost:{port}/login")
    print(f" ⚙️ 2. Painel do Administrador (Vítima): http://localhost:{port}/admin")
    print("=" * 68)
    
    # Abre o portal de login no navegador
    threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{port}/login")).start()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\\n [!] Servidor encerrado.")
        sys.exit(0)

if __name__ == '__main__':
    start_server()
