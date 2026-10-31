/**
 * CitationChip.jsx: the small "Page 3 · Clause 5" tag under every AI statement.
 * Clicking it tells the page to jump the document viewer to that page.
 * Hovering shows the exact quote from the official document.
 */
import { ExternalLink } from "lucide-react";

export default function CitationChip({ page, clause, quote, onClick, pageLabel = "Page" }) {
  if (!Number.isInteger(Number(page)) || Number(page) < 1) return null;
  return (
    <button className="chip" onClick={() => onClick?.(Number(page))} title={quote ? `"${quote}"` : undefined}>
      {pageLabel} {page}
      {clause ? ` · ${clause}` : ""}
      <ExternalLink size={12} />
    </button>
  );
}
