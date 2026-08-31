import React from "react";
import { useQuery } from "@tanstack/react-query";
import { adminApi } from "../api/resources";

export default function AuditLogsPage() {
  const { data: logs, isLoading } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: () => adminApi.auditLogs().then((r) => r.data),
  });

  return (
    <div className="page">
      <h1 className="page-title mb-6">Audit Logs</h1>
      <div className="table-card">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {["When", "Action", "Resource", "Resource ID"].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            )}
            {(logs || []).map((log) => (
              <tr key={log.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-500 text-xs">{new Date(log.created_at).toLocaleString()}</td>
                <td className="px-4 py-3 font-medium text-gray-900">{log.action}</td>
                <td className="px-4 py-3 text-gray-600">{log.resource_type}</td>
                <td className="px-4 py-3 font-mono text-xs text-gray-500">{log.resource_id || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
