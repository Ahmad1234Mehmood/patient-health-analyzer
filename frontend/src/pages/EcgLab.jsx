import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useApp } from "../context/AppContext";
import { analyzeEcg, getFilterResponse, listEcgRecords, uploadEcg } from "../api/services";
import { Badge, Button, EmptyState, ErrorBanner, Field, Kpi, PageHeader, Panel, Segmented, Slider, Spinner, Tabs, Toggle } from "../components/ui";
import Icon from "../components/Icon";
import { AutocorrChart, BandBars, FftChart, FilterResponseChart, PoincareChart, PsdChart, RRChart, SignalChart, TemplateChart } from "../components/charts";
import { exportEcgReport } from "../utils/exportReport";
import { fmt, qualityTone } from "../utils/format";

const DEFAULTS = { apply_filter: true, low_hz: 0.5, high_hz: 40, order: 4, notch: true, mains_hz: 50, start_s: 0, duration_s: 10 };
const TABS = [
  { id: "signal", label: "Signal", icon: "ecg" },
  { id: "spectrum", label: "Spectrum (FFT)", icon: "graphic_eq" },
  { id: "autocorr", label: "Autocorrelation", icon: "timeline" },
  { id: "hrv", label: "HRV", icon: "favorite" },
  { id: "beat", label: "Average beat", icon: "show_chart" },
  { id: "leads", label: "12 leads", icon: "view_list" },
  { id: "filter", label: "Filter design", icon: "tune" },
];
const LEVEL = { ok: ["check_circle", "success"], info: ["info", "secondary"], warn: ["warning", "warning"], alert: ["error", "error"] };

function Explain({ children }) {
  return (
    <div className="rounded-xl bg-surface-container/70 p-3.5 flex items-start gap-3">
      <div className="w-8 h-8 rounded-lg bg-primary-container/20 shrink-0 flex items-center justify-center text-primary mt-0.5">
        <Icon name="lightbulb" className="text-[20px]" />
      </div>
      <div className="flex flex-col gap-1">
        <span className="font-label-caps text-label-caps uppercase text-primary tracking-wider">How to read this</span>
        <p className="text-body-sm text-on-surface-variant leading-relaxed">{children}</p>
      </div>
    </div>
  );
}

