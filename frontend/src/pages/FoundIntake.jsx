import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import Icon from "../components/Icon";
import { formatApiError, foundDogIntake } from "../services/api";
import "./FoundIntake.css";

export default function FoundIntake() {
  const location = useLocation();
  const queryImageUrl = location.state?.queryImageUrl || "";
  const [form, setForm] = useState({ finder_nickname: "", finder_phone: "", location_note: "", breed: "", color: "", notes: "" });
  const [state, setState] = useState("form");
  const [error, setError] = useState("");
  const [dogId, setDogId] = useState("");

  const update = (field) => (e) => setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setState("saving");
    try {
      const payload = {};
      Object.entries(form).forEach(([key, value]) => { if (value.trim()) payload[key] = value.trim(); });
      if (queryImageUrl) payload.query_image_url = queryImageUrl;
      const res = await foundDogIntake(payload);
      setDogId(res.data.id);
      setState("done");
    } catch (err) { setError(formatApiError(err, "Could not list this dog as found")); setState("form"); }
  };

  return (
    <div className="page found-page">
      <div className="page-header">
        <h1>List as <span className="text-gradient">Found</span></h1>
        <p>No owner match? Leave a note for PawFriend staff. This is not owner registration — finder phone is optional and not shown publicly.{queryImageUrl ? " Your last nose scan will be attached." : ""}</p>
      </div>

      <div className="container">
        {state === "done" ? (
          <div className="glass-card text-center" style={{ padding: "2.5rem" }}>
            <div style={{ marginBottom: "0.75rem" }}><Icon name="clipboard" size={40} style={{ color: "var(--clr-primary)" }} /></div>
            <h2>Listed as found</h2>
            <p style={{ color: "var(--clr-text-muted)" }}>Staff can see this record. The nose crop from your scan was stored when available, so a later scan can match this found listing.</p>
            {dogId && <p className="found-id">Record ID: {dogId}</p>}
            <div className="found-actions">
              <Link to="/identify" className="btn btn-primary"><Icon name="scan" size={16} /> Scan another dog</Link>
              <Link to="/directory" className="btn btn-outline"><Icon name="grid" size={16} /> Directory</Link>
            </div>
          </div>
        ) : (
          <form className="glass-card found-form" onSubmit={handleSubmit}>
            <label className="form-label">Your nickname (optional)<input className="form-input" value={form.finder_nickname} onChange={update("finder_nickname")} placeholder="So staff can thank you" /></label>
            <label className="form-label">Phone (optional)<input className="form-input" value={form.finder_phone} onChange={update("finder_phone")} placeholder="Not shown on the public site" /></label>
            <label className="form-label">Where was the dog found?<input className="form-input" value={form.location_note} onChange={update("location_note")} placeholder="Area, landmark, or street" /></label>
            <label className="form-label">Breed (if you know)<input className="form-input" value={form.breed} onChange={update("breed")} /></label>
            <label className="form-label">Color<input className="form-input" value={form.color} onChange={update("color")} /></label>
            <label className="form-label">Notes<textarea className="form-input" rows={3} value={form.notes} onChange={update("notes")} placeholder="Collar, temperament, anything staff should know" /></label>
            {error && <p className="found-error">{error}</p>}
            <button className="btn btn-primary" type="submit" disabled={state === "saving"}>{state === "saving" ? "Saving..." : "List as found"}</button>
          </form>
        )}
      </div>
    </div>
  );
}
