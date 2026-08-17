import { useState } from "react";
import CameraCapture from "../components/CameraCapture";
import { identifyDog } from "../services/api";
import "./Identify.css";

export default function Identify() {
  const [state, setState] = useState("ready"); // ready | scanning | loading | results | no-match | error
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const handleCapture = async (blob) => {
    setState("loading");
    setError(null);

    try {
      const res = await identifyDog(blob);
      setResults(res.data);

      if (res.data.match_found && res.data.candidates.length > 0) {
        setState("results");
      } else {
        setState("no-match");
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === "object") {
        setError({
          message: detail.message || "Identification failed",
          issues: detail.issues || [],
          suggestions: detail.suggestions || [],
        });
      } else {
        setError({ message: detail || "Something went wrong. Please try again.", issues: [], suggestions: [] });
      }
      setState("error");
    }
  };

  const reset = () => {
    setState("ready");
    setResults(null);
    setError(null);
  };

  return (
    <div className="page identify-page">
      <div className="container">
        <div className="page-header">
          <h1>
            Identify a <span className="text-gradient">Dog</span>
          </h1>
          <p>
            Found a stray? Scan their nose — we'll check if they're registered
            in under 3 seconds.
          </p>
        </div>

        {/* Ready State */}
        {(state === "ready" || state === "scanning") && (
          <div className="animate-fade-in">
            <div className="glass-card identify-info">
              <h3>📱 How to Scan</h3>
              <div className="scan-tips">
                <div className="tip">
                  <span className="tip-icon">📏</span>
                  <span>Hold phone 15–30cm from the nose</span>
                </div>
                <div className="tip">
                  <span className="tip-icon">💡</span>
                  <span>Good lighting, no shadows</span>
                </div>
                <div className="tip">
                  <span className="tip-icon">🎯</span>
                  <span>Nose should fill the frame</span>
                </div>
                <div className="tip">
                  <span className="tip-icon">🤚</span>
                  <span>Hold steady — avoid blur</span>
                </div>
              </div>
            </div>
            <CameraCapture onCapture={handleCapture} mode="single" />
          </div>
        )}

        {/* Loading */}
        {state === "loading" && (
          <div className="glass-card loading-card animate-fade-in text-center">
            <div className="scan-animation">
              <div className="scan-ring"></div>
              <div className="scan-ring delay-1"></div>
              <div className="scan-ring delay-2"></div>
              <span className="scan-emoji">🔍</span>
            </div>
            <h3>Analyzing Nose Print...</h3>
            <p>Detecting nose → Checking quality → Searching database</p>
          </div>
        )}

        {/* Match Results */}
        {state === "results" && results && (
          <div className="results-section animate-slide-up">
            <div className="glass-card match-banner">
              <div className="match-icon">✅</div>
              <h2>Match Found!</h2>
              <p>
                Similarity score:{" "}
                <strong>{(results.top_score * 100).toFixed(1)}%</strong>
              </p>
              <p className="match-note">
                A PawFriend staff member will review this match before any
                contact information is shared.
              </p>
            </div>

            <div className="candidates-list">
              {results.candidates
                .filter((c) => c.similarity_score >= results.threshold_used)
                .map((candidate, idx) => (
                  <div key={idx} className="candidate-card glass-card">
                    <div className="candidate-header">
                      <span className="candidate-rank">#{idx + 1}</span>
                      <span
                        className={`badge badge-${candidate.status}`}
                      >
                        {candidate.status}
                      </span>
                    </div>
                    <div className="candidate-details">
                      <h3>{candidate.dog_name || "Unknown"}</h3>
                      <div className="detail-row">
                        <span>🏷️ Breed:</span>{" "}
                        <strong>{candidate.breed || "N/A"}</strong>
                      </div>
                      <div className="detail-row">
                        <span>🎨 Color:</span>{" "}
                        <strong>{candidate.color || "N/A"}</strong>
                      </div>
                      <div className="detail-row">
                        <span>👤 Owner:</span>{" "}
                        <strong>{candidate.owner_name || "Contact PawFriend"}</strong>
                      </div>
                      <div className="similarity-bar">
                        <div className="bar-label">
                          Match Confidence:{" "}
                          {(candidate.similarity_score * 100).toFixed(1)}%
                        </div>
                        <div className="bar-track">
                          <div
                            className="bar-fill"
                            style={{
                              width: `${candidate.similarity_score * 100}%`,
                            }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
            </div>

            <div className="text-center mt-3">
              <button className="btn btn-primary btn-lg" onClick={reset}>
                🔍 Scan Another Dog
              </button>
            </div>
          </div>
        )}

        {/* No Match */}
        {state === "no-match" && (
          <div className="glass-card no-match-card animate-slide-up text-center">
            <div className="no-match-icon">🔎</div>
            <h2>No Match Found</h2>
            <p>
              This dog doesn't appear to be registered in our database yet.
            </p>
            <div className="no-match-actions">
              <button className="btn btn-primary" onClick={reset}>
                🔍 Try Again
              </button>
              <a href="/register" className="btn btn-secondary">
                📝 Register This Dog
              </a>
            </div>
          </div>
        )}

        {/* Error */}
        {state === "error" && error && (
          <div className="glass-card error-card animate-fade-in">
            <div className="text-center">
              <div className="error-icon-lg">⚠️</div>
              <h3>{error.message}</h3>
            </div>
            {error.issues.length > 0 && (
              <ul className="error-issues">
                {error.issues.map((issue, i) => (
                  <li key={i}>{issue}</li>
                ))}
              </ul>
            )}
            {error.suggestions.length > 0 && (
              <div className="error-suggestions">
                <h4>💡 Tips:</h4>
                <ul>
                  {error.suggestions.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="text-center mt-2">
              <button className="btn btn-primary" onClick={reset}>
                Try Again
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
