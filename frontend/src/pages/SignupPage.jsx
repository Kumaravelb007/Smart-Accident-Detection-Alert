import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { signupUser } from "../api";
import { useToast } from "../components/ToastProvider";
import { saveSession } from "../lib/session";

export default function SignupPage() {
  const navigate = useNavigate();
  const { pushToast } = useToast();

  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting) {
      return;
    }

    setSubmitting(true);
    try {
      const data = await signupUser(form);
      saveSession({ token: data.token, name: data.name, email: data.email });
      pushToast("Account created", "success");
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
        <h1>Create operator account</h1>
        <p className="auth-subtitle">
          Access CNN-powered incident analysis and city-scale traffic intelligence from one console.
        </p>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Full Name
            <input
              type="text"
              required
              placeholder="Jane Doe"
              value={form.name}
              onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
            />
          </label>

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
              minLength={6}
              required
              placeholder="Minimum 6 characters"
              value={form.password}
              onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
            />
          </label>

          <button type="submit" disabled={submitting}>
            {submitting ? "Creating account..." : "Create Account"}
          </button>
        </form>

        <p className="auth-footnote">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </section>
    </div>
  );
}
