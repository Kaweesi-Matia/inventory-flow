import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi, warehousesApi } from "../api/resources";
import { apiError } from "../api/client";
import { ROLES, SCOPED_ROLES, roleLabel, roleMeta } from "../roles";
import { useAuth } from "../context/AuthContext";

const ROLE_OPTIONS = Object.keys(ROLES);

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState("");

  const { data: users, isLoading } = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => adminApi.listUsers().then((r) => r.data),
  });
  const { data: warehouses } = useQuery({
    queryKey: ["warehouses"],
    queryFn: () => warehousesApi.list().then((r) => r.data),
  });

  const roleMutation = useMutation({
    mutationFn: ({ userId, role }) => adminApi.changeRole(userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      setError("");
    },
    onError: (err) => setError(apiError(err, "Could not change role")),
  });

  const warehouseMutation = useMutation({
    mutationFn: ({ userId, warehouseIds }) => adminApi.setWarehouses(userId, warehouseIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      setError("");
    },
    onError: (err) => setError(apiError(err, "Could not update warehouses")),
  });

  function toggleWarehouse(user, warehouseId, checked) {
    const current = user.warehouse_ids || [];
    const next = checked
      ? [...current, warehouseId]
      : current.filter((id) => id !== warehouseId);
    warehouseMutation.mutate({ userId: user.id, warehouseIds: next });
  }

  return (
    <div className="page">
      <h1 className="page-title mb-2">Users & roles</h1>
      <p className="page-subtitle mb-6">
        Assign a role to control which menus and API actions a user can use. You cannot change your own role.
      </p>
      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      <div className="table-card">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {["Name", "Email", "Role", "Warehouses", "Active"].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            )}
            {(users || []).map((u) => {
              const isSelf = u.id === currentUser?.id;
              const isScoped = SCOPED_ROLES.includes(u.role);
              return (
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{u.full_name}</td>
                  <td className="px-4 py-3 text-gray-600">{u.email}</td>
                  <td className="px-4 py-3">
                    {isSelf ? (
                      <span className={`status-badge ${roleMeta(u.role).badge}`}>{roleLabel(u.role)}</span>
                    ) : (
                      <select
                        value={u.role}
                        disabled={roleMutation.isPending}
                        onChange={(e) => roleMutation.mutate({ userId: u.id, role: e.target.value })}
                        className="input py-1.5 text-xs"
                      >
                        {ROLE_OPTIONS.map((role) => (
                          <option key={role} value={role}>{roleLabel(role)}</option>
                        ))}
                      </select>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {isScoped ? (
                      <div className="flex flex-wrap gap-x-3 gap-y-1">
                        {(warehouses || []).map((w) => {
                          const checked = (u.warehouse_ids || []).includes(w.id);
                          return (
                            <label key={w.id} className="inline-flex items-center gap-1 text-xs text-gray-700">
                              <input
                                type="checkbox"
                                checked={checked}
                                disabled={warehouseMutation.isPending}
                                onChange={(e) => toggleWarehouse(u, w.id, e.target.checked)}
                              />
                              {w.code}
                            </label>
                          );
                        })}
                        {!(u.warehouse_ids || []).length && (
                          <span className="text-xs text-amber-600">None — no access until assigned</span>
                        )}
                      </div>
                    ) : (
                      <span className="text-xs text-gray-500">All</span>
                    )}
                  </td>
                  <td className="px-4 py-3">{u.is_active ? "Yes" : "No"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
