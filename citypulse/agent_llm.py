"""LLM MODE: Claude decides which tools to call (real tool calling / function calling).

How it works (explain in the viva):
  1. We describe our tools to the model as JSON schemas (TOOL_SCHEMAS).
  2. The model replies either with text or with a `tool_use` block ("call propose_route_swaps").
  3. WE run that tool on AgentSession and send the result back as a `tool_result`.
  4. Repeat until the model stops asking for tools; its last text message is the weekly report.
The LLM never does the maths - the tools do. The LLM chooses the order and writes the explanation
(in any language). That is why the numbers stay trustworthy.

Needs: pip install anthropic   and   export ANTHROPIC_API_KEY=...   (optional; the app works without it)
"""
from __future__ import annotations

import json
import os

from .agent import AgentSession

DEFAULT_MODEL = os.environ.get("CITYPULSE_MODEL", "claude-sonnet-5-5")

SYSTEM_PROMPT = """You are CityPulse, an agent that turns a person's week of urban exposure (heat, UV, PM2.5)
into healthier next-week actions. You have tools. Work like this:
1. Observe: call get_week_overview and get_exposure_report.
2. Plan: call find_sedentary_gaps, then propose_route_swaps.
3. Act: call schedule_workouts (at least 2), suggest_meetups, then export_calendar.
4. Learn: call get_learning_stats and mention any adaptation.
Finish with a short, friendly weekly report in the user's requested language: the exposure score, the biggest
change (commute swaps), the workout slots with day and time, and a meetup idea if one was suggested.
Rules: you give guidance on exposure and habits ONLY. Never diagnose, never suggest medicines or treatment.
Use only numbers returned by tools; never invent values. If the user seems distressed, stop planning and
share Tele-MANAS 14416 (India, free, 24x7)."""

_EMPTY = {"type": "object", "properties": {}, "required": []}
TOOL_SCHEMAS = [
    {"name": "get_week_overview", "description": "Summary of the user's persona, city, commutes and hours by activity.", "input_schema": _EMPTY},
    {"name": "get_exposure_report", "description": "Weekly Exposure Score (0-100), PM2.5 dose and the highest-exposure blocks.", "input_schema": _EMPTY},
    {"name": "find_sedentary_gaps", "description": "Finds long (3h+) inactive blocks and the free slots inside them.", "input_schema": _EMPTY},
    {"name": "propose_route_swaps", "description": "Finds lower-exposure departure times / greener paths for commutes. apply=true applies them to the plan.",
     "input_schema": {"type": "object", "properties": {"apply": {"type": "boolean", "description": "Apply the swaps to the plan (default true)"}}, "required": []}},
    {"name": "schedule_workouts", "description": "Picks workout slots at low-pollution, comfortable-heat times inside free time. Minimum 2.",
     "input_schema": {"type": "object", "properties": {"count": {"type": "integer", "minimum": 2, "maximum": 5}}, "required": []}},
    {"name": "suggest_meetups", "description": "If the week had little social contact, suggests clubs/meetups matching interests.", "input_schema": _EMPTY},
    {"name": "export_calendar", "description": "Writes the workout slots to a calendar (.ics) file. Call after schedule_workouts.", "input_schema": _EMPTY},
    {"name": "get_learning_stats", "description": "What the user accepted or ignored in past weeks and how the plan adapted.", "input_schema": _EMPTY},
]


def llm_available() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def run_llm_agent(session: AgentSession, lang_name: str = "English", model: str | None = None,
                  max_steps: int = 12, client=None) -> dict:
    """Drive `session` with a tool-calling LLM. `client` can be injected (tests use a fake)."""
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    session.observe()
    messages = [{"role": "user", "content":
                 f"Plan next week for this user. Write the final report in {lang_name}. Start by observing their week."}]
    final_text, steps = "", 0
    for steps in range(1, max_steps + 1):
        resp = client.messages.create(model=model or DEFAULT_MODEL, max_tokens=1500, system=SYSTEM_PROMPT,
                                      tools=TOOL_SCHEMAS, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            final_text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
            break
        results = []
        for block in resp.content:
            if getattr(block, "type", "") == "tool_use":
                out = session.call_tool(block.name, dict(block.input or {}))
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(out, default=str)})
        messages.append({"role": "user", "content": results})
    report = session.report(lang="en", record=True)
    report["llm"] = {"model": model or DEFAULT_MODEL, "steps": steps, "tool_calls": session.tool_log, "final_text": final_text}
    return report
