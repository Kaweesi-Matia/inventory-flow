import React from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Package, Boxes, AlertTriangle, XCircle, ClipboardList, ShoppingCart, Warehouse, DollarSign } from "lucide-react";
import { dashboardApi, reportsApi } from "../api/resources";
import { useAuth } from "../context/AuthContext";
import { SCOPED_ROLES, roleLabel } from "../roles";

const METRIC_TONES = {
  teal: "bg-brand-50 text-brand-700",
  amber: "bg-amber-50 text-amber-700",
  rose: "bg-rose-50 text-rose-700",
  sky: "bg-sky-50 text-sky-700",
  emerald: "bg-emerald-50 text-emerald-700",
  slate: "bg-slate-100 text-slate-700",
};

function MetricCard({ icon: Icon, label, value, tone = "teal" }) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</p>
          <p className="text-2xl font-bold tracking-tight text-slate-900 mt-2">{value}</p>
        </div>
        <span className={`h-10 w-10 rounded-xl grid place-items-center ${METRIC_TONES[tone]}`}>
          <Icon size={18} />
        </span>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const scoped = SCOPED_ROLES.includes(user?.role);
  const assigned = (user?.warehouse_labels || []).join(", ");
  const { data: overview, isLoading, isError, error } = useQuery({
    queryKey: ["dashboard-overview"],
    queryFn: () => dashboardApi.overview().then((r) => r.data),
  });

  const { data: warehouseInventory } = useQuery({
    queryKey: ["warehouse-inventory-report"],
    queryFn: () => reportsApi.warehouseInventory().then((r) => r.data),
  });

  if (isLoading) return <div className="page text-slate-500">Loading dashboard...</div>;
  if (isError) {
    return (
      <div className="page text-rose-600">
        Could not load dashboard: {error?.response?.data?.detail || error?.message || "unknown error"}
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">
            {scoped
              ? `${roleLabel(user.role)}${assigned ? ` — showing ${assigned} only` : " — no warehouse assigned, so these numbers are empty"}`
              : `Good to see you, ${user?.full_name?.split(" ")[0] || "there"}. Here is the current operations snapshot.`}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        <MetricCard icon={Package} label="Total Products" value={overview?.total_products ?? 0} />
        <MetricCard icon={Boxes} label="Inventory Units" value={overview?.total_inventory_units ?? 0} tone="slate" />
        <MetricCard icon={AlertTriangle} label="Low Stock" value={overview?.low_stock_items ?? 0} tone="amber" />
        <MetricCard icon={XCircle} label="Out of Stock" value={overview?.out_of_stock_items ?? 0} tone="rose" />
        <MetricCard icon={ClipboardList} label="Pending POs" value={overview?.pending_purchase_orders ?? 0} tone="sky" />
        <MetricCard icon={ShoppingCart} label="Pending Orders" value={overview?.pending_customer_orders ?? 0} tone="sky" />
        <MetricCard icon={Warehouse} label="Active Warehouses" value={overview?.active_warehouses ?? 0} tone="slate" />
        <MetricCard
          icon={DollarSign}
          label="Inventory Value"
          value={`$${Number(overview?.inventory_value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
          tone="emerald"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <h2 className="text-sm font-semibold text-slate-800 mb-4">Inventory by warehouse</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={warehouseInventory || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f6" />
              <XAxis dataKey="warehouse_name" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", boxShadow: "none" }}
              />
              <Bar dataKey="total_units" fill="#0f766e" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-6">
          <h2 className="text-sm font-semibold text-slate-800 mb-4">Recent stock movements</h2>
          <ul className="divide-y divide-slate-100">
            {(overview?.recent_movements || []).map((m) => (
              <li key={m.id} className="py-3 flex items-center justify-between text-sm">
                <span className="text-slate-600 font-medium">{m.movement_type.replace(/_/g, " ")}</span>
                <span className={`font-semibold tabular-nums ${m.quantity >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                  {m.quantity >= 0 ? "+" : ""}
                  {m.quantity}
                </span>
              </li>
            ))}
            {(overview?.recent_movements || []).length === 0 && (
              <li className="py-8 text-sm text-slate-400 text-center">No movements yet</li>
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
