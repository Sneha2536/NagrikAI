# NagrikAI: Civic Intelligence

Hackathon: Forge (Gen AI buildathon) · Theme 1: Civic Pulse, Digital Governance & Public Information
Problem: **Multilingual Policy, Rights & Scheme Explainer**

NagrikAI fetches real government documents, explains them in plain language in six Indian
languages, and links every statement to the exact page and clause it came from. Statements
the AI cannot prove from the document are removed.

## Features

- **Policy Explorer**: live search across official sources (PIB releases with a "Policy-related only" switch, myScheme), filters, beneficiary chips
- **Paste a link**: add any official document (gazette PDF, scheme guideline, draft policy) from a .gov.in / .nic.in address
- **Policy Explainer**: original document beside a Simple / Detailed / Key Benefits explanation, with citations
- **Ask about this policy**: Q&A using retrieval (RAG) over only that document; refuses when unsure
- **Eligibility Checker**: criteria, required documents and application steps extracted from the policy, then matched to your details
- **Languages**: English, Hindi, Bengali, Tamil, Telugu, Marathi · **Listen** button reads explanations aloud

## Architecture

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

    PR --> IDX[search_index<br/>BM25 retrieval]
    IDX --> LLM[llm.py<br/>Gemini or Claude]
    PR --> LLM
    LLM --> CIT[citations.py<br/>verify every quote<br/>drop unverified claims]
    CIT --> TR[translate.py<br/>6 languages]
    TR --> BE
    BE --> FE
    FE --> TTS[Browser speech synthesis<br/>Listen button]
```

More detail: [docs/architecture.md](docs/architecture.md).

```
frontend/   React (Vite)      what the user sees
backend/    FastAPI (Python)  fetches documents, calls the AI, verifies citations
data/       real downloaded documents and caches (created at runtime)
```

## Setup

You need **Node 18+** and **Python 3.10+**.

### 1. Keys
```bash
cp .env.example .env
# open .env and add GEMINI_API_KEY (free at https://aistudio.google.com/apikey)
```

### 2. Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python ../scripts/check_sources.py   # tests the live government sources
uvicorn main:app --reload --port 8000
```
Open http://localhost:8000/docs to try every endpoint.

### 3. Frontend (new terminal)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173.

### Tests
```bash
cd backend && pytest
```

## Data sources (no dummy data)

| Source | Status | Notes |
|---|---|---|
| PIB (pib.gov.in) | Works without a key | RSS feed of recent releases. Releases that look like policies are tagged and shown by default; untick "Policy-related only" to see all. These are announcements, not full policy documents |
| Pasted official link | Works without a key | Best source for real notifications, guidelines and draft policies |
| myScheme | Needs `MYSCHEME_API_KEY` | Undocumented API; run `check_sources.py` and adjust `sources/myscheme.py` if the response format differs |
| e-Gazette, India Code | Link-out only | Add a connector in `backend/sources/` (see `pib.py` as a template) |

If a source is down the app says so; it never fills the screen with made-up policies.

## Things to verify before the demo

1. `python scripts/check_sources.py` shows at least PIB returning policies.
2. Government sites with an incomplete certificate: `pip install -r requirements.txt` installs `truststore`, which uses your system certificates. If a link still fails, set `PDF_CA_BUNDLE` in `.env`.
3. The `GEMINI_MODEL` name in `.env` is currently valid (Google renames models). If the model is often busy, set `GEMINI_FALLBACK_MODEL` too.
4. Pick 2-3 policies, open each once so documents and explanations are cached (real data, saved locally), in case a government site is slow during judging.
5. Every team member can walk through: `routes/explain.py` -> `ai/citations.py` -> `ai/search_index.py`.

## Folder guide

```
backend/
  main.py              starts the server
  config.py            reads .env
  pdf_reader.py        document -> numbered pages
  routes/              API endpoints (policies, explain, ask, eligibility)
  sources/             government source connectors (+ registry.py combines them)
  ai/                  llm.py · prompts.py · search_index.py · citations.py · translate.py
  tests/               citation and retrieval tests
frontend/src/
  pages/               Dashboard, PolicyExplorer, PolicyExplainer, EligibilityChecker
  components/          Sidebar, Topbar, PolicyCard, CitationChip, ListenButton, ChatBox, ...
  api.js               every backend call
  translations.js      interface text in 6 languages
```
