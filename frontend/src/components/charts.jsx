import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceDot, ReferenceLine,
  AreaChart, Area, BarChart, Bar, ScatterChart, Scatter, ComposedChart, Cell,
} from "recharts";

const GRID = "var(--outline-variant)";
const tip = {
  contentStyle: {
    background: "var(--surface-container-high)",
    border: "1px solid color-mix(in srgb, var(--outline-variant) 60%, transparent)",
    borderRadius: 8,
    fontSize: 12,
    color: "var(--on-surface)",
  },
  labelStyle: { color: "var(--on-surface-variant)" },
  itemStyle: { color: "var(--on-surface)" },
};
const axis = { stroke: GRID, tickLine: false };
const f = (d) => (v) => (typeof v === "number" ? v.toFixed(d) : v);

function Box({ h = 300, children, grid = false }) {
  return (
    <div className={`rounded-xl ${grid ? "ecg-grid" : ""}`} style={{ height: h }}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}

/** Raw vs filtered ECG with R-peak markers. */
export function SignalChart({ signal, peaks, showRaw = true, h = 340, compact = false }) {
  const data = signal.t_s.map((t, i) => ({ t, raw: signal.raw_mv[i], filt: signal.filtered_mv[i] }));
  return (
    <Box h={h} grid={!compact}>
      <LineChart data={data} margin={compact ? { top: 6, right: 6, bottom: 6, left: 6 } : { top: 10, right: 16, bottom: 4, left: 0 }}>
        {!compact && <CartesianGrid stroke={GRID} strokeDasharray="2 4" vertical={false} />}
        <XAxis hide={compact} dataKey="t" type="number" domain={["dataMin", "dataMax"]} tickFormatter={f(1)} {...axis} label={compact ? undefined : { value: "time (s)", position: "insideBottomRight", offset: -2, fill: "var(--on-surface-variant)", fontSize: 11 }} />
        <YAxis hide={compact} {...axis} tickFormatter={f(1)} width={44} label={compact ? undefined : { value: "mV", angle: -90, position: "insideLeft", fill: "var(--on-surface-variant)", fontSize: 11 }} />
        {!compact && <Tooltip {...tip} formatter={(v) => (typeof v === "number" ? `${v.toFixed(3)} mV` : v)} labelFormatter={(t) => `t = ${Number(t).toFixed(3)} s`} />}
        {!compact && <Legend />}
        {showRaw && <Line name="Raw" dataKey="raw" stroke="var(--outline)" strokeOpacity={0.75} dot={false} strokeWidth={1} isAnimationActive={false} />}
        <Line name="Filtered" dataKey="filt" stroke="var(--signal)" dot={false} strokeWidth={compact ? 1.6 : 2} isAnimationActive={false} style={{ filter: "drop-shadow(0 0 4px color-mix(in srgb, var(--signal) 55%, transparent))" }} />
        {peaks.map((p, i) => (
          <ReferenceDot key={i} x={p.t_s} y={p.amp_mv} r={compact ? 3 : 4.5} fill="var(--peak)" stroke="var(--surface)" strokeWidth={1.5} ifOverflow="visible" />
        ))}
      </LineChart>
    </Box>
  );
}

/** Welch PSD (dB) raw vs filtered with mains marker. */
export function PsdChart({ psd, mains, h = 280 }) {
  const data = psd.freqs_hz.map((x, i) => ({ f: x, raw: psd.raw_db[i], filt: psd.filtered_db[i] })).filter((d) => d.f <= 100);
  return (
    <Box h={h}>
      <LineChart data={data} margin={{ top: 26, right: 16, bottom: 4, left: 0 }}>
        <CartesianGrid stroke={GRID} strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="f" type="number" domain={[0, 100]} tickFormatter={f(0)} {...axis} label={{ value: "frequency (Hz)", position: "insideBottomRight", offset: -2, fill: "var(--on-surface-variant)", fontSize: 11 }} />
        <YAxis {...axis} tickFormatter={f(0)} width={44} label={{ value: "dB", angle: -90, position: "insideLeft", fill: "var(--on-surface-variant)", fontSize: 11 }} />
        <Tooltip {...tip} formatter={(v) => `${Number(v).toFixed(1)} dB`} labelFormatter={(x) => `${Number(x).toFixed(2)} Hz`} />
        <Legend />
        <ReferenceLine x={mains} stroke="var(--warning)" strokeDasharray="4 3" label={{ value: `${mains} Hz mains`, fill: "var(--warning)", fontSize: 11, position: "top" }} />
        <Line name="Raw PSD" dataKey="raw" stroke="var(--outline)" dot={false} strokeWidth={1.4} isAnimationActive={false} />
        <Line name="Filtered PSD" dataKey="filt" stroke="var(--primary)" dot={false} strokeWidth={1.8} isAnimationActive={false} />
      </LineChart>
    </Box>
  );
}

/** Single-sided FFT amplitude spectrum. */
export function FftChart({ fft, domHz, h = 240 }) {
  const data = fft.freqs_hz.map((x, i) => ({ f: x, a: fft.amplitude_mv[i] }));
  return (
    <Box h={h}>
      <AreaChart data={data} margin={{ top: 26, right: 16, bottom: 4, left: 0 }}>
        <defs>
          <linearGradient id="fftg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--secondary)" stopOpacity={0.5} />
            <stop offset="100%" stopColor="var(--secondary)" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID} strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="f" type="number" domain={[0, 60]} tickFormatter={f(0)} {...axis} label={{ value: "frequency (Hz)", position: "insideBottomRight", offset: -2, fill: "var(--on-surface-variant)", fontSize: 11 }} />
        <YAxis {...axis} tickFormatter={f(2)} width={44} label={{ value: "amp (mV)", angle: -90, position: "insideLeft", fill: "var(--on-surface-variant)", fontSize: 11 }} />
        <Tooltip {...tip} formatter={(v) => `${Number(v).toFixed(4)} mV`} labelFormatter={(x) => `${Number(x).toFixed(2)} Hz`} />
        {domHz && <ReferenceLine x={domHz} stroke="var(--tertiary)" strokeDasharray="4 3" label={{ value: `HR line ${domHz.toFixed(2)} Hz`, fill: "var(--tertiary)", fontSize: 11, position: "insideTopRight" }} />}
        <Area dataKey="a" stroke="var(--secondary)" fill="url(#fftg)" strokeWidth={1.6} dot={false} isAnimationActive={false} />
      </AreaChart>
    </Box>
  );
}

