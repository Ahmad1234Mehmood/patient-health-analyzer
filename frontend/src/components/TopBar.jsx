import { useEffect, useState } from "react";
import { useApp } from "../context/AppContext";
import { healthCheck } from "../api/services";
import Icon from "./Icon";

export default function TopBar({ onMenu }) {
  const { theme, toggleTheme } = useApp();
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let alive = true;
    const ping = () =>
      healthCheck()
        .then((r) => alive && setStatus(r.data?.status === "healthy" ? "online" : "error"))
        .catch(() => alive && setStatus("offline"));
    ping();
    const t = setInterval(ping, 10000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  const online = status === "online";
  const dot = online ? "bg-primary" : status === "checking" ? "bg-outline" : "bg-error";

  return (
    <header className="sticky top-0 z-30 h-16 flex items-center justify-between px-4 sm:px-6 border-b border-outline-variant/30 bg-surface-container-lowest/85 backdrop-blur-xl">
      <div className="flex items-center gap-3 text-body-sm text-on-surface-variant">
        <button className="lg:hidden text-on-surface-variant" onClick={onMenu} aria-label="Open menu">
          <Icon name="menu" />
        </button>
        <span className="hidden sm:inline font-label-caps text-label-caps text-primary tracking-wider uppercase">Workbench</span>
        <span className="hidden sm:inline text-outline-variant">/</span>
        <span className="hidden sm:inline">ECG &amp; Chest X-ray Analysis</span>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-surface-container border border-outline-variant/30">
          <span className="relative flex h-2 w-2">
            {online && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />}
            <span className={`relative inline-flex rounded-full h-2 w-2 ${dot}`} />
          </span>
          <span className="font-metric-value text-metric-value text-on-surface">API {status}</span>
        </div>
        <button
          onClick={() => toggleTheme(theme === "light" ? "dark" : "light")}
          className="p-2 rounded hover:bg-surface-container text-on-surface-variant hover:text-on-surface transition-colors"
          aria-label="Toggle theme"
          title={theme === "light" ? "Switch to dark" : "Switch to light"}
        >
          <Icon name={theme === "light" ? "dark_mode" : "light_mode"} className="text-[20px]" />
        </button>
      </div>
    </header>
  );
}

// v2
