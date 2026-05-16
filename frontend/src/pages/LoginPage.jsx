import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { loginUser } from "../api";
import { saveSession } from "../lib/session";
import { useToast } from "../components/ToastProvider";

export default function LoginPage() {
  const navigate = useNavigate();
  const { pushToast } = useToast();

  const [form, setForm] = useState({ email: "", password: "" });
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting) {
      return;
    }

    setSubmitting(true);
    try {
      const data = await loginUser(form);
      saveSession({ token: data.token, name: data.name, email: data.email });
      pushToast("Login successful", "success");
      navigate("/dashboard", { replace: true });
    } catch (error) {
      pushToast(error.message, "error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="bg-layer" />
      <section className="auth-panel">
        <p className="eyebrow">Accident Vision</p>
        <h1>Sign in to command center</h1>
        <p className="auth-subtitle">
          Real-time accident detection, traffic density analytics, and emergency-ready evidence.
        </p>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Email
            <input
              type="email"
              required
              placeholder="you@example.com"
              value={form.email}
              onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
            />
          </label>

          <label>
            Password
            <input
              type="password"
              required
              placeholder="Enter password"
              value={form.password}
              onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
            />
          </label>

          <button type="submit" disabled={submitting}>
            {submitting ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className="auth-footnote">
          New here? <Link to="/signup">Create your operator account</Link>
        </p>
      </section>
    </div>
  );
}
