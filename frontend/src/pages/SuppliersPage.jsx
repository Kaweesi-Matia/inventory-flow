import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { suppliersApi } from "../api/resources";
import { apiError } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import Modal, { fieldClass } from "../components/Modal";
import { useAuth } from "../context/AuthContext";

export default function SuppliersPage() {
  const { hasRole } = useAuth();
  const queryClient = useQueryClient();
  const canManage = hasRole("ADMIN", "PROCUREMENT_MANAGER");
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ company_name: "", contact_person: "", email: "", country: "" });

  const { data: suppliers, isLoading } = useQuery({
    queryKey: ["suppliers"],
    queryFn: () => suppliersApi.list().then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (payload) => suppliersApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      setShowCreate(false);
      setForm({ company_name: "", contact_person: "", email: "", country: "" });
    },
    onError: (err) => setError(apiError(err, "Could not create supplier")),
  });

  function handleCreate(e) {
    e.preventDefault();
    setError("");
    createMutation.mutate({
      company_name: form.company_name.trim(),
      contact_person: form.contact_person || undefined,
      email: form.email || undefined,
      country: form.country || undefined,
    });
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Suppliers</h1>
        {canManage && (
          <button
            onClick={() => {
              setError("");
              setShowCreate(true);
            }}
            className="btn-primary"
          >
            Add supplier
          </button>
        )}
      </div>
      <div className="table-card">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {["Company", "Contact", "Email", "Country", "Status"].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            )}
            {(suppliers || []).map((s) => (
              <tr key={s.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{s.company_name}</td>
                <td className="px-4 py-3 text-gray-600">{s.contact_person || "—"}</td>
                <td className="px-4 py-3 text-gray-600">{s.email || "—"}</td>
                <td className="px-4 py-3 text-gray-600">{s.country || "—"}</td>
                <td className="px-4 py-3"><StatusBadge status={s.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <Modal title="Add supplier" onClose={() => setShowCreate(false)}>
          <form onSubmit={handleCreate} className="space-y-3">
            <input required placeholder="Company name" value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} className={fieldClass} />
            <input placeholder="Contact person" value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} className={fieldClass} />
            <input type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className={fieldClass} />
            <input placeholder="Country" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} className={fieldClass} />
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
