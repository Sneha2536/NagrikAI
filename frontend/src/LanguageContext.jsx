/**
 * LanguageContext.jsx: remembers which language the user picked and shares it with
 * every component, so the Topbar dropdown can change the whole app.
 *
 * In any component:   const { lang, setLang, t } = useLanguage();
 *                     <h1>{t("hero.title1")}</h1>
 */
import { createContext, useContext, useEffect, useState } from "react";
import { STRINGS } from "./translations.js";

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => {
    try {
      return localStorage.getItem("lang") || "en";
    } catch {
      return "en";
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem("lang", lang);
    } catch {
      /* storage blocked: fine */
    }
    document.documentElement.lang = lang;
  }, [lang]);

  // Falls back to English if a key is missing in the chosen language.
  const t = (key) => STRINGS[lang]?.[key] ?? STRINGS.en[key] ?? key;

  return <LanguageContext.Provider value={{ lang, setLang, t }}>{children}</LanguageContext.Provider>;
}

export const useLanguage = () => useContext(LanguageContext);