export function AutocorrChart({ ac, h = 280 }) {
  const data = ac.lags_s.map((l, i) => ({ l, r: ac.values[i] }));
  return (
    <Box h={h}>
      <AreaChart data={data} margin={{ top: 26, right: 16, bottom: 4, left: 0 }}>
        <defs>
          <linearGradient id="acg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.35} />
            <stop offset="100%" stopColor="var(--primary)" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID} strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="l" type="number" domain={[0, "dataMax"]} tickFormatter={f(1)} {...axis} label={{ value: "lag (s)", position: "insideBottomRight", offset: -2, fill: "var(--on-surface-variant)", fontSize: 11 }} />
        <YAxis domain={[-1, 1]} {...axis} tickFormatter={f(1)} width={44} />
        <Tooltip {...tip} formatter={(v) => Number(v).toFixed(3)} labelFormatter={(x) => `lag ${Number(x).toFixed(3)} s`} />
        <ReferenceLine y={0} stroke={GRID} />
        {ac.peak_lag_s && (
          <ReferenceLine x={ac.peak_lag_s} stroke="var(--tertiary)" strokeDasharray="4 3" label={{ value: `${(60 / ac.peak_lag_s).toFixed(0)} bpm`, fill: "var(--tertiary)", fontSize: 11, position: "top" }} />
        )}
        <Area dataKey="r" stroke="var(--primary)" fill="url(#acg)" strokeWidth={1.8} dot={false} isAnimationActive={false} />
      </AreaChart>
    </Box>
  );
}

