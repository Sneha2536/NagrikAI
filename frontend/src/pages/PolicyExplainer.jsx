/**
 * PolicyExplainer.jsx: Screen 3, the original document (left) next to the AI explanation (right).
 *
 * Flow when the page opens with a policy id:
 *   1. getDocument()  -> pages of the real official document (left pane)
 *   2. explainPolicy() -> AI points, each with a verified page + clause (right pane)
 * Clicking a citation chip jumps the left pane to that page.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ChevronLeft, ChevronRight, ExternalLink, FileText, Globe, Link2, Minus, Plus, RefreshCw, Search, ShieldCheck, Sparkles,
} from "lucide-react";
import { explainPolicy, getDocument } from "../api.js";
import ChatBox from "../components/ChatBox.jsx";
import CitationChip from "../components/CitationChip.jsx";
import ListenButton from "../components/ListenButton.jsx";
import StateMessage from "../components/StateMessage.jsx";
import { useLanguage } from "../LanguageContext.jsx";
import { addRecent } from "../recent.js";
import { LANGUAGES } from "../translations.js";

const TABS = [
  { key: "simple", label: "tab.simple" },
  { key: "detailed", label: "tab.detailed" },
  { key: "benefits", label: "tab.benefits" },
];

export default function PolicyExplainer() {
  const { policyId } = useParams();
  const { lang, setLang, t } = useLanguage();

  const [doc, setDoc] = useState(null);
  const [docError, setDocError] = useState("");
  const [page, setPage] = useState(1);
  const [zoom, setZoom] = useState(100);

  const [expl, setExpl] = useState(null);
  const [explError, setExplError] = useState("");
  const [explLoading, setExplLoading] = useState(false);
  const [tab, setTab] = useState("simple");
  const explanationRequest = useRef(0);

  // 1) Load the original document whenever the policy changes
  useEffect(() => {
    setDoc(null); setDocError(""); setExpl(null); setExplError(""); setPage(1);
    if (!policyId) return;
    let cancelled = false;
    getDocument(policyId)
      .then((d) => {
        const validPages = Array.isArray(d?.pages) && d.pages.length > 0 && d.pages.every((p) =>
          Number.isInteger(Number(p?.number)) && Number(p.number) > 0 && typeof p.text === "string"
        );
        if (!d?.policy || !validPages) throw new Error("The server returned an invalid or empty document. Return to Policy Explorer and choose another source.");
        if (!cancelled) { setDoc({ ...d, pages: d.pages.map((p) => ({ ...p, number: Number(p.number) })) }); addRecent(d.policy); }
      })
      .catch((e) => !cancelled && setDocError(e.message));
    return () => { cancelled = true; };
  }, [policyId]);

  // 2) Load the AI explanation whenever policy or language changes
  const loadExplanation = useCallback(async (refresh = false) => {
    if (!policyId) return;
    const requestId = ++explanationRequest.current;
    setExplLoading(true); setExplError("");
    setExpl(null);
    try {
      const result = await explainPolicy(policyId, lang, refresh);
      const sections = result?.sections;
      if (!sections || typeof sections !== "object" || Array.isArray(sections)) {
        throw new Error("The server returned an invalid explanation. Please retry.");
      }
      const safeSections = Object.fromEntries(TABS.map(({ key }) => [
        key,
        Array.isArray(sections[key]) ? sections[key].filter((point) =>
          point && typeof point.text === "string" && Number.isInteger(Number(point.page)) && Number(point.page) > 0
        ) : [],
      ]));
      if (requestId === explanationRequest.current) setExpl({
        ...result,
        sections: safeSections,
        stats: {
          verified: Number.isFinite(result.stats?.verified) ? result.stats.verified : Object.values(safeSections).reduce((n, list) => n + list.length, 0),
          dropped: Number.isFinite(result.stats?.dropped) ? result.stats.dropped : 0,
        },
      });
    } catch (e) {
      if (requestId === explanationRequest.current) setExplError(e.message);
    } finally {
      if (requestId === explanationRequest.current) setExplLoading(false);
    }
  }, [policyId, lang]);

  useEffect(() => {
    loadExplanation(false);
    return () => { explanationRequest.current += 1; };
  }, [loadExplanation]);

  const points = Array.isArray(expl?.sections?.[tab]) ? expl.sections[tab] : [];
  const speakText = useMemo(() => points.map((p) => p.text).filter(Boolean).join(". "), [points]);
  const pageCount = doc?.pages.length || 0;
  const current = doc?.pages.find((p) => p.number === page);
  const policy = doc?.policy;

  return (
    <div className="explainer">
      <div className="explainer-bar">
        <div className="tile small"><FileText size={20} /></div>
        <div className="grow">
          <strong>{policy ? policy.title : "No policy selected"}</strong>
          <small>{policy ? `${policy.authority} · ${policy.source}` : "Choose a policy from Policy Explorer"}</small>
        </div>
        <label className="select-pill">
          <Globe size={17} />
          <select value={lang} onChange={(e) => setLang(e.target.value)} aria-label="Explanation language">
            {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
          </select>
        </label>
        <button className="btn btn-outline" disabled={!policyId || explLoading} onClick={() => loadExplanation(true)}>
          <RefreshCw size={16} className={explLoading ? "spin" : ""} /> {t("reanalyse")}
        </button>
        <Link to="/explorer" className="btn btn-primary"><Search size={16} /> Explore policies</Link>
      </div>

      <div className="split">
        {/* ---------- LEFT: original document ---------- */}
        <section className="doc-pane">
          <div className="pane-head">
            <span><FileText size={16} /> Original document</span>
            <div className="zoom">
              <button onClick={() => setZoom((z) => Math.max(70, z - 10))} aria-label="Zoom out"><Minus size={13} /></button>
              <span>{zoom}%</span>
              <button onClick={() => setZoom((z) => Math.min(160, z + 10))} aria-label="Zoom in"><Plus size={13} /></button>
            </div>
          </div>
          <div className="doc-body">
            {!policyId && (
              <StateMessage title="Your selected policy will appear here"
                text="Find an official policy or scheme in Policy Explorer, then choose “Understand This Policy”.">
                <Link to="/explorer" className="btn btn-outline"><Search size={16} /> Open Policy Explorer</Link>
                <Link to="/explorer#paste" className="btn btn-outline"><Link2 size={16} /> Paste an official link</Link>
              </StateMessage>
            )}
            {policyId && !doc && !docError && <StateMessage loading title="Fetching the official document…" />}
            {docError && <StateMessage title="Could not load this document" text={docError}>
              {policy?.url && <a className="btn btn-outline" href={policy.url} target="_blank" rel="noreferrer"><ExternalLink size={15} /> Open official source</a>}
            </StateMessage>}
            {current && (
              <div className="paper" style={{ fontSize: `${(zoom / 100) * 14}px` }}>
                <pre>{current.text}</pre>
              </div>
            )}
          </div>
          <div className="pager">
            <button disabled={page <= 1 || !doc} onClick={() => setPage((p) => p - 1)}><ChevronLeft size={15} /></button>
            <span>Page {doc ? page : "—"} of {doc ? pageCount : "—"}</span>
            <button disabled={!doc || page >= pageCount} onClick={() => setPage((p) => p + 1)}><ChevronRight size={15} /></button>
            {policy?.url && <a href={policy.url} target="_blank" rel="noreferrer" className="link"><ExternalLink size={13} /> Official source</a>}
          </div>
        </section>

        {/* ---------- RIGHT: AI explanation ---------- */}
        <section className="ai-pane">
          <div className="ai-scroll">
            <div className="ai-head">
              <div>
                <div className="eyebrow dark"><Sparkles size={13} /> AI EXPLANATION</div>
                <h2>Understand this policy</h2>
              </div>
              <ListenButton text={speakText} disabled={explLoading || !points.length} />
            </div>

            <div className="tabs">
              {TABS.map((x) => (
                <button key={x.key} className={tab === x.key ? "active" : ""} onClick={() => setTab(x.key)}>{t(x.label)}</button>
              ))}
            </div>

            <div className="ai-body">
              {!policyId && (
                <StateMessage title={`${t(TABS.find((x) => x.key === tab).label)} will appear here`}
                  text="Once a policy is selected, NagrikAI will explain this section and show matching source quotes when available." />
              )}
              {policyId && explLoading && <StateMessage loading title="Reading the policy…" text="Writing a plain-language explanation and checking every point against the document." />}
              {policyId && !explLoading && explError && <StateMessage title="Could not generate the explanation" text={explError} onRetry={() => loadExplanation(false)} />}

              {policyId && !explLoading && !explError && expl && (
                points.length === 0 ? (
                  <StateMessage title="Nothing verified for this section"
                    text="NagrikAI only shows points it could match to the original text. Try Re-analyse, or open the official document." />
                ) : (
                  <ol className="points">
                    {points.map((p, i) => (
                      <li key={i}>
                        <p>{p.text}</p>
                        <CitationChip page={p.page} clause={p.clause} quote={p.quote} onClick={setPage} pageLabel={doc?.is_pdf === false ? "Text segment" : "Page"} />
                      </li>
                    ))}
                  </ol>
                )
              )}

              {expl && !explLoading && !explError && (
                <div className="notice">
                  <ShieldCheck size={15} /> {expl.stats.verified} source quotes matched in the document
                  {expl.stats.dropped > 0 && `; ${expl.stats.dropped} unverifiable points were removed`}.
                </div>
              )}
            </div>
          </div>
          <ChatBox policyId={policyId} onCite={setPage} />
        </section>
      </div>
    </div>
  );
}
