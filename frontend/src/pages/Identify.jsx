import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppearancePhoto from "../components/AppearancePhoto";
import PhotoIntake from "../components/PhotoIntake";
import Icon from "../components/Icon";
import { formatApiError, identifyDog, mediaUrl } from "../services/api";
import { formatCaptureError } from "../utils/imageFile";
import "./Identify.css";

function appearanceLabel(hint) {
  if (hint === "supports") return "Coat/body photo supports this candidate";
  if (hint === "conflicts") return "Coat/body photo looks different — extra staff caution";
  if (hint === "unclear") return "Coat/body photo is inconclusive";
  return "No full-dog photo to compare";
}

export default function Identify() {
  const [state, setState] = useState("ready");
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [queryPreview, setQueryPreview] = useState(null);
  const [noseBlob, setNoseBlob] = useState(null);
  const [appearanceFile, setAppearanceFile] = useState(null);
  const [appearancePreview, setAppearancePreview] = useState(null);
  const [appearanceBusy, setAppearanceBusy] = useState(false);
  const [nosePreCropped, setNosePreCropped] = useState(false);

  useEffect(() => {
    return () => {
      if (queryPreview) URL.revokeObjectURL(queryPreview);
    };
  }, [queryPreview]);

  const handleNose = (blob, meta = {}) => {
    const file = blob instanceof Blob ? blob : blob?.[0];
    if (!file) return;
    if (queryPreview) URL.revokeObjectURL(queryPreview);
    setNoseBlob(file);
    setNosePreCropped(Boolean(meta.preCropped));
    setQueryPreview(URL.createObjectURL(file));
    setState("have-nose");
  };

  const runIdentify = async () => {
    if (!noseBlob) return;
    setState("loading");
    setError(null);
    try {
      const res = await identifyDog(noseBlob, appearanceFile, { preCropped: nosePreCropped });
      setResults(res.data);
      if (res.data.match_found && res.data.candidates.length > 0) {
        setState("results");
      } else {
        setState("no-match");
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === "object" && detail !== null && !Array.isArray(detail)) {
        setError({ message: detail.message || "Identification failed", issues: detail.issues || [], suggestions: detail.suggestions || [] });
      } else {
        setError({ message: formatCaptureError(err, "Something went wrong. Please try again."), issues: [], suggestions: [] });
      }
      setState("error");
    }
  };

  const reset = () => {
    if (queryPreview) URL.revokeObjectURL(queryPreview);
    setQueryPreview(null);
    setNoseBlob(null);
    setNosePreCropped(false);
    if (appearancePreview) URL.revokeObjectURL(appearancePreview);
    setAppearancePreview(null);
    setAppearanceFile(null);
    setState("ready");
    setResults(null);
    setError(null);
  };

  const querySrc = queryPreview || mediaUrl(results?.query_image_url);
  const appearanceSrc =
    (results?.query_appearance_url && mediaUrl(results.query_appearance_url)) ||
    appearancePreview ||
    null;

  return (
    <div className="page identify-page">
      <div className="page-header">
        <h1>
          Identify a <span className="text-gradient">Dog</span>
        </h1>
        <p>Found a stray? Scan or upload the nose — we'll check if they're registered in under 3 seconds.</p>
      </div>

      <div className="container">
        {state === "ready" && (
          <div className="animate-fade-in">
            <div className="glass-card identify-info">
              <h3><Icon name="phone" size={20} /> How to capture</h3>
              <div className="scan-tips">
                <div className="tip">
                  <span className="tip-icon"><Icon name="camera" size={16} /></span>
                  <span>Open camera, frame the nose, then tap the shutter (no auto-capture)</span>
                </div>
                <div className="tip">
                  <span className="tip-icon"><Icon name="sun" size={16} /></span>
                  <span>Good lighting, no shadows</span>
                </div>
                <div className="tip">
                  <span className="tip-icon"><Icon name="target" size={16} /></span>
                  <span>Nose in the crop box, with a bit of muzzle showing</span>
                </div>
                <div className="tip">
                  <span className="tip-icon"><Icon name="dog" size={16} /></span>
                  <span>A full-dog photo after this helps staff confirm</span>
                </div>
              </div>
            </div>
            <PhotoIntake onCapture={handleNose} mode="single" />
          </div>
        )}

        {state === "have-nose" && (
          <div className="animate-fade-in">
            <div className="glass-card">
              <h3>Nose crop ready</h3>
              {queryPreview && <img className="nose-ready-preview" src={queryPreview} alt="Nose crop" />}
              <p className="match-note">Optional: add a full body or face photo. Staff use it with the nose print. It is not a second biometric.</p>
            </div>
            <AppearancePhoto
              help="Same dog, whole body or face — colour and markings. Wait for “Photo ready” before searching."
              onFile={setAppearanceFile}
              onPreview={setAppearancePreview}
              onBusyChange={setAppearanceBusy}
            />
            <div className="no-match-actions">
              <button className="btn btn-outline" type="button" onClick={reset} disabled={appearanceBusy}>
                Retake nose
              </button>
              <button
                className="btn btn-primary btn-lg"
                type="button"
                onClick={runIdentify}
                disabled={appearanceBusy}
              >
                <Icon name="scan" size={18} />{" "}
                {appearanceFile ? "Search with full photo" : "Search registry"}
              </button>
            </div>
          </div>
        )}

        {state === "loading" && (
          <div className="glass-card loading-card animate-fade-in text-center">
            <div className="scan-animation">
              <div className="scan-ring"></div>
              <div className="scan-ring delay-1"></div>
              <div className="scan-ring delay-2"></div>
              <span className="scan-emoji"><Icon name="scan" size={28} /></span>
            </div>
            <h3>Analyzing Nose Print...</h3>
            <p>
              Detecting nose → Checking quality → Searching database
              {appearanceFile ? " → Saving full-dog photo" : ""}
            </p>
          </div>
        )}

        {state === "results" && results && (
          <div className="results-section animate-slide-up">
            <div className="glass-card match-banner">
              <div className="match-icon"><Icon name="check" size={24} /></div>
              <h2>{results.confidence_band === "likely" ? "Likely match" : "Possible match"}</h2>
              <p>Nose similarity: <strong>{(results.top_score * 100).toFixed(1)}%</strong>{results.confidence_band === "possible" ? " — extra staff caution" : ""}</p>
              <p className="match-note">A PawFriend staff member will review the nose print and the full photos before any contact is shared.</p>
            </div>
            <div className="candidates-list">
              {results.candidates.map((candidate, idx) => (
                <div key={candidate.dog_id || idx} className="candidate-card glass-card">
                  <div className="candidate-header">
                    <span className="candidate-rank">#{idx + 1}</span>
                    <span className={`badge badge-${candidate.status}`}>{candidate.status}</span>
                  </div>
                  <div className="compare-grid">
                    <figure className="compare-shot">
                      {querySrc ? <img src={querySrc} alt="Scanned nose" /> : <div className="compare-placeholder">No scan preview</div>}
                      <figcaption>This nose</figcaption>
                    </figure>
                    <figure className="compare-shot">
                      {candidate.matched_image_url ? (
                        <img src={mediaUrl(candidate.matched_image_url)} alt="Registered nose" />
                      ) : (
                        <div className="compare-placeholder">No stored nose</div>
                      )}
                      <figcaption>Registered nose</figcaption>
                    </figure>
                    <figure className="compare-shot">
                      {appearanceSrc ? <img src={appearanceSrc} alt="Found dog" /> : <div className="compare-placeholder">No full photo</div>}
                      <figcaption>This dog (full)</figcaption>
                    </figure>
                    <figure className="compare-shot">
                      {candidate.profile_photo_url ? (
                        <img src={mediaUrl(candidate.profile_photo_url)} alt={candidate.dog_name || "Registered dog"} />
                      ) : (
                        <div className="compare-placeholder">No registered full photo</div>
                      )}
                      <figcaption>{candidate.dog_name || "Registered look"}</figcaption>
                    </figure>
                  </div>
                  <div className="candidate-details">
                    <h3>{candidate.dog_name || "Unknown"}</h3>
                    <div className="detail-row"><span>Breed:</span> <strong>{candidate.breed || "N/A"}</strong></div>
                    <div className="detail-row"><span>Color:</span> <strong>{candidate.color || "N/A"}</strong></div>
                    <div className="detail-row"><span>Look check:</span> <strong>{appearanceLabel(candidate.appearance_hint)}</strong></div>
                    <div className="detail-row"><span>Owner contact:</span> <strong>Held by PawFriend staff until they confirm this match</strong></div>
                    <div className="similarity-bar">
                      <div className="bar-label">Nose match: {(candidate.similarity_score * 100).toFixed(1)}%</div>
                      <div className="bar-track"><div className="bar-fill" style={{ width: `${candidate.similarity_score * 100}%` }}></div></div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="text-center mt-3">
              <button className="btn btn-primary btn-lg" onClick={reset}><Icon name="scan" size={18} /> Scan Another Dog</button>
            </div>
          </div>
        )}

        {state === "no-match" && (
          <div className="glass-card no-match-card animate-slide-up text-center">
            <div className="no-match-icon"><Icon name="searchEmpty" size={32} /></div>
            <h2>No Match Found</h2>
            <p>This dog doesn't appear to be registered yet. You can list them as found so PawFriend staff can follow up.</p>
            <div className="no-match-actions">
              <button className="btn btn-primary" onClick={reset}><Icon name="scan" size={16} /> Try Again</button>
              <Link to="/found" state={{ queryImageUrl: results?.query_image_url }} className="btn btn-secondary"><Icon name="clipboard" size={16} /> List as found</Link>
            </div>
          </div>
        )}

        {state === "error" && error && (
          <div className="glass-card error-card animate-fade-in">
            <div className="text-center">
              <div className="error-icon-lg"><Icon name="alertCircle" size={28} /></div>
              <h3>{error.message}</h3>
            </div>
            {error.issues.length > 0 && <ul className="error-issues">{error.issues.map((issue, i) => <li key={i}>{issue}</li>)}</ul>}
            {error.suggestions.length > 0 && (
              <div className="error-suggestions">
                <h4>Tips:</h4>
                <ul>{error.suggestions.map((s, i) => <li key={i}>{s}</li>)}</ul>
              </div>
            )}
            <div className="text-center mt-2"><button className="btn btn-primary" onClick={reset}>Try Again</button></div>
          </div>
        )}
      </div>
    </div>
  );
}
