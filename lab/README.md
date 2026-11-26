# 🎮 CypherDNA Lab & Secret Vault Challenge

> ⚠️ **Aviso Importante**: Ambiente de laboratório local e isolado (localhost), destinado exclusivamente a fins educacionais e de demonstração. Não utilize contra sistemas sem autorização explícita.

Ambiente interativo local para testar a eficácia de wordlists geradas pelo CypherDNA contra um sistema de autenticação em tempo real.

---

## 🎯 Como Funciona

1. **Inicie o Servidor do Alvo:**
   ```bash
   python target_server.py
   ```
   * O servidor abrirá a interface web em `http://localhost:5000`.

2. **Configuração da Senha Alvo:**
   * Acesse `http://localhost:5000/admin`.
   * Defina a senha alvo e a mensagem/recompensa secreta.

3. **Gere a Wordlist com o CypherDNA:**
   No diretório raiz do projeto:
   ```bash
   cypherdna generator <dicas_do_alvo> -R -S -N 1000
   ```

4. **Dispare o Ataque:**
   ```bash
   python crack_target.py
   ```
   * O script testará as senhas contra o endpoint `/api/login`.
   * Acompanhe as tentativas em tempo real no painel `http://localhost:5000/login`.
   * Ao acertar a senha, o cofre secreto é liberado!
