# NagrikAI architecture

```mermaid
flowchart LR
    U[Citizen] --> FE[React frontend<br/>Dashboard · Explorer · Explainer · Eligibility]
    FE -->|/api| BE[FastAPI backend]

    subgraph Sources[Official sources: live]
      PIB[PIB RSS]
      MS[myScheme API]
    end
    BE -->|search| Sources
    BE --> PR[pdf_reader<br/>download + parse into pages]
    Sources --> PR
    UP[PDF upload] --> PR

    PR --> IDX[search_index<br/>BM25 retrieval]
    IDX --> LLM[llm.py<br/>Gemini or Claude]
    PR --> LLM
    LLM --> CIT[citations.py<br/>verify every quote<br/>drop unverified claims]
    CIT --> TR[translate.py<br/>6 languages]
    TR --> BE
    BE --> FE
    FE --> TTS[Browser speech synthesis<br/>Listen button]
```

## The anti-hallucination loop

1. The AI may only use the document text it is given.
2. For every point it must return an exact quote from that text.
3. `citations.py` searches the real document for the quote.
   Found: attach the true page and clause. Not found: the point is removed.
4. `/api/ask` refuses to answer when no verified citation exists.

## Folder map

| Folder | What lives there |
|---|---|
| `frontend/src/pages` | the 4 screens |
| `frontend/src/components` | reusable UI pieces |
| `backend/routes` | API endpoints the frontend calls |
| `backend/sources` | one connector per government source |
| `backend/ai` | LLM calls, prompts, retrieval, citations, translation |
| `data` | real documents downloaded at runtime + caches |
