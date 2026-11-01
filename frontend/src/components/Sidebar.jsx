/**
 * Sidebar.jsx: navigation, the "How it works" pop-up, and your device-only workspace.
 * There is no login: "recently viewed" lives in this browser (see recent.js) and can be cleared.
 */
import { useState } from "react";
import { NavLink } from "react-router-dom";
import { CheckCircle2, FileText, HardDrive, Home, Info, Search, Target, Trash2 } from "lucide-react";
import { useLanguage } from "../LanguageContext.jsx";
import { clearRecent, getRecent } from "../recent.js";
import HowItWorks from "./HowItWorks.jsx";

const NAV = [
  { to: "/", key: "nav.dashboard", icon: Home, end: true },
  { to: "/explorer", key: "nav.explorer", icon: Search },
  { to: "/explainer", key: "nav.explainer", icon: FileText },
  { to: "/eligibility", key: "nav.eligibility", icon: CheckCircle2 },
];

export default function Sidebar() {
  const { t } = useLanguage();
  const [showHow, setShowHow] = useState(false);
  const count = getRecent().length;

  function clearMyData() {
    if (!window.confirm("Remove your recently viewed list and settings from this browser?")) return;
    clearRecent();
    window.location.assign("/");
  }

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-logo">
          <Target size={22} />
        </div>
        <div>
          <div className="brand-name">
            Nagrik<span>AI</span>
          </div>
          <div className="brand-sub">CIVIC INTELLIGENCE</div>
        </div>
      </div>

      <div className="nav-label">WORKSPACE</div>
      <nav className="nav">
        {NAV.map(({ to, key, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}>
            <Icon size={19} />
            <span>{t(key)}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="help-card">
          <div className="help-icon">
            <Info size={18} />
          </div>
          <strong>How it works</strong>
          <p>See how every answer is checked against the official document.</p>
          <button type="button" className="link-btn" onClick={() => setShowHow(true)}>
            Learn how →
          </button>
        </div>
        <div className="account">
          <div className="avatar"><HardDrive size={18} /></div>
          <div className="account-text">
            <strong>Your workspace</strong>
            <span>Saved on this device · {count} recent</span>
          </div>
          <button type="button" className="icon-ghost" onClick={clearMyData} aria-label="Clear my data" title="Clear my data">
            <Trash2 size={16} />
          </button>
        </div>
      </div>
      {showHow && <HowItWorks onClose={() => setShowHow(false)} />}
    </aside>
  );
}
