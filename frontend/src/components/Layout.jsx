import React from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Package, Boxes, ArrowLeftRight, ClipboardList,
  ShoppingCart, Truck, Warehouse, BarChart3, Users, ShieldCheck, Settings, LogOut,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { NAV_ITEMS, SCOPED_ROLES, roleMeta } from "../roles";

const ICONS = {
  LayoutDashboard, Package, Boxes, ArrowLeftRight, ClipboardList,
  ShoppingCart, Truck, Warehouse, BarChart3, Users, ShieldCheck, Settings,
};

export default function Layout() {
  const { user, logout, hasRole } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const meta = roleMeta(user?.role);
  const warehouseNote = (user?.warehouse_labels || []).length
    ? user.warehouse_labels.join(", ")
    : null;
  const needsWarehouse = SCOPED_ROLES.includes(user?.role) && !warehouseNote;
  const current = NAV_ITEMS.find((item) => item.to === location.pathname);
  const visibleItems = NAV_ITEMS.filter((item) => !item.roles || hasRole(...item.roles));

  return (
    <div className="flex h-screen bg-slate-100">
      <aside className="w-[272px] bg-ink-900 text-white flex flex-col shrink-0">
        <div className="h-[76px] flex items-center gap-3 px-6">
          <span className="h-9 w-9 rounded-xl bg-gradient-to-br from-brand-400 to-brand-700 grid place-items-center font-extrabold text-sm shadow-glow">
            SX
          </span>
          <div>
            <p className="text-[15px] font-bold tracking-tight leading-none">SupplyChainX</p>
            <p className="text-[11px] text-slate-400 mt-1">Inventory operations</p>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto py-3 space-y-0.5">
          {visibleItems.map(({ to, label, icon }) => {
            const Icon = ICONS[icon];
            return (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `nav-link ${isActive ? "nav-link-active" : ""}`
                }
              >
                {Icon && <Icon size={18} strokeWidth={1.85} />}
                {label}
              </NavLink>
            );
          })}
        </nav>
        <div className="m-3 rounded-2xl bg-white/5 border border-white/10 p-4">
          <p className="text-sm font-semibold text-white truncate">{user?.full_name}</p>
          <p className="text-[11px] text-slate-400 truncate mt-0.5">{user?.email}</p>
          <span className={`status-badge mt-2.5 ${meta.badge}`}>{meta.label}</span>
          {warehouseNote && (
            <p className="text-[11px] text-slate-400 mt-2">Assigned: {warehouseNote}</p>
          )}
          {needsWarehouse && (
            <p className="text-[11px] text-amber-300 mt-2">No warehouse assigned — ask an admin.</p>
          )}
          <p className="text-[11px] text-slate-500 mt-2 leading-snug">{meta.description}</p>
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="flex items-center gap-2 text-sm text-slate-400 hover:text-rose-300 mt-3 transition-colors"
          >
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </aside>
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="h-[76px] bg-white/80 backdrop-blur border-b border-slate-200/80 px-8 flex items-center justify-between shrink-0">
          <div>
            <p className="text-[11px] uppercase tracking-[0.16em] text-slate-400 font-semibold">Workspace</p>
            <h2 className="text-base font-semibold text-slate-900 leading-tight">
              {current?.label || "SupplyChainX"}
            </h2>
          </div>
          <div className="hidden sm:flex items-center gap-3">
            <div className="h-9 w-9 rounded-full bg-brand-100 text-brand-700 grid place-items-center text-xs font-bold">
              {(user?.full_name || "?").slice(0, 1).toUpperCase()}
            </div>
            <div className="text-right">
              <p className="text-sm font-medium text-slate-800 leading-tight">{user?.full_name}</p>
              <p className="text-[11px] text-slate-500">{meta.label}</p>
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