export default function EcgLab() {
  const { addToast } = useApp();
  const [params, setSearch] = useSearchParams();
  const [records, setRecords] = useState([]);
  const [recordId, setRecordId] = useState(params.get("record") || "");
  const [lead, setLead] = useState("II");
  const [cfg, setCfg] = useState(DEFAULTS);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("signal");
  const [showRaw, setShowRaw] = useState(true);
  const [csvFs, setCsvFs] = useState(500);
  const [resp, setResp] = useState(null);
  const fileRef = useRef(null);
  const reqId = useRef(0);

  const record = useMemo(() => records.find((r) => r.id === recordId), [records, recordId]);
  const leadNames = record?.lead_names || ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"];
  const duration = record?.duration_s || 10;

  useEffect(() => {
    listEcgRecords()
      .then((r) => {
        const recs = r.data.records;
        setRecords(recs);
        if (!recordId && recs.length) setRecordId(recs[0].id);
      })
      .catch((e) => setError(e.userMessage));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // keep the window inside the record
  useEffect(() => {
    if (record) setCfg((c) => ({ ...c, start_s: 0, duration_s: Math.min(record.duration_s, 10) }));
  }, [recordId]); // eslint-disable-line

  // debounced analysis
  useEffect(() => {
    if (!recordId) return;
    const id = ++reqId.current;
    const t = setTimeout(async () => {
      setLoading(true);
      setError("");
      try {
        const r = await analyzeEcg({ record_id: recordId, lead, ...cfg });
        if (id === reqId.current) setResult(r.data);
      } catch (e) {
        if (id === reqId.current) {
          setError(e.userMessage);
          setResult(null);
        }
      } finally {
        if (id === reqId.current) setLoading(false);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [recordId, lead, cfg]);

  useEffect(() => {
    if (tab !== "filter") return;
    getFilterResponse({ low_hz: cfg.low_hz, high_hz: cfg.high_hz, order: cfg.order, fs: record?.fs || 500 })
      .then((r) => setResp(r.data))
      .catch(() => setResp(null));
  }, [tab, cfg.low_hz, cfg.high_hz, cfg.order, record?.fs]);

  const set = (k) => (v) => setCfg((c) => ({ ...c, [k]: v }));

  const onUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    try {
      const r = await uploadEcg(files, csvFs);
      const rec = r.data.record;
      setRecords((p) => [rec, ...p.filter((x) => x.id !== rec.id)]);
      setRecordId(rec.id);
      setLead(rec.lead_names.includes("II") ? "II" : rec.lead_names[0]);
      addToast(`Loaded ${rec.original_name || rec.id} (${rec.n_leads} leads, ${rec.fs} Hz)`, "success");
    } catch (err) {
      addToast(err.userMessage, "error");
    }
    e.target.value = "";
  };

  const save = async () => {
    try {
      await analyzeEcg({ record_id: recordId, lead, ...cfg, save: true });
      addToast("Analysis saved to history", "success");
    } catch (e) {
      addToast(e.userMessage, "error");
    }
  };

  const r = result;
  const hr = r?.hrv?.hr_bpm;

  return (
    <div className="p-space-lg lg:p-margin-desktop">
      <div className="max-w-[1440px] mx-auto space-y-6">
        <PageHeader
          eyebrow="Electrophysiology"
          title="ECG Lab"
          subtitle="12-lead ECG processing: Butterworth filtering, FFT / Welch spectrum, autocorrelation, R-peak detection and heart-rate variability."
          right={
            <>
              <Button variant="ghost" icon="download" className="text-secondary" onClick={save} disabled={!r}>Save analysis</Button>
              <Button variant="ghost" icon="print" onClick={() => r && exportEcgReport(r)} disabled={!r}>PDF report</Button>
            </>
          }
        />

        <div className="grid grid-cols-1 xl:grid-cols-[330px_1fr] gap-6 items-start">
          {/* ---------------- controls ---------------- */}
          <div className="space-y-5 xl:sticky xl:top-20">
            <Panel title="Recording signal" icon="radio_button_checked">
              <div className="space-y-4">
                <Field label="Record" hint={record?.label ? `${record.label} (${record.source || "file"})` : undefined}>
                  <select value={recordId} onChange={(e) => setRecordId(e.target.value)}>
                    {records.map((x) => (
                      <option key={x.id} value={x.id}>{x.id}{x.hr_true ? `  -  ${x.hr_true} bpm` : ""}</option>
                    ))}
                  </select>
                </Field>
                <div className="flex gap-2 items-end">
                  <Field label="CSV/NPY fs (Hz)">
                    <input type="number" value={csvFs} min={50} max={5000} onChange={(e) => setCsvFs(Number(e.target.value))} />
                  </Field>
                  <input ref={fileRef} type="file" multiple accept=".csv,.txt,.npy,.npz,.hea,.dat" className="hidden" onChange={onUpload} />
                  <Button variant="ghost" icon="upload_file" className="shrink-0" onClick={() => fileRef.current?.click()}>Upload</Button>
                </div>
                <p className="text-body-sm text-on-surface-variant leading-snug">WFDB: select both <code className="font-metric-value">.hea</code> and <code className="font-metric-value">.dat</code>. CSV: one column per lead.</p>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-label-micro text-label-micro uppercase text-on-surface-variant">Lead</span>
                    <span className="font-metric-value text-body-sm text-primary">Lead {lead} active</span>
                  </div>
                  <div className="grid grid-cols-4 gap-1.5">
                    {leadNames.map((l) => (
                      <button key={l} onClick={() => setLead(l)} className={`py-1 rounded font-label-micro text-label-micro tracking-widest text-center transition-all ${lead === l ? "bg-primary-container text-on-primary-container font-semibold shadow-[0_0_12px_rgba(79,224,207,0.3)]" : "bg-surface-container hover:bg-surface-container-high text-on-surface-variant"}`}>{l}</button>
                    ))}
                  </div>
                </div>
                {duration > 4 && (
                  <>
                    <Slider label="Window start" value={cfg.start_s} min={0} max={Math.max(0, Math.floor(duration - 2))} step={0.5} onChange={set("start_s")} format={(v) => `${v} s`} />
                    <Slider label="Window length" value={cfg.duration_s} min={2} max={Math.floor(duration)} step={1} onChange={set("duration_s")} format={(v) => `${v} s`} />
                  </>
                )}
              </div>
            </Panel>

            <Panel title="DSP filter pipeline" icon="equalizer">
              <div className="space-y-4">
                <Toggle label="Butterworth band-pass" hint="IIR, zero-phase (forward-backward)" checked={cfg.apply_filter} onChange={set("apply_filter")} />
                {cfg.apply_filter && (
                  <>
                    <Slider label="Low cut-off" value={cfg.low_hz} min={0.05} max={5} step={0.05} onChange={set("low_hz")} format={(v) => `${v} Hz`} hint="Removes baseline wander (breathing, movement)" />
                    <Slider label="High cut-off" value={cfg.high_hz} min={10} max={150} step={1} onChange={set("high_hz")} format={(v) => `${v} Hz`} hint="Removes muscle noise; diagnostic ECG ≈ 40 Hz" />
                    <Slider label="Filter order" value={cfg.order} min={1} max={8} onChange={set("order")} hint="Steeper roll-off with higher order" />
                    <Toggle label="Notch filter" hint="Powerline noise rejection" checked={cfg.notch} onChange={set("notch")} />
                    {cfg.notch && (
                      <Field label="Mains frequency">
                        <Segmented size="sm" options={[{ value: 50, label: "50 Hz (EU/Asia)" }, { value: 60, label: "60 Hz (US)" }]} value={cfg.mains_hz} onChange={set("mains_hz")} />
                      </Field>
                    )}
                  </>
                )}
                <Button variant="ghost" icon="restart_alt" className="w-full" onClick={() => setCfg((c) => ({ ...DEFAULTS, start_s: c.start_s, duration_s: c.duration_s }))}>Reset defaults</Button>
              </div>
            </Panel>
          </div>

          {/* ---------------- results ---------------- */}
          <div className="space-y-4 min-w-0">
            <ErrorBanner>{error}</ErrorBanner>
            {!r && !error && <Panel><EmptyState icon="ecg" title={loading ? "Analysing…" : "Select a record"}>{loading ? <Spinner className="text-3xl" /> : "Pick a record on the left to start."}</EmptyState></Panel>}
            {r && (
              <>
                <div className={`grid grid-cols-2 lg:grid-cols-5 gap-3 transition-opacity ${loading ? "opacity-60" : ""}`}>
                  <Kpi label="Heart rate" icon="favorite" value={fmt(hr, 0)} unit="BPM" sub={`ACF ${fmt(r.hr_methods_bpm.autocorrelation, 0)} · FFT ${fmt(r.hr_methods_bpm.fft, 0)} bpm`} tone="primary" />
                  <Kpi label="Detected beats" icon="timeline" value={r.hrv.n_beats} unit="QRS" sub={`${r.record.fs} Hz · lead ${r.params.lead}`} tone="secondary" />
                  <Kpi label="SDNN" icon="waves" value={fmt(r.hrv.sdnn_ms, 0)} unit="MS" sub={`RMSSD ${fmt(r.hrv.rmssd_ms, 0)} ms`} tone="tertiary" />
                  <Kpi label="Regularity" icon="auto_graph" value={fmt(r.autocorr.regularity, 2)} sub="ACF peak · sinus ≈ 0.4-0.8, irregular < 0.25" tone="primary" />
                  <Kpi label="Signal quality" icon="verified" value={fmt(r.quality.score, 0)} unit="/ 100" sub={<Badge tone={qualityTone(r.quality.label)}>{r.quality.label}</Badge>} tone={qualityTone(r.quality.label)} />
                </div>

                <Panel bodyClass="p-5 space-y-4">
                  <Tabs tabs={TABS} value={tab} onChange={setTab} />
                  <div className="space-y-4">
                    {tab === "signal" && (
                      <>
                        <div className="flex flex-wrap items-center justify-between gap-3 bg-surface-container-lowest/80 p-2.5 rounded-lg">
                          <div className="flex flex-wrap items-center gap-4">
                            <label className="flex items-center gap-2 cursor-pointer select-none">
                              <input type="checkbox" checked={showRaw} onChange={(e) => setShowRaw(e.target.checked)} className="rounded h-4 w-4 accent-primary" />
                              <span className="text-body-sm text-on-surface">Show raw signal</span>
                            </label>
                            <div className="flex items-center gap-1.5"><span className="w-2.5 h-0.5 bg-outline inline-block" /><span className="font-label-micro text-label-micro text-on-surface-variant uppercase">Raw</span></div>
                            <div className="flex items-center gap-1.5"><span className="w-3 h-1 bg-primary inline-block rounded" /><span className="font-label-micro text-label-micro text-primary uppercase">Filtered</span></div>
                          </div>
                          <span className="font-metric-value text-metric-value text-on-surface-variant text-[12px]">Lead {r.params.lead} · {r.record.id}</span>
                        </div>
                        <SignalChart signal={r.signal} peaks={r.r_peaks} showRaw={showRaw} />
                        <Explain>Grey = raw recording (baseline drift + 50 Hz hum + noise). Teal = after notch + Butterworth band-pass. Red dots = detected R-peaks (Pan-Tompkins). Try turning the filter off to see why pre-processing matters.</Explain>
                      </>
                    )}
                    {tab === "spectrum" && (
                      <>
                        <PsdChart psd={r.spectrum.psd} mains={r.spectrum.mains_hz} />
                        <div className="grid md:grid-cols-2 gap-4">
                          <div><div className="text-xs font-semibold mb-2">FFT amplitude (filtered)</div><FftChart fft={r.spectrum.fft} domHz={r.spectrum.dominant_hz} /></div>
                          <div><div className="text-xs font-semibold mb-2">Relative band power</div><BandBars before={r.spectrum.band_power_raw} after={r.spectrum.band_power_filtered} /></div>
                        </div>
                        <Explain>Welch PSD averages many windowed FFTs for a smooth, reliable spectrum. The mains line ({fmt(r.spectrum.powerline_excess_db_raw, 0)} dB above its neighbours in the raw signal → {fmt(r.spectrum.powerline_excess_db_filtered, 0)} dB after filtering) disappears with the notch. Heart-rate fundamental from FFT: {fmt(r.spectrum.dominant_hz, 2)} Hz = {fmt(r.spectrum.hr_from_fft_bpm, 0)} bpm.</Explain>
                      </>
                    )}
                    {tab === "autocorr" && (
                      <>
                        <AutocorrChart ac={r.autocorr} />
                        <div className="grid sm:grid-cols-3 gap-3">
                          <Kpi label="First significant peak" value={fmt(r.autocorr.peak_lag_s, 3)} unit="s" />
                          <Kpi label="Heart rate (ACF)" value={fmt(r.autocorr.hr_bpm, 1)} unit="bpm" tone="error" />
                          <Kpi label="Regularity" value={fmt(r.autocorr.regularity, 2)} sub="sinus ≈ 0.4-0.8 · irregular < 0.25" tone="tertiary" />
                        </div>
                        <Explain>The autocorrelation compares the ECG with a delayed copy of itself. Peaks appear at multiples of the heartbeat period. HR = 60 / first-peak-lag. A low peak height (below 0.25) means irregular rhythm or noise; a healthy sinus rhythm typically scores 0.4-0.8 (not 1.0, because beat timing varies slightly).</Explain>
                      </>
                    )}
                    {tab === "hrv" && (r.hrv.valid ? (
                      <>
                        <div className="grid md:grid-cols-2 gap-4">
                          <div><div className="text-xs font-semibold mb-2">RR intervals (tachogram)</div><RRChart rr={r.hrv.rr_ms} /></div>
                          <div><div className="text-xs font-semibold mb-2">Poincaré plot (RRₙ vs RRₙ₊₁)</div><PoincareChart pc={r.hrv.poincare} /></div>
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                          <Kpi label="Mean RR" value={fmt(r.hrv.mean_rr_ms, 0)} unit="ms" />
                          <Kpi label="pNN50" value={fmt(r.hrv.pnn50_pct, 1)} unit="%" />
                          <Kpi label="SD1 / SD2" value={`${fmt(r.hrv.poincare.sd1_ms, 0)} / ${fmt(r.hrv.poincare.sd2_ms, 0)}`} unit="ms" />
                          <Kpi label="CV(RR)" value={fmt(r.hrv.cv * 100, 1)} unit="%" />
                        </div>
                        <Explain>HRV from a 10-second snapshot is only indicative (clinical norms use 5-minute or 24-hour recordings). A tight Poincaré cloud = regular rhythm; a wide scattered cloud = irregular RR intervals.</Explain>
                      </>
                    ) : <EmptyState icon="heart_broken" title="Not enough beats">Need at least 3 detected beats to compute HRV.</EmptyState>)}
                    {tab === "beat" && (r.template.t_s ? (
                      <>
                        <TemplateChart tpl={r.template} />
                        <Explain>Ensemble average of {r.template.n_beats} beats aligned on the R-peak (red line). Averaging cancels random noise (SNR grows ≈ √N), revealing P-QRS-T morphology. The shaded band is ±1 SD between beats.</Explain>
                      </>
                    ) : <EmptyState icon="show_chart" title="Not enough beats" />)}
                    {tab === "leads" && (
                      <div className="table-scroll">
                        <table className="w-full text-sm min-w-[520px]">
                          <thead>
                            <tr className="bg-surface-container-lowest text-on-surface-variant font-label-micro text-label-micro uppercase text-left">
                              <th className="py-3 px-3 rounded-l">Lead</th><th>RMS (mV)</th><th>Peak-to-peak (mV)</th><th>R amplitude (mV)</th><th className="rounded-r">SNR (dB)</th>
                            </tr>
                          </thead>
                          <tbody>
                            {r.leads_summary.map((l) => (
                              <tr key={l.lead} className={`hover:bg-surface-container transition-colors cursor-pointer ${l.lead === r.params.lead ? "bg-surface-container-high text-primary" : ""}`} onClick={() => setLead(l.lead)}>
                                <td className="py-2.5 px-3 font-semibold">{l.lead}</td>
                                <td className="font-metric-value">{fmt(l.rms_mv, 3)}</td>
                                <td className="font-metric-value">{fmt(l.peak_to_peak_mv, 2)}</td>
                                <td className="font-metric-value">{fmt(l.r_amplitude_mv, 2)}</td>
                                <td className="font-metric-value">{fmt(l.snr_db, 1)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        <p className="text-[11px] text-on-surface-variant mt-3">Click a row to view that lead. aVR is normally inverted (negative QRS) - the detector handles polarity automatically.</p>
                      </div>
                    )}
                    {tab === "filter" && (
                      <>
                        {resp ? <FilterResponseChart resp={resp} /> : <Spinner />}
                        <Explain>Magnitude response of your Butterworth band-pass. Butterworth = maximally flat pass-band (no ripple, so QRS amplitude is preserved). Running it forward + backward (<code className="font-metric-value">sosfiltfilt</code>) squares the response (doubles the dB) and cancels phase delay, so R-peaks stay at their true positions.</Explain>
                      </>
                    )}
                  </div>
                </Panel>

                <Panel title="Findings" icon="fact_check">
                  <ul className="space-y-2.5">
                    {r.findings.map((x, i) => {
                      const [ic, tone] = LEVEL[x.level] || LEVEL.info;
                      return (
                        <li key={i} className="flex items-start gap-3 p-3 rounded-lg bg-surface-container-lowest/80 hover:bg-surface-container-lowest transition-all">
                          <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5 tint-${tone}`}><Icon name={ic} className="text-[16px]" /></div>
                          <span className="text-body-sm text-on-surface pt-0.5">{x.text}</span>
                        </li>
                      );
                    })}
                  </ul>
                  <p className="text-body-sm text-on-surface-variant mt-4">{r.disclaimer}</p>
                </Panel>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