export function RRChart({ rr, h = 220 }) {
  const data = rr.map((v, i) => ({ n: i + 1, rr: v }));
  const mean = rr.reduce((a, b) => a + b, 0) / rr.length;
  return (
    <Box h={h}>
      <BarChart data={data} margin={{ top: 10, right: 16, bottom: 4, left: 0 }}>
        <CartesianGrid stroke={GRID} strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="n" {...axis} label={{ value: "beat #", position: "insideBottomRight", offset: -2, fill: "var(--on-surface-variant)", fontSize: 11 }} />
        <YAxis domain={["dataMin - 100", "dataMax + 100"]} {...axis} tickFormatter={f(0)} width={44} />
        <Tooltip {...tip} formatter={(v) => `${Number(v).toFixed(0)} ms`} labelFormatter={(n) => `RR #${n}`} />
        <ReferenceLine y={mean} stroke="var(--tertiary)" strokeDasharray="4 3" />
        <Bar dataKey="rr" fill="var(--primary)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </Box>
  );
}

export function PoincareChart({ pc, h = 240 }) {
  const data = pc.x.map((x, i) => ({ x, y: pc.y[i] }));
  const all = [...pc.x, ...pc.y];
  const lo = Math.floor((Math.min(...all) - 50) / 50) * 50;
  const hi = Math.ceil((Math.max(...all) + 50) / 50) * 50;
  return (
    <Box h={h}>
      <ScatterChart margin={{ top: 10, right: 16, bottom: 4, left: 0 }}>
        <CartesianGrid stroke={GRID} strokeDasharray="2 4" />
        <XAxis dataKey="x" type="number" domain={[lo, hi]} name="RRn" {...axis} tickFormatter={f(0)} label={{ value: "RR n (ms)", position: "insideBottomRight", offset: -2, fill: "var(--on-surface-variant)", fontSize: 11 }} />
        <YAxis dataKey="y" type="number" domain={[lo, hi]} name="RRn+1" {...axis} tickFormatter={f(0)} width={44} />
        <Tooltip {...tip} cursor={{ strokeDasharray: "3 3" }} />
        <ReferenceLine segment={[{ x: lo, y: lo }, { x: hi, y: hi }]} stroke={GRID} strokeDasharray="4 3" />
        <Scatter data={data} fill="var(--secondary)" isAnimationActive={false} />
      </ScatterChart>
    </Box>
  );
}

export function TemplateChart({ tpl, h = 260 }) {
  const data = tpl.t_s.map((t, i) => ({ t, m: tpl.mean_mv[i], lo: tpl.mean_mv[i] - tpl.std_mv[i], band: [tpl.mean_mv[i] - tpl.std_mv[i], tpl.mean_mv[i] + tpl.std_mv[i]] }));
  return (
    <Box h={h} grid>
      <ComposedChart data={data} margin={{ top: 10, right: 16, bottom: 4, left: 0 }}>
        <CartesianGrid stroke={GRID} strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="t" type="number" domain={["dataMin", "dataMax"]} tickFormatter={f(2)} {...axis} label={{ value: "time from R (s)", position: "insideBottomRight", offset: -2, fill: "var(--on-surface-variant)", fontSize: 11 }} />
        <YAxis {...axis} tickFormatter={f(1)} width={44} />
        <Tooltip {...tip} formatter={(v) => (Array.isArray(v) ? `${v[0].toFixed(2)} … ${v[1].toFixed(2)}` : `${Number(v).toFixed(3)} mV`)} labelFormatter={(t) => `${Number(t).toFixed(3)} s`} />
        <ReferenceLine x={0} stroke="var(--error)" strokeDasharray="3 3" />
        <Area dataKey="band" stroke="none" fill="var(--primary)" fillOpacity={0.18} isAnimationActive={false} name="± 1 SD" />
        <Line dataKey="m" stroke="var(--primary)" dot={false} strokeWidth={2.2} isAnimationActive={false} name="mean beat" />
      </ComposedChart>
    </Box>
  );
}

