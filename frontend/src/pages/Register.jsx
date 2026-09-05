import { useState } from "react";
import AppearancePhoto from "../components/AppearancePhoto";
import PhotoIntake from "../components/PhotoIntake";
import Icon from "../components/Icon";
import { formatApiError, registerOwnerAndDog, uploadNosePrint, uploadProfilePhoto } from "../services/api";
import { formatCaptureError } from "../utils/imageFile";
import "./Register.css";

export default function Register() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [owner, setOwner] = useState({ name: "", phone: "", email: "", address: "" });
  const [consent, setConsent] = useState(false);
  const [dog, setDog] = useState({ name: "", breed: "", color: "", sex: "", microchip_id: "" });
  const [createdOwner, setCreatedOwner] = useState(null);
  const [createdDog, setCreatedDog] = useState(null);
  const [uploadedPrints, setUploadedPrints] = useState(0);
  const [uploadTotal, setUploadTotal] = useState(0);
  const [uploadPhase, setUploadPhase] = useState("");
  const [appearanceFile, setAppearanceFile] = useState(null);
  const [lookForce, setLookForce] = useState(false);

  const handleOwnerSubmit = (e) => {
    e.preventDefault();
    setError(null);
    if (!consent) {
      setError("Please confirm consent before continuing.");
      return;
    }
    setStep(2);
  };

  const handleDogSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!dog.breed.trim() || !dog.color.trim()) {
      setError("Enter breed and color, or tap Unknown for each.");
      return;
    }
    setLoading(true);
    try {
      const res = await registerOwnerAndDog({
        owner: { ...owner, consent: true },
        dog: { ...dog, status: "registered" },
      });
      setCreatedOwner(res.data.owner);
      setCreatedDog(res.data.dog);
      setStep(3);
    } catch (err) {
      setError(formatApiError(err, "Failed to register"));
    } finally {
      setLoading(false);
    }
  };

  const handleNoseCapture = async (blobs, meta = {}) => {
    setLoading(true);
    setError(null);
    const images = Array.isArray(blobs) ? blobs : [blobs];
    const preCropped = Boolean(meta.preCropped);
    setUploadTotal(images.length);
    setUploadedPrints(0);

    let successCount = 0;
    const failures = [];
    for (let i = 0; i < images.length; i++) {
      setUploadPhase(`Checking nose print ${i + 1} of ${images.length}…`);
      try {
        await uploadNosePrint(createdDog.id, images[i], { preCropped });
        successCount++;
        setUploadedPrints(successCount);
      } catch (err) {
        failures.push(formatCaptureError(err, "This photo did not pass the quality check"));
        console.error("Upload failed:", err);
      }
    }

    setUploadPhase("");
    if (successCount >= 3) {
      setStep(5);
    } else if (successCount > 0) {
      setError(
        `Only ${successCount} of ${images.length} nose prints saved. Need at least 3 good crops — retake the failed ones.`
      );
    } else {
      setError(failures[0] || "None of the photos could be saved. Try a closer, sharper nose crop.");
    }
    setLoading(false);
  };

  return (
    <div className="page register-page">
      <div className="page-header">
        <h1>
          Register Your <span className="text-gradient">Dog</span>
        </h1>
        <p>Create a digital nose-print ID — your dog's unique fingerprint</p>
      </div>

      <div className="container">
        {/* Progress Steps */}
        <div className="progress-steps">
          {[
            { num: 1, label: "Owner" },
            { num: 2, label: "Dog" },
            { num: 3, label: "Look" },
            { num: 4, label: "Nose" },
            { num: 5, label: "Done" },
          ].map((s) => (
            <div
              key={s.num}
              className={`progress-step ${step >= s.num ? "active" : ""} ${
                step === s.num ? "current" : ""
              }`}
            >
              <div className="step-dot">{step > s.num ? "✓" : s.num}</div>
              <span className="step-label">{s.label}</span>
            </div>
          ))}
        </div>

        {error && (
          <div className="error-banner glass-card">
            <Icon name="alertCircle" size={18} /> {error}
          </div>
        )}

        {/* Step 1: Owner Info */}
        {step === 1 && (
          <form onSubmit={handleOwnerSubmit} className="register-form glass-card animate-fade-in">
            <h3><Icon name="user" size={20} style={{ marginRight: '0.4rem' }} /> Owner Information</h3>
            <p className="form-note">
              Your data is protected under India's DPDP Act 2023. We only use it
              to reunite you with your pet. Owner contact is never shown on
              public Identify results.
            </p>
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label">Full Name *</label>
                <input className="form-input" type="text" required value={owner.name} onChange={(e) => setOwner({ ...owner, name: e.target.value })} placeholder="Enter your full name" />
              </div>
              <div className="form-group">
                <label className="form-label">Phone Number *</label>
                <input className="form-input" type="tel" required value={owner.phone} onChange={(e) => setOwner({ ...owner, phone: e.target.value })} placeholder="+91 XXXXXXXXXX" />
              </div>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input className="form-input" type="email" value={owner.email} onChange={(e) => setOwner({ ...owner, email: e.target.value })} placeholder="your@email.com" />
              </div>
              <div className="form-group">
                <label className="form-label">Address</label>
                <input className="form-input" type="text" value={owner.address} onChange={(e) => setOwner({ ...owner, address: e.target.value })} placeholder="City, State" />
              </div>
            </div>
            <label className="consent-box">
              <input type="checkbox" required checked={consent} onChange={(e) => setConsent(e.target.checked)} />
              <span>
                I agree that PawFriend may store my contact details and this
                dog's nose photos to help reunite us if the dog is found. I
                understand I can ask for this data to be deleted.
              </span>
            </label>
            <button className="btn btn-primary btn-lg" type="submit" disabled={loading}>
              {loading ? "Registering..." : "Next → Dog Details"}
            </button>
          </form>
        )}

        {/* Step 2: Dog Info */}
        {step === 2 && (
          <form onSubmit={handleDogSubmit} className="register-form glass-card animate-fade-in">
            <h3><Icon name="dog" size={20} style={{ marginRight: '0.4rem' }} /> Dog Information</h3>
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label">Dog's Name</label>
                <input className="form-input" type="text" value={dog.name} onChange={(e) => setDog({ ...dog, name: e.target.value })} placeholder="Buddy, Luna, Max..." />
              </div>
              <div className="form-group">
                <label className="form-label">Breed *</label>
                <input className="form-input" type="text" value={dog.breed} onChange={(e) => setDog({ ...dog, breed: e.target.value })} placeholder="Indian Pariah, Labrador, mixed..." />
                <button
                  type="button"
                  className={`chip-unknown ${dog.breed === "Unknown" ? "active" : ""}`}
                  onClick={() => setDog({ ...dog, breed: "Unknown" })}
                >
                  Unknown
                </button>
              </div>
              <div className="form-group">
                <label className="form-label">Color *</label>
                <input className="form-input" type="text" value={dog.color} onChange={(e) => setDog({ ...dog, color: e.target.value })} placeholder="Brown, Black, Golden..." />
                <button
                  type="button"
                  className={`chip-unknown ${dog.color === "Unknown" ? "active" : ""}`}
                  onClick={() => setDog({ ...dog, color: "Unknown" })}
                >
                  Unknown
                </button>
              </div>
              <div className="form-group">
                <label className="form-label">Sex</label>
                <select className="form-select" value={dog.sex} onChange={(e) => setDog({ ...dog, sex: e.target.value })}>
                  <option value="">Select</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Microchip ID (optional)</label>
                <input className="form-input" type="text" value={dog.microchip_id} onChange={(e) => setDog({ ...dog, microchip_id: e.target.value })} placeholder="If available" />
              </div>
            </div>
            <div className="form-actions">
              <button className="btn btn-outline" type="button" onClick={() => setStep(1)}>
                <Icon name="arrowLeft" size={16} /> Back
              </button>
              <button className="btn btn-primary btn-lg" type="submit" disabled={loading}>
                {loading ? "Saving..." : "Next → Full photo"}
              </button>
            </div>
          </form>
        )}

        {/* Step 3: Full dog photo */}
        {step === 3 && (
          <div className="nose-scan-section animate-fade-in">
            {loading && (
              <div className="upload-progress glass-card">
                <div className="progress-spinner"></div>
                <p className="upload-progress-title">Saving dog photo…</p>
              </div>
            )}
            {!loading && (
              <>
            <AppearancePhoto
              title="Full dog photo"
              help="A body or face photo helps staff confirm the dog later. This is not the nose print — that comes next. Use Take photo or Choose from gallery."
              softGate
              readyLabel="Photo ready — will be saved with this dog"
              onFile={(file, meta = {}) => {
                setAppearanceFile(file);
                setLookForce(Boolean(meta.force));
              }}
            />
            <div className="form-actions" style={{ marginTop: "1rem" }}>
              <button className="btn btn-outline" type="button" onClick={() => setStep(2)}>
                <Icon name="arrowLeft" size={16} /> Back
              </button>
              <button
                className="btn btn-outline"
                type="button"
                onClick={() => {
                  setAppearanceFile(null);
                  setLookForce(false);
                  setStep(4);
                }}
              >
                Skip for now
              </button>
              <button
                className="btn btn-primary btn-lg"
                type="button"
                disabled={loading}
                onClick={async () => {
                  if (!appearanceFile) {
                    setStep(4);
                    return;
                  }
                  setLoading(true);
                  setError(null);
                  try {
                    await uploadProfilePhoto(createdDog.id, appearanceFile, { force: lookForce });
                    setStep(4);
                  } catch (err) {
                    const detail = err.response?.data?.detail;
                    if (detail?.soft_warn) {
                      setError("Confirm the look photo with Use anyway above, then tap Next.");
                    } else {
                      setError(formatApiError(err, "Could not save the dog photo"));
                    }
                  } finally {
                    setLoading(false);
                  }
                }}
              >
                Next → Nose print
              </button>
            </div>
              </>
            )}
          </div>
        )}

        {/* Step 4: Nose Scan */}
        {step === 4 && (
          <div className="nose-scan-section animate-fade-in">
            <div className="glass-card scan-instructions">
              <h3><Icon name="camera" size={20} style={{ marginRight: '0.4rem' }} /> Scan {dog.name || "the dog"}'s Nose</h3>
              <ul className="instruction-list">
                <li>Camera for a live close-up, or Gallery to pick a photo and crop the nose</li>
                <li>Fit the box to the black nose leather — not the eyes or whole head</li>
                <li>Hold 15–30 cm from the nose; a far-away body photo will be too blurry</li>
                <li>Save 3–5 crops from slightly different angles</li>
              </ul>
            </div>
            <PhotoIntake onCapture={handleNoseCapture} mode="multi" />
            <div className="form-actions" style={{ marginTop: "1rem" }}>
              <button className="btn btn-outline" type="button" onClick={() => setStep(3)}>
                <Icon name="arrowLeft" size={16} /> Back
              </button>
            </div>
            {loading && (
              <div className="upload-progress glass-card">
                <div className="progress-spinner"></div>
                <p className="upload-progress-title">
                  {uploadPhase || "Uploading nose prints…"}
                </p>
                <p className="upload-progress-count">
                  {uploadedPrints} of {uploadTotal} saved
                </p>
                <div className="upload-progress-bar">
                  <div
                    className="upload-progress-fill"
                    style={{ width: `${uploadTotal ? (uploadedPrints / uploadTotal) * 100 : 0}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 5: Success */}
        {step === 5 && (
          <div className="success-section glass-card animate-slide-up text-center">
            <div className="success-icon">
              <Icon name="check" size={32} />
            </div>
            <h2>Registration Complete!</h2>
            <p className="success-message">
              <strong>{dog.name || "Your dog"}</strong> now has a digital nose-print ID.
              <br />
              {uploadedPrints} nose print{uploadedPrints !== 1 ? "s" : ""} registered successfully.
            </p>
            <div className="success-info glass-card">
              <div className="info-row"><span>Dog:</span> <strong>{dog.name || "N/A"}</strong></div>
              <div className="info-row"><span>Breed:</span> <strong>{dog.breed || "Unknown"}</strong></div>
              <div className="info-row"><span>Color:</span> <strong>{dog.color || "Unknown"}</strong></div>
              <div className="info-row"><span>Owner:</span> <strong>{owner.name}</strong></div>
              <div className="info-row"><span>Nose Prints:</span> <strong>{uploadedPrints}</strong></div>
            </div>
            <div className="success-actions">
              <button className="btn btn-primary btn-lg" onClick={() => {
                setStep(1);
                setOwner({ name: "", phone: "", email: "", address: "" });
                setConsent(false);
                setDog({ name: "", breed: "", color: "", sex: "", microchip_id: "" });
                setCreatedOwner(null);
                setCreatedDog(null);
                setUploadedPrints(0);
                setAppearanceFile(null);
                setLookForce(false);
              }}>
                <Icon name="register" size={18} /> Register Another Dog
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
