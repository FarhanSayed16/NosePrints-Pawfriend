import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getLostDogs } from "../services/api";
import "./LostDogs.css";

export default function LostDogs() {
  const [dogs, setDogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  useEffect(() => {
    const fetchLost = async () => {
      setLoading(true);
      try {
        const res = await getLostDogs(page);
        setDogs(res.data);
      } catch (err) {
        console.error("Failed to fetch lost dogs:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchLost();
  }, [page]);

  return (
    <div className="page lost-page">
      <div className="container">
        <div className="page-header">
          <h1>
            🚨 <span className="text-gradient">Lost Dogs</span>
          </h1>
          <p>
            These dogs have been reported missing. If you've seen any of them,
            please scan their nose or contact PawFriend.
          </p>
        </div>

        {/* Action Banner */}
        <div className="glass-card action-banner">
          <div className="banner-content">
            <h3>Found a dog that might be on this list?</h3>
            <p>Scan their nose — our AI will check if they match any lost dog instantly.</p>
          </div>
          <Link to="/identify" className="btn btn-accent btn-lg">
            🔍 Scan Now
          </Link>
        </div>

        {loading && (
          <div className="text-center mt-4">
            <div className="progress-spinner"></div>
            <p className="mt-1" style={{ color: "var(--clr-text-muted)" }}>
              Loading...
            </p>
          </div>
        )}

        {!loading && dogs.length === 0 && (
          <div className="glass-card text-center mt-3" style={{ padding: "3rem" }}>
            <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🎉</div>
            <h3>No lost dogs reported</h3>
            <p style={{ color: "var(--clr-text-muted)" }}>
              Great news! No dogs are currently listed as missing.
            </p>
          </div>
        )}

        {!loading && dogs.length > 0 && (
          <div className="lost-grid stagger-children">
            {dogs.map((dog) => (
              <div key={dog.id} className="lost-card glass-card">
                <div className="lost-card-top">
                  <div className="lost-avatar">
                    {dog.profile_photo_url ? (
                      <img src={dog.profile_photo_url} alt={dog.name} />
                    ) : (
                      <span className="avatar-placeholder">🐕</span>
                    )}
                  </div>
                  <span className="badge badge-lost">LOST</span>
                </div>
                <h3>{dog.name || "Unnamed Dog"}</h3>
                <div className="lost-details">
                  {dog.breed && <div className="lost-detail">🏷️ {dog.breed}</div>}
                  {dog.color && <div className="lost-detail">🎨 {dog.color}</div>}
                  {dog.sex && (
                    <div className="lost-detail">
                      {dog.sex === "male" ? "♂️" : "♀️"} {dog.sex}
                    </div>
                  )}
                  {dog.last_seen_at && (
                    <div className="lost-detail">
                      📅 Last seen: {new Date(dog.last_seen_at).toLocaleDateString()}
                    </div>
                  )}
                </div>
                <div className="lost-cta">
                  <Link to="/identify" className="btn btn-primary btn-sm">
                    🔍 I Found This Dog
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && dogs.length > 0 && (
          <div className="pagination">
            <button
              className="btn btn-outline btn-sm"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              ← Previous
            </button>
            <span className="page-number">Page {page}</span>
            <button
              className="btn btn-outline btn-sm"
              disabled={dogs.length < 20}
              onClick={() => setPage(page + 1)}
            >
              Next →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