export function FilterResponseChart({ resp, h = 240 }) {
  const data = resp.freqs_hz.map((x, i) => ({ f: x, one: Math.max(resp.single_pass_db[i], -80), zero: Math.max(resp.zero_phase_db[i], -80) }));
  return (
    <Box h={h}>
      <LineChart data={data} margin={{ top: 10, right: 16, bottom: 4, left: 0 }}>
        <CartesianGrid stroke={GRID} strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="f" type="number" scale="sqrt" domain={[0, "dataMax"]} ticks={[0, 1, 5, 10, 20, 40, 80, 150, 250]} tickFormatter={f(0)} {...axis} label={{ value: "frequency (Hz)", position: "insideBottomRight", offset: -2, fill: "var(--on-surface-variant)", fontSize: 11 }} />
        <YAxis domain={[-80, 5]} {...axis} tickFormatter={f(0)} width={44} label={{ value: "gain (dB)", angle: -90, position: "insideLeft", fill: "var(--on-surface-variant)", fontSize: 11 }} />
        <Tooltip {...tip} formatter={(v) => `${Number(v).toFixed(1)} dB`} labelFormatter={(x) => `${Number(x).toFixed(2)} Hz`} />
        <Legend />
        <ReferenceLine y={-3} stroke="var(--warning)" strokeDasharray="4 3" label={{ value: "-3 dB", fill: "var(--warning)", fontSize: 11, position: "right" }} />
        <Line name="single pass (filter)" dataKey="one" stroke="var(--secondary)" dot={false} strokeWidth={1.6} isAnimationActive={false} />
        <Line name="zero-phase (filtfilt = squared)" dataKey="zero" stroke="var(--primary)" dot={false} strokeWidth={2} isAnimationActive={false} />
      </LineChart>
    </Box>
  );
}

export function BandBars({ before, after }) {
  const labels = { baseline_wander: "< 0.5 Hz  baseline", p_t_waves: "0.5-5 Hz  P / T", qrs: "5-15 Hz  QRS", high_freq: "15-40 Hz  high", noise: "> 40 Hz  noise" };
  const data = Object.keys(labels).map((k) => ({ band: labels[k], before: (before[k] || 0) * 100, after: (after[k] || 0) * 100 }));
  return (
    <Box h={240}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 10 }}>
        <CartesianGrid stroke={GRID} strokeDasharray="2 4" horizontal={false} />
        <XAxis type="number" unit="%" {...axis} tickFormatter={f(0)} />
        <YAxis type="category" dataKey="band" width={120} {...axis} />
        <Tooltip {...tip} formatter={(v) => `${Number(v).toFixed(1)} %`} />
        <Legend />
        <Bar name="raw" dataKey="before" fill="var(--outline)" radius={[0, 4, 4, 0]} isAnimationActive={false} />
        <Bar name="filtered" dataKey="after" fill="var(--primary)" radius={[0, 4, 4, 0]} isAnimationActive={false} />
      </BarChart>
    </Box>
  );
}

export function HistogramChart({ original, enhanced, h = 200 }) {
  const data = original.map((v, i) => ({ bin: Math.round((i / original.length) * 255), original: v, enhanced: enhanced[i] }));
  return (
    <Box h={h}>
      <AreaChart data={data} margin={{ top: 6, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={GRID} strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="bin" {...axis} />
        <YAxis hide />
        <Tooltip {...tip} />
        <Legend />
        <Area name="original" dataKey="original" stroke="var(--outline)" fill="var(--outline)" fillOpacity={0.25} isAnimationActive={false} />
        <Area name="CLAHE enhanced" dataKey="enhanced" stroke="var(--primary)" fill="var(--primary)" fillOpacity={0.25} isAnimationActive={false} />
      </AreaChart>
    </Box>
  );
}

export function DiceHistogram({ hist, h = 240 }) {
  const data = hist.bins.map((b, i) => ({ bin: b, count: hist.counts[i] }));
  return (
    <Box h={h}>
      <BarChart data={data} margin={{ top: 10, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={GRID} strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="bin" {...axis} tick={{ fontSize: 10 }} />
        <YAxis {...axis} width={34} allowDecimals={false} />
        <Tooltip {...tip} />
        <Bar dataKey="count" name="images" radius={[4, 4, 0, 0]} isAnimationActive={false}>
          {data.map((d, i) => (
            <Cell key={i} fill={i >= 9 ? "var(--success)" : i >= 8 ? "var(--primary)" : i >= 6 ? "var(--warning)" : "var(--error)"} />
          ))}
        </Bar>
      </BarChart>
    </Box>
  );
}
