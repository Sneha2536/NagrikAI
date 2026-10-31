/**
 * EligibilityChecker.jsx: Screen 4, a 3-step flow.
 *   Step 1  choose which policy to check
 *   Step 2  enter your details
 *   Step 3  review, then run the check
 * The three tabs on top show what the policy itself requires (eligibility / documents / process),
 * extracted by the AI and verified against the document.
 */
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, CheckCircle2, FileText, Info, Search, ShieldCheck, XCircle, HelpCircle } from "lucide-react";
import { checkEligibility, getRules } from "../api.js";
import { getFollowUpQuestions } from "../eligibilityRequests.js";
import CitationChip from "../components/CitationChip.jsx";
import StateMessage from "../components/StateMessage.jsx";
import { INDIAN_STATES } from "../constants.js";
import { useLanguage } from "../LanguageContext.jsx";
import { getRecent } from "../recent.js";

const STEPS = [
  { title: "Choose policy", sub: "Select the source to check" },
  { title: "Your details", sub: "Add relevant information" },
  { title: "Review", sub: "Confirm before checking" },
];
const EMPTY = { age: "", gender: "", state: "", annual_income: "", category: "", occupation: "", education: "", disability: null };
const VERDICTS = {
  eligible: { cls: "ok", text: "You appear to meet all stated criteria." },
  not_eligible: { cls: "bad", text: "You do not appear to meet at least one stated criterion." },
  need_more_info: { cls: "warn", text: "Some criteria could not be assessed from the details you gave." },
  no_criteria: { cls: "warn", text: "This document does not state clear eligibility criteria." },
};
const UNKNOWN_VERDICT = { cls: "warn", text: "The result could not be classified. Please review the source criteria or try again." };
const STATUS_LABELS = { met: "Satisfied", not_met: "Not satisfied", unknown: "Still unknown" };

