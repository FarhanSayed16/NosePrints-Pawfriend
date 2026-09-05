import { useEffect, useState } from "react";
import Icon from "../components/Icon";
import {
  confirmMatch, formatApiError, getMatchQueue, getStaffToken,
  mediaUrl, setStaffToken, staffLogin, staffMe,
} from "../services/api";
import "./Staff.css";

export default function Staff() {
  const [authed, setAuthed] = useState(Boolean(getStaffToken()));
  const [staff, setStaff] = useState(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(null);
  const [notes, setNotes] = useState("");
  const [actionMsg, setActionMsg] = useState("");
  const [ownerReveal, setOwnerReveal] = useState(null);

  const loadQueue = async () => {
    setLoading(true);
    try {
      const res = await getMatchQueue();
      setQueue(res.data);
    } catch (err) {
      if (err.response?.status === 401) { setStaffToken(null); setAuthed(false); }
    } finally { setLoading(false); }
  };

  useEffect(() => {
    if (!authed) return;
    staffMe().then((res) => { setStaff(res.data); loadQueue(); }).catch(() => { setStaffToken(null); setAuthed(false); });
  }, [authed]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError("");
    try {
      const res = await staffLogin({ email, password });
      setStaffToken(res.data.access_token);
      setStaff(res.data);
      setAuthed(true);
    } catch (err) { setLoginError(formatApiError(err, "Login failed")); }
  };

  const logout = () => {
    setStaffToken(null); setAuthed(false); setStaff(null);
    setQueue([]); setSelected(null); setOwnerReveal(null);
  };

  const handleDecision = async (confirmed) => {
    if (!selected) return;
    setActionMsg("");
    try {
      const res = await confirmMatch({ match_log_id: selected.id, confirmed, staff_notes: notes || null });
      setOwnerReveal(confirmed ? res.data.owner : null);
      setActionMsg(confirmed
        ? res.data.owner ? "Confirmed. Owner contact is below — do not share it publicly." : "Confirmed, but this dog has no owner on file."
        : "Marked as false positive.");
      if (res.data.email_sent) setActionMsg((msg) => `${msg} Owner email sent.`);
      if (confirmed && selected.status === "lost") setActionMsg((msg) => `${msg} Lost listing cleared.`);
      await loadQueue();
      if (!confirmed) setSelected(null);
    } catch (err) { setActionMsg(formatApiError(err, "Could not save decision")); }
  };

  if (!authed) {
    return (
      <div className="page staff-page">
        <div className="page-header">
          <h1>Staff <span className="text-gradient">Login</span></h1>
          <p>PawFriend staff only. Owner contact stays hidden until you confirm a match.</p>
        </div>
        <div className="container">
          <form className="glass-card staff-login" onSubmit={handleLogin}>
            <label className="form-label">
              Email
              <input className="form-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </label>
            <label className="form-label">
              Password
              <input className="form-input" type="password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required />
            </label>
            {loginError && <p className="staff-error">{loginError}</p>}
            <button className="btn btn-primary" type="submit"><Icon name="lock" size={16} /> Sign in</button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="page staff-page">
      <div className="page-header">
        <h1>Match <span className="text-gradient">Queue</span></h1>
        <p>Signed in as {staff?.email}. Confirm side-by-side before contacting an owner.</p>
      </div>

      <div className="container">
        <div className="staff-actions-bar">
          <button className="btn btn-outline btn-sm" onClick={logout}>Log out</button>
        </div>

        {loading && (
          <div className="text-center mt-4">
            <div className="progress-spinner"></div>
            <p className="mt-1" style={{ color: "var(--clr-text-muted)" }}>Loading queue...</p>
          </div>
        )}

        {!loading && queue.length === 0 && (
          <div className="glass-card text-center" style={{ padding: "3rem" }}>
            <div style={{ marginBottom: "1rem" }}><Icon name="check" size={48} style={{ color: "var(--clr-secondary)" }} /></div>
            <h3>No pending matches</h3>
            <p style={{ color: "var(--clr-text-muted)" }}>New identify scans that score as likely or possible will show up here.</p>
          </div>
        )}

        {!loading && queue.length > 0 && (
          <div className="queue-list">
            {queue.map((item) => (
              <button key={item.id} type="button" className={`queue-row glass-card ${selected?.id === item.id ? "active" : ""}`}
                onClick={() => { setSelected(item); setNotes(item.staff_notes || ""); setOwnerReveal(null); setActionMsg(""); }}>
                <span className={`badge badge-${item.result_status}`}>{item.result_status === "possible_match" ? "possible" : "likely"}</span>
                <strong>{item.dog_name || "Unnamed dog"}</strong>
                <span>{item.top_match_score != null ? `${(item.top_match_score * 100).toFixed(1)}%` : "—"}</span>
                <span className="queue-time">{new Date(item.created_at).toLocaleString()}</span>
              </button>
            ))}
          </div>
        )}

        {selected && (
          <div className="glass-card review-card">
            <h3>Review match</h3>
            <div className="compare-grid">
              <figure className="compare-shot">
                {selected.query_image_url ? <img src={mediaUrl(selected.query_image_url)} alt="Query crop" /> : <div className="compare-placeholder">No query photo</div>}
                <figcaption>Found nose</figcaption>
              </figure>
              <figure className="compare-shot">
                {selected.matched_image_url ? (
                  <img src={mediaUrl(selected.matched_image_url)} alt="Registered nose" />
                ) : <div className="compare-placeholder">No stored nose</div>}
                <figcaption>Registered nose</figcaption>
              </figure>
              <figure className="compare-shot">
                {selected.query_appearance_url ? (
                  <img src={mediaUrl(selected.query_appearance_url)} alt="Found dog" />
                ) : <div className="compare-placeholder">No full photo</div>}
                <figcaption>Found dog (full)</figcaption>
              </figure>
              <figure className="compare-shot">
                {selected.profile_photo_url ? (
                  <img src={mediaUrl(selected.profile_photo_url)} alt={selected.dog_name || "Candidate"} />
                ) : <div className="compare-placeholder">No registered look</div>}
                <figcaption>{selected.dog_name || "Registered look"}</figcaption>
              </figure>
            </div>
            <p>{selected.breed || "Unknown breed"} · {selected.color || "unknown color"} · {selected.status || "—"} · {selected.top_match_score != null ? `${(selected.top_match_score * 100).toFixed(1)}% nose cosine` : "no score"}</p>
            <label className="form-label">
              Notes
              <textarea className="form-input" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Lighting, angle, why you confirmed or rejected..." />
            </label>
            <div className="review-actions">
              <button className="btn btn-primary" type="button" onClick={() => handleDecision(true)}><Icon name="check" size={16} /> Confirm match</button>
              <button className="btn btn-outline" type="button" onClick={() => handleDecision(false)}><Icon name="x" size={16} /> Reject</button>
            </div>
            {actionMsg && <p className="review-msg">{actionMsg}</p>}
            {ownerReveal && (
              <div className="owner-reveal">
                <h4>Owner contact (staff only)</h4>
                <p><strong>{ownerReveal.name}</strong></p>
                <p>Phone: {ownerReveal.phone}</p>
                {ownerReveal.email && <p>Email: {ownerReveal.email}</p>}
                {ownerReveal.address && <p>Address: {ownerReveal.address}</p>}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
