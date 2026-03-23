#!/usr/bin/env python3
"""
PYTA 单 Agent 推演诊断脚本
用途：以 NVDA (US) 为对象，只调用一个 agent，完整暴露 LLM 请求/响应/错误链路。

运行方式：
  cd /path/to/secondary-market-mvp
  python -m scripts.diagnose_single_agent [agent_type]

  agent_type 可选：
    traditional_institution | quant_institution | retail |
    offshore_capital | short_term_capital
  默认：traditional_institution
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── make sure src/ is importable ─────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx

from src.api import settings_store  # noqa: E402  (populated from DB at import)
from src.config.settings import settings  # noqa: E402
from src.sandbox.agents.templates.secondary_prompts import (  # noqa: E402
    SECONDARY_SANDBOX_SYSTEM_PROMPT,
    build_secondary_user_prompt,
)
from src.sandbox.schemas.agents import ParticipantType  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────

TICKER    = "NVDA"
MARKET    = "US"
ROUND_N   = 1
NARRATIVE = "英伟达 2026Q1 算力订单增长超预期，但台积电 CoWoS 产能瓶颈仍存，请从你的视角分析当前格局。"

SAMPLE_EVENT = {
    "event_id": "diag-001",
    "event_type": "manual_input",
    "content": NARRATIVE,
    "source": "diagnose_script",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "symbol": TICKER,
    "metadata": {"inputMode": "diagnostic"},
}

# ─────────────────────────────────────────────────────────────────────────────

def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def dump_json(label: str, data: object) -> None:
    print(f"\n[{label}]")
    print(json.dumps(data, ensure_ascii=False, indent=2)
          if isinstance(data, (dict, list)) else str(data))


# ─────────────────────────────────────────────────────────────────────────────

async def run_single_agent(agent_type: ParticipantType) -> None:
    section(f"PYTA 单 Agent 诊断 — {agent_type.value}  @  {TICKER}/{MARKET}")

    # ── 1. LLM 配置读取 ──────────────────────────────────────────────────────
    section("1. LLM 配置状态")

    api_key   = settings_store.get("llm_api_key") or settings.llm_api_key
    base_url  = (settings_store.get("llm_base_url") or settings.llm_base_url).rstrip("/")
    model     = settings_store.get("llm_model") or settings.llm_model
    timeout   = settings.llm_timeout_seconds

    print(f"  api_key   : {'***已配置***' if api_key else '(空 — 将使用 stub 模式)'}")
    print(f"  base_url  : {base_url}")
    print(f"  model     : {model or '(空 — 将使用 stub 模式)'}")
    print(f"  timeout   : {timeout}s")
    print(f"  enabled   : {bool(api_key and model)}")

    if not api_key or not model:
        section("⚠ STUB 模式 — 未配置 LLM，返回固定占位回答")
        print("  → 请通过 /api/v1/settings/llm 接口配置 api_key + model，或在 .env 文件中设置。")
        print("  → 以下将继续运行 stub，展示 stub 输出格式：")
        from src.sandbox.agents.runner import SecondaryAgentRunner
        runner = SecondaryAgentRunner()
        perspective, narrative = runner._stub_response(agent_type, TICKER, MARKET, [SAMPLE_EVENT])
        dump_json("stub perspective", perspective.model_dump(mode="json"))
        dump_json("stub narrative", narrative.model_dump(mode="json"))
        return

    # ── 2. 构建 Prompt ───────────────────────────────────────────────────────
    section("2. Prompt 构建")

    system_prompt = SECONDARY_SANDBOX_SYSTEM_PROMPT
    user_prompt   = build_secondary_user_prompt(
        agent_type, TICKER, MARKET, ROUND_N, [SAMPLE_EVENT], NARRATIVE
    )

    print(f"\n[system_prompt length] {len(system_prompt)} chars")
    print(f"\n[user_prompt preview]\n{user_prompt[:600]}{'…' if len(user_prompt) > 600 else ''}")

    # ── 3. HTTP 请求 ─────────────────────────────────────────────────────────
    section("3. HTTP 请求 → LLM 端点")

    request_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    print(f"  POST {base_url}/chat/completions")
    print(f"  model={model}  temperature=0.2  response_format=json_object")

    t0 = time.monotonic()
    error_detail: str | None = None
    raw_data: dict | None = None
    status_code: int | None = None

    try:
        async with httpx.AsyncClient(timeout=timeout + 10) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=request_payload,
            )
            status_code = resp.status_code
            elapsed = time.monotonic() - t0
            print(f"\n  HTTP {status_code}  ({elapsed:.2f}s)")

            raw_text = resp.text
            try:
                raw_data = resp.json()
            except Exception:
                raw_data = None

            if not resp.is_success:
                error_detail = raw_text[:2000]
    except httpx.TimeoutException as exc:
        elapsed = time.monotonic() - t0
        print(f"\n  ⏱  TIMEOUT after {elapsed:.2f}s — {exc}")
        print(f"\n  提示：当前 timeout={timeout}s，某些推理型模型（如 Qwen-Max、MiniMax-M2）需要 30-60s。")
        print(f"  → 建议把 LLM_TIMEOUT_SECONDS 改为 60。")
        return
    except httpx.ConnectError as exc:
        elapsed = time.monotonic() - t0
        print(f"\n  🔌 CONNECTION ERROR after {elapsed:.2f}s")
        print(f"  {exc}")
        print(f"\n  提示：base_url={base_url} 无法连接，请检查：")
        print(f"  1. URL 是否正确（末尾不含 /chat/completions）")
        print(f"  2. 网络代理设置")
        return
    except Exception as exc:
        elapsed = time.monotonic() - t0
        print(f"\n  ❌ 未知错误 ({elapsed:.2f}s): {exc}")
        return

    # ── 4. 响应分析 ──────────────────────────────────────────────────────────
    section("4. 响应分析")

    if error_detail:
        print(f"\n  ❌ HTTP {status_code} 错误")
        print(f"\n  原始响应：\n{error_detail}")

        # 常见错误诊断
        lower = error_detail.lower()
        if "response_format" in lower or "json_object" in lower or "unsupported" in lower:
            print("\n  🔍 诊断：该模型/API 不支持 response_format=json_object")
            print("  → 修复方案：在 client.py 中根据 base_url 判断是否删除 response_format 字段")
        elif "model" in lower and ("not found" in lower or "does not exist" in lower or "invalid" in lower):
            print(f"\n  🔍 诊断：模型名称 '{model}' 无效或不存在")
            print("  → 请确认你的 API provider 支持的 model 列表")
        elif "401" in str(status_code) or "unauthorized" in lower or "api key" in lower:
            print("\n  🔍 诊断：API Key 无效或权限不足")
        elif "429" in str(status_code) or "rate limit" in lower:
            print("\n  🔍 诊断：Rate limit / 配额耗尽")
        elif "context" in lower and ("length" in lower or "too long" in lower):
            print("\n  🔍 诊断：Prompt 过长，超出模型上下文窗口")
        return

    if not raw_data:
        print("  ❌ 响应体无法解析为 JSON")
        return

    dump_json("raw response (simplified)", {
        "id": raw_data.get("id"),
        "model": raw_data.get("model"),
        "usage": raw_data.get("usage"),
        "choices_count": len(raw_data.get("choices", [])),
    })

    choices = raw_data.get("choices", [])
    if not choices:
        print("  ❌ choices 为空")
        return

    raw_content = choices[0].get("message", {}).get("content", "")
    print(f"\n[content preview — first 800 chars]\n{raw_content[:800]}")

    # ── 5. JSON 解析 ─────────────────────────────────────────────────────────
    section("5. JSON 解析 & 结构校验")

    import re

    def extract_json(text: str) -> dict | None:
        # Strip think tags (reasoning models)
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        # Try direct parse
        try:
            return json.loads(text)
        except Exception:
            pass
        # Fenced block
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
        # Find first { }
        decoder = json.JSONDecoder()
        for i, c in enumerate(text):
            if c == "{":
                try:
                    obj, _ = decoder.raw_decode(text[i:])
                    return obj  # type: ignore
                except Exception:
                    pass
        return None

    parsed = extract_json(raw_content)
    if parsed is None:
        print("  ❌ 无法从 LLM 输出中提取有效 JSON")
        print(f"\n  完整 content：\n{raw_content}")
        print("\n  🔍 诊断：模型未按 JSON 格式输出。可能原因：")
        print("  1. 该模型不理解 json_object 指令（非 OpenAI 协议兼容）")
        print("  2. System prompt 中的 '只输出 JSON' 指令被忽略")
        print("  → 建议：在 user prompt 末尾加强提示：'IMPORTANT: Return ONLY valid JSON.'")
        return

    dump_json("parsed payload (top-level keys)", list(parsed.keys()))

    # Validate structure
    perspective = parsed.get("perspective")
    narrative   = parsed.get("narrative")
    issues: list[str] = []

    if not isinstance(perspective, dict):
        issues.append("缺少 'perspective' 对象")
    else:
        for field in ("market_bias", "key_observations", "key_concerns", "analytical_focus", "confidence"):
            if field not in perspective:
                issues.append(f"perspective 缺少字段: {field}")
        obs = perspective.get("key_observations", [])
        if not obs:
            issues.append("key_observations 为空 — agent 没有实质性观察")

    if not isinstance(narrative, dict) and not isinstance(narrative, str):
        issues.append("缺少 'narrative' 对象")

    if issues:
        print(f"\n  ⚠  结构问题 ({len(issues)} 项):")
        for iss in issues:
            print(f"    • {iss}")
    else:
        print(f"\n  ✅ JSON 结构完整")

    dump_json("perspective", perspective)
    dump_json("narrative", narrative)

    # ── 6. 总结 ──────────────────────────────────────────────────────────────
    section("6. 诊断总结")
    if not issues:
        print(f"  ✅ Agent '{agent_type.value}' 对 {TICKER} 推演完成，响应结构正常。")
        print(f"  market_bias = {perspective.get('market_bias')}")
        print(f"  confidence  = {perspective.get('confidence')}")
        print(f"  observations: {len(perspective.get('key_observations', []))} 条")
    else:
        print(f"  ❌ 发现 {len(issues)} 个问题，需修复：")
        for iss in issues:
            print(f"    • {iss}")


# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    agent_name = sys.argv[1] if len(sys.argv) > 1 else "traditional_institution"
    try:
        agent_type = ParticipantType(agent_name)
    except ValueError:
        valid = [p.value for p in ParticipantType]
        print(f"无效的 agent_type: {agent_name!r}")
        print(f"可选: {valid}")
        sys.exit(1)

    asyncio.run(run_single_agent(agent_type))


if __name__ == "__main__":
    main()
