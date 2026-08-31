import React, { useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, Plus } from "lucide-react";
import { categoriesApi, productsApi } from "../api/resources";
import { apiError } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import Modal, { fieldClass } from "../components/Modal";
import { useAuth } from "../context/AuthContext";

const PAGE_SIZE = 20;
const emptyForm = {
  sku: "",
  name: "",
  unit_price: "",
  cost_price: "",
  reorder_level: "10",
  category_id: "",
};

export default function ProductsPage() {
  const { hasRole } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [formError, setFormError] = useState("");
  const [importMessage, setImportMessage] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["products", search, page],
    queryFn: () =>
      productsApi
        .list({ search: search || undefined, page, page_size: PAGE_SIZE })
        .then((r) => r.data),
    placeholderData: keepPreviousData,
  });

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => categoriesApi.list().then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (payload) => productsApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      setShowCreate(false);
      setForm(emptyForm);
    },
    onError: (err) => setFormError(apiError(err, "Could not create product")),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const canManage = hasRole("ADMIN", "INVENTORY_MANAGER");

  function handleCreate(e) {
    e.preventDefault();
    setFormError("");
    createMutation.mutate({
      sku: form.sku.trim(),
      name: form.name.trim(),
      unit_price: form.unit_price,
      cost_price: form.cost_price,
      reorder_level: Number(form.reorder_level) || 0,
      category_id: form.category_id || null,
    });
  }

  async function handleImport(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setImportMessage("");
    try {
      const res = await productsApi.importCsv(file);
      const summary = res.data;
      setImportMessage(
        `Imported ${summary.successful}/${summary.total_rows} rows` +
          (summary.failed ? ` (${summary.failed} failed)` : "")
      );
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
    } catch (err) {
      setImportMessage(apiError(err, "CSV import failed"));
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Products</h1>
        {canManage && (
          <div className="flex items-center gap-2">
            <label className="btn-secondary">
              Import CSV
              <input type="file" accept=".csv" className="hidden" onChange={handleImport} />
            </label>
            <button
              onClick={() => {
                setFormError("");
                setShowCreate(true);
              }}
              className="btn-primary"
            >
              <Plus size={16} /> Add product
            </button>
          </div>
        )}
      </div>

      {importMessage && <p className="mb-4 text-sm text-slate-600">{importMessage}</p>}

      <div className="mb-5 relative max-w-sm">
        <Search className="absolute left-3.5 top-3 text-slate-400" size={16} />
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          placeholder="Search by SKU or name..."
          className="input pl-10"
        />
      </div>

      <div className="table-card">
        <table>
          <thead>
            <tr>
              {["SKU", "Product", "Price", "Cost", "Reorder Level", "Status"].map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  Loading...
                </td>
              </tr>
            )}
            {!isLoading && data?.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  No products found
                </td>
              </tr>
            )}
            {data?.items.map((p) => (
              <tr key={p.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs text-gray-600">{p.sku}</td>
                <td className="px-4 py-3 font-medium text-gray-900">{p.name}</td>
                <td className="px-4 py-3">${Number(p.unit_price).toFixed(2)}</td>
                <td className="px-4 py-3 text-gray-500">${Number(p.cost_price).toFixed(2)}</td>
                <td className="px-4 py-3">{p.reorder_level}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={p.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && (
        <div className="flex items-center justify-between mt-4 text-sm text-slate-500">
          <span>
            Page {page} of {totalPages} — {data.total} products
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="btn-secondary py-1.5 px-3 disabled:opacity-40"
            >
              Previous
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="btn-secondary py-1.5 px-3 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {showCreate && (
        <Modal title="Add product" onClose={() => setShowCreate(false)}>
          <form onSubmit={handleCreate} className="space-y-3">
            <input
              required
              placeholder="SKU"
              value={form.sku}
              onChange={(e) => setForm({ ...form, sku: e.target.value })}
              className={fieldClass}
            />
            <input
              required
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className={fieldClass}
            />
            <div className="grid grid-cols-2 gap-3">
              <input
                required
                type="number"
                min="0"
                step="0.01"
                placeholder="Unit price"
                value={form.unit_price}
                onChange={(e) => setForm({ ...form, unit_price: e.target.value })}
                className={fieldClass}
              />
              <input
                required
                type="number"
                min="0"
                step="0.01"
                placeholder="Cost price"
                value={form.cost_price}
                onChange={(e) => setForm({ ...form, cost_price: e.target.value })}
                className={fieldClass}
              />
            </div>
            <input
              type="number"
              min="0"
              placeholder="Reorder level"
              value={form.reorder_level}
              onChange={(e) => setForm({ ...form, reorder_level: e.target.value })}
              className={fieldClass}
            />
            <select
              value={form.category_id}
              onChange={(e) => setForm({ ...form, category_id: e.target.value })}
              className={fieldClass}
            >
              <option value="">No category</option>
              {(categories || []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            {formError && <p className="text-sm text-red-600">{formError}</p>}
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setShowCreate(false)} className="btn-ghost">
                Cancel
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="btn-primary"
              >
                {createMutation.isPending ? "Saving..." : "Create"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