export default function EligibilityChecker() {
  const { policyId: routeId } = useParams();
  const navigate = useNavigate();
  const { lang } = useLanguage();
  const recent = getRecent();

  const [tab, setTab] = useState("eligibility");
  const [step, setStep] = useState(0);
  const [policyId, setPolicyId] = useState(routeId || "");
  const [profile, setProfile] = useState(EMPTY);

  const [rules, setRules] = useState(null);
  const [rulesError, setRulesError] = useState("");
  const [rulesLoading, setRulesLoading] = useState(false);

  const [result, setResult] = useState(null);
  const [checking, setChecking] = useState(false);
  const [checkError, setCheckError] = useState("");
  const [followUpQuestions, setFollowUpQuestions] = useState([]);
  const [followUpAnswers, setFollowUpAnswers] = useState({});
  const [followUpsSubmitted, setFollowUpsSubmitted] = useState(false);

  const selected = recent.find((p) => p.id === policyId) || rules?.policy;
  const verdict = result ? (VERDICTS[result.verdict] || UNKNOWN_VERDICT) : null;

  // Load what the selected policy requires
  useEffect(() => {
    setRules(null); setRulesError(""); setResult(null); setFollowUpQuestions([]); setFollowUpAnswers({}); setFollowUpsSubmitted(false);
    if (!policyId) return;
    let cancelled = false;
    setRulesLoading(true);
    getRules(policyId)
      .then((r) => !cancelled && setRules(r))
      .catch((e) => !cancelled && setRulesError(e.message))
      .finally(() => !cancelled && setRulesLoading(false));
    return () => { cancelled = true; };
  }, [policyId]);

  function choose(id) {
    setPolicyId(id);
    navigate(`/eligibility/${id}`, { replace: true });
  }
  const set = (k) => (e) => {
    setProfile((p) => ({ ...p, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));
    setResult(null);
    setFollowUpQuestions([]);
    setFollowUpsSubmitted(false);
  };

  async function runCheck(answers = followUpAnswers, followUpSubmitted = followUpsSubmitted) {
    setChecking(true); setCheckError(""); setResult(null);
    const body = {
      age: profile.age === "" ? null : Number(profile.age),
      gender: profile.gender || null,
      state: profile.state || null,
      annual_income: profile.annual_income === "" ? null : Number(profile.annual_income),
      category: profile.category || null,
      occupation: profile.occupation.trim() || null,
      education: profile.education || null,
      disability: profile.disability,
    };
    try {
      const response = await checkEligibility(policyId, body, lang, answers, followUpSubmitted);
      if (!response || typeof response !== "object" || !Array.isArray(response.results)) {
        throw new Error("The server returned an invalid eligibility result. Please retry.");
      }
      setResult(response);
      const questions = getFollowUpQuestions(response);
      setFollowUpQuestions(followUpSubmitted ? [] : questions);
      if (followUpSubmitted) setFollowUpsSubmitted(true);
    } catch (e) {
      setCheckError(e.message);
    } finally {
      setChecking(false);
    }
  }

  function submitFollowUps(e) {
    e.preventDefault();
    runCheck(followUpAnswers, true);
  }

  function updateFollowUp(id, value) {
    setFollowUpAnswers((current) => ({ ...current, [id]: value }));
  }

  /* ---------- the three tabs that show what the policy requires ---------- */
  function RulesList({ items, empty, field = "text" }) {
    if (!policyId) return <StateMessage title="Select a policy first" text="Eligibility cannot be assessed without a verified source." />;
    if (rulesLoading) return <StateMessage loading title="Reading the policy…" />;
    if (rulesError) return <StateMessage title="Could not read this policy" text={rulesError} />;
    if (!items?.length) return <StateMessage title={empty} text="Only requirements found in the official text are shown." />;
    return (
      <ol className="points">
        {items.map((it, i) => (
          <li key={i}><p>{it[field]}</p><CitationChip page={it.page} clause={it.clause} quote={it.quote} onClick={() => window.open(rules?.policy?.url, "_blank")} /></li>
        ))}
      </ol>
    );
  }

  return (
    <>
      <div className="eyebrow">POLICY REQUIREMENTS</div>
      <h1 className="page-title">Eligibility Checker</h1>
      <p className="page-sub">Review eligibility conditions, required documents and application instructions extracted from the selected official policy.</p>

      <div className="big-tabs">
        {[["eligibility", "Eligibility"], ["documents", "Required Documents"], ["process", "Application Process"]].map(([k, label]) => (
          <button key={k} className={tab === k ? "active" : ""} onClick={() => setTab(k)}>{label}</button>
        ))}
      </div>

      {tab === "documents" && <section className="card"><RulesList items={rules?.documents} empty="No required documents stated" /></section>}
      {tab === "process" && <section className="card"><RulesList items={rules?.process} empty="No application steps stated" /></section>}

      {tab === "eligibility" && (
        <div className="elig-layout">
          <ol className="stepper">
            {STEPS.map((s, i) => (
              <li key={s.title} className={i === step ? "current" : i < step ? "done" : ""}>
                <span className="dot">{i + 1}</span>
                <div><strong>{s.title}</strong><small>{s.sub}</small></div>
              </li>
            ))}
            <li className="privacy"><ShieldCheck size={16} /> Your answers are used only for this check.</li>
          </ol>

          <section className="card step-card">
            <div className="progress"><span>STEP {step + 1} OF 3</span><div className="bar"><i style={{ width: `${((step + 1) / 3) * 100}%` }} /></div></div>

            {step === 0 && (
              <>
                <h2>Which policy do you want to check?</h2>
                <p className="section-sub">Choose an official policy from Policy Explorer. Eligibility cannot be assessed without a verified source.</p>
                {recent.length === 0 ? (
                  <label className="radio-card disabled">
                    <input type="radio" disabled />
                    <div className="tile small"><FileText size={20} /></div>
                    <div><strong>Select a policy in Policy Explorer</strong><small>No official policy is currently selected.</small></div>
                  </label>
                ) : recent.map((p) => (
                  <label key={p.id} className={"radio-card" + (policyId === p.id ? " selected" : "")}>
                    <input type="radio" name="policy" checked={policyId === p.id} onChange={() => choose(p.id)} />
                    <div className="tile small"><FileText size={20} /></div>
                    <div><strong>{p.title}</strong><small>{p.authority} · {p.source}</small></div>
                  </label>
                ))}
                <Link to="/explorer" className="link block"><Search size={15} /> Explore and select a policy</Link>
                <div className="notice"><Info size={15} /> You can continue to preview the flow, but the result will require a policy source.</div>
              </>
            )}

            {step === 1 && (
              <>
                <h2>Your details</h2>
                <p className="section-sub">Add only what you are comfortable sharing. Missing details are marked “could not be assessed”.</p>
                <div className="form-grid">
                  <label>Age<input type="number" min="0" max="120" value={profile.age} onChange={set("age")} /></label>
                  <label>Gender
                    <select value={profile.gender} onChange={set("gender")}>
                      <option value="">Prefer not to say</option><option>Female</option><option>Male</option><option>Transgender</option><option>Other</option>
                    </select>
                  </label>
                  <label>State / UT
                    <select value={profile.state} onChange={set("state")}><option value="">Select</option>{INDIAN_STATES.map((s) => <option key={s}>{s}</option>)}</select>
                  </label>
                  <label>Annual family income (₹)<input type="number" min="0" value={profile.annual_income} onChange={set("annual_income")} /></label>
                  <label>Social category
                    <select value={profile.category} onChange={set("category")}>
                      <option value="">Prefer not to say</option><option>General</option><option>OBC</option><option>SC</option><option>ST</option><option>EWS</option>
                    </select>
                  </label>
                  <label>Occupation<input value={profile.occupation} onChange={set("occupation")} placeholder="e.g. farmer, student" /></label>
                  <label>Education
                    <select value={profile.education} onChange={set("education")}>
                      <option value="">Select</option><option>Below Class 10</option><option>Class 10</option><option>Class 12</option><option>Graduate</option><option>Postgraduate</option>
                    </select>
                  </label>
                  <label className="check"><input type="checkbox" checked={profile.disability === true} onChange={set("disability")} /> Person with disability</label>
                </div>
              </>
            )}

            {step === 2 && (
              <>
                <h2>Review</h2>
                <p className="section-sub">Confirm before checking against <strong>{selected?.title || "no policy selected"}</strong>.</p>
                <dl className="review">
                  {Object.entries(profile).filter(([, v]) => v !== "" && v !== null).map(([k, v]) => (
                    <div key={k}><dt>{k.replace("_", " ")}</dt><dd>{String(v === true ? "Yes" : v === false ? "No" : v)}</dd></div>
                  ))}
                </dl>
                {!policyId && <div className="notice"><Info size={15} /> Select a policy in step 1 to run the check.</div>}
                {checkError && <div className="notice error"><Info size={15} /> {checkError}</div>}
                {checking && <StateMessage loading title="Checking each criterion…" />}

                {followUpQuestions.length > 0 && (
                  <form className="follow-up" onSubmit={submitFollowUps}>
                    <div className="notice"><Info size={15} /> A few source criteria need more information. These questions are based on the cited policy conditions.</div>
                    {followUpQuestions.map((question) => (
                      <fieldset className="follow-up-question" key={question.id}>
                        <legend>{question.question}</legend>
                        {question.criteria.map((criterion) => (
                          <div className="follow-up-criterion" key={criterion.criterion_id}>
                            <p>{criterion.text}</p>
                            <CitationChip page={criterion.page} clause={criterion.clause} quote={criterion.quote}
                              onClick={() => window.open(rules?.policy?.url, "_blank")} />
                          </div>
                        ))}
                        {question.answer_type === "choice" && <p className="follow-up-help">{question.answer_help}</p>}
                        {question.answer_type === "choice" ? (
                          <div className="follow-up-choices" role="radiogroup" aria-label={question.question}>
                            {["yes", "no", "not_sure"].map((answer) => (
                              <label key={answer} className={followUpAnswers[question.id] === answer ? "selected" : ""}>
                                <input type="radio" name={question.id} value={answer}
                                  checked={followUpAnswers[question.id] === answer}
                                  onChange={() => updateFollowUp(question.id, answer)} />
                                {answer === "not_sure" ? "Not sure" : answer === "yes" ? "Yes" : "No"}
                              </label>
                            ))}
                          </div>
                        ) : (
                          <div className="follow-up-input">
                            <input type={question.answer_type === "number" ? "number" : "text"}
                              min={question.answer_type === "number" ? "0" : undefined}
                              max={question.id === "field:age" ? "120" : undefined}
                            maxLength={question.answer_type === "text" ? 300 : undefined}
                              value={followUpAnswers[question.id] === "not_sure" ? "" : followUpAnswers[question.id] || ""}
                              disabled={followUpAnswers[question.id] === "not_sure"}
                              onChange={(event) => updateFollowUp(question.id, event.target.value)} />
                            <label className="check"><input type="checkbox" checked={followUpAnswers[question.id] === "not_sure"}
                              onChange={(event) => updateFollowUp(question.id, event.target.checked ? "not_sure" : "")} /> Not sure</label>
                          </div>
                        )}
                      </fieldset>
                    ))}
                    <button type="submit" className="btn btn-primary" disabled={checking}>
                      {checking ? "Reassessing…" : "Assess eligibility"} <ArrowRight size={16} />
                    </button>
                  </form>
                )}

                {result && followUpQuestions.length === 0 && (
                  <div className="result">
                    <div className={`verdict ${verdict.cls}`}>{verdict.text}</div>
                    <ul>
                      {(Array.isArray(result.results) ? result.results.filter((r) => r && typeof r === "object") : []).map((r, i) => (
                        <li key={i}>
                          {r.status === "met" ? <CheckCircle2 className="ok" size={18} /> : r.status === "not_met" ? <XCircle className="bad" size={18} /> : <HelpCircle className="warn" size={18} />}
                          <div><p>{r.criterion}</p><small className={`criterion-status ${r.status}`}>{STATUS_LABELS[r.status] || STATUS_LABELS.unknown}</small><small>{r.reason}</small>{r.manual_verification && <small className="criterion-status unknown">Requires manual verification</small>}</div>
                          <CitationChip page={r.page} clause={r.clause} onClick={() => window.open(rules?.policy?.url, "_blank")} />
                        </li>
                      ))}
                    </ul>
                    <p className="disclaimer">This is guidance based on the published text, not a final decision. The scheme authority decides eligibility.</p>
                  </div>
                )}
              </>
            )}

            <div className="step-actions">
              {step > 0 && <button className="btn btn-outline" onClick={() => setStep(step - 1)}><ArrowLeft size={16} /> Back</button>}
              <span className="grow" />
              {step < 2 ? (
                <button className="btn btn-primary" onClick={() => setStep(step + 1)}>Continue <ArrowRight size={16} /></button>
              ) : followUpQuestions.length === 0 ? (
                <button className="btn btn-primary" disabled={!policyId || checking} onClick={() => runCheck()}>Check eligibility <ArrowRight size={16} /></button>
              ) : null}
            </div>
          </section>
        </div>
      )}
    </>
  );
}
