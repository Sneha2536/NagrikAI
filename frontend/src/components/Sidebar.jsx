import { NavLink } from "react-router-dom";
import { CheckCircle2, ChevronRight, FileText, Headphones, Home, Search, Target } from "lucide-react";
import { useLanguage } from "../LanguageContext.jsx";

const NAV = [
  { to: "/", key: "nav.dashboard", icon: Home, end: true },
  { to: "/explorer", key: "nav.explorer", icon: Search },
  { to: "/explainer", key: "nav.explainer", icon: FileText },
  { to: "/eligibility", key: "nav.eligibility", icon: CheckCircle2 },
];

export default function Sidebar() {
  const { t } = useLanguage();
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
            <Headphones size={18} />
          </div>
          <strong>Need help?</strong>
          <p>Learn how NagrikAI uses official sources.</p>
          <a href="#how-it-works" onClick={(e) => e.preventDefault()}>
            View help centre →
          </a>
        </div>
        <div className="account">
          <div className="avatar">AK</div>
          <div className="account-text">
            <strong>Citizen account</strong>
            <span>Personal workspace</span>
          </div>
          <ChevronRight size={16} />
        </div>
      </div>
    </aside>
  );
}
