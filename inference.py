"""
SQL Query Builder — Baseline Inference Script
===================================
MANDATORY
- Before submitting, ensure the following variables are defined in your environment configuration:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.

- Defaults are set only for API_BASE_URL and MODEL_NAME
    (and should reflect your active inference setup):
    API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
    MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

- The inference script must be named `inference.py` and placed in the root directory of the project
- Participants must use OpenAI Client for all LLM calls using above variables

STDOUT FORMAT
- The script must emit exactly three line types to stdout, in this order:

    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>

  Rules:
    - One [START] line at episode begin.
    - One [STEP] line per step, immediately after env.step() returns.
    - One [END] line after episode ends, always emitted (even on exception).
    - reward and rewards are formatted to 2 decimal places.
    - done and success are lowercase booleans: true or false.
    - error is the raw error string, or null if none.
    - All fields on a single line with no newlines within a line.
    - Each task should return score in [0, 1]
"""

import asyncio
import os
import re
import sys
import time
import traceback

from openai import AsyncOpenAI

from sql_query_env import SqlQueryAction, SqlQueryEnv

# ── Environment Variables ─────────────────────────────────
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
IMAGE_NAME = os.getenv("IMAGE_NAME")

# ── Constants ─────────────────────────────────────────────
BENCHMARK = "sql_query_env"
TASKS = ["simple_lookup", "analytics_query", "complex_report"]
MAX_STEPS = 5

# ── Async OpenAI Client ───────────────────────────────────
client = AsyncOpenAI(base_url=API_BASE_URL, api_key=API_KEY)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ANSI Theme System — colors shift by difficulty
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
R = "\033[0m"
B = "\033[1m"
D = "\033[2m"
ITALIC = "\033[3m"

# Base colors
WHITE = "\033[97m"
GRAY = "\033[90m"
RED = "\033[91m"
GRN = "\033[92m"
YLW = "\033[93m"
BLU = "\033[94m"
MAG = "\033[95m"
CYN = "\033[96m"

# Difficulty theme palettes
THEME = {
    "easy":   {"accent": "\033[38;5;114m", "sec": "\033[38;5;157m", "icon": "🟢", "bar_fg": "\033[38;5;71m",  "label": "EASY"},
    "medium": {"accent": "\033[38;5;221m", "sec": "\033[38;5;229m", "icon": "🟡", "bar_fg": "\033[38;5;178m", "label": "MEDIUM"},
    "hard":   {"accent": "\033[38;5;204m", "sec": "\033[38;5;217m", "icon": "🔴", "bar_fg": "\033[38;5;167m", "label": "HARD"},
}

DIFF_MAP = {
    "simple_lookup": "easy",
    "analytics_query": "medium",
    "complex_report": "hard",
}


def log(msg: str = "") -> None:
    print(msg, file=sys.stderr)


def bar(score: float, w: int = 20, theme: str = "easy") -> str:
    f = int(score * w)
    fg = THEME[theme]["bar_fg"]
    return f"{fg}{'█' * f}{GRAY}{'░' * (w - f)}{R} {B}{score:.2f}{R}"


def signal_line(bd: dict) -> str:
    parts = []
    for sig, lbl in [("syntax_valid", "SYN"), ("executes", "EXE"),
                      ("correct_columns", "COL"), ("correct_rows", "ROW"),
                      ("values_match", "VAL")]:
        v = bd.get(sig, 0.0)
        if v >= 0.99:
            parts.append(f"{GRN}{lbl}✓{R}")
        elif v > 0:
            parts.append(f"{YLW}{lbl}~{R}")
        else:
            parts.append(f"{RED}{lbl}✗{R}")
    return "  ".join(parts)


