import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { analyzeEcg, analyzeXray, getDatasetSummary, listEcgRecords, listXrays } from "../api/services";
import { Badge, Kpi } from "../components/ui";
import Icon from "../components/Icon";
import { SignalChart } from "../components/charts";
import { fmt } from "../utils/format";

const ECG_STEPS = [
  ["Notch Filter", "50/60 Hz line rejection", "filter_alt", "iirnotch · Q 30"],
  ["Butterworth BP", "0.5 - 40 Hz passband", "waves", "order 4 · zero-phase"],
  ["R-peak detection", "Pan-Tompkins style", "show_chart", "5-15 Hz · 120 ms window"],
  ["FFT & Welch PSD", "spectral density", "analytics", "Hann window"],
  ["Autocorrelation", "period & regularity", "repeat", "first peak = RR"],
  ["HRV & quality", "time-domain indices", "verified", "SDNN · RMSSD · pNN50"],
];
const XR_STEPS = [
  ["CLAHE contrast", "adaptive equalization", "tune", "clip limit 2.0"],
  ["Sobel & Canny", "edge gradient maps", "grain", "auto thresholds"],
  ["Thresholding", "Otsu · k-means · adaptive", "contrast", "3 methods"],
  ["Morphology", "open / close / fill holes", "texture", "kernel 7 px"],
  ["Lung selection", "2 largest central blobs", "hub", "anatomical priors"],
  ["Validation", "ground-truth masks", "task_alt", "Dice · IoU · HD95"],
];

function Steps({ steps, tone }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {steps.map(([title, desc, icon, param], i) => (
        <div key={title} className="p-3 rounded-lg bg-surface-container hover:bg-surface-container-high transition-colors flex flex-col justify-between min-h-[7rem]">
          <div className="flex items-center justify-between">
            <span className={`font-label-micro text-label-micro text-${tone}`}>STAGE 0{i + 1}</span>
            <Icon name={icon} className="text-[16px] text-on-surface-variant" />
          </div>
          <div className="my-2">
            <div className="text-body-md text-on-surface font-medium">{title}</div>
            <p className="text-body-sm text-on-surface-variant">{desc}</p>
          </div>
          <span className="font-metric-value text-metric-value text-on-surface-variant text-[12px]">{param}</span>
        </div>
      ))}
    </div>
  );
}

function CardTitle({ icon, tone = "primary", title, sub, right }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
      <div className="flex items-center gap-2.5">
        <div className={`w-7 h-7 rounded bg-surface-container-high flex items-center justify-center text-${tone}`}>
          <Icon name={icon} className="text-[18px]" />
        </div>
        <div>
          <h2 className="text-headline-sm text-on-surface font-semibold tracking-tight">{title}</h2>
          {sub && <p className="text-body-sm text-on-surface-variant">{sub}</p>}
        </div>
      </div>
      {right && <div className="flex items-center gap-2 flex-wrap">{right}</div>}
    </div>
  );
}

function Metric({ label, value, unit, tone = "on-surface" }) {
  return (
    <div className="p-2.5 rounded bg-surface-container flex flex-col">
      <span className="font-label-micro text-label-micro text-on-surface-variant uppercase">{label}</span>
      <span className={`font-metric-display text-metric-display text-${tone} mt-0.5`}>
        {value} {unit && <span className="font-label-micro text-label-micro text-on-surface-variant font-normal">{unit}</span>}
      </span>
    </div>
  );
}

