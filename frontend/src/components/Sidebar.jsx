import { NavLink } from "react-router-dom";
import { NAV_ITEMS } from "./navItems";
import Icon from "./Icon";

function NavItem({ item, onNavigate }) {
  return (
    <NavLink
      to={item.to}
      end={item.to === "/"}
      onClick={onNavigate}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2.5 rounded-r text-body-md transition-all ${
          isActive ? "nav-active font-semibold" : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
        }`
      }
    >
      <Icon name={item.icon} className="text-[20px]" />
      <span>{item.label}</span>
    </NavLink>
  );
}

/** Same markup for the fixed desktop rail and the sliding mobile drawer. */
export default function Sidebar({ variant = "desktop", open = false, onClose }) {
  const isMobile = variant === "mobile";
  const base = "w-64 bg-surface-container-lowest border-r border-outline-variant/30 flex-col justify-between pt-5 pb-6";
  const wrapper = isMobile
    ? `lg:hidden fixed left-0 top-0 h-full z-50 max-w-[85%] flex drawer overflow-y-auto ${base} ${open ? "translate-x-0" : "-translate-x-full"}`
    : `hidden lg:flex fixed left-0 top-0 h-full z-40 ${base}`;

  return (
    <aside className={wrapper}>
      <div className="flex flex-col">
        <div className="px-5 pb-6 border-b border-outline-variant/20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-primary-container flex items-center justify-center shadow-[inset_0_1px_0_0_rgba(255,255,255,0.4)]">
              <Icon name="monitor_heart" className="text-on-primary-container text-[20px]" />
            </div>
            <div className="flex flex-col">
              <span className="text-headline-sm font-semibold tracking-tight text-on-surface">HealthLens</span>
              <span className="font-label-micro text-label-micro uppercase tracking-wider text-primary">Data Analyzer</span>
            </div>
          </div>
          {isMobile && (
            <button onClick={onClose} className="text-on-surface-variant hover:text-on-surface" aria-label="Close menu">
              <Icon name="close" />
            </button>
          )}
        </div>

        <div className="px-3 pt-5">
          <span className="px-3 font-label-micro text-label-micro uppercase text-on-surface-variant tracking-wider block mb-2">Workspaces</span>
          <nav className="space-y-1">
            {NAV_ITEMS.map((item) => (
              <NavItem key={item.to} item={item} onNavigate={isMobile ? onClose : undefined} />
            ))}
          </nav>
        </div>
      </div>
    </aside>
  );
}

// v2
