import { useState } from "react";
import { Link } from "react-router-dom";
import { evaluateXray } from "../api/services";
import { Badge, Button, EmptyState, ErrorBanner, Kpi, PageHeader, Panel, Segmented, Spinner } from "../components/ui";
import { DiceHistogram } from "../components/charts";
import { fmt } from "../utils/format";
import Icon from "../components/Icon";

const METRICS = [
  ["dice", "Dice", 3],
  ["iou", "IoU", 3],
  ["sensitivity", "Sensitivity", 3],
  ["specificity", "Specificity", 4],
  ["hd95_px", "HD95 (px)", 1],
];

function exportCsv(method, rep) {
  const cols = ["id", "dice", "iou", "sensitivity", "specificity", "hd95_px"];
  const csv = [cols.join(","), ...rep.rows.map((r) => cols.map((c) => r[c]).join(","))].join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = `segmentation_metrics_${method}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

export default function Validation() {
  const [method, setMethod] = useState("otsu");
  const [morph, setMorph] = useState(7);
  const [reports, setReports] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async (methods) => {
    setLoading(true);
    setError("");
    try {
      const out = {};
      for (const m of methods) {
        const r = await evaluateXray({ method: m, morph_k: morph });
        out[m] = r.data;
      }
      setReports((p) => ({ ...p, ...out }));
    } catch (e) {
      setError(e.userMessage);
    } finally {
      setLoading(false);
    }
  };

  const rep = reports[method];
  const compared = Object.entries(reports);

  return (
    <div className="p-space-lg lg:p-margin-desktop">
      <div className="max-w-[1440px] mx-auto space-y-space-lg">
        <PageHeader
          eyebrow="Benchmark"
          title="Segmentation Validation"
          subtitle="Run the lung-segmentation pipeline over every image that has a ground-truth mask and measure agreement (Dice, IoU, sensitivity, specificity, HD95)."
          right={rep && rep.n > 0 && <Button variant="ghost" icon="file_download" onClick={() => exportCsv(method, rep)}>Export metrics CSV</Button>}
        />

        <Panel title="Evaluation configuration" icon="science" right={loading && <Spinner />}>
          <div className="flex flex-wrap items-end gap-4">
            <div><div className="font-label-micro text-label-micro uppercase text-on-surface-variant mb-1.5">Segmentation method</div><Segmented options={["otsu", "kmeans", "adaptive"]} value={method} onChange={setMethod} /></div>
            <div className="w-40"><div className="font-label-micro text-label-micro uppercase text-on-surface-variant mb-1.5">Morph. kernel (px)</div><input type="number" min={3} max={31} step={2} value={morph} onChange={(e) => setMorph(Number(e.target.value))} /></div>
            <Button icon="play_arrow" onClick={() => run([method])} disabled={loading}>Evaluate {method}</Button>
            <Button variant="ghost" icon="compare" onClick={() => run(["otsu", "kmeans", "adaptive"])} disabled={loading}>Compare all methods</Button>
          </div>
          <p className="text-body-sm text-on-surface-variant mt-3">On the real Montgomery set (138 images) this takes a minute or two - full-resolution PNGs are loaded from disk. Results are cached per parameter set.</p>
        </Panel>

        <ErrorBanner>{error}</ErrorBanner>
        {!rep && !error && <Panel><EmptyState icon="fact_check" title="No evaluation yet">Press “Evaluate” to run the batch. Needs images with masks in <code className="font-metric-value">data/xray/masks</code>.</EmptyState></Panel>}

        {rep && rep.n === 0 && <Panel><EmptyState icon="image_not_supported" title="No images with ground-truth masks">No X-ray images with masks were found in <code className="font-metric-value">data/xray/masks</code>.</EmptyState></Panel>}

        {rep && rep.n > 0 && (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-space-md">
              <Kpi label="Test images" icon="photo_library" value={rep.n} sub="paired with masks" />
              <Kpi label="Mean Dice" icon="check_circle" value={fmt(rep.summary.dice.mean, 3)} sub={`SD ± ${fmt(rep.summary.dice.std, 3)}`} tone="primary" />
              <Kpi label="Mean IoU" icon="layers" value={fmt(rep.summary.iou.mean, 3)} sub={`median ${fmt(rep.summary.iou.median, 3)}`} tone="secondary" />
              <Kpi label="Dice ≥ 0.90" icon="verified" value={fmt(rep.fraction_dice_above_0_9 * 100, 0)} unit="% of images" tone="tertiary" />
              <Kpi label="Mean HD95" icon="straighten" value={fmt(rep.summary.hd95_px?.mean, 1)} unit="PX" sub="95th pct boundary error" tone="secondary" />
            </div>

            <div className="grid lg:grid-cols-2 gap-4">
              <Panel title="Dice distribution" icon="bar_chart"><DiceHistogram hist={rep.dice_histogram} /></Panel>
              <Panel title={`Summary - ${method}`} icon="table">
                <table className="w-full text-left text-body-sm [&_th]:px-3 [&_th]:py-3 [&_td]:px-3 [&_td]:py-2.5 [&_th:first-child]:rounded-l [&_th:last-child]:rounded-r">
                  <thead><tr className="bg-surface-container-lowest text-on-surface-variant font-label-micro text-label-micro uppercase tracking-wider"><th className="py-2">Metric</th><th>Mean</th><th>SD</th><th>Median</th><th>Min</th></tr></thead>
                  <tbody>
                    {METRICS.map(([k, label, d]) => rep.summary[k] && (
                      <tr key={k} className="hover:bg-surface-container transition-colors"><td className="py-2 font-semibold">{label}</td>
                        <td className="font-metric-value">{fmt(rep.summary[k].mean, d)}</td><td className="font-metric-value">{fmt(rep.summary[k].std, d)}</td>
                        <td className="font-metric-value">{fmt(rep.summary[k].median, d)}</td><td className="font-metric-value">{fmt(rep.summary[k].min, d)}</td></tr>
                    ))}
                  </tbody>
                </table>
              </Panel>
            </div>

            {compared.length > 1 && (
              <Panel title="Method comparison" icon="compare">
                <table className="w-full text-left text-body-sm [&_th]:px-3 [&_th]:py-3 [&_td]:px-3 [&_td]:py-2.5 [&_th:first-child]:rounded-l [&_th:last-child]:rounded-r">
                  <thead><tr className="bg-surface-container-lowest text-on-surface-variant font-label-micro text-label-micro uppercase tracking-wider"><th className="py-2">Method</th><th>Dice</th><th>IoU</th><th>Sensitivity</th><th>Specificity</th><th>HD95 px</th><th>Dice ≥ .9</th></tr></thead>
                  <tbody>
                    {compared.map(([m, rp]) => rp.summary && (
                      <tr key={m} className="hover:bg-surface-container transition-colors"><td className="py-2 font-semibold"><Badge tone={m === method ? "primary" : "neutral"}>{m}</Badge></td>
                        <td className="font-metric-value">{fmt(rp.summary.dice.mean, 3)}</td><td className="font-metric-value">{fmt(rp.summary.iou.mean, 3)}</td>
                        <td className="font-metric-value">{fmt(rp.summary.sensitivity.mean, 3)}</td><td className="font-metric-value">{fmt(rp.summary.specificity.mean, 4)}</td>
                        <td className="font-metric-value">{fmt(rp.summary.hd95_px?.mean, 1)}</td><td className="font-metric-value">{fmt(rp.fraction_dice_above_0_9 * 100, 0)}%</td></tr>
                    ))}
                  </tbody>
                </table>
              </Panel>
            )}

            <Panel title="Per-image results (worst first)" icon="priority_high" bodyClass="p-3">
              <div className="table-scroll max-h-[420px] overflow-y-auto">
                <table className="w-full text-left text-body-sm min-w-[560px] [&_th]:px-3 [&_th]:py-3 [&_td]:px-3 [&_td]:py-2.5">
                  <thead className="sticky top-0 bg-surface-container-low z-10"><tr className="bg-surface-container-lowest text-on-surface-variant font-label-micro text-label-micro uppercase tracking-wider"><th>Image</th><th>Dice</th><th>IoU</th><th>Sens.</th><th>Spec.</th><th>HD95</th><th></th></tr></thead>
                  <tbody>
                    {rep.rows.map((x) => (
                      <tr key={x.id} className="hover:bg-surface-container transition-colors">
                        <td className="font-metric-value">{x.id}</td>
                        <td><Badge tone={x.dice >= 0.9 ? "success" : x.dice >= 0.8 ? "warning" : "error"}>{fmt(x.dice, 3)}</Badge></td>
                        <td className="font-metric-value">{fmt(x.iou, 3)}</td><td className="font-metric-value">{fmt(x.sensitivity, 3)}</td>
                        <td className="font-metric-value">{fmt(x.specificity, 3)}</td><td className="font-metric-value">{fmt(x.hd95_px, 1)}</td>
                        <td className="text-right"><Link className="text-primary text-body-sm inline-flex items-center gap-1 hover:text-primary-fixed-dim" to={`/xray?image=${x.id}`}>Inspect in lab <Icon name="arrow_forward" className="text-[16px]" /></Link></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          </>
        )}
      </div>
    </div>
  );
}

// v2
