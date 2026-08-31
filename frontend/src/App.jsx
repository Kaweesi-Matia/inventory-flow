import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { canAccessPath, roleLabel } from "./roles";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import ProductsPage from "./pages/ProductsPage";
import InventoryPage from "./pages/InventoryPage";
import TransfersPage from "./pages/TransfersPage";
import PurchaseOrdersPage from "./pages/PurchaseOrdersPage";
import OrdersPage from "./pages/OrdersPage";
import SuppliersPage from "./pages/SuppliersPage";
import WarehousesPage from "./pages/WarehousesPage";
import ReportsPage from "./pages/ReportsPage";
import UsersPage from "./pages/UsersPage";
import AuditLogsPage from "./pages/AuditLogsPage";
import SettingsPage from "./pages/SettingsPage";

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center text-slate-400">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function RoleGate({ path, children }) {
  const { user } = useAuth();
  if (!canAccessPath(user.role, path)) {
    return (
      <div className="page max-w-lg">
        <div className="card p-8">
          <h1 className="page-title">Access denied</h1>
          <p className="page-subtitle">
            {roleLabel(user.role)} cannot open this page. Use the menu on the left for sections you can access.
          </p>
        </div>
      </div>
    );
  }
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/inventory" element={<InventoryPage />} />
        <Route path="/transfers" element={<RoleGate path="/transfers"><TransfersPage /></RoleGate>} />
        <Route path="/purchase-orders" element={<RoleGate path="/purchase-orders"><PurchaseOrdersPage /></RoleGate>} />
        <Route path="/orders" element={<RoleGate path="/orders"><OrdersPage /></RoleGate>} />
        <Route path="/suppliers" element={<RoleGate path="/suppliers"><SuppliersPage /></RoleGate>} />
        <Route path="/warehouses" element={<RoleGate path="/warehouses"><WarehousesPage /></RoleGate>} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/users" element={<RoleGate path="/users"><UsersPage /></RoleGate>} />
        <Route path="/audit-logs" element={<RoleGate path="/audit-logs"><AuditLogsPage /></RoleGate>} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
