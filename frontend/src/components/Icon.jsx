/** Material Symbols icon:  <Icon name="monitor_heart" fill className="text-lg" /> */
export default function Icon({ name, fill = false, className = "", style = {} }) {
  return (
    <span
      className={`material-symbols-outlined ${className}`}
      style={fill ? { fontVariationSettings: "'FILL' 1", ...style } : style}
    >
      {name}
    </span>
  );
}
