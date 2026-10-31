/**
 * PolicyExplorer.jsx: Screen 2, search official policies.
 *
 * Flow: user types / picks filters -> api.searchPolicies() -> backend asks PIB, myScheme...
 *       -> list of PolicyCards. If a source is down we say so honestly (no fake results).
 */
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, ExternalLink, Info, Link2, Loader2, Search, ShieldCheck } from "lucide-react";
import { addPolicyFromUrl, searchPolicies } from "../api.js";
import PolicyCard from "../components/PolicyCard.jsx";
import StateMessage from "../components/StateMessage.jsx";
import { BENEFICIARIES, DATE_OPTIONS, INDIAN_STATES, OFFICIAL_SITES } from "../constants.js";

export default function PolicyExplorer() {
  const [searchParams] = useSearchParams();
  const [text, setText] = useState(searchParams.get("q") || "");
  const [filters, setFilters] = useState({ q: searchParams.get("q") || "", ministry: "", state: "", category: "", date: "", beneficiary: "", policy_only: "" });
  const [data, setData] = useState(null);       // { items, sources }
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);        // bump to force a reload ("Try again")
  const [ministries, setMinistries] = useState([]);
  const [categories, setCategories] = useState([]);

  // "Paste a link" box: add any official document (gazette PDF, scheme guideline, draft policy)
  const navigate = useNavigate();
  const [link, setLink] = useState("");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState("");

  useEffect(() => {
    if (window.location.hash === "#paste") document.getElementById("paste")?.scrollIntoView({ behavior: "smooth" });
  }, []);

  async function addLink(e) {
    e.preventDefault();
    setAdding(true);
    setAddError("");
    try {
      const policy = await addPolicyFromUrl(link.trim());
      navigate(`/explainer/${policy.id}`);
    } catch (err) {
      setAddError(err.message);
    } finally {
      setAdding(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    searchPolicies(filters)
      .then((res) => {
        if (cancelled) return;
        setData(res);
        // Build dropdown options from what the real sources actually returned.
        setMinistries((prev) => [...new Set([...prev, ...res.items.map((p) => p.authority)])].sort());
        setCategories((prev) => [...new Set([...prev, ...res.items.map((p) => p.category).filter(Boolean)])].sort());
      })
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [filters, nonce]);

  const set = (key) => (e) => setFilters((f) => ({ ...f, [key]: e.target.value }));
  // "skipped" = optional source with no API key. That is not a failure, so we don't warn about it.
  const active = data?.sources.filter((s) => !s.skipped) || [];
  const failed = active.filter((s) => !s.ok);
  const allFailed = data && active.length > 0 && failed.length === active.length;
  const pibCount = data?.sources.find((s) => s.source === "PIB")?.count || 0;
  const policyOnly = filters.policy_only !== "false";

  function submit(e) {
    e.preventDefault();
    setFilters((f) => ({ ...f, q: text.trim() }));
  }

  return (
    <>
      <div className="eyebrow">OFFICIAL POLICY DISCOVERY</div>
      <h1 className="page-title">Policy Explorer</h1>
      <p className="page-sub">Search government policies, schemes, notifications and circulars across trusted official sources.</p>

      <form className="card search-card" onSubmit={submit}>
        <div className="search-row">
          <Search size={19} />
          <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Search by policy, scheme, topic or issuing authority…" />
          <button className="btn btn-primary" type="submit"><Search size={17} /> Search official sources</button>
        </div>
        <div className="filters">
          <label>Ministry or department
            <select value={filters.ministry} onChange={set("ministry")}>
              <option value="">All ministries and departments</option>
              {ministries.map((m) => <option key={m}>{m}</option>)}
            </select>
          </label>
          <label>State
            <select value={filters.state} onChange={set("state")}>
              <option value="">All states and Union Territories</option>
              {INDIAN_STATES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </label>
          <label>Category
            <select value={filters.category} onChange={set("category")}>
              <option value="">All categories</option>
              {categories.map((c) => <option key={c}>{c}</option>)}
            </select>
          </label>
          <label>Publication date
            <select value={filters.date} onChange={set("date")}>
              {DATE_OPTIONS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
            </select>
          </label>
        </div>
      </form>

      <form id="paste" className="card add-card" onSubmit={addLink}>
        <div>
          <strong>Have a gazette notification, scheme guideline or draft policy?</strong>
          <p className="section-sub">Paste the link to the official PDF or page (.gov.in or .nic.in) and NagrikAI will explain it.</p>
        </div>
        <div className="search-row">
          <Link2 size={19} />
          <input value={link} onChange={(e) => setLink(e.target.value)} placeholder="https://…gov.in/…/notification.pdf" />
          <button className="btn btn-primary" type="submit" disabled={adding || !link.trim()}>
            {adding ? <Loader2 size={17} className="spin" /> : <ArrowRight size={17} />} {adding ? "Reading…" : "Explain this document"}
          </button>
        </div>
        {addError && <div className="notice error"><Info size={15} /> {addError}</div>}
      </form>

      <div className="bene-row">
        <div>
          <h2>Explore by beneficiary</h2>
          <p className="section-sub">Discover information relevant to you or someone you are helping.</p>
        </div>
        <div className="pills">
          {BENEFICIARIES.map((b) => (
            <button key={b.value} className={"pill" + (filters.beneficiary === b.value ? " active" : "")}
              onClick={() => setFilters((f) => ({ ...f, beneficiary: b.value }))}>
              {b.label}
            </button>
          ))}
        </div>
      </div>

      <section className="card results">
        <div className="card-head">
          <div>
            <h2>{filters.q ? `Results for “${filters.q}”` : "Recently published or updated"}</h2>
            <p className="section-sub">Results include issuing authority, publication dates, descriptions and original sources.</p>
            <label className="toggle">
              <input type="checkbox" checked={policyOnly}
                onChange={(e) => setFilters((f) => ({ ...f, policy_only: e.target.checked ? "" : "false" }))} />
              Policy-related only <small>(hides speeches, visits and events{pibCount ? `; PIB returned ${pibCount} recent releases` : ""})</small>
            </label>
          </div>
          <span className="official-only"><ShieldCheck size={14} /> Official sources only</span>
        </div>
        <hr />

        {loading && <StateMessage loading title="Searching official sources…" text="Contacting government portals in real time." />}

        {!loading && error && (
          <StateMessage title="Live policy discovery is currently unavailable" text={error} onRetry={() => setNonce((n) => n + 1)} />
        )}

        {!loading && !error && allFailed && (
          <StateMessage title="Live policy discovery is currently unavailable"
            text="None of the official sources responded, so NagrikAI will not display unverified or fabricated policy information."
            onRetry={() => setNonce((n) => n + 1)}>
            <ul className="source-errors">{failed.map((s) => <li key={s.source}><strong>{s.source}:</strong> {s.error}</li>)}</ul>
          </StateMessage>
        )}

        {!loading && !error && data && !allFailed && (
          <>
            {failed.length > 0 && (
              <div className="notice">
                <Info size={15} /> Some sources are unavailable right now: {failed.map((s) => `${s.source} (${s.error})`).join("; ")}
              </div>
            )}
            {data.items.length === 0 ? (
              <StateMessage title="No matching policies"
                text={policyOnly && pibCount > 0
                  ? `PIB returned ${pibCount} recent releases, but none look like policies or schemes. Untick “Policy-related only” to see them, or paste a link to a real notification or guideline above.`
                  : "Try a different keyword or clear some filters."} />
            ) : (
              <div className="policy-list">{data.items.map((p) => <PolicyCard key={p.id} policy={p} />)}</div>
            )}
          </>
        )}
      </section>

      <div className="browse-row">
        <div>
          <h2>Browse official sources directly</h2>
          <p className="section-sub">Open the original government portals in a new tab.</p>
        </div>
        <div className="pills">
          {OFFICIAL_SITES.map((s) => (
            <a key={s.label} className="btn btn-outline" href={s.url} target="_blank" rel="noreferrer">
              <ExternalLink size={15} /> {s.label} <ArrowRight size={14} />
            </a>
          ))}
        </div>
      </div>
      <div className="notice big">
        <Info size={16} /> Every result provides <b>Open Official Document</b>, <b>Understand This Policy</b> and <b>Share Policy Link</b> actions. No result is shown without a verified official source.
      </div>
    </>
  );
}
