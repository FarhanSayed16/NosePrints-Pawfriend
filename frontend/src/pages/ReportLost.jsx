import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Icon from "../components/Icon";
import { formatApiError, getDog, mediaUrl, reportDogLost } from "../services/api";
import "./FoundIntake.css";

export default function ReportLost() {
  const { dogId } = useParams();
  const [dog, setDog] = useState(null);
  const [note, setNote] = useState("");
  const [state, setState] = useState("loading");
  const [error, setError] = useState("");

  useEffect(() => {
    getDog(dogId).then((res) => { setDog(res.data); setState("form"); }).catch((err) => { setError(formatApiError(err, "Dog not found")); setState("error"); });
  }, [dogId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setState("saving");
    try {
      const res = await reportDogLost(dogId, { last_seen_note: note.trim() || null });
      setDog(res.data);
      setState("done");
    } catch (err) {
      if (err.response?.status === 401) { setError("Staff login required to mark a dog as lost."); setState("error"); return; }
      setError(formatApiError(err, "Could not report this dog as lost"));
      setState("form");
    }
  };

  return (
    <div className="page found-page">
      <div className="page-header">
        <h1>Report <span className="text-gradient">Lost</span></h1>
        <p>Marks the dog as lost so identify ranking prefers them slightly.</p>
      </div>

      <div className="container">
        {state === "loading" && <div className="text-center mt-4"><div className="progress-spinner"></div></div>}

        {state === "error" && (
          <div className="glass-card text-center" style={{ padding: "2rem" }}>
            <h3>{error || "Dog not found"}</h3>
            <div className="found-actions">
              {error?.includes("Staff login") && <Link to="/staff" className="btn btn-primary mt-2"><Icon name="shield" size={16} /> Staff login</Link>}
              <Link to="/directory" className="btn btn-outline mt-2"><Icon name="arrowLeft" size={16} /> Back to directory</Link>
            </div>
          </div>
        )}

        {dog && state !== "error" && (
          <div className="glass-card found-form">
            <div className="lost-preview">
              {dog.profile_photo_url ? <img src={mediaUrl(dog.profile_photo_url)} alt={dog.name || "Dog"} /> : <span className="avatar-placeholder"><Icon name="dog" size={32} /></span>}
              <div>
                <h3>{dog.name || "Unnamed"}</h3>
                <p style={{ color: "var(--clr-text-muted)" }}>{dog.breed || "Unknown breed"} · {dog.color || "unknown color"} · {dog.status}</p>
              </div>
            </div>
            {state === "done" ? (
              <>
                <p>This dog is now listed as lost.</p>
                <div className="found-actions">
                  <Link to="/lost" className="btn btn-primary"><Icon name="alert" size={16} /> View lost dogs</Link>
                  <Link to="/directory" className="btn btn-outline"><Icon name="grid" size={16} /> Directory</Link>
                </div>
              </>
            ) : (
              <form onSubmit={handleSubmit}>
                <label className="form-label">Last seen note<textarea className="form-input" rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Neighborhood, time, distinctive collar..." /></label>
                {error && <p className="found-error">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={state === "saving"}>{state === "saving" ? "Saving..." : "Mark as lost"}</button>
              </form>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
