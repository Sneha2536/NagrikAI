"""
llm.py: the ONLY file that talks to the AI model.

Everything else calls:
    generate(system, prompt)        -> plain text
    generate_json(system, prompt)   -> a Python dict/list (the AI is told to reply in JSON)

To switch AI provider, change LLM_PROVIDER in .env. No other file changes.

Reliability: busy models answer 503/429. We retry with a short wait, and if you set
GEMINI_FALLBACK_MODEL in .env we then try that model too.
"""
import json
import re
import time

import httpx

from config import settings


class LLMError(Exception):
    """Raised when the AI service fails or is not configured."""


RETRY_STATUS = {500, 502, 503, 504}
ATTEMPTS_PER_MODEL = 2


def _gemini_error(r: httpx.Response, model: str) -> str:
    """Return a provider-aware message without exposing request credentials."""
    try:
        error = r.json().get("error", {})
        message = str(error.get("message", ""))
        status = str(error.get("status", "")).upper()
    except (ValueError, AttributeError):
        message, status = r.text[:300], ""
    upper = f"{status} {message}".upper()
    if r.status_code == 429:
        if any(term in upper for term in ("QUOTA_EXCEEDED", "DAILY", "PER_DAY", "PERDAY", "BILLING")):
            return "Gemini's quota for this key or model appears to be exhausted. Check its quota in Google AI Studio and try again later."
        return "Gemini is rate-limiting requests. Wait a while before retrying."
    if r.status_code in (401, 403) or any(term in upper for term in ("API_KEY_INVALID", "INVALID API KEY", "PERMISSION_DENIED")):
        return "Gemini rejected the configured credentials or access. Check the API key and model access in Google AI Studio."
    if r.status_code in RETRY_STATUS:
        return f"Gemini model {model} is temporarily unavailable (HTTP {r.status_code}). Please retry shortly."
    return f"Gemini rejected the request (HTTP {r.status_code}): {message[:240]}"


def _quota_exhausted(r: httpx.Response) -> bool:
    """True for a used-up daily/billing quota (waiting a minute cannot fix it)."""
    upper = r.text.upper()
    return any(term in upper for term in ("QUOTA_EXCEEDED", "DAILY", "PER_DAY", "PERDAY", "BILLING"))


def _retry_delay(body: str) -> float:
    """Google's 429 reply says how long to wait, e.g. "retryDelay": "34s"."""
    m = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', body)
    return float(m.group(1)) if m else 20.0


def _gemini_url(model: str) -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _call_gemini(system: str, prompt: str, json_mode: bool) -> str:
    if not settings.GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY is not set. Add it to the .env file.")
    config = {"temperature": 0.2}
    if json_mode:
        config["responseMimeType"] = "application/json"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": config,
    }
    models = [settings.GEMINI_MODEL]
    if settings.GEMINI_FALLBACK_MODEL and settings.GEMINI_FALLBACK_MODEL != settings.GEMINI_MODEL:
        models.append(settings.GEMINI_FALLBACK_MODEL)

    timeout = httpx.Timeout(240, connect=15)
    last_problem = "The AI service did not answer."
    for model in models:
        for attempt in range(ATTEMPTS_PER_MODEL):
            try:
                r = httpx.post(
                    _gemini_url(model), params={"key": settings.GEMINI_API_KEY}, json=body, timeout=timeout
                )
            except httpx.TimeoutException:
                last_problem = f"{model} took too long to respond."
                break  # don't wait another 4 minutes on the same model: try the next one
            except httpx.HTTPError as e:
                raise LLMError(f"Could not reach the AI service: {e}") from e

            if r.status_code == 200:
                try:
                    parts = r.json()["candidates"][0]["content"]["parts"]
                    return "".join(p.get("text", "") for p in parts)
                except (KeyError, IndexError, ValueError) as e:
                    raise LLMError("AI service returned an unexpected response.") from e
            if r.status_code == 429:
                if _quota_exhausted(r):
                    raise LLMError(_gemini_error(r, model))   # waiting will not help
                # Per-minute limit: wait as long as Google asks, then try again.
                last_problem = _gemini_error(r, model)
                if attempt + 1 < ATTEMPTS_PER_MODEL:
                    time.sleep(min(_retry_delay(r.text) + 1, 65))
                continue
            if r.status_code in (400, 401, 403):
                raise LLMError(_gemini_error(r, model))
            if r.status_code in RETRY_STATUS:
                last_problem = _gemini_error(r, model)
                if attempt + 1 < ATTEMPTS_PER_MODEL:
                    time.sleep(1)
                continue
            raise LLMError(_gemini_error(r, model))

    raise LLMError(f"{last_problem} Please click Try again in a minute.")


def _call_anthropic(system: str, prompt: str, json_mode: bool) -> str:
    if not settings.ANTHROPIC_API_KEY:
        raise LLMError("ANTHROPIC_API_KEY is not set. Add it to the .env file.")
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    try:
        msg = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=8000,
            temperature=0.2,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as e:
        raise LLMError(f"AI service error: {e}") from e
    return "".join(b.text for b in msg.content if b.type == "text")


def generate(system: str, prompt: str, json_mode: bool = False) -> str:
    if settings.LLM_PROVIDER == "anthropic":
        return _call_anthropic(system, prompt, json_mode)
    return _call_gemini(system, prompt, json_mode)


def _extract_json(text: str):
    """Models sometimes wrap JSON in ```json fences. Strip them and parse."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Last resort: grab the outermost {...} or [...]
        m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
        if m:
            return json.loads(m.group(1))
        raise


def generate_json(system: str, prompt: str):
    """Ask for JSON. If the reply isn't valid JSON, retry once."""
    system = system + "\n\nReply with ONLY valid JSON. No commentary."
    raw = generate(system, prompt, json_mode=True)
    try:
        return _extract_json(raw)
    except (json.JSONDecodeError, ValueError):
        raw = generate(
            system, prompt + "\n\nYour previous reply was not valid JSON. Try again.", True
        )
        try:
            return _extract_json(raw)
        except (json.JSONDecodeError, ValueError) as e:
            raise LLMError("The AI did not return valid JSON.") from e