export default function Dashboard() {
  const nav = useNavigate();
  const [summary, setSummary] = useState(null);
  const [offline, setOffline] = useState(false);
  const [ecg, setEcg] = useState(null);
  const [xr, setXr] = useState(null);

  useEffect(() => {
    getDatasetSummary().then((r) => setSummary(r.data)).catch(() => setOffline(true));
    listEcgRecords()
      .then((r) => r.data.records[0] && analyzeEcg({ record_id: r.data.records[0].id, lead: "II", duration_s: 6 }).then((a) => setEcg(a.data)))
      .catch(() => {});
    listXrays()
      .then((r) => r.data.images[0] && analyzeXray({ image_id: r.data.images[0].id }).then((a) => setXr(a.data)))
      .catch(() => {});
  }, []);

  const modeTone = (m) => (m === "real" ? "success" : m === "synthetic" ? "warning" : m === "mixed" ? "secondary" : "neutral");
  const fsLabel = summary ? summary.ecg.sampling_rates_hz.join("/") : "";

  return (
    <div className="p-space-lg lg:p-margin-desktop">
      <div className="max-w-[1440px] mx-auto space-y-space-xl">
        {/* Hero */}
        <section className="relative overflow-hidden rounded-xl bg-surface-container-low shadow-xl">
          <div className="absolute inset-0 bg-gradient-to-r from-primary/10 via-surface-container-high/40 to-transparent pointer-events-none" />
          <div className="relative z-10 flex flex-col lg:flex-row items-stretch justify-between p-space-lg lg:p-space-xl gap-space-lg">
            <div className="flex-1 flex flex-col justify-between max-w-2xl gap-space-md">
              <div className="space-y-space-xs">
                <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-surface-container-highest text-primary">
                  <span className={`w-1.5 h-1.5 rounded-full ${offline ? "bg-error" : "bg-primary animate-pulse"}`} />
                  <span className="font-label-micro text-label-micro uppercase tracking-widest">{offline ? "Backend offline" : "System live"}</span>
                </div>
                <h1 className="text-headline-lg text-on-surface tracking-tight pt-1">Patient Health Data Analyzer</h1>
                <p className="text-body-lg text-on-surface-variant max-w-xl leading-relaxed">
                  Research workbench for 12-lead ECG analysis (Butterworth filtering, FFT, autocorrelation) and chest X-ray image processing (Canny / Sobel edges, lung segmentation) with quantitative validation.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3 pt-2">
                <button type="button" onClick={() => nav("/ecg")} className="group flex items-center gap-2 px-5 py-2.5 rounded-lg bg-inverse-primary text-white text-body-md font-semibold transition-all hover:brightness-110 shadow-sm shadow-primary/20">
                  <Icon name="ecg" className="text-[18px]" />
                  <span>Open ECG Lab</span>
                  <Icon name="arrow_forward" className="text-[16px] transition-transform group-hover:translate-x-0.5" />
                </button>
                <button type="button" onClick={() => nav("/xray")} className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-surface-container-high text-primary text-body-md font-medium hover:bg-surface-variant hover:text-on-surface transition-all">
                  <Icon name="radiology" className="text-[18px]" />
                  <span>Open X-ray Lab</span>
                </button>
              </div>
            </div>

            {/* Live lead II monitor (first record) */}
            <div className="lg:w-[420px] w-full flex flex-col justify-between bg-surface-container-lowest rounded-lg p-3 relative overflow-hidden shadow-inner">
              <div className="flex items-center justify-between pb-2 gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-label-caps text-label-caps text-primary tracking-wider uppercase">Lead II</span>
                  <span className="font-metric-value text-metric-value text-on-surface-variant truncate text-[12px]">{ecg ? ecg.record.id : "…"}</span>
                </div>
                {ecg && <span className="font-label-micro text-label-micro px-2 py-0.5 rounded bg-surface-container-high text-secondary">{ecg.record.fs} Hz · {ecg.record.source}</span>}
              </div>
              <div className="relative h-28 w-full overflow-hidden rounded bg-surface">
                {ecg ? <SignalChart signal={ecg.signal} peaks={ecg.r_peaks} showRaw={false} h={112} compact /> : <div className="h-full flex items-center justify-center text-body-sm text-on-surface-variant">Loading…</div>}
              </div>
              <div className="flex items-center justify-between pt-2.5 text-body-sm text-on-surface-variant">
                <span>RR: <strong className="font-metric-value text-on-surface">{ecg ? fmt(ecg.hrv.mean_rr_ms, 0) : "—"} ms</strong></span>
                <span>HR: <strong className="font-metric-value text-on-surface">{ecg ? fmt(ecg.hrv.hr_bpm, 0) : "—"} bpm</strong></span>
                <span className="text-tertiary">Quality: {ecg ? ecg.quality.label : "—"}</span>
              </div>
            </div>
          </div>
        </section>

        {offline && (
          <div className="rounded-xl tint-error border bd-error px-4 py-3 text-body-md text-on-surface">
            Cannot reach the API. Start the backend: <code className="font-metric-value">cd backend &amp;&amp; python run.py</code>
          </div>
        )}

        {/* KPIs */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Kpi label="ECG recordings" icon="monitor_heart" value={summary?.ecg.count ?? "—"} sub={summary ? `${summary.ecg.leads} leads · ${fsLabel} Hz` : ""} />
          <Kpi label="Chest X-rays" icon="radiology" value={summary?.xray.count ?? "—"} sub={summary ? `${summary.xray.with_masks} with lung masks` : ""} tone="secondary" />
          <Kpi label="Saved analyses" icon="fact_check" value={summary ? Object.values(summary.history).reduce((a, b) => a + b, 0) : "—"} sub="stored locally (SQLite)" tone="tertiary" />
          <div className="panel rounded-xl p-4 flex flex-col justify-between hover:bg-surface-container transition-colors">
            <div className="flex items-center justify-between text-on-surface-variant mb-2">
              <span className="font-label-caps text-label-caps uppercase tracking-wider">Data source</span>
              <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-tertiary"><Icon name="verified" className="text-[18px]" /></div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge tone={modeTone(summary?.ecg.mode)}>ECG: {summary?.ecg.mode ?? "…"}</Badge>
              <Badge tone={modeTone(summary?.xray.mode)}>X-ray: {summary?.xray.mode ?? "…"}</Badge>
            </div>
          </div>
        </section>

        {/* Quick look */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-space-lg">
          <div className="flex flex-col rounded-xl bg-surface-container-low p-space-lg shadow-md gap-space-md">
            <CardTitle icon="vital_signs" title="ECG quick look" sub={ecg ? `Rhythm strip · lead II · ${ecg.record.id}` : "Loading…"} />
            <div className="rounded-lg bg-surface-container-lowest overflow-hidden shadow-inner p-2">
              {ecg ? <SignalChart signal={ecg.signal} peaks={ecg.r_peaks} showRaw={false} h={190} /> : <div className="h-[190px] flex items-center justify-center text-body-sm text-on-surface-variant">Loading…</div>}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <Metric label="Heart rate" value={ecg ? fmt(ecg.hrv.hr_bpm, 0) : "—"} unit="BPM" tone="primary" />
              <Metric label="SDNN" value={ecg ? fmt(ecg.hrv.sdnn_ms, 0) : "—"} unit="MS" tone="secondary" />
              <Metric label="RMSSD" value={ecg ? fmt(ecg.hrv.rmssd_ms, 0) : "—"} unit="MS" />
              <Metric label="Quality" value={ecg ? fmt(ecg.quality.score, 0) : "—"} unit={ecg ? ecg.quality.label : ""} tone="tertiary" />
            </div>
            <Link to="/ecg" className="inline-flex items-center gap-1 text-body-md text-primary font-semibold">Analyse in ECG Lab <Icon name="arrow_forward" className="text-[16px]" /></Link>
          </div>

          <div className="flex flex-col rounded-xl bg-surface-container-low p-space-lg shadow-md gap-space-md">
            <CardTitle
              icon="document_scanner"
              tone="secondary"
              title="X-ray quick look"
              sub={xr ? `Lung segmentation · ${xr.image_id}` : "Loading…"}
              right={xr?.validation && (<>
                <span className="px-2 py-0.5 rounded bg-surface-container-highest text-primary font-metric-value text-metric-value">Dice {fmt(xr.validation.dice, 3)}</span>
                <span className="px-2 py-0.5 rounded bg-surface-container-highest text-secondary font-metric-value text-metric-value">IoU {fmt(xr.validation.iou, 3)}</span>
              </>)}
            />
            {xr ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[["Original", xr.images.original], ["Segmentation", xr.images.overlay]].map(([label, src]) => (
                  <div key={label} className="relative rounded-lg overflow-hidden bg-surface-container-lowest aspect-square">
                    <img className="absolute inset-0 w-full h-full object-contain" src={src} alt={label} />
                    <span className="absolute left-2.5 bottom-2.5 px-2 py-0.5 rounded bg-surface/80 backdrop-blur font-label-micro text-label-micro uppercase text-on-surface tracking-wider">{label}</span>
                  </div>
                ))}
              </div>
            ) : <div className="h-[190px] flex items-center justify-center text-body-sm text-on-surface-variant">Loading…</div>}
            {xr && (
              <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 rounded bg-surface-container text-body-sm">
                <span><span className="font-label-caps text-label-caps text-on-surface-variant uppercase">Lung area </span><span className="font-metric-value text-on-surface">{fmt(xr.measurements.lung_area_pct, 1)} %</span></span>
                <span><span className="font-label-caps text-label-caps text-on-surface-variant uppercase">Asymmetry </span><span className="font-metric-value text-secondary">{fmt(xr.measurements.asymmetry_index, 2)}</span></span>
                <span className="flex items-center gap-1 text-primary"><Icon name="check_circle" className="text-[16px]" /><span className="font-label-micro text-label-micro uppercase">{xr.params.method}</span></span>
              </div>
            )}
            <Link to="/xray" className="inline-flex items-center gap-1 text-body-md text-primary font-semibold">Analyse in X-ray Lab <Icon name="arrow_forward" className="text-[16px]" /></Link>
          </div>
        </section>

        {/* Pipelines */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-space-lg">
          <div className="rounded-xl bg-surface-container-low p-space-lg space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded bg-primary" /><h2 className="text-headline-sm text-on-surface font-semibold">ECG pipeline</h2></div>
              <span className="font-label-micro text-label-micro text-on-surface-variant uppercase tracking-wider">Signal processing</span>
            </div>
            <Steps steps={ECG_STEPS} tone="primary" />
          </div>
          <div className="rounded-xl bg-surface-container-low p-space-lg space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded bg-secondary" /><h2 className="text-headline-sm text-on-surface font-semibold">X-ray pipeline</h2></div>
              <span className="font-label-micro text-label-micro text-on-surface-variant uppercase tracking-wider">Classical vision</span>
            </div>
            <Steps steps={XR_STEPS} tone="secondary" />
          </div>
        </section>
      </div>
    </div>
  );
}
