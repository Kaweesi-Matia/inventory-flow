import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { inventoryApi, productsApi, warehousesApi } from "../api/resources";
import { apiError } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import Modal, { fieldClass } from "../components/Modal";
import { useAuth } from "../context/AuthContext";
import { scopedWarehouses } from "../roles";

function computeStatus(inv) {
  const available = inv.quantity_on_hand - inv.quantity_reserved;
  if (available <= 0) return "OUT_OF_STOCK";
  if (available <= (inv.reorder_level ?? 0)) return "LOW_STOCK";
  return "IN_STOCK";
}

export default function InventoryPage() {
  const { hasRole, user } = useAuth();
  const queryClient = useQueryClient();
  const [warehouseId, setWarehouseId] = useState("");
  const [showAdjust, setShowAdjust] = useState(false);
  const [form, setForm] = useState({ product_id: "", warehouse_id: "", quantity_delta: "", reason: "" });
  const [error, setError] = useState("");

  const { data: warehouses } = useQuery({
    queryKey: ["warehouses"],
    queryFn: () => warehousesApi.list().then((r) => r.data),
  });
  const visibleWarehouses = scopedWarehouses(warehouses, user);

  const canAdjust = hasRole("ADMIN", "INVENTORY_MANAGER", "WAREHOUSE_MANAGER");

  const { data: products } = useQuery({
    queryKey: ["products-dropdown"],
    queryFn: () => productsApi.list({ page_size: 200 }).then((r) => r.data),
    enabled: showAdjust,
  });

  const { data: inventory, isLoading } = useQuery({
    queryKey: ["inventory", warehouseId],
    queryFn: () => inventoryApi.list({ warehouse_id: warehouseId || undefined }).then((r) => r.data),
  });

  const adjustMutation = useMutation({
    mutationFn: (payload) => inventoryApi.adjust(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-overview"] });
      setShowAdjust(false);
      setForm({ product_id: "", warehouse_id: "", quantity_delta: "", reason: "" });
    },
    onError: (err) => setError(apiError(err, "Could not adjust stock")),
  });

  function handleAdjust(e) {
    e.preventDefault();
    setError("");
    adjustMutation.mutate({
      product_id: form.product_id,
      warehouse_id: form.warehouse_id,
      quantity_delta: Number(form.quantity_delta),
      reason: form.reason.trim(),
    });
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Inventory</h1>
        {canAdjust && (
          <button
            onClick={() => {
              setError("");
              setShowAdjust(true);
            }}
            className="btn-primary"
          >
            Adjust stock
          </button>
        )}
      </div>

      <select
        value={warehouseId}
        onChange={(e) => setWarehouseId(e.target.value)}
        className="input mb-5 max-w-xs"
      >
        <option value="">All warehouses</option>
        {visibleWarehouses.map((w) => (
          <option key={w.id} value={w.id}>
            {w.name}
          </option>
        ))}
      </select>

      <div className="table-card">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {["Product", "SKU", "Warehouse", "On Hand", "Reserved", "Available", "Status"].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                  Loading...
                </td>
              </tr>
            )}
            {!isLoading && (inventory || []).length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                  {visibleWarehouses.length === 0 && user?.role
                    ? "No warehouse assigned — ask an admin to grant access."
                    : "No inventory records"}
                </td>
              </tr>
            )}
            {(inventory || []).map((inv) => {
              const available = inv.quantity_on_hand - inv.quantity_reserved;
              const status = computeStatus(inv);
              return (
                <tr key={inv.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{inv.product_name || "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">{inv.product_sku || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{inv.warehouse_name || "—"}</td>
                  <td className="px-4 py-3">{inv.quantity_on_hand}</td>
                  <td className="px-4 py-3 text-gray-500">{inv.quantity_reserved}</td>
                  <td className="px-4 py-3 font-medium">{available}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={status} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {showAdjust && (
        <Modal title="Adjust stock" onClose={() => setShowAdjust(false)}>
          <form onSubmit={handleAdjust} className="space-y-3">
            <select
              required
              value={form.product_id}
              onChange={(e) => setForm({ ...form, product_id: e.target.value })}
              className={fieldClass}
            >
              <option value="">Select product</option>
              {(products?.items || []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.sku} — {p.name}
                </option>
              ))}
            </select>
            <select
              required
              value={form.warehouse_id}
              onChange={(e) => setForm({ ...form, warehouse_id: e.target.value })}
              className={fieldClass}
            >
              <option value="">Select warehouse</option>
              {(visibleWarehouses || []).map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
            <input
              required
              type="number"
              placeholder="Quantity (+ add / − remove)"
              value={form.quantity_delta}
              onChange={(e) => setForm({ ...form, quantity_delta: e.target.value })}
              className={fieldClass}
            />
            <input
              required
              placeholder="Reason"
              value={form.reason}
              onChange={(e) => setForm({ ...form, reason: e.target.value })}
              className={fieldClass}
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setShowAdjust(false)} className="btn-ghost">
                Cancel
              </button>
              <button
                type="submit"
                disabled={adjustMutation.isPending}
                className="btn-primary"
              >
                {adjustMutation.isPending ? "Saving..." : "Apply"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
