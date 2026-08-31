import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { warehousesApi } from "../api/resources";
import { apiError } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import Modal, { fieldClass } from "../components/Modal";
import { useAuth } from "../context/AuthContext";

export default function WarehousesPage() {
  const { hasRole } = useAuth();
  const queryClient = useQueryClient();
  const canManage = hasRole("ADMIN");
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ name: "", code: "", city: "", country: "", manager_name: "" });

  const { data: warehouses, isLoading } = useQuery({
    queryKey: ["warehouses"],
    queryFn: () => warehousesApi.list().then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (payload) => warehousesApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["warehouses"] });
      setShowCreate(false);
      setForm({ name: "", code: "", city: "", country: "", manager_name: "" });
    },
    onError: (err) => setError(apiError(err, "Could not create warehouse")),
  });

  function handleCreate(e) {
    e.preventDefault();
    setError("");
    createMutation.mutate({
      name: form.name.trim(),
      code: form.code.trim(),
      city: form.city || undefined,
      country: form.country || undefined,
      manager_name: form.manager_name || undefined,
    });
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Warehouses</h1>
        {canManage && (
          <button
            onClick={() => {
              setError("");
              setShowCreate(true);
            }}
            className="btn-primary"
          >
            Add warehouse
          </button>
        )}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {isLoading && <p className="text-gray-400">Loading...</p>}
        {(warehouses || []).map((w) => (
          <div key={w.id} className="card p-5">
            <div className="flex items-center justify-between mb-2">
              <h2 className="font-semibold text-gray-900">{w.name}</h2>
              <StatusBadge status={w.status} />
            </div>
            <p className="text-sm text-gray-500 font-mono">{w.code}</p>
            <p className="text-sm text-gray-600 mt-2">{w.city}, {w.country}</p>
            {w.manager_name && <p className="text-sm text-gray-500 mt-1">Manager: {w.manager_name}</p>}
          </div>
        ))}
      </div>

      {showCreate && (
        <Modal title="Add warehouse" onClose={() => setShowCreate(false)}>
          <form onSubmit={handleCreate} className="space-y-3">
            <input required placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className={fieldClass} />
            <input required placeholder="Code (e.g. WH-D)" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} className={fieldClass} />
            <input placeholder="City" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} className={fieldClass} />
            <input placeholder="Country" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} className={fieldClass} />
            <input placeholder="Manager name" value={form.manager_name} onChange={(e) => setForm({ ...form, manager_name: e.target.value })} className={fieldClass} />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setShowCreate(false)} className="btn-ghost">Cancel</button>
              <button type="submit" disabled={createMutation.isPending} className="btn-primary">
                {createMutation.isPending ? "Saving..." : "Create"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
