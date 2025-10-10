import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

function header(doc, title, subtitle) {
  doc.setFillColor(11, 127, 115);
  doc.rect(0, 0, 210, 22, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(15);
  doc.setFont("helvetica", "bold");
  doc.text(title, 14, 13);
  doc.setFontSize(9);
  doc.setFont("helvetica", "normal");
  doc.text(subtitle, 14, 19);
  doc.setTextColor(30, 30, 30);
}

function footer(doc) {
  const n = doc.getNumberOfPages();
  for (let i = 1; i <= n; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(110, 110, 110);
    doc.text(`Page ${i}/${n}`, 190, 290, { align: "right" });
  }
}

const f = (v, d = 1, u = "") => (v === null || v === undefined ? "-" : `${Number(v).toFixed(d)}${u}`);

export function exportEcgReport(r) {
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  header(doc, "ECG Analysis Report", `Record ${r.record.id} - lead ${r.params.lead} - ${new Date().toLocaleString()}`);

  autoTable(doc, {
    startY: 28,
    head: [["Recording", "Value"]],
    body: [
      ["Record ID", r.record.id],
      ["Source", r.record.source || r.record.format],
      ["Sampling rate", `${r.record.fs} Hz`],
      ["Duration analysed", `${f(r.params.window[1] - r.params.window[0], 1)} s`],
      ["Leads", r.record.lead_names.join(", ")],
      ["Filter", r.params.apply_filter ? `Butterworth band-pass ${r.params.low_hz}-${r.params.high_hz} Hz, order ${r.params.order} (zero-phase)${r.params.notch ? `, notch ${r.params.mains_hz} Hz` : ""}` : "none"],
    ],
    theme: "grid", headStyles: { fillColor: [11, 127, 115] }, styles: { fontSize: 9 },
  });

  autoTable(doc, {
    head: [["Metric", "Value", "Method"]],
    body: [
      ["Heart rate", f(r.hrv.hr_bpm, 1, " bpm"), "mean RR (R-peak detection)"],
      ["Heart rate", f(r.hr_methods_bpm.autocorrelation, 1, " bpm"), "autocorrelation"],
      ["Heart rate", f(r.hr_methods_bpm.fft, 1, " bpm"), "FFT fundamental"],
      ["Beats detected", String(r.hrv.n_beats), "Pan-Tompkins style"],
      ["SDNN", f(r.hrv.sdnn_ms, 1, " ms"), "HRV (short window - indicative)"],
      ["RMSSD", f(r.hrv.rmssd_ms, 1, " ms"), "HRV"],
      ["pNN50", f(r.hrv.pnn50_pct, 1, " %"), "HRV"],
      ["Rhythm regularity", f(r.autocorr.regularity, 2), "autocorrelation peak height (sinus ~0.4-0.8, irregular <0.25)"],
      ["Signal quality", `${r.quality.label} (${r.quality.score})`, `SNR ${f(r.quality.snr_db, 1)} dB`],
    ],
    theme: "striped", headStyles: { fillColor: [11, 127, 115] }, styles: { fontSize: 9 },
  });

  autoTable(doc, {
    head: [["Lead", "RMS (mV)", "Peak-to-peak (mV)", "R amplitude (mV)", "SNR (dB)"]],
    body: r.leads_summary.map((l) => [l.lead, f(l.rms_mv, 3), f(l.peak_to_peak_mv, 2), f(l.r_amplitude_mv, 2), f(l.snr_db, 1)]),
    theme: "grid", headStyles: { fillColor: [11, 127, 115] }, styles: { fontSize: 8 },
  });

  autoTable(doc, {
    head: [["Level", "Finding"]],
    body: r.findings.map((x) => [x.level.toUpperCase(), x.text]),
    theme: "plain", headStyles: { fillColor: [11, 127, 115] }, styles: { fontSize: 9 }, columnStyles: { 0: { cellWidth: 20 } },
  });
  footer(doc);
  doc.save(`ECG_report_${r.record.id}_${r.params.lead}.pdf`);
}

export function exportXrayReport(r) {
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  header(doc, "Chest X-ray Analysis Report", `Image ${r.image_id} - method ${r.params.method} - ${new Date().toLocaleString()}`);
  const m = r.measurements;
  let y = 28;
  try {
    doc.addImage(r.images.original, "PNG", 14, y, 58, 58);
    doc.addImage(r.images.overlay, "PNG", 76, y, 58, 58);
    doc.addImage(r.images.canny, "PNG", 138, y, 58, 58);
    doc.setFontSize(8);
    doc.text("Original (resized)", 14, y + 62);
    doc.text(r.validation ? "Segmentation (cyan) vs ground truth (magenta)" : "Segmentation overlay", 76, y + 62);
    doc.text("Canny edges", 138, y + 62);
    y += 68;
  } catch (e) {
    /* image embedding is best-effort */
  }
  autoTable(doc, {
    startY: y,
    head: [["Measurement", "Value"]],
    body: [
      ["Lung area (% of image)", f(m.lung_area_pct, 1, " %")],
      ["Right lung area (image left)", `${m.area_right_lung_px} px`],
      ["Left lung area (image right)", `${m.area_left_lung_px} px`],
      ["Asymmetry index", f(m.asymmetry_index, 3)],
      ["Regions found", String(m.n_regions)],
      ["Mean / SD intensity in lungs", `${f(m.lung_mean_intensity, 1)} / ${f(m.lung_std_intensity, 1)}`],
      ["Texture entropy", f(m.lung_entropy_bits, 2, " bits")],
      ["Edge density in lungs", f(m.edge_density_in_lung, 3)],
      ["Threshold used", f(r.segmentation.threshold, 0)],
    ],
    theme: "striped", headStyles: { fillColor: [11, 127, 115] }, styles: { fontSize: 9 },
  });
  if (r.validation) {
    const v = r.validation;
    autoTable(doc, {
      head: [["Validation vs ground-truth mask", "Value"]],
      body: [
        ["Dice", f(v.dice, 4)], ["IoU", f(v.iou, 4)], ["Sensitivity", f(v.sensitivity, 4)],
        ["Specificity", f(v.specificity, 4)], ["Precision", f(v.precision, 4)], ["HD95", f(v.hd95_px, 1, " px")],
      ],
      theme: "grid", headStyles: { fillColor: [11, 127, 115] }, styles: { fontSize: 9 },
    });
  }
  autoTable(doc, {
    head: [["Parameter", "Value"]],
    body: Object.entries(r.params).map(([k, v]) => [k, v === null ? "auto" : String(v)]),
    theme: "plain", headStyles: { fillColor: [11, 127, 115] }, styles: { fontSize: 8 },
  });
  footer(doc);
  doc.save(`Xray_report_${r.image_id}.pdf`);
}

// v2
