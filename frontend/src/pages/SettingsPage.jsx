import React, { useState } from "react";
import { apiClient } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { roleMeta } from "../roles";

export default function SettingsPage() {
  const { user } = useAuth();
  const meta = roleMeta(user?.role);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      await apiClient.put("/api/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setMessage("Password updated successfully.");
      setCurrentPassword("");
      setNewPassword("");
    } catch (err) {
      setError(err.response?.data?.detail || "Could not update password");
    }
  }

  return (
    <div className="page max-w-lg">
      <h1 className="page-title mb-6">Settings</h1>

      <div className="card p-6 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Profile</h2>
        <p className="text-sm text-gray-600">{user?.full_name}</p>
        <p className="text-sm text-gray-500">{user?.email}</p>
        <p className="mt-2">
          <span className={`status-badge ${meta.badge}`}>{meta.label}</span>
        </p>
        <p className="text-sm text-gray-500 mt-2">{meta.description}</p>
        {(user?.warehouse_labels || []).length > 0 && (
          <p className="text-sm text-gray-500 mt-1">Assigned warehouses: {user.warehouse_labels.join(", ")}</p>
        )}
      </div>

      <div className="card p-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Change Password</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Current password</label>
            <input
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="input"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">New password</label>
            <input
              type="password"
              required
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="input"
            />
          </div>
          {message && <p className="text-sm text-green-600">{message}</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" className="btn-primary">
            Update password
          </button>
        </form>
      </div>
    </div>
  );
}
