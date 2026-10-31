/**
 * ChatBox.jsx: "Ask about this policy".
 * Sends the question to /api/ask. The backend only answers from this policy's text
 * and returns citations; if it can't find the answer it says so (it never guesses).
 */
import { useEffect, useRef, useState } from "react";
import { MessageSquare, Send, Sparkles } from "lucide-react";
import { askPolicy } from "../api.js";
import { useLanguage } from "../LanguageContext.jsx";
import CitationChip from "./CitationChip.jsx";

export default function ChatBox({ policyId, onCite }) {
  const { lang, t } = useLanguage();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  // Effects must not return a value (React treats it as a cleanup function), so use braces.
  useEffect(() => {
    setMessages([]);
  }, [policyId]);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function send(e) {
    e.preventDefault();
    const q = input.trim();
    if (!q || !policyId || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const r = await askPolicy(policyId, q, lang);
      setMessages((m) => [...m, { role: "ai", text: r.answer, citations: r.citations, refused: !r.answerable }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "ai", text: err.message, error: true }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="chat">
      <div className="chat-head">
        <div className="chat-icon">
          <MessageSquare size={18} />
        </div>
        <div>
          <strong>{t("ask.title")}</strong>
          <small>{policyId ? "Answers use only this policy" : "No policy selected"}</small>
        </div>
      </div>

      <div className="chat-log">
        {messages.length === 0 && (
          <p className="chat-hint">
            <Sparkles size={15} /> Ask a follow-up question. Answers will use only this policy and cited official sources.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role} ${m.error ? "error" : ""} ${m.refused ? "refused" : ""}`}>
            <p>{m.text}</p>
            {m.citations?.map((c, j) => (
              <CitationChip key={j} {...c} onClick={onCite} />
            ))}
          </div>
        ))}
        {busy && <div className="bubble ai typing">Searching the document…</div>}
        <div ref={endRef} />
      </div>

      <form className="chat-input" onSubmit={send}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={policyId ? "Ask a question about this policy" : "Select a policy to ask a question"}
          disabled={!policyId || busy}
        />
        <button type="submit" disabled={!policyId || busy || !input.trim()} aria-label="Send">
          <Send size={18} />
        </button>
      </form>
    </section>
  );
}
