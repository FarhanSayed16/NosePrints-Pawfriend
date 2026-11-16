import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Icon from "../components/Icon";
import {
  confirmMatch,
  deleteDog,
  deleteOwner,
  formatApiError,
  getDogs,
  getMatchQueue,
  getOwners,
  getStaffToken,
  mediaUrl,
  setStaffToken,
  staffAuditLogs,
  staffDeactivate,
  staffInvite,
  staffList,
  staffListInvites,
  staffLogin,
  staffMe,
  staffUpdateRole,
} from "../services/api";
import "./Staff.css";

const STRICT_LIKELY_ONLY = true; // MATCH_STRICT_DEMO demo messaging

function statusChip(status) {
  if (!status) return "pending";
  if (status === "matched" || status === "possible_match") return "pending";
  if (status === "false_positive") return "rejected";
  return "confirmed";
}

export default function Staff() {
  const [authed, setAuthed] = useState(Boolean(getStaffToken()));
  const [staff, setStaff] = useState(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginBusy, setLoginBusy] = useState(false);

  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(false);
  const [queueError, setQueueError] = useState("");
  const [includeReviewed, setIncludeReviewed] = useState(false);
  const [selected, setSelected] = useState(null);
  const [notes, setNotes] = useState("");
  const [actionMsg, setActionMsg] = useState("");
  const [decisionBusy, setDecisionBusy] = useState(false);
  const [ownerReveal, setOwnerReveal] = useState(null);

  const [tab, setTab] = useState("queue");
  const [registry, setRegistry] = useState([]);
  const [registryLoading, setRegistryLoading] = useState(false);
  const [registryQuery, setRegistryQuery] = useState("");
  const [regionFilter, setRegionFilter] = useState("");
  const [purgeMsg, setPurgeMsg] = useState("");
  const [deletingId, setDeletingId] = useState(null);
  const [registryPage, setRegistryPage] = useState(1);
  const [registryHasMore, setRegistryHasMore] = useState(false);

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("staff");
  const [inviteMsg, setInviteMsg] = useState("");
  const [inviteBusy, setInviteBusy] = useState(false);
  const [invites, setInvites] = useState([]);
  const [staffRows, setStaffRows] = useState([]);
  const [auditRows, setAuditRows] = useState([]);
  const [adminBusy, setAdminBusy] = useState(false);

  const [eraseQuery, setEraseQuery] = useState("");
  const [eraseOwners, setEraseOwners] = useState([]);
  const [eraseMsg, setEraseMsg] = useState("");
  const [erasingId, setErasingId] = useState(null);

  const isAdmin = staff?.role === "admin";
  const canDecide = staff?.role === "admin" || staff?.role === "staff";

  const loadQueue = async (reviewed = includeReviewed) => {
    setLoading(true);
    setQueueError("");
    try {
      const res = await getMatchQueue({ include_reviewed: reviewed });
      setQueue(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      if (err.response?.status === 401) {
        setStaffToken(null);
        setAuthed(false);
      } else {
        setQueueError(formatApiError(err, "Could not load match queue"));
        setQueue([]);
      }
    } finally {
      setLoading(false);
    }
  };

  const loadRegistry = async ({ name = registryQuery, region = regionFilter, page = 1, append = false } = {}) => {
    setRegistryLoading(true);
    setPurgeMsg("");
    try {
      const perPage = 50;
      const params = { per_page: perPage, page };
      if (name.trim()) params.name = name.trim();
      if (region.trim()) params.region = region.trim();
      const res = await getDogs(params);
      const rows = Array.isArray(res.data) ? res.data : res.data?.items || [];
      setRegistry((prev) => (append ? [...prev, ...rows] : rows));
      setRegistryPage(page);
      setRegistryHasMore(rows.length >= perPage);
    } catch (err) {
      if (err.response?.status === 401) {
        setStaffToken(null);
        setAuthed(false);
      } else setPurgeMsg(formatApiError(err, "Could not load registry"));
    } finally {
      setRegistryLoading(false);
    }
  };

  const loadAdmin = async () => {
    if (!isAdmin) return;
    setAdminBusy(true);
    try {
      const [inv, list, audit] = await Promise.all([
        staffListInvites(),
        staffList(),
        staffAuditLogs({ per_page: 40 }),
      ]);
      setInvites(inv.data || []);
      setStaffRows(list.data || []);
      setAuditRows(audit.data || []);
    } catch (err) {
      setInviteMsg(formatApiError(err, "Could not load admin data"));
    } finally {
      setAdminBusy(false);
    }
  };

  useEffect(() => {
    if (!authed) return;
    staffMe()
      .then((res) => {
        setStaff(res.data);
        loadQueue();
      })
      .catch(() => {
        setStaffToken(null);
        setAuthed(false);
      });
  }, [authed]);

  useEffect(() => {
    if (authed && tab === "registry") loadRegistry({ page: 1, append: false });
    if (authed && tab === "admin" && staff?.role === "admin") loadAdmin();
  }, [authed, tab, staff?.role]);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (loginBusy) return;
    setLoginError("");
    setLoginBusy(true);
    try {
      const res = await staffLogin({ email, password });
      setStaffToken(res.data.access_token);
      setStaff(res.data);
      setAuthed(true);
    } catch (err) {
      setLoginError(formatApiError(err, "Login failed"));
    } finally {
      setLoginBusy(false);
    }
  };

  const logout = () => {
    setStaffToken(null);
    setAuthed(false);
    setStaff(null);
    setQueue([]);
    setSelected(null);
    setOwnerReveal(null);
    setRegistry([]);
    setTab("queue");
  };

  const handleDecision = async (confirmed) => {
    if (!selected || decisionBusy || !canDecide) return;
    setActionMsg("");
    setDecisionBusy(true);
    try {
      const res = await confirmMatch({
        match_log_id: selected.id,
        confirmed,
        staff_notes: notes || null,
      });
      setOwnerReveal(confirmed ? res.data.owner : null);
      setActionMsg(
        confirmed
          ? res.data.owner
            ? "Confirmed. Owner contact is below — do not share it publicly."
            : "Confirmed, but this dog has no owner on file."
          : "Marked as false positive."
      );
      if (res.data.email_sent) setActionMsg((msg) => `${msg} Owner email sent.`);
      if (confirmed && selected.status === "lost") setActionMsg((msg) => `${msg} Lost listing cleared.`);
      await loadQueue();
      if (!confirmed) setSelected(null);
    } catch (err) {
      setActionMsg(formatApiError(err, "Could not save decision"));
    } finally {
      setDecisionBusy(false);
    }
  };

  const handleDeleteDog = async (dog) => {
    if (!isAdmin) return;
    const label = dog.name || "Unnamed dog";
    if (!window.confirm(`Delete ${label} and all nose prints? This cannot be undone.`)) return;
    setDeletingId(dog.id);
    setPurgeMsg("");
    try {
      await deleteDog(dog.id);
      setPurgeMsg(`Deleted ${label}.`);
      setRegistry((rows) => rows.filter((d) => d.id !== dog.id));
      if (selected?.top_match_dog_id === dog.id) setSelected(null);
    } catch (err) {
      setPurgeMsg(formatApiError(err, "Delete failed"));
    } finally {
      setDeletingId(null);
    }
  };

  const handleInvite = async (e) => {
    e.preventDefault();
    if (inviteBusy) return;
    setInviteBusy(true);
    setInviteMsg("");
    try {
      const res = await staffInvite({ email: inviteEmail, role: inviteRole });
      const urlNote = res.data.accept_url
        ? ` Copy link: ${res.data.accept_url}`
        : res.data.email_sent
          ? " Invite email sent."
          : "";
      setInviteMsg(`Invited ${res.data.email} as ${res.data.role}.${urlNote}`);
      setInviteEmail("");
      await loadAdmin();
    } catch (err) {
      setInviteMsg(formatApiError(err, "Invite failed"));
    } finally {
      setInviteBusy(false);
    }
  };

  const searchOwnersForErase = async (e) => {
    e.preventDefault();
    setEraseMsg("");
    try {
      const q = eraseQuery.trim();
      const res = await getOwners(1, q ? { q } : {});
      setEraseOwners(Array.isArray(res.data) ? res.data : res.data?.items || []);
    } catch (err) {
      setEraseMsg(formatApiError(err, "Could not load owners"));
    }
  };

  const handleEraseOwner = async (owner) => {
    if (!isAdmin) return;
    if (
      !window.confirm(
        `Erase owner ${owner.name} and all dogs/prints/photos? DPDP erasure — cannot be undone.`
      )
    )
      return;
    setErasingId(owner.id);
    setEraseMsg("");
    try {
      await deleteOwner(owner.id);
      setEraseMsg(`Erased ${owner.name}.`);
      setEraseOwners((rows) => rows.filter((o) => o.id !== owner.id));
    } catch (err) {
      setEraseMsg(formatApiError(err, "Erase failed"));
    } finally {
      setErasingId(null);
    }
  };

  if (!authed) {
    return (
      <div className="page staff-page staff-login-page">
        <div className="staff-login-hero">
          <p className="staff-brand">PawFriend</p>
          <h1>Staff console</h1>
          <p className="staff-login-lead">
            Secure ops access. Owner contact stays hidden until a match is confirmed.
          </p>
        </div>
        <div className="container">
          <form className="staff-login-panel" onSubmit={handleLogin}>
            <label className="form-label">
              Email
              <input
                className="form-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="username"
              />
            </label>
            <label className="form-label">
              Password
              <input
                className="form-input"
                type="password"
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </label>
            {loginError && <p className="staff-error" role="alert">{loginError}</p>}
            <button className="btn btn-primary" type="submit" disabled={loginBusy}>
              <Icon name="lock" size={16} /> {loginBusy ? "Signing in…" : "Sign in"}
            </button>
            <p className="staff-login-links">
              <Link to="/staff/reset-password">Forgot password?</Link>
            </p>
          </form>
        </div>
      </div>
    );
  }

  const emptyQueueCopy = STRICT_LIKELY_ONLY
    ? "New identify scans that score as likely (strict demo) will show up here. Use Registry cleanup for junk dogs."
    : "New identify scans that score as likely or possible will show up here.";

  return (
    <div className="page staff-page staff-console">
      <header className="staff-console-header">
        <div>
          <p className="staff-brand">PawFriend Staff</p>
          <h1>
            {tab === "queue" && (
              <>
                Match <span className="text-gradient">queue</span>
              </>
            )}
            {tab === "registry" && (
              <>
                Registry <span className="text-gradient">cleanup</span>
              </>
            )}
            {tab === "admin" && (
              <>
                Staff <span className="text-gradient">admin</span>
              </>
            )}
            {tab === "privacy" && (
              <>
                Privacy <span className="text-gradient">erasure</span>
              </>
            )}
          </h1>
          <p className="staff-console-sub">
            {staff?.email} · {staff?.role}
            {tab === "queue" && " · Confirm side-by-side before contacting an owner."}
          </p>
        </div>
        <button type="button" className="btn btn-outline btn-sm" onClick={logout}>
          Log out
        </button>
      </header>

      <div className="container staff-console-body">
        <nav className="staff-actions-bar" aria-label="Staff sections">
          <div className="staff-tabs">
            <button
              type="button"
              className={`btn btn-sm ${tab === "queue" ? "btn-primary" : "btn-outline"}`}
              onClick={() => setTab("queue")}
            >
              Match queue
            </button>
            <button
              type="button"
              className={`btn btn-sm ${tab === "registry" ? "btn-primary" : "btn-outline"}`}
              onClick={() => setTab("registry")}
            >
              Registry
            </button>
            {isAdmin && (
              <>
                <button
                  type="button"
                  className={`btn btn-sm ${tab === "admin" ? "btn-primary" : "btn-outline"}`}
                  onClick={() => setTab("admin")}
                >
                  Admin
                </button>
                <button
                  type="button"
                  className={`btn btn-sm ${tab === "privacy" ? "btn-primary" : "btn-outline"}`}
                  onClick={() => setTab("privacy")}
                >
                  Erasure
                </button>
              </>
            )}
          </div>
          {tab === "queue" && (
            <div className="staff-queue-tools">
              <label className="staff-toggle">
                <input
                  type="checkbox"
                  checked={includeReviewed}
                  onChange={(e) => {
                    const next = e.target.checked;
                    setIncludeReviewed(next);
                    loadQueue(next);
                  }}
                />
                Show reviewed
              </label>
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={() => loadQueue()}
                disabled={loading}
              >
                Refresh
              </button>
            </div>
          )}
        </nav>

        {tab === "privacy" && isAdmin && (
          <section className="staff-panel">
            <h3>DPDP owner erasure</h3>
            <p className="purge-help">
              Erases owner contact, dogs, nose prints, and stored photos. Audit-logged. Admin only.
            </p>
            <form className="purge-search" onSubmit={searchOwnersForErase}>
              <input
                className="form-input"
                value={eraseQuery}
                onChange={(e) => setEraseQuery(e.target.value)}
                placeholder="Filter by name, email, or phone"
              />
              <button className="btn btn-outline btn-sm" type="submit">
                Load owners
              </button>
            </form>
            {eraseMsg && <p className="review-msg">{eraseMsg}</p>}
            <ul className="purge-list">
              {eraseOwners.map((owner) => (
                <li key={owner.id} className="purge-row">
                  <div className="purge-meta">
                    <div>
                      <strong>{owner.name}</strong>
                      <span>
                        {owner.phone}
                        {owner.email ? ` · ${owner.email}` : ""} · consent {owner.consent_text_version || "v1"}
                      </span>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-outline btn-sm staff-danger"
                    disabled={erasingId === owner.id}
                    onClick={() => handleEraseOwner(owner)}
                  >
                    {erasingId === owner.id ? "Erasing…" : "Erase"}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {tab === "admin" && isAdmin && (
          <section className="staff-panel staff-admin-grid">
            <div>
              <h3>Invite staff</h3>
              <form className="staff-invite-form" onSubmit={handleInvite}>
                <label className="form-label">
                  Email
                  <input
                    className="form-input"
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    required
                  />
                </label>
                <label className="form-label">
                  Role
                  <select
                    className="form-input"
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                  >
                    <option value="viewer">viewer</option>
                    <option value="staff">staff</option>
                    <option value="admin">admin</option>
                  </select>
                </label>
                <button className="btn btn-primary btn-sm" type="submit" disabled={inviteBusy}>
                  {inviteBusy ? "Sending…" : "Send invite"}
                </button>
              </form>
              {inviteMsg && <p className="review-msg">{inviteMsg}</p>}
              <h4 className="staff-subhead">Pending invites</h4>
              {adminBusy && <p className="purge-help">Loading…</p>}
              <ul className="purge-list">
                {invites.map((inv) => (
                  <li key={inv.id} className="purge-row">
                    <div>
                      <strong>{inv.email}</strong>
                      <span>
                        {inv.role} · expires {new Date(inv.expires_at).toLocaleString()}
                      </span>
                    </div>
                  </li>
                ))}
                {!adminBusy && invites.length === 0 && <p className="purge-help">No pending invites.</p>}
              </ul>
            </div>
            <div>
              <h3>Team</h3>
              <ul className="purge-list">
                {staffRows.map((row) => (
                  <li key={row.staff_id} className="purge-row staff-team-row">
                    <div>
                      <strong>{row.email}</strong>
                      <span>
                        {row.role} · {row.is_active ? "active" : "inactive"}
                      </span>
                    </div>
                    <div className="staff-team-actions">
                      <select
                        className="form-input form-input-sm"
                        value={row.role}
                        disabled={!row.is_active}
                        onChange={async (e) => {
                          try {
                            await staffUpdateRole(row.staff_id, { role: e.target.value });
                            await loadAdmin();
                          } catch (err) {
                            setInviteMsg(formatApiError(err, "Role update failed"));
                          }
                        }}
                      >
                        <option value="viewer">viewer</option>
                        <option value="staff">staff</option>
                        <option value="admin">admin</option>
                      </select>
                      {row.is_active && row.staff_id !== staff?.staff_id && (
                        <button
                          type="button"
                          className="btn btn-outline btn-sm staff-danger"
                          onClick={async () => {
                            if (!window.confirm(`Deactivate ${row.email}?`)) return;
                            try {
                              await staffDeactivate(row.staff_id);
                              await loadAdmin();
                            } catch (err) {
                              setInviteMsg(formatApiError(err, "Deactivate failed"));
                            }
                          }}
                        >
                          Deactivate
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
              <h4 className="staff-subhead">Recent audit</h4>
              <ul className="staff-audit-list">
                {auditRows.map((row) => (
                  <li key={row.id}>
                    <time>{new Date(row.created_at).toLocaleString()}</time>
                    <span>{row.action}</span>
                    {row.resource_type && (
                      <span className="muted">
                        {row.resource_type}:{row.resource_id}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )}

        {tab === "registry" && (
          <section className="staff-panel">
            <h3>Dogs</h3>
            <p className="purge-help">
              {isAdmin
                ? "Delete polluted test dogs before demos. Admin only."
                : "Read-only registry view for your role."}
            </p>
            <form
              className="purge-search"
              onSubmit={(e) => {
                e.preventDefault();
                loadRegistry({ name: registryQuery, region: regionFilter, page: 1, append: false });
              }}
            >
              <input
                className="form-input"
                value={registryQuery}
                onChange={(e) => setRegistryQuery(e.target.value)}
                placeholder="Search by name"
              />
              <input
                className="form-input"
                value={regionFilter}
                onChange={(e) => setRegionFilter(e.target.value)}
                placeholder="Region (optional)"
              />
              <button className="btn btn-outline btn-sm" type="submit" disabled={registryLoading}>
                Search
              </button>
            </form>
            {purgeMsg && <p className="review-msg">{purgeMsg}</p>}
            {registryLoading && <p className="purge-help">Loading…</p>}
            {!registryLoading && registry.length === 0 && <p className="purge-help">No dogs found.</p>}
            {!registryLoading && registry.length > 0 && (
              <div className="staff-table-wrap">
                <table className="staff-table">
                  <thead>
                    <tr>
                      <th>Dog</th>
                      <th>Meta</th>
                      <th>Prints</th>
                      {isAdmin && <th>Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {registry.map((dog) => (
                      <tr key={dog.id}>
                        <td>
                          <div className="purge-meta">
                            {dog.profile_photo_url ? (
                              <img className="purge-thumb" src={mediaUrl(dog.profile_photo_url)} alt="" />
                            ) : (
                              <span className="purge-thumb placeholder" />
                            )}
                            <strong>{dog.name || "Unnamed"}</strong>
                          </div>
                        </td>
                        <td>
                          {dog.breed || "Unknown"} · {dog.color || "Unknown"} · {dog.status}
                          {dog.region ? ` · ${dog.region}` : ""}
                        </td>
                        <td>{dog.nose_print_count ?? "—"}</td>
                        {isAdmin && (
                          <td>
                            <button
                              type="button"
                              className="btn btn-outline btn-sm staff-danger"
                              disabled={deletingId === dog.id}
                              onClick={() => handleDeleteDog(dog)}
                            >
                              {deletingId === dog.id ? "Deleting…" : "Delete"}
                            </button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {!registryLoading && registryHasMore && (
              <button
                type="button"
                className="btn btn-outline btn-sm"
                style={{ marginTop: "0.75rem" }}
                onClick={() =>
                  loadRegistry({
                    name: registryQuery,
                    region: regionFilter,
                    page: registryPage + 1,
                    append: true,
                  })
                }
              >
                Load more
              </button>
            )}
          </section>
        )}

        {tab === "queue" && queueError && (
          <p className="staff-error staff-queue-error" role="alert">
            {queueError}
          </p>
        )}

        {tab === "queue" && loading && (
          <div className="text-center mt-4">
            <div className="progress-spinner" />
            <p className="mt-1" style={{ color: "var(--clr-text-muted)" }}>
              Loading queue...
            </p>
          </div>
        )}

        {tab === "queue" && !loading && !queueError && queue.length === 0 && (
          <div className="staff-empty">
            <Icon name="check" size={48} style={{ color: "var(--clr-secondary)" }} />
            <h3>No pending matches</h3>
            <p>{emptyQueueCopy}</p>
          </div>
        )}

        {tab === "queue" && !loading && queue.length > 0 && (
          <div className="staff-review-layout">
            <div className="queue-list" role="list">
              {queue.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`queue-row ${selected?.id === item.id ? "active" : ""}`}
                  onClick={() => {
                    setSelected(item);
                    setNotes(item.staff_notes || "");
                    setOwnerReveal(null);
                    setActionMsg("");
                  }}
                >
                  <span className={`staff-chip staff-chip-${statusChip(item.result_status)}`}>
                    {item.confirmed_at
                      ? item.result_status === "false_positive"
                        ? "rejected"
                        : "confirmed"
                      : item.result_status === "possible_match"
                        ? "possible"
                        : "likely"}
                  </span>
                  <strong>{item.dog_name || "Unnamed dog"}</strong>
                  <span>
                    {item.top_match_score != null ? `${(item.top_match_score * 100).toFixed(1)}%` : "—"}
                  </span>
                  <span className="queue-time">{new Date(item.created_at).toLocaleString()}</span>
                </button>
              ))}
            </div>

            {selected && (
              <div className="review-card">
                <h3>Review match</h3>
                <div className="compare-grid">
                  <figure className="compare-shot">
                    {selected.query_image_url ? (
                      <img src={mediaUrl(selected.query_image_url)} alt="Query crop" />
                    ) : (
                      <div className="compare-placeholder">No query photo</div>
                    )}
                    <figcaption>Found nose</figcaption>
                  </figure>
                  <figure className="compare-shot">
                    {selected.matched_image_url ? (
                      <img src={mediaUrl(selected.matched_image_url)} alt="Registered nose" />
                    ) : (
                      <div className="compare-placeholder">No stored nose</div>
                    )}
                    <figcaption>Registered nose</figcaption>
                  </figure>
                  <figure className="compare-shot">
                    {selected.query_appearance_url ? (
                      <img src={mediaUrl(selected.query_appearance_url)} alt="Found dog" />
                    ) : (
                      <div className="compare-placeholder">No full photo</div>
                    )}
                    <figcaption>Found dog (full)</figcaption>
                  </figure>
                  <figure className="compare-shot">
                    {selected.profile_photo_url ? (
                      <img src={mediaUrl(selected.profile_photo_url)} alt={selected.dog_name || "Candidate"} />
                    ) : (
                      <div className="compare-placeholder">No registered look</div>
                    )}
                    <figcaption>{selected.dog_name || "Registered look"}</figcaption>
                  </figure>
                </div>
                <p className="review-meta">
                  {selected.breed || "Unknown breed"} · {selected.color || "unknown color"} ·{" "}
                  {selected.status || "—"} ·{" "}
                  {selected.top_match_score != null
                    ? `${(selected.top_match_score * 100).toFixed(1)}% nose cosine`
                    : "no score"}
                  {selected.consent_text_version ? ` · consent ${selected.consent_text_version}` : ""}
                  {selected.region ? ` · ${selected.region}` : ""}
                </p>
                <label className="form-label">
                  Notes
                  <textarea
                    className="form-input"
                    rows={3}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Lighting, angle, why you confirmed or rejected..."
                    disabled={!canDecide || Boolean(selected.confirmed_at)}
                  />
                </label>
                {canDecide && !selected.confirmed_at && (
                  <div className="review-actions">
                    <button
                      className="btn btn-primary"
                      type="button"
                      disabled={decisionBusy}
                      onClick={() => handleDecision(true)}
                    >
                      <Icon name="check" size={16} /> {decisionBusy ? "Saving…" : "Confirm match"}
                    </button>
                    <button
                      className="btn btn-outline"
                      type="button"
                      disabled={decisionBusy}
                      onClick={() => handleDecision(false)}
                    >
                      <Icon name="x" size={16} /> Reject
                    </button>
                  </div>
                )}
                {!canDecide && (
                  <p className="purge-help">Your role is viewer — confirm/reject is disabled.</p>
                )}
                {actionMsg && <p className="review-msg">{actionMsg}</p>}
                {ownerReveal && (
                  <div className="owner-reveal">
                    <h4>Owner contact (staff only)</h4>
                    <p>
                      <strong>{ownerReveal.name}</strong>
                    </p>
                    <p>Phone: {ownerReveal.phone}</p>
                    {ownerReveal.email && <p>Email: {ownerReveal.email}</p>}
                    {ownerReveal.address && <p>Address: {ownerReveal.address}</p>}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
