import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { formatApiError, setStaffToken, staffAcceptInvite } from "../services/api";
import "./Staff.css";

export default function StaffAcceptInvite() {
  const [params] = useSearchParams();
  const tokenFromUrl = useMemo(() => params.get("token") || "", [params]);
  const [token, setToken] = useState(tokenFromUrl);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const onSubmit = async (e) => {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await staffAcceptInvite({ token, password });
      setStaffToken(res.data.access_token);
      navigate("/staff", { replace: true });
    } catch (err) {
      setError(formatApiError(err, "Could not accept invite"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page staff-page">
      <div className="staff-token-page">
        <p className="staff-brand">PawFriend</p>
        <h1>Accept staff invite</h1>
        <p className="purge-help">Choose a password to activate your staff account.</p>
        <form className="staff-login-panel" onSubmit={onSubmit}>
          {!tokenFromUrl && (
            <label className="form-label">
              Invite token
              <input
                className="form-input"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                required
              />
            </label>
          )}
          <label className="form-label">
            Password
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
          <button className="btn btn-primary" type="submit" disabled={busy || !token}>
            {busy ? "Activating…" : "Activate account"}
          </button>
          <p className="staff-login-links">
            <Link to="/staff">Back to login</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
