/**
 * HowItWorks.jsx: a small pop-up that explains, in plain words, how NagrikAI avoids making things up.
 * Opened from the sidebar. (It is explanation text only; it contains no policy data.)
 */
import { useEffect } from "react";
import { CheckCircle2, X } from "lucide-react";

const STEPS = [
  ["Get the real document", "You paste an official .gov.in link, upload a PDF, or pick a release from the live PIB feed. We read the document itself."],
  ["Split it into pages", "Every page is kept, so each statement can point to an exact page and clause."],
  ["The AI writes with quotes", "The AI explains the policy in plain words, and for every point it must copy the exact sentence it relied on."],
  ["We check every quote", "Our code searches the original document for each quote. If the quote is not there, the point is deleted before you see it."],
  ["Your language, your voice", "Verified points are translated into six Indian languages and can be read aloud."],
];

export default function HowItWorks({ onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label="How NagrikAI works" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close"><X size={18} /></button>
        <div className="eyebrow dark">HOW IT WORKS</div>
        <h2>Every answer is checked against the document</h2>
        <ol className="how-steps">
          {STEPS.map(([title, text], i) => (
            <li key={title}><span className="how-num">{i + 1}</span><div><strong>{title}</strong><p>{text}</p></div></li>
          ))}
        </ol>
        <ul className="checks">
          <li><CheckCircle2 size={15} /> If the document does not contain the answer, NagrikAI says so instead of guessing.</li>
          <li><CheckCircle2 size={15} /> Uploaded files are labelled “not verified as official”.</li>
          <li><CheckCircle2 size={15} /> No account, no tracking: your history stays in this browser.</li>
        </ul>
      </div>
    </div>
  );
}
