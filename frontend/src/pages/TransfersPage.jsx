import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { productsApi, transfersApi, warehousesApi } from "../api/resources";
import { apiError } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import Modal, { fieldClass } from "../components/Modal";
import { useAuth } from "../context/AuthContext";
import { scopedWarehouses } from "../roles";

export default function TransfersPage() {
  const { hasRole, user } = useAuth();
  const queryClient = useQueryClient();
  const canManage = hasRole("ADMIN", "INVENTORY_MANAGER", "WAREHOUSE_MANAGER");
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    source_warehouse_id: "",
    destination_warehouse_id: "",
    product_id: "",
    quantity: "",
    notes: "",
  });

  const { data: transfers, isLoading } = useQuery({
    queryKey: ["transfers"],
    queryFn: () => transfersApi.list().then((r) => r.data),
  });
  const { data: warehouses } = useQuery({
    queryKey: ["warehouses"],
    queryFn: () => warehousesApi.list().then((r) => r.data),
  });
  const { data: products } = useQuery({
    queryKey: ["products-dropdown"],
    queryFn: () => productsApi.list({ page_size: 200 }).then((r) => r.data),
    enabled: showCreate,
  });
  const warehousesById = Object.fromEntries((warehouses || []).map((w) => [w.id, w]));

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["transfers"] });
    queryClient.invalidateQueries({ queryKey: ["inventory"] });
  };

  const receiveMutation = useMutation({
    mutationFn: (id) => transfersApi.receive(id),
    onSuccess: invalidate,
    onError: (err) => setError(apiError(err, "Could not receive transfer")),
  });
  const cancelMutation = useMutation({
    mutationFn: (id) => transfersApi.cancel(id),
    onSuccess: invalidate,
    onError: (err) => setError(apiError(err, "Could not cancel transfer")),
  });
  const createMutation = useMutation({
    mutationFn: (payload) => transfersApi.create(payload),
    onSuccess: () => {
      invalidate();
      setShowCreate(false);
    },
    onError: (err) => setError(apiError(err, "Could not create transfer")),
  });

  function handleCreate(e) {
    e.preventDefault();
    setError("");
    createMutation.mutate({
      source_warehouse_id: form.source_warehouse_id,
      destination_warehouse_id: form.destination_warehouse_id,
      notes: form.notes || undefined,
      items: [{ product_id: form.product_id, quantity: Number(form.quantity) }],
    });
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Warehouse Transfers</h1>
        {canManage && (
          <button
            onClick={() => {
              setError("");
              setShowCreate(true);
            }}
            className="btn-primary"
          >
            New transfer
          </button>
        )}
      </div>
      {error && !showCreate && <p className="mb-4 text-sm text-red-600">{error}</p>}
      <div className="table-card">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {["Transfer #", "From", "To", "Status", "Actions"].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            )}
            {(transfers || []).map((t) => (
              <tr key={t.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{t.transfer_number}</td>
                <td className="px-4 py-3 text-gray-600">{warehousesById[t.source_warehouse_id]?.name || "—"}</td>
                <td className="px-4 py-3 text-gray-600">{warehousesById[t.destination_warehouse_id]?.name || "—"}</td>
                <td className="px-4 py-3"><StatusBadge status={t.status} /></td>
                <td className="px-4 py-3 space-x-3">
                  {canManage && t.status === "PENDING" && (
                    <>
                      <button onClick={() => receiveMutation.mutate(t.id)} className="link-action text-emerald-700">
                        Receive
                      </button>
                      <button onClick={() => cancelMutation.mutate(t.id)} className="link-action text-rose-600">
                        Cancel
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <Modal title="New transfer" onClose={() => setShowCreate(false)}>
          <form onSubmit={handleCreate} className="space-y-3">
            <select
              required
              value={form.source_warehouse_id}
              onChange={(e) => setForm({ ...form, source_warehouse_id: e.target.value })}
              className={fieldClass}
            >
              <option value="">From warehouse</option>
              {scopedWarehouses(warehouses, user).map((w) => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
            <select
              required
              value={form.destination_warehouse_id}
              onChange={(e) => setForm({ ...form, destination_warehouse_id: e.target.value })}
              className={fieldClass}
            >
              <option value="">To warehouse</option>
              {(warehouses || []).map((w) => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
            <select
              required
              value={form.product_id}
              onChange={(e) => setForm({ ...form, product_id: e.target.value })}
              className={fieldClass}
            >
              <option value="">Product</option>
              {(products?.items || []).map((p) => (
                <option key={p.id} value={p.id}>{p.sku} — {p.name}</option>
              ))}
            </select>
            <input
              required
              type="number"
              min="1"
              placeholder="Quantity"
              value={form.quantity}
              onChange={(e) => setForm({ ...form, quantity: e.target.value })}
              className={fieldClass}
            />
            <input
              placeholder="Notes (optional)"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className={fieldClass}
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setShowCreate(false)} className="btn-ghost">Cancel</button>
              <button type="submit" disabled={createMutation.isPending} className="btn-primary">
                {createMutation.isPending ? "Creating..." : "Create"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
