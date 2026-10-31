/**
 * ListenButton.jsx: reads the explanation aloud.
 *
 * Uses the browser's built-in text-to-speech (window.speechSynthesis): free, no API key.
 *
 * Why this file is careful:
 *  - It looks at the TEXT to decide the language (Devanagari -> Hindi, Tamil script -> Tamil...),
 *    so Hindi text is never read with an English voice (which stays silent or garbles it).
 *  - It picks a real installed voice for that language and says so if none exists.
 *  - Voices load late in Chrome/Edge, so it waits for them.
 *  - Long text is read in short pieces; browsers silently stop long utterances.
 */
import { useEffect, useState } from "react";
import { Square, Volume2 } from "lucide-react";
import { useLanguage } from "../LanguageContext.jsx";
import { LANGUAGES } from "../translations.js";

const SCRIPTS = [
  [/[ऀ-ॿ]/, "hi"],  // Devanagari (Hindi / Marathi)
  [/[ঀ-৿]/, "bn"],  // Bengali
  [/[஀-௿]/, "ta"],  // Tamil
  [/[ఀ-౿]/, "te"],  // Telugu
];

function detectLang(text, selected) {
  for (const [re, code] of SCRIPTS) {
    if (re.test(text)) return code === "hi" && selected === "mr" ? "mr" : code;
  }
  return "en";
}

function loadVoices() {
  const synth = window.speechSynthesis;
  return new Promise((resolve) => {
    const now = synth.getVoices();
    if (now.length) return resolve(now);
    const done = () => resolve(synth.getVoices());
    synth.addEventListener("voiceschanged", done, { once: true });
    setTimeout(done, 1500);
  });
}

function pickVoice(voices, code) {
  const full = LANGUAGES.find((l) => l.code === code)?.speech.toLowerCase();
  const norm = (v) => v.lang.toLowerCase().replace("_", "-");
  return voices.find((v) => norm(v) === full) || voices.find((v) => norm(v).startsWith(code));
}

/** Cut text into pieces of at most ~180 characters, at sentence ends. */
function chunk(text, max = 180) {
  const sentences = text.split(/(?<=[.!?।])\s+/);
  const out = [];
  let cur = "";
  for (const s of sentences) {
    if (cur && (cur + " " + s).length > max) {
      out.push(cur);
      cur = s;
    } else {
      cur = cur ? cur + " " + s : s;
    }
  }
  if (cur) out.push(cur);
  return out;
}

export default function ListenButton({ text, disabled }) {
  const { lang, t } = useLanguage();
  const [speaking, setSpeaking] = useState(false);
  const [note, setNote] = useState("");

  useEffect(() => () => window.speechSynthesis?.cancel(), []);
  useEffect(() => {
    window.speechSynthesis?.cancel();
    setSpeaking(false);
    setNote("");
  }, [text, lang]);

  async function toggle() {
    const synth = window.speechSynthesis;
    if (!synth) return setNote("Your browser does not support reading aloud.");
    if (speaking) {
      synth.cancel();
      return setSpeaking(false);
    }

    const code = detectLang(text, lang);
    const name = LANGUAGES.find((l) => l.code === code)?.label || code;
    const voice = pickVoice(await loadVoices(), code);
    if (!voice) {
      return setNote(
        `No ${name} voice is installed on this device. Microsoft Edge usually includes Indian-language voices, or add one in your system's speech settings.`
      );
    }

    setNote("");
    synth.cancel();
    const pieces = chunk(text);
    const fallbackLang = LANGUAGES.find((l) => l.code === code)?.speech || "en-IN";
    let retried = false;

    // Speak all pieces with `v` (a chosen voice) or, if v is null, the browser's default voice.
    function speakAll(v) {
      pieces.forEach((piece, i) => {
        const u = new SpeechSynthesisUtterance(piece);
        u.lang = v ? v.lang : fallbackLang;
        if (v) u.voice = v;
        u.onerror = (e) => {
          if (e.error === "canceled" || e.error === "interrupted") return;
          if (v && !retried) {      // the chosen voice failed: try once more with the default voice
            retried = true;
            synth.cancel();
            speakAll(null);
            return;
          }
          setNote(`Could not play audio (${e.error}). Try another browser such as Microsoft Edge.`);
          setSpeaking(false);
        };
        if (i === pieces.length - 1) u.onend = () => setSpeaking(false);
        synth.speak(u);
      });
    }
    speakAll(voice);
    setSpeaking(true);
  }

  return (
    <div className="listen-wrap">
      <button className="btn btn-outline" onClick={toggle} disabled={disabled || !text}>
        {speaking ? <Square size={15} /> : <Volume2 size={17} />}
        {speaking ? t("stop") : t("listen")}
      </button>
      {note && <small className="listen-note">{note}</small>}
    </div>
  );
}
