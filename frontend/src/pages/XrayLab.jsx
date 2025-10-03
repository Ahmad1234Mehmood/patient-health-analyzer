import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useApp } from "../context/AppContext";
import { analyzeXray, listXrays, uploadXray } from "../api/services";
import { Badge, Button, EmptyState, ErrorBanner, Field, Kpi, PageHeader, Panel, Segmented, Slider, Spinner, Toggle } from "../components/ui";
import Icon from "../components/Icon";
import { HistogramChart } from "../components/charts";
import { exportXrayReport } from "../utils/exportReport";
import { fmt } from "../utils/format";

const DEFAULTS = {
  method: "otsu", clahe_clip: 2, blur_k: 5, sobel_ksize: 3, auto_canny: true, canny_low: 40, canny_high: 100,
  morph_k: 7, min_area_pct: 1, max_side: 512, invert: false, use_ground_truth: true,
};
const STAGES = [
  { id: "original", label: "Original", note: "Input resized to ≤ 512 px (keeps aspect ratio)." },
  { id: "enhanced", label: "CLAHE", note: "Contrast-Limited Adaptive Histogram Equalisation + Gaussian blur." },
  { id: "sobel", label: "Sobel", note: "Gradient magnitude √(Gx²+Gy²): bright where intensity changes fast." },
  { id: "canny", label: "Canny", note: "Thin binary edges: smoothing → gradient → non-max suppression → hysteresis." },
  { id: "mask", label: "Lung mask", note: "Threshold → morphology → two largest central blobs → hole filling." },
  { id: "overlay", label: "Overlay", note: "Predicted contour (cyan); ground-truth contour (magenta) when a mask exists." },
];
const METHOD_INFO = {
  otsu: "Global Otsu threshold - fast baseline.",
  kmeans: "k-means (k=4) on intensities - air / lung / tissue / bone.",
  adaptive: "Local adaptive threshold ∧ relaxed Otsu - copes with uneven exposure.",
};

