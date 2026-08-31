export const ROLES = {
  ADMIN: {
    label: "Admin",
    description: "Full access — users, warehouses, and every workflow.",
    badge: "bg-violet-50 text-violet-700 ring-1 ring-violet-100",
  },
  INVENTORY_MANAGER: {
    label: "Inventory Manager",
    description: "Catalog, stock adjustments, and transfers across all warehouses.",
    badge: "bg-sky-50 text-sky-700 ring-1 ring-sky-100",
  },
  WAREHOUSE_MANAGER: {
    label: "Warehouse Manager",
    description: "Receive POs, fulfill orders, adjust stock, and transfers at assigned warehouses.",
    badge: "bg-amber-50 text-amber-700 ring-1 ring-amber-100",
  },
  PROCUREMENT_MANAGER: {
    label: "Procurement Manager",
    description: "Suppliers and purchase orders — create, submit, approve, and receive.",
    badge: "bg-teal-50 text-teal-700 ring-1 ring-teal-100",
  },
  SALES_USER: {
    label: "Sales",
    description: "Customer orders at assigned warehouses — create, confirm, and cancel.",
    badge: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100",
  },
};

export const CROSS_WAREHOUSE_ROLES = ["ADMIN", "INVENTORY_MANAGER", "PROCUREMENT_MANAGER"];
export const SCOPED_ROLES = ["WAREHOUSE_MANAGER", "SALES_USER"];

export const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "LayoutDashboard", roles: null },
  { to: "/products", label: "Products", icon: "Package", roles: null },
  { to: "/inventory", label: "Inventory", icon: "Boxes", roles: null },
  { to: "/transfers", label: "Transfers", icon: "ArrowLeftRight", roles: ["ADMIN", "INVENTORY_MANAGER", "WAREHOUSE_MANAGER"] },
  { to: "/purchase-orders", label: "Purchase Orders", icon: "ClipboardList", roles: ["ADMIN", "PROCUREMENT_MANAGER", "WAREHOUSE_MANAGER"] },
  { to: "/orders", label: "Customer Orders", icon: "ShoppingCart", roles: ["ADMIN", "SALES_USER", "WAREHOUSE_MANAGER"] },
  { to: "/suppliers", label: "Suppliers", icon: "Truck", roles: ["ADMIN", "PROCUREMENT_MANAGER"] },
  { to: "/warehouses", label: "Warehouses", icon: "Warehouse", roles: ["ADMIN"] },
  { to: "/reports", label: "Reports", icon: "BarChart3", roles: null },
  { to: "/users", label: "Users", icon: "Users", roles: ["ADMIN"] },
  { to: "/audit-logs", label: "Audit Logs", icon: "ShieldCheck", roles: ["ADMIN"] },
  { to: "/settings", label: "Settings", icon: "Settings", roles: null },
];

export function roleLabel(role) {
  return ROLES[role]?.label || (role || "").replace(/_/g, " ");
}

export function roleMeta(role) {
  return ROLES[role] || { label: roleLabel(role), description: "", badge: "bg-gray-100 text-gray-700" };
}

export function canAccessPath(role, path) {
  const item = NAV_ITEMS.find((nav) => nav.to === path);
  if (!item || !item.roles) return true;
  return item.roles.includes(role);
}

export function scopedWarehouses(warehouses, user) {
  if (!user || CROSS_WAREHOUSE_ROLES.includes(user.role)) return warehouses || [];
  const allowed = new Set(user.warehouse_ids || []);
  if (!allowed.size) return [];
  return (warehouses || []).filter((w) => allowed.has(w.id));
}
