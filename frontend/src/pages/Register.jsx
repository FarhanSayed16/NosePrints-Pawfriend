import { useState } from "react";
import CameraCapture from "../components/CameraCapture";
import { createOwner, createDog, uploadNosePrint } from "../services/api";
import "./Register.css";

export default function Register() {
  const [step, setStep] = useState(1); // 1: owner info, 2: dog info, 3: nose scan, 4: done
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Owner data
  const [owner, setOwner] = useState({ name: "", phone: "", email: "", address: "" });
  // Dog data
  const [dog, setDog] = useState({ name: "", breed: "", color: "", sex: "", microchip_id: "" });
  // Created IDs
  const [createdOwner, setCreatedOwner] = useState(null);
  const [createdDog, setCreatedDog] = useState(null);
  const [uploadedPrints, setUploadedPrints] = useState(0);

  const handleOwnerSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await createOwner(owner);
      setCreatedOwner(res.data);
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to register owner");
    } finally {
      setLoading(false);
    }
  };

  const handleDogSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await createDog({
        ...dog,
        owner_id: createdOwner.id,
        status: "registered",
      });
      setCreatedDog(res.data);
      setStep(3);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to register dog");
    } finally {
      setLoading(false);
    }
  };

  const handleNoseCapture = async (blobs) => {
    setLoading(true);
    setError(null);
    const images = Array.isArray(blobs) ? blobs : [blobs];

    let successCount = 0;
    for (const blob of images) {
      try {
        await uploadNosePrint(createdDog.id, blob);
        successCount++;
        setUploadedPrints(successCount);
      } catch (err) {
        const detail = err.response?.data?.detail;
        const issues = typeof detail === "object" ? detail.issues?.join(", ") : detail;
        console.error("Upload failed:", issues);
      }
    }

    if (successCount > 0) {
      setStep(4);
    } else {
      setError("All photos failed quality check. Please try again with better lighting.");
    }
    setLoading(false);
  };

  return (
    <div className="page register-page">
      <div className="container">
        <div className="page-header">
          <h1>
            Register Your <span className="text-gradient">Dog</span>
          </h1>
          <p>Create a digital nose-print ID — your dog's unique fingerprint</p>
        </div>

        {/* Progress Steps */}
        <div className="progress-steps">
          {[
            { num: 1, label: "Owner Info" },
            { num: 2, label: "Dog Details" },
            { num: 3, label: "Nose Scan" },
            { num: 4, label: "Done!" },
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
            <span>⚠️</span> {error}
          </div>
        )}

        {/* Step 1: Owner Info */}
        {step === 1 && (
          <form onSubmit={handleOwnerSubmit} className="register-form glass-card animate-fade-in">
            <h3>👤 Owner Information</h3>
            <p className="form-note">
              Your data is protected under India's DPDP Act 2023. We only use it
              to reunite you with your pet.
            </p>
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label">Full Name *</label>
                <input
                  className="form-input"
                  type="text"
                  required
                  value={owner.name}
                  onChange={(e) => setOwner({ ...owner, name: e.target.value })}
                  placeholder="Enter your full name"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Phone Number *</label>
                <input
                  className="form-input"
                  type="tel"
                  required
                  value={owner.phone}
                  onChange={(e) => setOwner({ ...owner, phone: e.target.value })}
                  placeholder="+91 XXXXXXXXXX"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input
                  className="form-input"
                  type="email"
                  value={owner.email}
                  onChange={(e) => setOwner({ ...owner, email: e.target.value })}
                  placeholder="your@email.com"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Address</label>
                <input
                  className="form-input"
                  type="text"
                  value={owner.address}
                  onChange={(e) => setOwner({ ...owner, address: e.target.value })}
                  placeholder="City, State"
                />
              </div>
            </div>
            <button className="btn btn-primary btn-lg" type="submit" disabled={loading}>
              {loading ? "Registering..." : "Next → Dog Details"}
            </button>
          </form>
        )}

        {/* Step 2: Dog Info */}
        {step === 2 && (
          <form onSubmit={handleDogSubmit} className="register-form glass-card animate-fade-in">
            <h3>🐕 Dog Information</h3>
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label">Dog's Name</label>
                <input
                  className="form-input"
                  type="text"
                  value={dog.name}
                  onChange={(e) => setDog({ ...dog, name: e.target.value })}
                  placeholder="Buddy, Luna, Max..."
                />
              </div>
              <div className="form-group">
                <label className="form-label">Breed</label>
                <input
                  className="form-input"
                  type="text"
                  value={dog.breed}
                  onChange={(e) => setDog({ ...dog, breed: e.target.value })}
                  placeholder="Indian Pariah, Labrador, mixed..."
                />
              </div>
              <div className="form-group">
                <label className="form-label">Color</label>
                <input
                  className="form-input"
                  type="text"
                  value={dog.color}
                  onChange={(e) => setDog({ ...dog, color: e.target.value })}
                  placeholder="Brown, Black, Golden..."
                />
              </div>
              <div className="form-group">
                <label className="form-label">Sex</label>
                <select
                  className="form-select"
                  value={dog.sex}
                  onChange={(e) => setDog({ ...dog, sex: e.target.value })}
                >
                  <option value="">Select</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Microchip ID (optional)</label>
                <input
                  className="form-input"
                  type="text"
                  value={dog.microchip_id}
                  onChange={(e) => setDog({ ...dog, microchip_id: e.target.value })}
                  placeholder="If available"
                />
              </div>
            </div>
            <div className="form-actions">
              <button className="btn btn-outline" type="button" onClick={() => setStep(1)}>
                ← Back
              </button>
              <button className="btn btn-primary btn-lg" type="submit" disabled={loading}>
                {loading ? "Saving..." : "Next → Nose Scan"}
              </button>
            </div>
          </form>
        )}

        {/* Step 3: Nose Scan */}
        {step === 3 && (
          <div className="nose-scan-section animate-fade-in">
            <div className="glass-card scan-instructions">
              <h3>📸 Scan {dog.name || "the dog"}'s Nose</h3>
              <ul className="instruction-list">
                <li>Hold your phone close to the nose (15-30 cm)</li>
                <li>Ensure good lighting — avoid shadows</li>
                <li>The nose should fill most of the frame</li>
                <li>Take 3-5 photos from slightly different angles</li>
                <li>Hold steady — avoid blur!</li>
              </ul>
            </div>
            <CameraCapture onCapture={handleNoseCapture} mode="multi" />
            {loading && (
              <div className="upload-progress glass-card">
                <div className="progress-spinner"></div>
                <p>Uploading and processing... ({uploadedPrints} done)</p>
              </div>
            )}
          </div>
        )}

        {/* Step 4: Success */}
        {step === 4 && (
          <div className="success-section glass-card animate-slide-up text-center">
            <div className="success-icon">🎉</div>
            <h2>Registration Complete!</h2>
            <p className="success-message">
              <strong>{dog.name || "Your dog"}</strong> now has a digital nose-print ID.
              <br />
              {uploadedPrints} nose print{uploadedPrints !== 1 ? "s" : ""} registered successfully.
            </p>
            <div className="success-info glass-card">
              <div className="info-row">
                <span>🐕 Dog:</span> <strong>{dog.name || "N/A"}</strong>
              </div>
              <div className="info-row">
                <span>🏷️ Breed:</span> <strong>{dog.breed || "N/A"}</strong>
              </div>
              <div className="info-row">
                <span>👤 Owner:</span> <strong>{owner.name}</strong>
              </div>
              <div className="info-row">
                <span>📸 Nose Prints:</span> <strong>{uploadedPrints}</strong>
              </div>
            </div>
            <div className="success-actions">
              <button
                className="btn btn-primary btn-lg"
                onClick={() => {
                  setStep(1);
                  setOwner({ name: "", phone: "", email: "", address: "" });
                  setDog({ name: "", breed: "", color: "", sex: "", microchip_id: "" });
                  setCreatedOwner(null);
                  setCreatedDog(null);
                  setUploadedPrints(0);
                }}
              >
                📝 Register Another Dog
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
