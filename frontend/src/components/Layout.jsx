/**
 * Layout.jsx: the frame around every page (sidebar on the left, top bar on top).
 * <Outlet /> is where the current page appears.
 */
import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { getHealth } from "../api.js";
import { BUILD } from "../constants.js";
import { useLocation } from "react-router-dom";
import ErrorBoundary from "./ErrorBoundary.jsx";
import Sidebar from "./Sidebar.jsx";
import Topbar from "./Topbar.jsx";

export default function Layout() {
  const { pathname } = useLocation();
  const [stale, setStale] = useState(false);

  // If the backend is an older version than this frontend, say so plainly.
  useEffect(() => {
    getHealth().then((h) => setStale(h.build !== BUILD)).catch(() => {});
  }, []);
  return (
    <div className="shell">
      <Sidebar />
      <div className="main-col">
        {stale && (
          <div className="stale-banner">
            Your backend is running an older version. Press Ctrl+C in its terminal, then start it again:
            <code>uvicorn main:app --reload --port 8000</code>
          </div>
        )}
        <Topbar />
        <main className="content">
          {/* key={pathname} resets the boundary when you navigate away from a crashed page */}
          <ErrorBoundary key={pathname}>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
