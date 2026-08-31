import React from "react";
import { useQuery } from "@tanstack/react-query";
import { reportsApi } from "../api/resources";

export default function ReportsPage() {
  const { data: valuation, isLoading } = useQuery({
    queryKey: ["inventory-valuation-report"],
    queryFn: () => reportsApi.inventoryValuation().then((r) => r.data),
  });

  const totalValue = (valuation || []).reduce((sum, row) => sum + row.total_value, 0);

  return (
    <div className="page">
      <h1 className="page-title mb-6">Reports</h1>

      <div className="table-card mb-6">
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Inventory Valuation</h2>
          <span className="text-sm text-gray-500">
            Total: ${totalValue.toLocaleString(undefined, { maximumFractionDigits: 2 })}
          </span>
        </div>
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {["SKU", "Product", "Units on Hand", "Total Value"].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            )}
            {(valuation || []).map((row) => (
              <tr key={row.product_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{row.sku}</td>
                <td className="px-4 py-3 font-medium text-gray-900">{row.name}</td>
                <td className="px-4 py-3">{row.total_on_hand}</td>
                <td className="px-4 py-3">${Number(row.total_value).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
