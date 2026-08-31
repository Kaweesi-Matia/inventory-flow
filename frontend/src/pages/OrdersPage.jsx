import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { customersApi, ordersApi, productsApi, warehousesApi } from "../api/resources";
import { apiError } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import Modal, { fieldClass } from "../components/Modal";
import { useAuth } from "../context/AuthContext";
import { scopedWarehouses } from "../roles";

export default function OrdersPage() {
  const { hasRole, user } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    customer_id: "",
    warehouse_id: "",
    product_id: "",
    quantity: "1",
  });

  const { data: orders, isLoading } = useQuery({
    queryKey: ["customer-orders"],
    queryFn: () => ordersApi.list().then((r) => r.data),
  });
  const { data: customers } = useQuery({
    queryKey: ["customers"],
    queryFn: () => customersApi.list().then((r) => r.data),
    enabled: showCreate,
  });
  const { data: warehouses } = useQuery({
    queryKey: ["warehouses"],
    queryFn: () => warehousesApi.list().then((r) => r.data),
    enabled: showCreate,
  });
  const { data: products } = useQuery({
    queryKey: ["products-dropdown"],
    queryFn: () => productsApi.list({ page_size: 200 }).then((r) => r.data),
    enabled: showCreate,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["customer-orders"] });
    queryClient.invalidateQueries({ queryKey: ["inventory"] });
  };
  const actionError = (err, fallback) => setError(apiError(err, fallback));

  const confirmMutation = useMutation({
    mutationFn: (id) => ordersApi.confirm(id),
    onSuccess: invalidate,
    onError: (err) => actionError(err, "Could not confirm order"),
  });
  const fulfillMutation = useMutation({
    mutationFn: (id) => ordersApi.fulfill(id),
    onSuccess: invalidate,
    onError: (err) => actionError(err, "Could not fulfill order"),
  });
  const cancelMutation = useMutation({
    mutationFn: (id) => ordersApi.cancel(id),
    onSuccess: invalidate,
    onError: (err) => actionError(err, "Could not cancel order"),
  });
  const createMutation = useMutation({
    mutationFn: (payload) => ordersApi.create(payload),
    onSuccess: () => {
      invalidate();
      setShowCreate(false);
    },
    onError: (err) => actionError(err, "Could not create order"),
  });

  const canSell = hasRole("ADMIN", "SALES_USER");
  const canFulfill = hasRole("ADMIN", "WAREHOUSE_MANAGER");

  function handleCreate(e) {
    e.preventDefault();
    setError("");
    const product = (products?.items || []).find((p) => p.id === form.product_id);
    createMutation.mutate({
      customer_id: form.customer_id,
      warehouse_id: form.warehouse_id,
      items: [
        {
          product_id: form.product_id,
          quantity: Number(form.quantity),
          unit_price: product?.unit_price || 0,
        },
      ],
    });
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Customer Orders</h1>
        {canSell && (
          <button
            onClick={() => {
              setError("");
              setShowCreate(true);
            }}
            className="btn-primary"
          >
            New order
          </button>
        )}
      </div>
      {error && !showCreate && <p className="mb-4 text-sm text-red-600">{error}</p>}
      <div className="table-card">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {["Order #", "Date", "Total", "Status", "Actions"].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            )}
            {(orders || []).map((o) => (
              <tr key={o.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{o.order_number}</td>
                <td className="px-4 py-3 text-gray-600">{o.order_date}</td>
                <td className="px-4 py-3">${Number(o.total_amount).toFixed(2)}</td>
                <td className="px-4 py-3"><StatusBadge status={o.status} /></td>
                <td className="px-4 py-3 space-x-3">
                  {canSell && o.status === "PENDING" && (
                    <button onClick={() => confirmMutation.mutate(o.id)} className="link-action">
                      Confirm
                    </button>
                  )}
                  {canFulfill && o.status === "RESERVED" && (
                    <button onClick={() => fulfillMutation.mutate(o.id)} className="link-action text-emerald-700">
                      Fulfill
                    </button>
                  )}
                  {canSell && ["PENDING", "RESERVED", "CONFIRMED"].includes(o.status) && (
                    <button onClick={() => cancelMutation.mutate(o.id)} className="link-action text-rose-600">
                      Cancel
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <Modal title="New customer order" onClose={() => setShowCreate(false)}>
          <form onSubmit={handleCreate} className="space-y-3">
            <select required value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })} className={fieldClass}>
              <option value="">Customer</option>
              {(customers || []).map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <select required value={form.warehouse_id} onChange={(e) => setForm({ ...form, warehouse_id: e.target.value })} className={fieldClass}>
              <option value="">Warehouse</option>
              {scopedWarehouses(warehouses, user).map((w) => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
            <select required value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })} className={fieldClass}>
              <option value="">Product</option>
              {(products?.items || []).map((p) => (
                <option key={p.id} value={p.id}>{p.sku} — {p.name}</option>
              ))}
            </select>
            <input required type="number" min="1" placeholder="Quantity" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} className={fieldClass} />
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
