import { Link } from "react-router-dom";
import Icon from "../components/Icon";
import "./Home.css";

export default function Home() {
  return (
    <div className="page home-page">
      {/* Hero Section */}
      <section className="hero">
        <div className="container">
          <div className="hero-content animate-slide-up">
            <div className="hero-badge">
              <Icon name="fingerprint" size={14} />
              Powered by AI Biometrics
            </div>
            <h1>
              Every Dog Has a Unique{" "}
              <span className="text-gradient">NosePrint</span>
            </h1>
            <p className="hero-subtitle">
              Like human fingerprints, every dog's nose print is unique for life.
              We use AI-powered nose-print recognition to help reunite lost dogs
              with their families — a free phone-camera complement to microchips.
            </p>
            <div className="hero-actions">
              <Link to="/register" className="btn btn-primary btn-lg">
                <Icon name="register" size={18} />
                Register Your Dog
              </Link>
              <Link to="/identify" className="btn btn-secondary btn-lg">
                <Icon name="scan" size={18} />
                Identify a Dog
              </Link>
            </div>
            <div className="hero-trust-strip">
              <div className="trust-chip">
                <Icon name="shield" size={14} /> Staff-verified matches
              </div>
              <div className="trust-chip">
                <Icon name="phone" size={14} /> No app install needed
              </div>
              <div className="trust-chip">
                <Icon name="heart" size={14} /> 100% free
              </div>
            </div>
          </div>

          <div className="hero-visual animate-fade-in">
            <img src="/hero-dog.jpg" alt="Dog with AI nose-print scan" className="hero-image" />
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="how-it-works">
        <div className="container">
          <div className="section-header">
            <span className="section-label">Simple Process</span>
            <h2>
              How It <span className="text-gradient">Works</span>
            </h2>
            <p>Three simple steps to create or match a digital nose-print ID</p>
          </div>
          <div className="steps-grid stagger-children">
            <div className="step-card glass-card">
              <div className="step-number">1</div>
              <div className="step-icon-wrap">
                <Icon name="camera" size={28} />
              </div>
              <h3>Scan</h3>
              <p>
                Open the camera and scan the dog's nose — no special equipment
                needed, just your phone.
              </p>
            </div>
            <div className="step-card glass-card">
              <div className="step-number">2</div>
              <div className="step-icon-wrap">
                <Icon name="cpu" size={28} />
              </div>
              <h3>AI Match</h3>
              <p>
                Our AI extracts a unique 512-point digital fingerprint from the
                nose pattern and searches the database in under 3 seconds.
              </p>
            </div>
            <div className="step-card glass-card">
              <div className="step-number">3</div>
              <div className="step-icon-wrap">
                <Icon name="heartPaw" size={28} />
              </div>
              <h3>Reunite</h3>
              <p>
                If a match is found, PawFriend staff verify and connect you with
                the dog's owner — bringing families back together.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Stats / Trust Indicators */}
      <section className="trust-section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">Why NosePrints</span>
            <h2>
              Built on <span className="text-gradient">Trust</span>
            </h2>
          </div>
          <div className="trust-grid">
            <div className="trust-card glass-card">
              <div className="trust-icon-wrap">
                <Icon name="staff" size={24} />
              </div>
              <div className="trust-value">Staff</div>
              <div className="trust-label">Always Confirms</div>
              <p>A PawFriend volunteer reviews every match before contact is shared</p>
            </div>
            <div className="trust-card glass-card">
              <div className="trust-icon-wrap">
                <Icon name="fingerprint" size={24} />
              </div>
              <div className="trust-value">512</div>
              <div className="trust-label">Data Points</div>
              <p>Each nose print encoded as a unique 512-dimension vector</p>
            </div>
            <div className="trust-card glass-card">
              <div className="trust-icon-wrap">
                <Icon name="phone" size={24} />
              </div>
              <div className="trust-value">0s</div>
              <div className="trust-label">App Install</div>
              <p>Works directly in your browser — no download required</p>
            </div>
            <div className="trust-card glass-card">
              <div className="trust-icon-wrap">
                <Icon name="heart" size={24} />
              </div>
              <div className="trust-value">Lifetime</div>
              <div className="trust-label">ID</div>
              <p>A dog's nose print is stable from 2 months of age for life</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta-section">
        <div className="container text-center">
          <div className="cta-card">
            <Icon name="search" size={32} className="cta-icon" />
            <h2>Found a Stray Dog?</h2>
            <p>
              Scan their nose — it takes about 10 seconds. If there is a likely
              match, PawFriend staff review it before any owner contact is shared.
            </p>
            <Link to="/identify" className="btn btn-lg mt-2 cta-btn">
              <Icon name="scan" size={18} />
              Identify Now — It's Free
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
