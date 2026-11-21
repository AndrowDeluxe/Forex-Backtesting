"""LangChain-Chatmodell, das den lokalen Claude Code ueber das Abo aufruft (`claude.exe -p`), kein API-Key.

Datenabrufe (Tool-Calls) werden nachgebildet: `bind_tools` merkt sich die Tool-Schemas, der Prompt bittet um
`{"tool_calls": [...]}` oder den fertigen Text, und die Antwort wird zu `AIMessage.tool_calls`. Die Tools
selbst fuehrt TradingAgents aus, das Framework bleibt unveraendert. `with_structured_output` gibt es nicht,
dann nimmt TradingAgents seinen eingebauten Freitext-Weg.
"""

from __future__ import annotations

import json
import re
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool

SYSTEM = ("You are one component of an automated multi-agent research pipeline. Follow the instructions in the "
          "user message exactly. Do not ask questions back.")

TOOL_INSTRUCTION = """

## HOW TO USE TOOLS
You cannot call tools natively. To call one or more tools, reply with ONLY this JSON object and nothing else:
{"tool_calls": [{"name": "<tool name>", "args": {<arguments>}}]}
You may request several calls at once. The results come back in the next turn.
When you have the data you need (or no tool helps), reply with your final answer as plain text, NOT as JSON.
Available tools (name, description, JSON-schema of args):
"""


def claude_exe() -> str:
    """Neueste Claude-Code-Extension (wie fusion_lab/copy_trading/extract.py, ohne Repo-Abhaengigkeiten)."""
    exts = sorted((Path.home() / ".vscode" / "extensions").glob("anthropic.claude-code-*"),
                  key=lambda p: [int(x) for x in re.findall(r"\d+", p.name.split("-")[2])[:3]], reverse=True)
    for e in exts:
        exe = e / "resources" / "native-binary" / "claude.exe"
        if exe.exists():
            return str(exe)
    raise FileNotFoundError("claude.exe nicht gefunden (Claude-Code-Extension)")


class Usage:
    """Zaehler je Lauf (thread-sicher, die Analysten laufen parallel)."""

    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        with self._lock:
            self.calls, self.cost_usd, self.errors = 0, 0.0, 0

    def add(self, cost: float = 0.0, error: bool = False):
        with self._lock:
            self.calls += 1
            self.cost_usd += cost or 0.0
            self.errors += int(error)


USAGE = Usage()


def render(messages: list[BaseMessage]) -> str:
    """Verlauf als ein Text fuer `claude -p` (stdin)."""
    parts = []
    for m in messages:
        content = m.content if isinstance(m.content, str) else json.dumps(m.content, default=str)
        if isinstance(m, SystemMessage):
            parts.append(f"## INSTRUCTIONS\n{content}")
        elif isinstance(m, ToolMessage):
            parts.append(f"## TOOL RESULT ({m.name or 'tool'})\n{content}")
        elif isinstance(m, AIMessage):
            calls = "; ".join(f"{c['name']}({json.dumps(c['args'], default=str)})" for c in (m.tool_calls or []))
            parts.append(f"## YOUR EARLIER TURN\n{content}" + (f"\n[You called: {calls}]" if calls else ""))
        else:
            parts.append(f"## USER\n{content}")
    return "\n\n".join(parts)


def parse_reply(text: str, tool_names: set[str]) -> AIMessage:
    """Tool-JSON -> AIMessage mit tool_calls, sonst Text. Unbekannte Tools oder kaputtes JSON -> Text."""
    t = (text or "").strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", t, flags=re.S)
    if fenced:
        t = fenced.group(1)
    if tool_names and t.startswith("{") and '"tool_calls"' in t:
        try:
            obj = json.loads(t)
            calls = [c for c in obj.get("tool_calls", []) if isinstance(c, dict) and c.get("name") in tool_names]
            if calls:
                return AIMessage(content="", tool_calls=[
                    {"name": c["name"], "args": c.get("args") or {}, "id": f"call_{uuid.uuid4().hex[:12]}"}
                    for c in calls])
        except (json.JSONDecodeError, AttributeError):
            pass
    return AIMessage(content=text or "")


class ClaudeCodeChat(BaseChatModel):
    model: str = "haiku"
    timeout: int = 600
    tools_spec: list[dict] = []

    @property
    def _llm_type(self) -> str:
        return "claude-code-abo"

    def bind_tools(self, tools, **kwargs: Any):
        return self.model_copy(update={"tools_spec": [convert_to_openai_tool(t)["function"] for t in tools]})

    def with_structured_output(self, *args, **kwargs):
        raise NotImplementedError("claude -p liefert kein structured output")

    def _call(self, prompt: str) -> str:
        res = subprocess.run(
            [claude_exe(), "-p", "--model", self.model, "--output-format", "json", "--tools", "",
             "--strict-mcp-config", "--no-session-persistence", "--setting-sources", "", "--system-prompt", SYSTEM],
            input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=self.timeout)
        if res.returncode != 0:
            raise RuntimeError(f"claude rc={res.returncode}: {(res.stderr or res.stdout)[-300:]}")
        out = json.loads(res.stdout)
        if out.get("is_error"):
            raise RuntimeError(f"claude Fehler: {str(out.get('result'))[:300]}")
        USAGE.add(out.get("total_cost_usd", 0.0))
        return out.get("result", "")

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        prompt = render(messages)
        if self.tools_spec:
            prompt += TOOL_INSTRUCTION + json.dumps(self.tools_spec, ensure_ascii=False)
        last = None
        for _ in range(2):                      # ein Wiederholversuch bei Ausfall/Zeitueberschreitung
            try:
                text = self._call(prompt)
                return ChatResult(generations=[ChatGeneration(
                    message=parse_reply(text, {t["name"] for t in self.tools_spec}))])
            except (subprocess.TimeoutExpired, RuntimeError, json.JSONDecodeError) as e:
                USAGE.add(error=True)
                last = e
        raise RuntimeError(f"claude -p zweimal fehlgeschlagen: {last}")


def install(quick: str, deep: str, timeout: int = 600) -> None:
    """TradingAgents auf das Abo umstellen: create_tier_client im Graph-Modul ersetzen (fester Commit 9fa1196)."""
    import tradingagents.graph.trading_graph as tg

    class _Client:
        def __init__(self, model):
            self.model = model

        def get_llm(self):
            return ClaudeCodeChat(model=self.model, timeout=timeout)

    tg.create_tier_client = lambda cfg, tier, **kw: _Client(quick if tier == "quick" else deep)


__all__ = ["ClaudeCodeChat", "USAGE", "install", "parse_reply", "render"]
