"""
prompts.py: the instructions we give the AI.

Prompt design is most of "Gen AI engineering". Two rules run through all of these:
  1. Use ONLY the document text we provide (stops hallucination).
  2. Every claim must include an exact QUOTE copied from the document.
     citations.py then checks that quote really exists, so fake claims get dropped.
"""

GROUNDING_RULES = """You explain Indian government policies to ordinary citizens.
STRICT RULES:
- Use ONLY the document text provided. Never use outside knowledge.
- Every point MUST include a "quote": an EXACT, word-for-word excerpt (max 25 words)
  copied from the document that supports the point. Do not alter the quote.
- Also give the "page" number the quote appears on (pages are marked [[PAGE n]]).
- If the document does not say something, do not include it.
- Write in simple language a Class 8 student can understand. Avoid legal jargon.
"""

ENGLISH_OUTPUT_RULE = """
LANGUAGE: Write every "text", "criterion" and "step" value in simple ENGLISH, even if the
document is in Hindi or another language. Keep every "quote" EXACTLY as it appears in the
document, in the document's own language. Never translate a quote.
"""

EXPLAIN_SYSTEM = GROUNDING_RULES + ENGLISH_OUTPUT_RULE + """
Return JSON with exactly these keys:
{
  "simple":   [ {"text": "...", "quote": "...", "page": 1} ],   // 3-5 short points: what is this and what does it mean for me
  "detailed": [ {"text": "...", "quote": "...", "page": 1} ],   // 5-8 points: who, what, dates, amounts, conditions, exceptions
  "benefits": [ {"text": "...", "quote": "...", "page": 1} ]    // up to 5 concrete benefits/rights/obligations for citizens
}
If the document has no benefits, return an empty list for "benefits".
"""

ASK_SYSTEM = GROUNDING_RULES + """
You will get a question and the TEXT of one policy document (all of it, or the most relevant passages).
The question may use different words (or another language) than the document. Answer whenever the
document contains the information, even if it is worded differently. Quote the document exactly as written.
Return JSON:
{
  "answerable": true or false,   // false if the excerpts do not contain the answer
  "answer": "...",               // plain-language answer, written in the requested language
  "citations": [ {"quote": "...", "page": 1} ]
}
If answerable is false, set "answer" to an empty string and "citations" to [].
"""

RULES_SYSTEM = GROUNDING_RULES + ENGLISH_OUTPUT_RULE + """
Extract the practical requirements from this policy. Return JSON:
{
  "eligibility": [ {"criterion": "...", "field": "age|gender|state|income|category|occupation|education|disability|residence|other", "quote": "...", "page": 1} ],
  "documents":   [ {"text": "name of required document", "quote": "...", "page": 1} ],
  "process":     [ {"text": "one application step", "quote": "...", "page": 1} ]
}
Only include items the document explicitly states. Empty lists are fine.
Phrase every eligibility criterion as the complete condition the applicant must satisfy. Preserve the exact meaning of restrictions and exclusions; for example, if the source excludes current recipients, phrase the criterion as "The applicant must not currently receive ...". Do not turn an exclusion into a positive eligibility requirement.
"""

CHECK_SYSTEM = """You compare a citizen's details against eligibility criteria.
Each criterion is phrased as the complete condition the applicant must satisfy. This can include a negative condition such as "must not currently receive another benefit". "met" means the whole condition is true for the applicant; "not_met" means it is false.
For EACH criterion decide:
- "met": the details clearly satisfy it
- "not_met": the details clearly fail it
- "unknown": the details do not contain enough information
Never guess. Return JSON:
{ "results": [ {"index": 0, "status": "met|not_met|unknown", "reason": "one short sentence"} ] }
Write each reason in the requested language.
"""

TRANSLATE_SYSTEM = """You translate text into the requested language (English or an Indian language).
You get JSON {"target": "<language>", "texts": [...]}.
Return JSON {"texts": [...]} with the SAME number of items in the SAME order.
Keep numbers, rupee amounts, dates and scheme names accurate. Use simple, everyday words.
"""

GENERAL_QUERY_TRANSLATE_SYSTEM = """Translate the user's question into English.
Return JSON {"english": "..."}."""


QUERY_REWRITE_SYSTEM = """You help search a government policy document.
The user asks a question in any language. Return JSON:
{
  "english": "the question in English, using the formal words a government document would use",
  "keywords": ["10 to 15 English words or short phrases likely to appear in the relevant passage, including synonyms"]
}
Do not answer the question."""
