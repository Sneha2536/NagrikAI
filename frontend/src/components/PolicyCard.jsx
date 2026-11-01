/**
 * PolicyCard.jsx: one search result in Policy Explorer.
 * Every result has the three actions promised in the design:
 *   Open Official Document · Understand This Policy · Share Policy Link
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { Check, ExternalLink, FileText, Share2 } from "lucide-react";

export default function PolicyCard({ policy }) {
  const [copied, setCopied] = useState(false);

  async function share() {
    const link = `${window.location.origin}/explainer/${policy.id}`;
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      window.prompt("Copy this link:", link);
    }
  }

  return (
    <article className="policy-card">
      <div className="policy-meta">
        <span className="tag">{policy.source}</span>
        {policy.category && <span className="tag tag-soft">{policy.category}</span>}
        {policy.published && <span className="meta-date">Published {policy.published}</span>}
      </div>
      <h3>{policy.title}</h3>
      <p className="policy-authority">{policy.authority}</p>
      {policy.summary && <p className="policy-summary">{policy.summary}</p>}
      <div className="policy-actions">
        {policy.url && (
          <a className="btn btn-outline" href={policy.url} target="_blank" rel="noreferrer">
            <ExternalLink size={15} /> Open Official Document
          </a>
        )}
        <Link className="btn btn-primary" to={`/explainer/${policy.id}`}>
          <FileText size={15} /> Understand This Policy
        </Link>
        <button className="btn btn-ghost" onClick={share}>
          {copied ? <Check size={15} /> : <Share2 size={15} />} {copied ? "Link copied" : "Share Policy Link"}
        </button>
      </div>
    </article>
  );
}