export default function XrayLab() {
  const { addToast } = useApp();
  const [qs] = useSearchParams();
  const [images, setImages] = useState([]);
  const [imageId, setImageId] = useState(qs.get("image") || "");
  const [cfg, setCfg] = useState(DEFAULTS);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [stage, setStage] = useState("overlay");
  const [grid, setGrid] = useState(false);
  const fileRef = useRef(null);
  const reqId = useRef(0);

  const current = useMemo(() => images.find((i) => i.id === imageId), [images, imageId]);

  useEffect(() => {
    listXrays()
      .then((r) => {
        setImages(r.data.images);
        if (!imageId && r.data.images.length) setImageId(r.data.images[0].id);
      })
      .catch((e) => setError(e.userMessage));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const payload = (extra = {}) => ({
    image_id: imageId, method: cfg.method, clahe_clip: cfg.clahe_clip, blur_k: cfg.blur_k, sobel_ksize: cfg.sobel_ksize,
    canny_low: cfg.auto_canny ? null : cfg.canny_low, canny_high: cfg.auto_canny ? null : cfg.canny_high,
    morph_k: cfg.morph_k, min_area_pct: cfg.min_area_pct, max_side: cfg.max_side, invert: cfg.invert, use_ground_truth: cfg.use_ground_truth, ...extra,
  });

  useEffect(() => {
    if (!imageId) return;
    const id = ++reqId.current;
    const t = setTimeout(async () => {
      setLoading(true);
      setError("");
      try {
        const r = await analyzeXray(payload());
        if (id === reqId.current) setResult(r.data);
      } catch (e) {
        if (id === reqId.current) { setError(e.userMessage); setResult(null); }
      } finally {
        if (id === reqId.current) setLoading(false);
      }
    }, 350);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageId, cfg]);

  const set = (k) => (v) => setCfg((c) => ({ ...c, [k]: v }));

  const onUpload = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    try {
      const r = await uploadXray(f);
      const img = r.data.image;
      setImages((p) => [img, ...p]);
      setImageId(img.id);
      addToast(`Loaded ${f.name}`, "success");
    } catch (err) {
      addToast(err.userMessage, "error");
    }
    e.target.value = "";
  };

  const save = async () => {
    try {
      await analyzeXray(payload({ save: true }));
      addToast("Analysis saved to history", "success");
    } catch (e) {
      addToast(e.userMessage, "error");
    }
  };

  const r = result;
  const m = r?.measurements;
  const v = r?.validation;
  const stageInfo = STAGES.find((s) => s.id === stage);
  const dtone = (d) => (d >= 0.9 ? "success" : d >= 0.8 ? "warning" : "error");

  return (
    <div className="p-space-lg lg:p-margin-desktop">
      <div className="max-w-[1440px] mx-auto space-y-6">
        <PageHeader
          eyebrow="Radiography"
          title="Chest X-ray Lab"
          subtitle="Classical chest X-ray pipeline: CLAHE enhancement, Sobel & Canny edge detection, threshold-based lung segmentation and validation against ground-truth masks."
          right={
            <>
              <Button variant="ghost" icon="download" className="text-secondary" onClick={save} disabled={!r}>Save analysis</Button>
              <Button variant="ghost" icon="print" onClick={() => r && exportXrayReport(r)} disabled={!r}>PDF report</Button>
            </>
          }
        />

        <div className="grid grid-cols-1 xl:grid-cols-[330px_1fr] gap-6 items-start">
          <div className="space-y-5 xl:sticky xl:top-20">
            <Panel title="Image selection" icon="photo_library">
              <div className="space-y-4">
                <Field label="Chest X-ray" hint={current ? `${current.source || "file"}${current.label ? ` · ${current.label}` : ""}${current.has_mask ? " · has ground-truth mask" : ""}` : undefined}>
                  <select value={imageId} onChange={(e) => setImageId(e.target.value)}>
                    {images.map((x) => (<option key={x.id} value={x.id}>{x.id}{x.has_mask ? "  ✓ mask" : ""}</option>))}
                  </select>
                </Field>
                <input ref={fileRef} type="file" accept=".png,.jpg,.jpeg,.tif,.tiff,.bmp" className="hidden" onChange={onUpload} />
                <Button variant="ghost" icon="upload_file" className="w-full" onClick={() => fileRef.current?.click()}>Upload your own image</Button>
                {current?.has_mask && <Toggle label="Compare with ground truth" hint="Dice / IoU / HD95 + magenta contour" checked={cfg.use_ground_truth} onChange={set("use_ground_truth")} />}
                <Toggle label="Invert intensities" hint="For images where air is white (DICOM MONOCHROME1)" checked={cfg.invert} onChange={set("invert")} />
              </div>
            </Panel>

            <Panel title="Segmentation method" icon="layers">
              <div className="space-y-4">
                <Field label="Method" hint={METHOD_INFO[cfg.method]}>
                  <Segmented options={["otsu", "kmeans", "adaptive"]} value={cfg.method} onChange={set("method")} />
                </Field>
                <Slider label="Morphology kernel" value={cfg.morph_k} min={3} max={21} step={2} onChange={set("morph_k")} format={(x) => `${x} px`} hint="Opening/closing size: removes specks, bridges gaps" />
                <Slider label="Min. region area" value={cfg.min_area_pct} min={0.5} max={10} step={0.5} onChange={set("min_area_pct")} format={(x) => `${x} %`} />
                <Slider label="Working resolution" value={cfg.max_side} min={256} max={1024} step={128} onChange={set("max_side")} format={(x) => `${x} px`} />
              </div>
            </Panel>

            <Panel title="Enhancement & edge presets" icon="tune">
              <div className="space-y-4">
                <Slider label="CLAHE clip limit" value={cfg.clahe_clip} min={0.5} max={8} step={0.5} onChange={set("clahe_clip")} hint="Higher = stronger local contrast (and noise)" />
                <Slider label="Gaussian blur" value={cfg.blur_k} min={0} max={15} step={2} onChange={set("blur_k")} format={(x) => (x ? `${x}×${x}` : "off")} />
                <Field label="Sobel kernel size">
                  <Segmented size="sm" options={[1, 3, 5, 7].map(String)} value={String(cfg.sobel_ksize)} onChange={(x) => set("sobel_ksize")(Number(x))} />
                </Field>
                <Toggle label="Auto Canny thresholds" hint="high = Otsu level, low = high / 2" checked={cfg.auto_canny} onChange={set("auto_canny")} />
                {!cfg.auto_canny && (
                  <>
                    <Slider label="Canny low" value={cfg.canny_low} min={0} max={255} onChange={set("canny_low")} />
                    <Slider label="Canny high" value={cfg.canny_high} min={0} max={255} onChange={set("canny_high")} />
                  </>
                )}
                <Button variant="ghost" icon="restart_alt" className="w-full" onClick={() => setCfg(DEFAULTS)}>Reset defaults</Button>
              </div>
            </Panel>
          </div>

          <div className="space-y-4 min-w-0">
            <ErrorBanner>{error}</ErrorBanner>
            {!r && !error && <Panel><EmptyState icon="radiology" title={loading ? "Analysing…" : "Select an image"}>{loading ? <Spinner className="text-3xl" /> : "Pick a chest X-ray on the left."}</EmptyState></Panel>}
            {r && (
              <>
                <div className={`grid grid-cols-2 lg:grid-cols-5 gap-3 transition-opacity ${loading ? "opacity-60" : ""}`}>
                  <Kpi label="Lung area" icon="pie_chart" value={fmt(m.lung_area_pct, 1)} unit="% of image" sub={`${m.n_regions} region(s)`} />
                  <Kpi label="Asymmetry" icon="balance" value={fmt(m.asymmetry_index, 3)} sub="|R−L| / (R+L)" tone="secondary" />
                  <Kpi label="Edge density" icon="grain" value={fmt(m.edge_density_in_lung, 3)} sub="Canny px inside lungs" tone="tertiary" />
                  <Kpi label="Lung texture" icon="query_stats" value={fmt(m.lung_entropy_bits, 2)} unit="bits" sub={`σ ${fmt(m.lung_std_intensity, 1)}`} />
                  {v ? <Kpi label="Dice vs GT" icon="verified" value={fmt(v.dice, 3)} sub={`IoU ${fmt(v.iou, 3)} · HD95 ${fmt(v.hd95_px, 1)} px`} tone={dtone(v.dice)} /> : <Kpi label="Ground truth" icon="help" value="—" sub="no mask for this image" tone="warning" />}
                </div>

                {r.warnings.map((w, i) => (
                  <div key={i} className="flex gap-3 items-start rounded-xl tint-warning border bd-warning px-4 py-3 text-sm"><Icon name="warning" className="text-lg" /><span className="text-on-surface">{w}</span></div>
                ))}

                <Panel
                  title="Pipeline stages"
                  icon="account_tree"
                  right={<Segmented size="sm" options={[{ value: false, label: "Single" }, { value: true, label: "All stages" }]} value={grid} onChange={setGrid} />}
                >
                  {!grid ? (
                    <div className="space-y-4">
                      <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
                        {STAGES.map((st) => (
                          <button
                            key={st.id}
                            onClick={() => setStage(st.id)}
                            className={`px-2.5 py-1.5 rounded font-label-caps text-label-caps uppercase whitespace-nowrap transition-colors ${
                              stage === st.id ? "bg-primary-container text-on-primary-container font-semibold shadow-sm" : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
                            }`}
                          >
                            {st.label}
                          </button>
                        ))}
                      </div>
                      <div className="grid lg:grid-cols-12 gap-space-md">
                        <div className="lg:col-span-8 bg-surface-container-lowest rounded-xl p-3 flex flex-col items-center justify-center min-h-[360px]">
                          <img src={r.images[stage]} alt={stage} className="max-h-[560px] w-auto max-w-full object-contain rounded-lg" />
                          {stage === "overlay" && (
                            <div className="w-full flex flex-wrap items-center justify-center gap-3 pt-3 mt-3 border-t border-surface-container">
                              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-container font-label-caps text-label-caps"><span className="w-2.5 h-2.5 rounded-full bg-primary inline-block" /><span className="text-on-surface">Predicted contour</span></div>
                              {v && <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-container font-label-caps text-label-caps"><span className="w-2.5 h-0.5 border-t-2 border-dashed inline-block" style={{ borderColor: "var(--gt)" }} /><span className="text-on-surface">Ground truth</span></div>}
                            </div>
                          )}
                        </div>
                        <div className="lg:col-span-4 flex flex-col gap-space-md bg-surface-container p-space-md rounded-xl">
                          {v && (
                            <div>
                              <div className="flex items-center gap-2 pb-2 mb-3 border-b border-surface-container-high">
                                <Icon name="verified_user" className="text-primary text-[18px]" />
                                <span className="font-label-caps text-label-caps uppercase text-on-surface font-semibold tracking-wider">Metric validation</span>
                              </div>
                              <div className="space-y-2">
                                {[
                                  ["Dice coefficient", "Sørensen–Dice", fmt(v.dice, 3), "text-primary"],
                                  ["IoU (Jaccard)", "intersection / union", fmt(v.iou, 3), "text-secondary"],
                                  ["Sensitivity", "true positive rate", fmt(v.sensitivity, 3), "text-on-surface"],
                                  ["Specificity", "true negative rate", fmt(v.specificity, 3), "text-on-surface"],
                                  ["HD95", "boundary distance", `${fmt(v.hd95_px, 1)} px`, "text-primary"],
                                ].map(([k, sub, val, cls]) => (
                                  <div key={k} className="flex items-center justify-between bg-surface-container-low p-2.5 rounded">
                                    <div className="flex flex-col"><span className="text-body-sm text-on-surface font-medium">{k}</span><span className="font-label-micro text-label-micro text-on-surface-variant">{sub}</span></div>
                                    <span className={`font-metric-value text-metric-value font-semibold ${cls}`}>{val}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          <div className="bg-surface-container-lowest p-3 rounded-lg">
                            <span className="font-label-micro text-label-micro uppercase text-on-surface-variant block mb-2 font-semibold">Segmentation details</span>
                            <dl className="space-y-1.5 text-body-sm">
                              {[
                                ["Method", r.segmentation.method],
                                ["Threshold", fmt(r.segmentation.threshold, 0)],
                                ["Canny (low/high)", `${fmt(r.segmentation.canny_low, 0)} / ${fmt(r.segmentation.canny_high, 0)}`],
                                ["Right lung", `${m.area_right_lung_px} px`],
                                ["Left lung", `${m.area_left_lung_px} px`],
                                ["Thoracic width", `${m.thoracic_width_px ?? "—"} px`],
                                ["Lung height", `${m.lung_height_px ?? "—"} px`],
                                ["Mean intensity", fmt(m.lung_mean_intensity, 1)],
                              ].map(([k, val]) => (
                                <div key={k} className="flex justify-between gap-3"><dt className="text-on-surface-variant">{k}</dt><dd className="font-metric-value text-on-surface">{val}</dd></div>
                              ))}
                            </dl>
                          </div>
                        </div>
                      </div>
                      <div className="rounded-xl bg-surface-container/70 p-3.5 flex items-start gap-3">
                        <div className="w-8 h-8 rounded-lg bg-primary-container/20 shrink-0 flex items-center justify-center text-primary"><Icon name="lightbulb" className="text-[20px]" /></div>
                        <p className="text-body-sm text-on-surface-variant leading-relaxed self-center">{stageInfo.note}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {STAGES.map((st) => (
                        <button key={st.id} onClick={() => { setStage(st.id); setGrid(false); }} className="text-left group">
                          <div className="rounded-lg overflow-hidden bg-surface-container-lowest group-hover:ring-1 ring-primary transition-all"><img src={r.images[st.id]} alt={st.label} className="w-full aspect-square object-contain" /></div>
                          <div className="font-label-caps text-label-caps uppercase text-on-surface-variant group-hover:text-primary mt-1.5">{st.label}</div>
                        </button>
                      ))}
                    </div>
                  )}
                </Panel>

                <Panel title="Radiometric intensity histogram" icon="analytics">
                  <HistogramChart original={r.histogram.original} enhanced={r.histogram.enhanced} />
                  <p className="text-body-sm text-on-surface-variant mt-2">CLAHE spreads the crowded mid-grey values over the full 0-255 range, which makes lung borders easier to threshold.</p>
                </Panel>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// v2
