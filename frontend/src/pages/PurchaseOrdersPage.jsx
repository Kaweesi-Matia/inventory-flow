import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { productsApi, purchaseOrdersApi, suppliersApi, warehousesApi } from "../api/resources";
import { apiError } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import Modal, { fieldClass } from "../components/Modal";
import { useAuth } from "../context/AuthContext";
import { scopedWarehouses } from "../roles";

const RECEIVABLE = ["SUBMITTED", "APPROVED", "PARTIALLY_RECEIVED"];

export default function PurchaseOrdersPage() {
  const { hasRole, user } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [receiving, setReceiving] = useState(null);
  const [receiptQty, setReceiptQty] = useState({});
  const [form, setForm] = useState({
    supplier_id: "",
    warehouse_id: "",
    product_id: "",
    quantity: "",
    unit_cost: "",
  });

  const { data: orders, isLoading } = useQuery({
    queryKey: ["purchase-orders"],
    queryFn: () => purchaseOrdersApi.list().then((r) => r.data),
  });
  const { data: suppliers } = useQuery({
    queryKey: ["suppliers"],
    queryFn: () => suppliersApi.list().then((r) => r.data),
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
    queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
    queryClient.invalidateQueries({ queryKey: ["inventory"] });
  };

  const canProcure = hasRole("ADMIN", "PROCUREMENT_MANAGER");
  const canReceive = hasRole("ADMIN", "PROCUREMENT_MANAGER", "WAREHOUSE_MANAGER");

  const actionError = (err, fallback) => setError(apiError(err, fallback));

  const submitMutation = useMutation({
    mutationFn: (id) => purchaseOrdersApi.submit(id),
    onSuccess: invalidate,
    onError: (err) => actionError(err, "Could not submit"),
  });
  const approveMutation = useMutation({
    mutationFn: (id) => purchaseOrdersApi.approve(id),
    onSuccess: invalidate,
    onError: (err) => actionError(err, "Could not approve"),
  });
  const createMutation = useMutation({
    mutationFn: (payload) => purchaseOrdersApi.create(payload),
    onSuccess: () => {
      invalidate();
      setShowCreate(false);
    },
    onError: (err) => actionError(err, "Could not create purchase order"),
  });
  const receiveMutation = useMutation({
    mutationFn: ({ id, payload }) => purchaseOrdersApi.receive(id, payload),
    onSuccess: () => {
      invalidate();
      setReceiving(null);
    },
    onError: (err) => actionError(err, "Could not receive"),
  });

  function handleCreate(e) {
    e.preventDefault();
    setError("");
    const product = (products?.items || []).find((p) => p.id === form.product_id);
    createMutation.mutate({
      supplier_id: form.supplier_id,
      warehouse_id: form.warehouse_id,
      items: [
        {
          product_id: form.product_id,
          quantity: Number(form.quantity),
          unit_cost: form.unit_cost || product?.cost_price || 0,
        },
      ],
    });
  }

  function openReceive(order) {
    setError("");
    const qty = {};
    (order.items || []).forEach((item) => {
      qty[item.id] = String(item.quantity_ordered - item.quantity_received);
    });
    setReceiptQty(qty);
    setReceiving(order);
  }

  function handleReceive(e) {
    e.preventDefault();
    setError("");
    const receipts = (receiving.items || [])
      .map((item) => ({
        item_id: item.id,
        quantity_received: Number(receiptQty[item.id] || 0),
      }))
      .filter((r) => r.quantity_received > 0);
    if (!receipts.length) {
      setError("Enter a received quantity for at least one line");
      return;
    }
    receiveMutation.mutate({ id: receiving.id, payload: { receipts } });
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Purchase Orders</h1>
        {canProcure && (
          <button
            onClick={() => {
              setError("");
              setShowCreate(true);
            }}
            className="btn-primary"
          >
            New purchase order
          </button>
        )}
      </div>
      {error && !showCreate && !receiving && <p className="mb-4 text-sm text-red-600">{error}</p>}
      <div className="table-card">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {["Order #", "Order Date", "Expected Delivery", "Total", "Status", "Actions"].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            )}
            {(orders || []).map((o) => (
              <tr key={o.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{o.order_number}</td>
                <td className="px-4 py-3 text-gray-600">{o.order_date}</td>
                <td className="px-4 py-3 text-gray-600">{o.expected_delivery_date || "—"}</td>
                <td className="px-4 py-3">${Number(o.total_cost).toFixed(2)}</td>
                <td className="px-4 py-3"><StatusBadge status={o.status} /></td>
                <td className="px-4 py-3 space-x-3">
                  {canProcure && o.status === "DRAFT" && (
                    <button onClick={() => submitMutation.mutate(o.id)} className="link-action">
                      Submit
                    </button>
                  )}
                  {canProcure && o.status === "SUBMITTED" && (
                    <button onClick={() => approveMutation.mutate(o.id)} className="link-action">
                      Approve
                    </button>
                  )}
                  {canReceive && RECEIVABLE.includes(o.status) && (
                    <button onClick={() => openReceive(o)} className="link-action text-emerald-700">
                      Receive
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <Modal title="New purchase order" onClose={() => setShowCreate(false)}>
          <form onSubmit={handleCreate} className="space-y-3">
            <select required value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })} className={fieldClass}>
              <option value="">Supplier</option>
              {(suppliers || []).map((s) => (
                <option key={s.id} value={s.id}>{s.company_name}</option>
              ))}
            </select>
            <select required value={form.warehouse_id} onChange={(e) => setForm({ ...form, warehouse_id: e.target.value })} className={fieldClass}>
              <option value="">Warehouse</option>
              {scopedWarehouses(warehouses, user).map((w) => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
            <select
              required
              value={form.product_id}
              onChange={(e) => {
                const product = (products?.items || []).find((p) => p.id === e.target.value);
                setForm({
                  ...form,
                  product_id: e.target.value,
                  unit_cost: product ? String(product.cost_price) : form.unit_cost,
                });
              }}
              className={fieldClass}
            >
              <option value="">Product</option>
              {(products?.items || []).map((p) => (
                <option key={p.id} value={p.id}>{p.sku} — {p.name}</option>
              ))}
            </select>
            <div className="grid grid-cols-2 gap-3">
              <input required type="number" min="1" placeholder="Quantity" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} className={fieldClass} />
              <input required type="number" min="0" step="0.01" placeholder="Unit cost" value={form.unit_cost} onChange={(e) => setForm({ ...form, unit_cost: e.target.value })} className={fieldClass} />
            </div>
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

      {receiving && (
        <Modal title={`Receive ${receiving.order_number}`} onClose={() => setReceiving(null)} wide>
          <form onSubmit={handleReceive} className="space-y-3">
            {(receiving.items || []).map((item) => {
              const remaining = item.quantity_ordered - item.quantity_received;
              return (
                <div key={item.id} className="flex items-center justify-between gap-3 text-sm">
                  <span className="text-gray-700">
                    Remaining {remaining} of {item.quantity_ordered}
                  </span>
                  <input
                    type="number"
                    min="0"
                    max={remaining}
                    value={receiptQty[item.id] ?? ""}
                    onChange={(e) => setReceiptQty({ ...receiptQty, [item.id]: e.target.value })}
                    className={`${fieldClass} w-28`}
                  />
                </div>
              );
            })}
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setReceiving(null)} className="btn-ghost">Cancel</button>
              <button type="submit" disabled={receiveMutation.isPending} className="btn-primary">
                {receiveMutation.isPending ? "Receiving..." : "Receive"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