def fmt_row(row: dict, max_len: int = 90) -> str:
    """Format a result row dict as a compact readable string."""
    parts = []
    for k, v in row.items():
        parts.append(f"{B}{k}{R}={v}")
    s = "  ".join(parts)
    if len(s) > max_len + 20:  # account for ANSI codes
        s = s[:max_len + 20] + f"{GRAY}…{R}"
    return s


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LLM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def ask_llm(schema: str, question: str, error: str = "", prev_query: str = "") -> tuple[str, float]:
    prompt = (
        "You are an expert SQL developer. Write a SQLite-compatible SQL query "
        "to answer the following question.\n\n"
        f"{schema}\n\nQUESTION: {question}\n"
    )
    if error and prev_query:
        prompt += f"\nYour previous query was:\n{prev_query}\nFeedback: {error}\nPlease fix the query.\n"
    prompt += (
        "\nRules:\n- Respond with ONLY the SQL query\n"
        "- No markdown, no backticks, no explanation\n"
        "- Use SQLite-compatible syntax\n- No trailing semicolon\n"
    )

    kwargs = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.1,
    }
    if "nemotron" in MODEL_NAME.lower():
        kwargs["max_tokens"] = 4096
        kwargs["extra_body"] = {
            "chat_template_kwargs": {"enable_thinking": True},
            "reasoning_budget": 2048,
        }

    t0 = time.monotonic()
    response = await client.chat.completions.create(**kwargs)
    latency = time.monotonic() - t0

    raw = response.choices[0].message.content or ""
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    return text, latency


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Task Runner
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def run_task(task_name: str, env_url: str) -> float:
    diff = DIFF_MAP.get(task_name, "easy")
    t = THEME[diff]
    ac = t["accent"]
    sc = t["sec"]

    # ── Task banner ──
    log()
    log(f"  {ac}{B}┏{'━' * 56}┓{R}")
    log(f"  {ac}{B}┃{R}  {t['icon']}  {ac}{B}{task_name}{R}  {GRAY}· {t['label']}{R}{' ' * (40 - len(task_name) - len(t['label']))}{ac}{B}┃{R}")
    log(f"  {ac}{B}┗{'━' * 56}┛{R}")

    # ── MANDATORY STDOUT ──
    print(f"[START] task={task_name} env={BENCHMARK} model={MODEL_NAME}")

    rewards = []
    final_score = 0.0
    success = False
    steps = 0
    prev_query = ""
    prev_error = ""

    try:
        async with SqlQueryEnv(base_url=env_url) as env:
            result = await env.reset(options={"task": task_name})
            obs = result.observation

            # Question block
            log()
            log(f"    {sc}{B}❯ Question{R}")
            log(f"    {WHITE}{obs.question}{R}")
            log()
            if obs.hints:
                log(f"    {GRAY}{ITALIC}💡 {' │ '.join(obs.hints)}{R}")
                log()

            for step_num in range(1, MAX_STEPS + 1):
                sql_query, latency = await ask_llm(
                    schema=obs.db_schema,
                    question=obs.question,
                    error=prev_error if step_num > 1 else "",
                    prev_query=prev_query if step_num > 1 else "",
                )

                result = await env.step(SqlQueryAction(query=sql_query))
                obs = result.observation
                reward = result.reward if result.reward is not None else 0.0
                rewards.append(reward)
                steps = step_num

                bd = obs.reward_breakdown or {}
                sql_short = sql_query.replace("\n", " ").strip()

                # ── Step block ──
                log(f"    {ac}╭─ {B}Step {step_num}{R}  {GRAY}{latency:.1f}s{R}")
                log(f"    {ac}│{R}")

                # SQL query (show full if short, truncated if long)
                if len(sql_short) <= 100:
                    log(f"    {ac}│{R}   {D}SQL →{R}  {sc}{sql_short}{R}")
                else:
                    log(f"    {ac}│{R}   {D}SQL →{R}  {sc}{sql_short[:100]}{R}")
                    log(f"    {ac}│{R}          {sc}{sql_short[100:200]}{R}")

                log(f"    {ac}│{R}")
                log(f"    {ac}│{R}   {D}Score{R}  {bar(reward, 22, diff)}   {signal_line(bd)}")

                # Feedback
                if reward < 0.99 and obs.feedback:
                    log(f"    {ac}│{R}")
                    log(f"    {ac}│{R}   {YLW}↳ {obs.feedback}{R}")

                # Error
                if obs.error:
                    log(f"    {ac}│{R}   {RED}⚠ {obs.error}{R}")

                # ── Results display ──
                agent_rows = obs.agent_result or []
                expected_rows = obs.expected_result or []

                if agent_rows:
                    log(f"    {ac}│{R}")

                    if expected_rows and reward < 0.99:
                        # ── Show both + diff ──
                        all_cols = sorted(set(
                            list(agent_rows[0].keys()) + list(expected_rows[0].keys())
                        ))
                        max_r = min(max(len(agent_rows), len(expected_rows)), 6)

                        log(f"    {ac}│{R}   {B}Agent Result{R} {GRAY}({len(agent_rows)} rows){R}    vs    {B}Expected{R} {GRAY}({len(expected_rows)} rows){R}")
                        log(f"    {ac}│{R}")

                        for i in range(max_r):
                            a = agent_rows[i] if i < len(agent_rows) else None
                            e = expected_rows[i] if i < len(expected_rows) else None

                            if a is None:
                                log(f"    {ac}│{R}     {RED}⊖{R} Row {i+1}:  {RED}missing from agent{R}")
                                log(f"    {ac}│{R}        {GRN}expected →{R} {D}{fmt_row(e)}{R}")
                                continue
                            if e is None:
                                log(f"    {ac}│{R}     {YLW}⊕{R} Row {i+1}:  {YLW}extra in agent{R}")
                                log(f"    {ac}│{R}        {YLW}agent    →{R} {D}{fmt_row(a)}{R}")
                                continue

                            diffs = [(c, a.get(c, "∅"), e.get(c, "∅"))
                                     for c in all_cols
                                     if str(a.get(c, "∅")) != str(e.get(c, "∅"))]

                            if diffs:
                                log(f"    {ac}│{R}     {RED}✗{R} Row {i+1}:")
                                for c, av, ev in diffs:
                                    log(f"    {ac}│{R}        {B}{c}{R}:  {RED}{av}{R}  →  {GRN}{ev}{R}")
                                matching = [c for c in all_cols if str(a.get(c, "∅")) == str(e.get(c, "∅"))]
                                if matching:
                                    log(f"    {ac}│{R}        {GRAY}✓ ok: {', '.join(matching)}{R}")
                            else:
                                log(f"    {ac}│{R}     {GRN}✓{R} Row {i+1}:  {GRAY}{fmt_row(a)}{R}")

                        if max(len(agent_rows), len(expected_rows)) > max_r:
                            extra = max(len(agent_rows), len(expected_rows)) - max_r
                            log(f"    {ac}│{R}     {GRAY}… {extra} more row(s){R}")

                    elif reward >= 0.99:
                        # ── Perfect — show results nicely ──
                        log(f"    {ac}│{R}   {GRN}{B}🎉 PERFECT!{R}")
                        log(f"    {ac}│{R}")
                        log(f"    {ac}│{R}   {B}Result{R} {GRAY}({len(agent_rows)} rows){R}")
                        for row in agent_rows[:5]:
                            log(f"    {ac}│{R}     {GRAY}›{R} {fmt_row(row)}")
                        if len(agent_rows) > 5:
                            log(f"    {ac}│{R}     {GRAY}… +{len(agent_rows) - 5} more{R}")

                    else:
                        # ── Not done yet, show agent result only ──
                        log(f"    {ac}│{R}   {B}Agent Result{R} {GRAY}({len(agent_rows)} rows){R}")
                        for row in agent_rows[:4]:
                            log(f"    {ac}│{R}     {GRAY}›{R} {fmt_row(row)}")
                        if len(agent_rows) > 4:
                            log(f"    {ac}│{R}     {GRAY}… +{len(agent_rows) - 4} more{R}")

                # Attempts remaining
                if not result.done:
                    log(f"    {ac}│{R}")
                    log(f"    {ac}│{R}   {YLW}⏳ {obs.attempts_remaining} attempt(s) remaining{R}")

                log(f"    {ac}│{R}")
                log(f"    {ac}╰{'─' * 55}{R}")

                # ── MANDATORY STDOUT ──
                action_log = sql_query.replace("\n", " ").strip()[:100]
                error_str = obs.error if obs.error else "null"
                done_str = "true" if result.done else "false"
                print(f"[STEP] step={step_num} action={action_log} reward={reward:.2f} done={done_str} error={error_str}")

                if result.done:
                    final_score = reward
                    success = reward >= 0.99
                    break

                prev_query = sql_query
                prev_error = obs.feedback or ""

    except Exception:
        traceback.print_exc(file=sys.stderr)
        if not rewards:
            rewards = [0.0]

    # ── MANDATORY STDOUT ──
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    success_str = "true" if success else "false"
    print(f"[END] success={success_str} steps={steps} score={final_score:.2f} rewards={rewards_str}")
    return final_score


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def main():
    env_url = os.getenv("ENV_URL", "http://localhost:8000")
    model_short = MODEL_NAME.split("/")[-1] if "/" in MODEL_NAME else MODEL_NAME

    log()
    log(f"  {B}{MAG}╔══════════════════════════════════════════════╗{R}")
    log(f"  {B}{MAG}║{R}   {B}⚡ SQL Query Builder{R}  —  Inference Run    {B}{MAG}║{R}")
    log(f"  {B}{MAG}╚══════════════════════════════════════════════╝{R}")
    log()
    log(f"    {GRAY}Model :{R}  {B}{model_short}{R}")
    log(f"    {GRAY}API   :{R}  {D}{API_BASE_URL}{R}")
    log(f"    {GRAY}Env   :{R}  {D}{env_url}{R}")

    scores = []
    t0 = time.monotonic()

    for task in TASKS:
        score = await run_task(task, env_url)
        scores.append(score)

    elapsed = time.monotonic() - t0
    avg = sum(scores) / len(scores) if scores else 0.0

    # ── Final scoreboard ──
    log()
    log(f"  {B}{MAG}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓{R}")
    log(f"  {B}{MAG}┃{R}   {B}📊  FINAL SCOREBOARD{R}{' ' * 35}{B}{MAG}┃{R}")
    log(f"  {B}{MAG}┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫{R}")
    log(f"  {B}{MAG}┃{R}{' ' * 56}{B}{MAG}┃{R}")

    for task, score in zip(TASKS, scores):
        diff = DIFF_MAP.get(task, "easy")
        th = THEME[diff]
        icon = f"{GRN}✅{R}" if score >= 0.99 else f"{YLW}⚠️ {R}" if score > 0 else f"{RED}❌{R}"
        padding = 36 - len(task) - len(th["label"])
        log(f"  {B}{MAG}┃{R}   {th['icon']}  {th['accent']}{B}{task}{R} {GRAY}({th['label']}){R}{' ' * padding}{bar(score, 15, diff)} {icon} {B}{MAG}┃{R}")

    log(f"  {B}{MAG}┃{R}{' ' * 56}{B}{MAG}┃{R}")
    log(f"  {B}{MAG}┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫{R}")
    avg_color = GRN if avg >= 0.99 else YLW if avg >= 0.7 else RED
    log(f"  {B}{MAG}┃{R}   {B}Average:{R}  {avg_color}{B}{avg:.2f}{R}        {GRAY}⏱ {elapsed:.1f}s   🤖 {model_short}{R}     {B}{MAG}┃{R}")
    log(f"  {B}{MAG}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛{R}")
    log()


if __name__ == "__main__":
    asyncio.run(main())
