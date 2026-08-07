import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/call", label: "Call" },
  { to: "/knowledge", label: "Knowledge" },
  { to: "/traza", label: "TRAZA" },
  { to: "/sessions", label: "Sessions" },
  { to: "/settings", label: "Settings" },
] as const;

export function AppShell() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">◈ LIMEN</div>
          <div className="brand-sub">Seguimiento postoperatorio por voz</div>
        </div>
        <nav className="nav" aria-label="Principal">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) => (isActive ? "active" : undefined)}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
