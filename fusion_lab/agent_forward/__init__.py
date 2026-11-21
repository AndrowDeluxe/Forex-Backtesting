"""Forward-Test des Multi-Agenten-Frameworks TradingAgents (TauricResearch) ueber das Claude-Abo.

Siehe knowledge/resources/tradingagents-tauric.md. Laeuft NICHT mit der Repo-Python, sondern mit der venv
unter C:\\Users\\andre\\TradingAgents\\venv (TradingAgents fest auf Commit 9fa1196). Kein Handel, keine Bridge.

    <venv-python> -m fusion_lab.agent_forward run            # Tageslauf (Abrechnung + Entscheide + Summary)
    <venv-python> -m fusion_lab.agent_forward run --tickers NVDA   # nur ein Titel (Test)
    <venv-python> -m fusion_lab.agent_forward summary        # nur summary.json neu rechnen

ledger.py und summary kommen ohne TradingAgents aus (nur Standardbibliothek).
"""
