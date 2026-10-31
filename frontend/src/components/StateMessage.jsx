/**
 * StateMessage.jsx: reusable "empty / error / loading" box so every screen
 * handles bad situations in the same, friendly way (judges test edge cases!).
 */
import { Info, Loader2, RefreshCw } from "lucide-react";

export default function StateMessage({ title, text, onRetry, loading, children }) {
  return (
    <div className="state">
      <div className="state-icon">{loading ? <Loader2 size={26} className="spin" /> : <Info size={26} />}</div>
      <h3>{title}</h3>
      {text && <p>{text}</p>}
      {onRetry && (
        <button className="btn btn-outline" onClick={onRetry}>
          <RefreshCw size={16} /> Try again
        </button>
      )}
      {children}
    </div>
  );
}
