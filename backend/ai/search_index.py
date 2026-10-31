"""
search_index.py: finds the RIGHT parts of a document for a question (the "R" in RAG).

Idea: a long document is cut into small chunks. When the user asks something we score
every chunk against the question (BM25, the classic keyword-ranking formula) and send
only the best few chunks to the AI. Less text = cheaper, faster, fewer hallucinations.

No external library needed; BM25 is implemented below in ~30 lines.
"""
import math
import re
from collections import Counter

from pdf_reader import Document

_TOKEN = re.compile(r"\w+", re.UNICODE)
_STOP = {
    "the", "a", "an", "of", "to", "and", "or", "in", "on", "for", "is", "are", "be",
    "by", "with", "as", "at", "this", "that", "it", "from", "shall", "will", "may",
}


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


def chunk_document(doc: Document, size: int = 900, overlap: int = 150) -> list[dict]:
    """Split each page into overlapping windows. Each chunk remembers its page."""
    chunks = []
    for page in doc.pages:
        text = page.text
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunks.append({"page": page.number, "text": text[start:end]})
            if end == len(text):
                break
            start = end - overlap
    return chunks


class BM25Index:
    def __init__(self, chunks: list[dict], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(c["text"])) for c in chunks]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = (sum(self.lengths) / len(self.lengths)) if self.lengths else 0
        df = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 5) -> list[dict]:
        q_tokens = tokenize(query)
        scored = []
        for i, doc in enumerate(self.docs):
            score = 0.0
            for t in q_tokens:
                if t not in doc:
                    continue
                tf = doc[t]
                denom = tf + self.k1 * (
                    1 - self.b + self.b * self.lengths[i] / (self.avg_len or 1)
                )
                score += self.idf.get(t, 0) * tf * (self.k1 + 1) / denom
            if score > 0:
                scored.append((score, i))
        scored.sort(reverse=True)
        return [{**self.chunks[i], "score": round(s, 3)} for s, i in scored[:k]]


_cache: dict[str, BM25Index] = {}


def get_index(doc: Document) -> BM25Index:
    """Build the index once per document, then reuse it."""
    if doc.policy_id not in _cache:
        _cache[doc.policy_id] = BM25Index(chunk_document(doc))
    return _cache[doc.policy_id]
