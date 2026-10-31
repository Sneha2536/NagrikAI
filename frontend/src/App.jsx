/**
 * App.jsx: the map of the website.
 * Each <Route> says "when the URL is X, show page Y".
 * Layout wraps every page with the sidebar + top bar.
 */
import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import PolicyExplorer from "./pages/PolicyExplorer.jsx";
import PolicyExplainer from "./pages/PolicyExplainer.jsx";
import EligibilityChecker from "./pages/EligibilityChecker.jsx";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/explorer" element={<PolicyExplorer />} />
        <Route path="/explainer" element={<PolicyExplainer />} />
        <Route path="/explainer/:policyId" element={<PolicyExplainer />} />
        <Route path="/eligibility" element={<EligibilityChecker />} />
        <Route path="/eligibility/:policyId" element={<EligibilityChecker />} />
      </Route>
    </Routes>
  );
}
