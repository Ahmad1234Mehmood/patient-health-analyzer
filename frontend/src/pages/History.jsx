import { useEffect, useState } from "react";
import { useApp } from "../context/AppContext";
import { clearHistory, deleteHistory, getHistory } from "../api/services";
import { EmptyState, PageHeader, Panel } from "../components/ui";
import Icon from "../components/Icon";
import { fmt, timeAgo } from "../utils/format";

export default function History() {
  const { addToast } = useApp();
  const [history, setHistory] = useState([]);

  const loadHistory = () => getHistory().then((r) => setHistory(r.data.items)).catch(() => {});

  useEffect(() => {
    loadHistory();
  }, []);

  return (
    <div className="p-space-lg lg:p-margin-desktop">
      <div className="max-w-[1440px] mx-auto space-y-space-lg">
        <PageHeader
          eyebrow="Saved"
          title="History"
          subtitle="Results you saved with the Save button in a lab."
          right={
            history.length > 0 && (
              <button
                className="px-3 py-1.5 rounded bg-surface-container hover:bg-surface-container-high text-body-sm text-error transition-colors flex items-center gap-1.5"
                onClick={async () => {
                  await clearHistory();
                  loadHistory();
                  addToast("History cleared", "info");
                }}
              >
                <Icon name="delete_sweep" className="text-[16px]" /> Clear all
              </button>
            )
          }
        />

        <Panel bodyClass="p-0">
          {history.length === 0 ? (
            <EmptyState icon="history" title="Nothing saved yet">
              Press <b>Save</b> in a lab to keep a result here.
            </EmptyState>
          ) : (
            <div className="table-scroll">
              <table className="w-full text-left min-w-[560px]">
                <thead>
                  <tr className="bg-surface-container-lowest text-on-surface-variant font-label-micro text-label-micro uppercase">
                    <th className="py-3 px-4 rounded-l">Modality</th>
                    <th className="py-3 px-4">Subject ID</th>
                    <th className="py-3 px-4">Result summary</th>
                    <th className="py-3 px-4">When</th>
                    <th className="py-3 px-4 rounded-r" />
                  </tr>
                </thead>
                <tbody className="text-on-surface text-body-md">
                  {history.map((h) => (
                    <tr key={h.id} className="hover:bg-surface-container transition-colors">
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded font-label-caps text-label-caps ${h.kind === "ecg" ? "bg-primary-container/20 text-primary" : "bg-secondary-container/30 text-secondary"}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${h.kind === "ecg" ? "bg-primary" : "bg-secondary"}`} /> {h.kind === "ecg" ? "ECG" : "CXR"}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-metric-value text-metric-value">{h.subject_id}</td>
                      <td className="py-3 px-4 text-body-sm text-on-surface-variant">
                        {h.kind === "ecg"
                          ? `HR ${fmt(h.summary.hr_bpm, 0)} bpm · SDNN ${fmt(h.summary.sdnn_ms, 0)} ms · lead ${h.summary.lead} · ${h.summary.quality}`
                          : `${h.summary.method} · lung ${fmt(h.summary.lung_area_pct, 1)} %${h.summary.dice != null ? ` · Dice ${fmt(h.summary.dice, 3)}` : ""}`}
                      </td>
                      <td className="py-3 px-4 text-on-surface-variant font-metric-value text-metric-value whitespace-nowrap">{timeAgo(h.created_at)}</td>
                      <td className="py-3 px-4 text-right">
                        <button
                          aria-label="delete"
                          className="p-1 rounded text-on-surface-variant hover:text-error hover:bg-surface-container-high transition-colors"
                          onClick={async () => {
                            await deleteHistory(h.id);
                            loadHistory();
                          }}
                        >
                          <Icon name="delete" className="text-[18px]" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
