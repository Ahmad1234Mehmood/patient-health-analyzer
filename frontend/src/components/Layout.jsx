import { useState, useEffect } from "react";
import { useLocation, Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import Toast from "./Toast";

export default function Layout() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();

  useEffect(() => setDrawerOpen(false), [location.pathname]);
  useEffect(() => {
    document.body.classList.toggle("drawer-open", drawerOpen);
    return () => document.body.classList.remove("drawer-open");
  }, [drawerOpen]);
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && setDrawerOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="min-h-screen bg-surface text-on-surface font-body">
      <div
        onClick={() => setDrawerOpen(false)}
        className={`lg:hidden fixed inset-0 z-40 scrim drawer-overlay ${drawerOpen ? "opacity-100" : "opacity-0 pointer-events-none"}`}
      />
      <Sidebar variant="mobile" open={drawerOpen} onClose={() => setDrawerOpen(false)} />
      <Sidebar variant="desktop" />
      <div className="lg:ml-64 flex flex-col min-h-screen">
        <TopBar onMenu={() => setDrawerOpen(true)} />
        <main className="flex-1 mesh-bg">
          <Outlet />
        </main>
      </div>
      <Toast />
    </div>
  );
}
