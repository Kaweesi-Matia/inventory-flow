const STATUS_STYLES = {
  ACTIVE: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100",
  IN_STOCK: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100",
  INACTIVE: "bg-slate-100 text-slate-600 ring-1 ring-slate-200",
  DISCONTINUED: "bg-slate-100 text-slate-500 ring-1 ring-slate-200",
  LOW_STOCK: "bg-amber-50 text-amber-700 ring-1 ring-amber-100",
  OUT_OF_STOCK: "bg-rose-50 text-rose-700 ring-1 ring-rose-100",
  DRAFT: "bg-slate-100 text-slate-600 ring-1 ring-slate-200",
  SUBMITTED: "bg-sky-50 text-sky-700 ring-1 ring-sky-100",
  APPROVED: "bg-indigo-50 text-indigo-700 ring-1 ring-indigo-100",
  PARTIALLY_RECEIVED: "bg-amber-50 text-amber-700 ring-1 ring-amber-100",
  RECEIVED: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100",
  CANCELLED: "bg-rose-50 text-rose-700 ring-1 ring-rose-100",
  PENDING: "bg-slate-100 text-slate-600 ring-1 ring-slate-200",
  CONFIRMED: "bg-sky-50 text-sky-700 ring-1 ring-sky-100",
  RESERVED: "bg-indigo-50 text-indigo-700 ring-1 ring-indigo-100",
  PROCESSING: "bg-amber-50 text-amber-700 ring-1 ring-amber-100",
  FULFILLED: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100",
  IN_TRANSIT: "bg-amber-50 text-amber-700 ring-1 ring-amber-100",
};

export default function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] || "bg-slate-100 text-slate-600 ring-1 ring-slate-200";
  return <span className={`status-badge ${style}`}>{status.replace(/_/g, " ")}</span>;
}
