import React, { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Boxes, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { apiError } from "../api/client";
import { ROLES, roleLabel } from "../roles";

const emptyForm = {
  fullName: "",
  email: "",
  password: "",
  role: "ADMIN",
};

export default function LoginPage() {
  const { login, register, user, loading } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("signin");
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setForm(emptyForm);
  }, [mode]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-400">Loading...</div>;
  }
  if (user) return <Navigate to="/dashboard" replace />;

  function setField(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function unlock(e) {
    e.target.readOnly = false;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      if (mode === "signup") {
        await register({
          fullName: form.fullName.trim(),
          email: form.email.trim(),
          password: form.password,
          role: form.role,
        });
      } else {
        await login(form.email.trim(), form.password);
      }
      navigate("/dashboard");
    } catch (err) {
      setError(apiError(err, mode === "signup" ? "Could not create account" : "Login failed"));
    } finally {
      setSubmitting(false);
    }
  }

  const isSignup = mode === "signup";

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="relative hidden lg:flex flex-col justify-between p-12 text-white overflow-hidden bg-ink-950">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_20%_10%,rgba(45,212,191,0.22),transparent_50%),radial-gradient(ellipse_at_90%_90%,rgba(56,189,248,0.14),transparent_45%)]" />
        <div className="absolute inset-0 opacity-[0.12] bg-[linear-gradient(to_right,#fff_1px,transparent_1px),linear-gradient(to_bottom,#fff_1px,transparent_1px)] bg-[size:48px_48px]" />
        <div className="relative">
          <div className="flex items-center gap-3">
            <span className="h-10 w-10 rounded-xl bg-gradient-to-br from-brand-400 to-brand-700 grid place-items-center font-extrabold shadow-glow">
              SX
            </span>
            <span className="text-lg font-bold tracking-tight">SupplyChainX</span>
          </div>
          <h1 className="mt-16 text-4xl font-extrabold leading-tight tracking-tight max-w-md">
            Inventory that stays in step with the business.
          </h1>
          <p className="mt-4 text-slate-300 max-w-md leading-relaxed">
            Products, warehouses, purchase orders, and fulfilment — one workspace, role-aware from the first click.
          </p>
        </div>
        <div className="relative grid grid-cols-2 gap-4 max-w-lg">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm">
            <Boxes size={18} className="text-brand-400 mb-2" />
            <p className="text-sm font-semibold">Live stock</p>
            <p className="text-xs text-slate-400 mt-1">On-hand, reserved, and transfers in one ledger.</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm">
            <ShieldCheck size={18} className="text-brand-400 mb-2" />
            <p className="text-sm font-semibold">Role control</p>
            <p className="text-xs text-slate-400 mt-1">Admin, warehouse, procurement, and sales stay in their lanes.</p>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-10 bg-slate-50">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <span className="h-9 w-9 rounded-xl bg-gradient-to-br from-brand-400 to-brand-700 grid place-items-center font-extrabold text-white text-sm">
              SX
            </span>
            <span className="text-lg font-bold text-slate-900">SupplyChainX</span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">
            {isSignup ? "Create your account" : "Welcome back"}
          </h2>
          <p className="text-sm text-slate-500 mt-1 mb-7">
            {isSignup ? "Choose a role, including Admin, then start working." : "Sign in to continue to operations."}
          </p>

          <form onSubmit={handleSubmit} className="space-y-4" autoComplete="off">
            <input type="text" name="prevent-autofill-user" autoComplete="off" tabIndex={-1} aria-hidden="true" className="hidden" />
            <input type="password" name="prevent-autofill-pass" autoComplete="off" tabIndex={-1} aria-hidden="true" className="hidden" />

            {isSignup && (
              <div>
                <label className="label">Full name</label>
                <input
                  type="text"
                  name="scx-full-name"
                  autoComplete="off"
                  required
                  readOnly
                  value={form.fullName}
                  onFocus={unlock}
                  onChange={(e) => setField("fullName", e.target.value)}
                  className="input"
                />
              </div>
            )}

            <div>
              <label className="label">Email</label>
              <input
                type="text"
                inputMode="email"
                name="scx-login-email"
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="none"
                spellCheck={false}
                required
                readOnly
                value={form.email}
                onFocus={unlock}
                onChange={(e) => setField("email", e.target.value)}
                className="input"
              />
            </div>
            <div>
              <label className="label">Password</label>
              <input
                type="password"
                name="scx-login-password"
                autoComplete="off"
                required
                minLength={isSignup ? 8 : undefined}
                readOnly
                value={form.password}
                onFocus={unlock}
                onChange={(e) => setField("password", e.target.value)}
                className="input"
              />
            </div>

            {isSignup && (
              <div>
                <label className="label">Role</label>
                <select
                  required
                  value={form.role}
                  onChange={(e) => setField("role", e.target.value)}
                  className="input"
                >
                  {Object.keys(ROLES).map((role) => (
                    <option key={role} value={role}>
                      {roleLabel(role)}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-slate-500 mt-1.5">{ROLES[form.role]?.description}</p>
              </div>
            )}

            {error && <p className="text-sm text-rose-600 bg-rose-50 border border-rose-100 rounded-xl px-3 py-2">{error}</p>}
            <button type="submit" disabled={submitting} className="btn-primary w-full py-3">
              {submitting ? (isSignup ? "Creating account..." : "Signing in...") : isSignup ? "Sign up" : "Sign in"}
            </button>
          </form>

          <p className="text-sm text-slate-500 mt-5 text-center">
            {isSignup ? "Already have an account?" : "Need an account?"}{" "}
            <button
              type="button"
              onClick={() => {
                setError("");
                setMode(isSignup ? "signin" : "signup");
              }}
              className="text-brand-700 hover:text-brand-600 font-semibold"
            >
              {isSignup ? "Sign in" : "Sign up"}
            </button>
          </p>

          {isSignup && (
            <div className="mt-8 space-y-2">
              {Object.entries(ROLES).map(([key, meta]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setField("role", key)}
                  className={`w-full text-left rounded-xl border px-3 py-2.5 transition ${
                    form.role === key ? "border-brand-500 bg-brand-50" : "border-slate-200 bg-white hover:border-slate-300"
                  }`}
                >
                  <span className={`status-badge ${meta.badge}`}>{meta.label}</span>
                  <p className="text-xs text-slate-500 mt-1">{meta.description}</p>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
