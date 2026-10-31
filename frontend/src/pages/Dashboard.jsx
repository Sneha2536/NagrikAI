/**
 * Dashboard.jsx: Screen 1, the home page.
 * Nothing here is fake: "Recently viewed" comes from the user's own history (recent.js).
 */
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight, CheckCircle2, Clock, FileText, Globe, Search, ShieldCheck, Sparkles,
} from "lucide-react";
import { useLanguage } from "../LanguageContext.jsx";
import { getRecent } from "../recent.js";

const QUICK = [
  { to: "/explorer", icon: FileText, title: "Policy Explorer", text: "Discover official policies, schemes, notifications and circulars." },
  { to: "/explainer", icon: FileText, title: "Policy Explainer", text: "Turn complex policies into clear, cited explanations." },
  { to: "/eligibility", icon: CheckCircle2, title: "Eligibility Checker", text: "Understand which policy conditions may apply to you." },
];

export default function Dashboard() {
  const { t } = useLanguage();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const recent = getRecent();

  function go(e) {
    e.preventDefault();
    navigate(q.trim() ? `/explorer?q=${encodeURIComponent(q.trim())}` : "/explorer");
  }

  return (
    <>
      <section className="hero">
        <div className="hero-text">
          <div className="eyebrow">{t("hero.eyebrow").toUpperCase()}</div>
          <h1>
            {t("hero.title1")} <em>{t("hero.title2")}</em>
          </h1>
          <p>{t("hero.sub")}</p>
          <form className="hero-search" onSubmit={go}>
            <Search size={20} />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("hero.search")} />
            <button className="btn btn-primary" type="submit">
              {t("hero.cta")} <ArrowRight size={16} />
            </button>
          </form>
          <div className="hero-trust">
            <ShieldCheck size={15} /> {t("hero.trust")}
          </div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="ring r1" />
          <div className="ring r2" />
          <div className="ring r3" />
          <div className="float-card f1">
            <FileText size={20} />
            <div><strong>Simple language</strong><small>Clear explanations</small></div>
          </div>
          <div className="hero-core"><Sparkles size={34} /></div>
          <div className="float-card f2">
            <Globe size={20} />
            <div><strong>6 languages</strong><small>Built for India</small></div>
          </div>
        </div>
      </section>

      <h2 className="section-title">{t("quick.title")}</h2>
      <p className="section-sub">{t("quick.sub")}</p>
      <div className="quick-grid">
        {QUICK.map(({ to, icon: Icon, title, text }) => (
          <Link key={to} to={to} className="quick-card">
            <div className="quick-top">
              <div className="tile"><Icon size={22} /></div>
              <ArrowRight size={18} />
            </div>
            <h3>{title}</h3>
            <p>{text}</p>
          </Link>
        ))}
      </div>

      <div className="two-col">
        <section className="card">
          <div className="card-head">
            <div>
              <h2>Recently viewed</h2>
              <p className="section-sub">Policies and documents you open will appear here.</p>
            </div>
            <Link to="/explorer" className="link">View all <ArrowRight size={14} /></Link>
          </div>
          {recent.length === 0 ? (
            <div className="dashed">
              <div className="tile round"><Clock size={20} /></div>
              <div className="grow">
                <strong>No recently viewed policies</strong>
                <p>Explore official sources and open a policy to begin.</p>
              </div>
              <Link to="/explorer" className="btn btn-outline"><FileText size={15} /> Open explorer</Link>
            </div>
          ) : (
            <ul className="recent-list">
              {recent.map((p) => (
                <li key={p.id}>
                  <Link to={`/explainer/${p.id}`}>
                    <FileText size={17} />
                    <span className="grow"><strong>{p.title}</strong><small>{p.authority}</small></span>
                    <ArrowRight size={15} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card">
          <div className="tile"><ShieldCheck size={22} /></div>
          <h2>Built around official sources</h2>
          <p className="section-sub">
            NagrikAI grounds explanations in selected official documents and links each answer back to its source.
          </p>
          <ul className="checks">
            <li><CheckCircle2 size={15} /> Clause-level citations</li>
            <li><CheckCircle2 size={15} /> Multilingual explanations</li>
            <li><CheckCircle2 size={15} /> No uncited conclusions</li>
          </ul>
        </section>
      </div>
    </>
  );
}
