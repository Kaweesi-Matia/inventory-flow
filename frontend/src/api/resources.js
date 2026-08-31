import { apiClient } from "./client";

export const authApi = {
  login: (email, password) => apiClient.post("/api/auth/login-json", { email, password }),
  register: (payload) => apiClient.post("/api/auth/register", payload),
  me: () => apiClient.get("/api/auth/me"),
};

export const productsApi = {
  list: (params) => apiClient.get("/api/products", { params }),
  get: (id) => apiClient.get(`/api/products/${id}`),
  create: (payload) => apiClient.post("/api/products", payload),
  update: (id, payload) => apiClient.put(`/api/products/${id}`, payload),
  deactivate: (id) => apiClient.delete(`/api/products/${id}`),
  importCsv: (file) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.post("/api/products/import", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

export const categoriesApi = {
  list: () => apiClient.get("/api/categories"),
  create: (payload) => apiClient.post("/api/categories", payload),
};

export const suppliersApi = {
  list: (params) => apiClient.get("/api/suppliers", { params }),
  create: (payload) => apiClient.post("/api/suppliers", payload),
};

export const warehousesApi = {
  list: () => apiClient.get("/api/warehouses"),
  create: (payload) => apiClient.post("/api/warehouses", payload),
};

export const inventoryApi = {
  list: (params) => apiClient.get("/api/inventory", { params }),
  lowStock: (params) => apiClient.get("/api/inventory/low-stock", { params }),
  movements: (params) => apiClient.get("/api/inventory/movements", { params }),
  adjust: (payload) => apiClient.post("/api/inventory/adjust", payload),
};

export const transfersApi = {
  list: () => apiClient.get("/api/transfers"),
  create: (payload) => apiClient.post("/api/transfers", payload),
  receive: (id) => apiClient.post(`/api/transfers/${id}/receive`),
  cancel: (id) => apiClient.post(`/api/transfers/${id}/cancel`),
};

export const purchaseOrdersApi = {
  list: () => apiClient.get("/api/purchase-orders"),
  get: (id) => apiClient.get(`/api/purchase-orders/${id}`),
  create: (payload) => apiClient.post("/api/purchase-orders", payload),
  submit: (id) => apiClient.post(`/api/purchase-orders/${id}/submit`),
  approve: (id) => apiClient.post(`/api/purchase-orders/${id}/approve`),
  receive: (id, payload) => apiClient.post(`/api/purchase-orders/${id}/receive`, payload),
};

export const customersApi = {
  list: () => apiClient.get("/api/customers"),
  create: (payload) => apiClient.post("/api/customers", payload),
};

export const ordersApi = {
  list: () => apiClient.get("/api/orders"),
  get: (id) => apiClient.get(`/api/orders/${id}`),
  create: (payload) => apiClient.post("/api/orders", payload),
  confirm: (id) => apiClient.post(`/api/orders/${id}/confirm`),
  fulfill: (id) => apiClient.post(`/api/orders/${id}/fulfill`),
  cancel: (id) => apiClient.post(`/api/orders/${id}/cancel`),
};

export const dashboardApi = {
  overview: () => apiClient.get("/api/dashboard/overview"),
};

export const reportsApi = {
  inventoryValuation: () => apiClient.get("/api/reports/inventory"),
  warehouseInventory: () => apiClient.get("/api/reports/warehouse"),
  stockMovements: (params) => apiClient.get("/api/reports/stock-movements", { params }),
};

export const adminApi = {
  listUsers: () => apiClient.get("/api/admin/users"),
  changeRole: (userId, role) => apiClient.put(`/api/admin/users/${userId}/role`, null, { params: { role } }),
  setWarehouses: (userId, warehouseIds) =>
    apiClient.put(`/api/admin/users/${userId}/warehouses`, { warehouse_ids: warehouseIds }),
  auditLogs: (params) => apiClient.get("/api/admin/audit-logs", { params }),
};
