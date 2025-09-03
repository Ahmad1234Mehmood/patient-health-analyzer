import { useApp } from "../context/AppContext";
import Icon from "./Icon";

const ICON = { success: "check_circle", error: "error", info: "info" };
const TONE = { success: "tint-success bd-success", error: "tint-error bd-error", info: "tint-primary bd-primary" };

export default function Toast() {
  const { toasts } = useApp();
  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <div key={t.id} className={`toast-slide-in flex items-start gap-3 px-4 py-3 rounded-xl border text-sm panel ${TONE[t.type] || TONE.info}`}>
          <Icon name={ICON[t.type] || ICON.info} className="text-lg mt-0.5" />
          <span className="text-on-surface">{t.message}</span>
        </div>
      ))}
    </div>
  );
}
