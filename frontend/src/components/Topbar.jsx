/**
 * Topbar.jsx: breadcrumb, the language dropdown (changes the whole app, see LanguageContext.jsx),
 * and the "Add document" shortcut (paste an official link or upload a PDF).
 */
import { Link, useLocation } from "react-router-dom";
import { ChevronDown, Globe, Plus } from "lucide-react";
import { useLanguage } from "../LanguageContext.jsx";
import { LANGUAGES } from "../translations.js";

const CRUMBS = {
  "/": ["Citizen dashboard", "Good morning"],
  "/explorer": ["Official policy discovery", "Policy Explorer"],
  "/explainer": ["Understand official documents", "Policy Explainer"],
  "/eligibility": ["Check policy conditions", "Eligibility Checker"],
};

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

export default function Topbar() {
  const { pathname } = useLocation();
  const { lang, setLang } = useLanguage();
  const base = "/" + pathname.split("/")[1];
  const [parent, current] = CRUMBS[base] || CRUMBS["/"];

  return (
    <header className="topbar">
      <div className="crumbs">
        <span>{parent}</span>
        <span className="sep">›</span>
        <strong>{base === "/" ? greeting() : current}</strong>
      </div>
      <div className="topbar-actions">
        <label className="select-pill">
          <Globe size={17} />
          <select value={lang} onChange={(e) => setLang(e.target.value)} aria-label="Language">
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
          <ChevronDown size={13} />
        </label>
        <Link to="/explorer#paste" className="btn btn-primary">
          <Plus size={17} /> Add document
        </Link>
      </div>
    </header>
  );
}
