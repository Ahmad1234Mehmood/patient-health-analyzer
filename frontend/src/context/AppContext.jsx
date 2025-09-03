import { createContext, useContext, useState, useCallback, useEffect } from "react";

const AppContext = createContext(null);
let _id = 0;

export function AppProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem("theme") === "light" ? "light" : "dark";
    } catch {
      return "dark";
    }
  });

  const addToast = useCallback((message, type = "info") => {
    const id = ++_id;
    setToasts((p) => [...p, { id, message, type }]);
    setTimeout(() => setToasts((p) => p.filter((t) => t.id !== id)), 3800);
  }, []);

  const toggleTheme = useCallback((next) => {
    setTheme(next);
    try {
      localStorage.setItem("theme", next);
    } catch {}
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("light", theme === "light");
    root.classList.toggle("dark", theme !== "light");
  }, [theme]);

  return (
    <AppContext.Provider value={{ toasts, addToast, theme, toggleTheme }}>{children}</AppContext.Provider>
  );
}

export const useApp = () => useContext(AppContext);
