"""
translate.py: English -> Indian languages using the AI model.

We translate all the text of an explanation in ONE call (fast + consistent).
Citations (page, clause, quote) are never translated: they point at the original document.
"""
from ai.llm import LLMError, generate_json
from ai.prompts import TRANSLATE_SYSTEM
import json
import re

LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
}


def translate_texts(texts: list[str], lang: str, force: bool = False) -> list[str]:
    if (lang == "en" and not force) or not texts:
        return texts
    if lang not in LANGUAGES:
        raise LLMError(f"Unsupported language: {lang}")
    result = generate_json(
        TRANSLATE_SYSTEM, json.dumps({"target": LANGUAGES[lang], "texts": texts}, ensure_ascii=False)
    )
    out = result.get("texts") if isinstance(result, dict) else None
    if not isinstance(out, list) or len(out) != len(texts):
        raise LLMError("Translation came back in the wrong shape. Please try again.")
    return [str(t) for t in out]


def translate_sections(sections: dict, lang: str) -> dict:
    """sections = {"simple": [point, ...], "detailed": [...], ...}. Returns a translated copy."""
    if lang == "en":
        return sections
    flat = [(name, i) for name, pts in sections.items() for i in range(len(pts))]
    translated = translate_texts([sections[n][i]["text"] for n, i in flat], lang)
    out = {name: [dict(p) for p in pts] for name, pts in sections.items()}
    for (name, i), text in zip(flat, translated):
        out[name][i]["text"] = text
    return out


_INDIAN_SCRIPT = re.compile(r"[\u0900-\u0DFF]")  # Devanagari, Bengali, Tamil, Telugu, ...


def ensure_english(sections: dict) -> dict:
    """
    Safety net: the prompt asks the AI to write in English, but if any point still came back
    in an Indian script (e.g. copied from a Hindi document), translate just those points.
    """
    todo = [
        (name, i)
        for name, pts in sections.items()
        for i, p in enumerate(pts)
        if _INDIAN_SCRIPT.search(p["text"])
    ]
    if not todo:
        return sections
    fixed = translate_texts([sections[n][i]["text"] for n, i in todo], "en", force=True)
    out = {name: [dict(p) for p in pts] for name, pts in sections.items()}
    for (n, i), text in zip(todo, fixed):
        out[n][i]["text"] = text
    return out
