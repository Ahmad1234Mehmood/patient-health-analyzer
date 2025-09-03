import Icon from "./Icon";

export function Panel({ title, icon, right, children, className = "", bodyClass = "p-5" }) {
  return (
    <section className={`panel rounded-xl ${className}`}>
      {(title || right) && (
        <header className="flex items-center justify-between gap-3 px-5 pt-4 pb-1">
          <h3 className="flex items-center gap-2 font-label-caps text-label-caps uppercase tracking-wider text-on-surface">
            {icon && <Icon name={icon} className="text-[18px] text-primary" />}
            {title}
          </h3>
          {right}
        </header>
      )}
      <div className={bodyClass}>{children}</div>
    </section>
  );
}

export function Badge({ tone = "neutral", children, className = "" }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-label-micro text-label-micro uppercase tint-${tone} ${className}`}>
      {children}
    </span>
  );
}

export function Kpi({ label, value, unit, sub, tone = "primary", icon }) {
  return (
    <div className="panel rounded-xl p-4 hover:bg-surface-container transition-colors">
      <div className="flex items-center justify-between text-on-surface-variant">
        <div className="font-label-caps text-label-caps uppercase tracking-wider">{label}</div>
        {icon && (
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center bg-surface-container-high text-${tone}`}>
            <Icon name={icon} className="text-[18px]" />
          </div>
        )}
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className={`font-metric-display text-metric-display font-semibold ${tone === "primary" ? "text-primary" : "text-on-surface"}`}>{value}</span>
        {unit && <span className="font-label-caps text-label-caps text-on-surface-variant">{unit}</span>}
      </div>
      {sub && <div className="mt-1 text-body-sm text-on-surface-variant">{sub}</div>}
    </div>
  );
}

export function Field({ label, hint, value, children }) {
  return (
    <label className="block space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="font-label-micro text-label-micro uppercase text-on-surface-variant">{label}</span>
        {value !== undefined && <span className="font-metric-value text-metric-value text-primary">{value}</span>}
      </div>
      {children}
      {hint && <div className="text-body-sm text-on-surface-variant leading-snug">{hint}</div>}
    </label>
  );
}

export function Slider({ label, hint, value, min, max, step = 1, onChange, format }) {
  return (
    <Field label={label} hint={hint} value={format ? format(value) : value}>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} />
    </Field>
  );
}

export function Toggle({ label, checked, onChange, hint }) {
  return (
    <div className="flex items-center justify-between gap-3 p-2.5 rounded-lg bg-surface-container-lowest/60">
      <div>
        <div className="text-body-sm font-medium text-on-surface">{label}</div>
        {hint && <div className="font-label-micro text-label-micro text-on-surface-variant normal-case tracking-normal">{hint}</div>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className="relative shrink-0 w-9 h-5 rounded-full transition-colors"
        style={{ background: checked ? "var(--primary-container)" : "var(--surface-container-high)" }}
      >
        <span className="absolute top-[2px] w-4 h-4 rounded-full transition-all" style={{ left: checked ? 18 : 2, background: checked ? "var(--surface-container-lowest)" : "var(--on-surface)" }} />
      </button>
    </div>
  );
}

export function Segmented({ options, value, onChange, size = "md" }) {
  return (
    <div className="inline-flex flex-wrap gap-1 p-1 rounded-lg bg-surface-container-lowest">
      {options.map((o) => {
        const v = typeof o === "string" ? o : o.value;
        const l = typeof o === "string" ? o : o.label;
        const active = v === value;
        return (
          <button
            key={v}
            onClick={() => onChange(v)}
            className={`${size === "sm" ? "px-2.5 py-1" : "px-3 py-1.5"} rounded text-body-sm transition-colors ${
              active ? "bg-surface-container-high text-primary font-medium shadow-sm" : "text-on-surface-variant hover:text-on-surface"
            }`}
          >
            {l}
          </button>
        );
      })}
    </div>
  );
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="flex gap-1 overflow-x-auto no-scrollbar pb-2 border-b border-outline-variant/20">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-body-sm whitespace-nowrap transition-colors ${
            value === t.id ? "bg-surface-container-high text-primary font-medium shadow-sm" : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
          }`}
        >
          {t.icon && <Icon name={t.icon} className="text-base" />}
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function Button({ children, icon, variant = "primary", className = "", ...rest }) {
  return (
    <button
      {...rest}
      className={`inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-body-sm font-semibold transition-all active:scale-95 ${
        variant === "primary" ? "btn-primary" : "btn-ghost"
      } ${className}`}
    >
      {icon && <Icon name={icon} className="text-[18px]" />}
      {children}
    </button>
  );
}

export function Spinner({ className = "" }) {
  return <Icon name="progress_activity" className={`animate-spin text-primary ${className}`} />;
}

export function EmptyState({ icon = "inbox", title, children }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-14 px-6 text-on-surface-variant">
      <div className="w-14 h-14 rounded-2xl tint-neutral flex items-center justify-center mb-4">
        <Icon name={icon} className="text-3xl" />
      </div>
      <div className="font-semibold text-on-surface mb-1">{title}</div>
      <div className="text-sm max-w-md">{children}</div>
    </div>
  );
}

export function ErrorBanner({ children }) {
  if (!children) return null;
  return (
    <div className="flex items-start gap-3 rounded-xl tint-error border bd-error px-4 py-3 text-sm">
      <Icon name="error" className="text-lg mt-0.5" />
      <div className="text-on-surface">{children}</div>
    </div>
  );
}

export function PageHeader({ title, subtitle, eyebrow, right }) {
  return (
    <section className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-6 border-b border-outline-variant/30">
      <div className="flex flex-col gap-1 max-w-3xl">
        {eyebrow && (
          <span className="self-start px-2 py-0.5 rounded font-label-micro text-label-micro uppercase bg-primary-container/20 text-primary">{eyebrow}</span>
        )}
        <h1 className="text-headline-lg text-on-surface tracking-tight">{title}</h1>
        {subtitle && <p className="text-body-md text-on-surface-variant">{subtitle}</p>}
      </div>
      {right && <div className="flex flex-wrap items-center gap-3">{right}</div>}
    </section>
  );
}
