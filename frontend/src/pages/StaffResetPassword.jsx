import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  formatApiError,
  setStaffToken,
  staffRequestPasswordReset,
  staffResetPassword,
} from "../services/api";
import "./Staff.css";

export default function StaffResetPassword() {
  const [params] = useSearchParams();
  const tokenFromUrl = useMemo(() => params.get("token") || "", [params]);
  const [email, setEmail] = useState("");
  const [token, setToken] = useState(tokenFromUrl);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const hasToken = Boolean(tokenFromUrl || token);

  const requestReset = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMsg("");
    try {
      const res = await staffRequestPasswordReset({ email });
      let text = res.data.message || "If that email is registered, a reset link was issued.";
      if (res.data.reset_url) text += ` Staging link: ${res.data.reset_url}`;
      setMsg(text);
    } catch (err) {
      setError(formatApiError(err, "Request failed"));
    } finally {
      setBusy(false);
    }
  };

  const completeReset = async (e) => {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await staffResetPassword({ token, password });
      setStaffToken(res.data.access_token);
      navigate("/staff", { replace: true });
    } catch (err) {
      setError(formatApiError(err, "Reset failed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page staff-page">
      <div className="staff-token-page">
        <p className="staff-brand">PawFriend</p>
        <h1>{tokenFromUrl ? "Set new password" : "Forgot password"}</h1>
        <p className="purge-help">
          {tokenFromUrl
            ? "Enter a new password for your staff account."
            : "We will issue a reset link. With SMTP unset, the API returns a copyable staging link."}
        </p>

        {!tokenFromUrl ? (
          <form className="staff-login-panel" onSubmit={requestReset}>
            <label className="form-label">
              Email
              <input
                className="form-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>
            {msg && <p className="review-msg">{msg}</p>}
            {error && (
              <p className="staff-error" role="alert">
                {error}
              </p>
            )}
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? "Sending…" : "Request reset"}
            </button>
            <p className="staff-login-links">
              <Link to="/staff">Back to login</Link>
            </p>
          </form>
        ) : (
          <form className="staff-login-panel" onSubmit={completeReset}>
            {!tokenFromUrl && (
              <label className="form-label">
                Reset token
                <input
                  className="form-input"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  required
                />
              </label>
            )}
            <label className="form-label">
              New password
              <input
                className="form-input"
                type="password"
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
              />
            </label>
            <label className="form-label">
              Confirm password
              <input
                className="form-input"
                type="password"
                minLength={8}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                autoComplete="new-password"
              />
            </label>
            {error && (
              <p className="staff-error" role="alert">
                {error}
              </p>
            )}
            <button className="btn btn-primary" type="submit" disabled={busy || !hasToken}>
              {busy ? "Saving…" : "Update password"}
            </button>
            <p className="staff-login-links">
              <Link to="/staff">Back to login</Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
