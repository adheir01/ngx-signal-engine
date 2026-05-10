"""
gemini_explainer.py
Sends signal context to Gemini and returns an explanation + risk flag.

Free tier: 20 requests/day — only call for BUY/SELL signals, not HOLD.
"""

import os
import json
import logging

import google.generativeai as genai

logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.5-flash"


SYSTEM_PROMPT = """You are a financial analyst assistant specialising in emerging market equities,
specifically the Nigerian Stock Exchange (NGX).

Given a trading signal and price context, provide:
1. A concise explanation (2–3 sentences) of why this signal was triggered
2. A risk flag: LOW, MEDIUM, or HIGH
3. A one-sentence risk reasoning

Respond ONLY with valid JSON. No markdown, no preamble.

Format:
{
  "explanation": "...",
  "risk_flag": "LOW|MEDIUM|HIGH",
  "risk_reasoning": "..."
}"""


def explain_signal(signal_dict: dict) -> dict:
    """
    Send a signal to Gemini and return explanation + risk assessment.
    Returns empty dict on failure (to avoid blocking the pipeline).
    """
    ticker   = signal_dict.get("ticker", "UNKNOWN")
    signal   = signal_dict.get("signal")
    strength = signal_dict.get("signal_strength", 0)
    rules    = signal_dict.get("triggered_rules", [])
    close    = signal_dict.get("close_price")
    rsi      = signal_dict.get("rsi_14")

    if signal == "HOLD":
        logger.debug(f"Skipping Gemini for HOLD signal on {ticker}")
        return {}

    prompt = f"""
Ticker: {ticker} (NGX — Nigerian Stock Exchange)
Signal: {signal}
Signal Strength: {strength}/100
Close Price: ₦{close}
RSI (14): {rsi:.1f if rsi else 'N/A'}
Rules triggered: {', '.join(rules) if rules else 'None'}

Provide your analysis.
"""

    try:
        model    = genai.GenerativeModel(MODEL, system_instruction=SYSTEM_PROMPT)
        response = model.generate_content(prompt)
        raw      = response.text.strip()

        parsed = json.loads(raw)
        return {
            "explanation":    parsed.get("explanation", ""),
            "risk_flag":      parsed.get("risk_flag", "MEDIUM"),
            "risk_reasoning": parsed.get("risk_reasoning", ""),
            "prompt_tokens":  response.usage_metadata.prompt_token_count if hasattr(response, "usage_metadata") else None,
        }
    except json.JSONDecodeError:
        logger.error(f"Gemini returned non-JSON for {ticker}: {raw[:200]}")
        return {}
    except Exception as e:
        logger.error(f"Gemini API error for {ticker}: {e}")
        return {}
