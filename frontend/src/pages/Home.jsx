import { Link } from "react-router-dom";
import "./Home.css";

export default function Home() {
  return (
    <div className="page home-page">
      {/* Hero Section */}
      <section className="hero">
        <div className="container">
          <div className="hero-content animate-slide-up">
            <div className="hero-badge">🐾 Powered by AI Biometrics</div>
            <h1>
              Every Dog Has a Unique{" "}
              <span className="text-gradient">NosePrint</span>
            </h1>
            <p className="hero-subtitle">
              Like human fingerprints, every dog's nose print is unique for life.
              We use AI-powered nose-print recognition to help reunite lost dogs
              with their families — no microchip needed, just a smartphone.
            </p>
            <div className="hero-actions">
              <Link to="/register" className="btn btn-primary btn-lg">
                📝 Register Your Dog
              </Link>
              <Link to="/identify" className="btn btn-secondary btn-lg">
                🔍 Identify a Dog
              </Link>
            </div>
          </div>

          <div className="hero-visual animate-fade-in">
            <div className="hero-glow"></div>
            <div className="hero-nose-icon">🐕</div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="how-it-works">
        <div className="container">
          <h2 className="text-center mb-3">
            How It <span className="text-gradient">Works</span>
          </h2>
          <div className="steps-grid stagger-children">
            <div className="step-card glass-card">
              <div className="step-number">1</div>
              <div className="step-icon">📱</div>
              <h3>Scan</h3>
              <p>
                Open the camera and scan the dog's nose — no special equipment
                needed, just your phone.
              </p>
            </div>
            <div className="step-card glass-card">
              <div className="step-number">2</div>
              <div className="step-icon">🧠</div>
              <h3>AI Match</h3>
              <p>
                Our AI extracts a unique 512-point digital fingerprint from the
                nose pattern and searches the database in under 3 seconds.
              </p>
            </div>
            <div className="step-card glass-card">
              <div className="step-number">3</div>
              <div className="step-icon">🎉</div>
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
          <div className="trust-grid">
            <div className="trust-card glass-card">
              <div className="trust-value text-gradient">98%+</div>
              <div className="trust-label">Lab Accuracy</div>
              <p>Peer-reviewed research validates nose-print biometrics</p>
            </div>
            <div className="trust-card glass-card">
              <div className="trust-value text-gradient">512</div>
              <div className="trust-label">Data Points</div>
              <p>Each nose print encoded as a unique 512-dimension vector</p>
            </div>
            <div className="trust-card glass-card">
              <div className="trust-value text-gradient">0s</div>
              <div className="trust-label">App Install</div>
              <p>Works directly in your browser — no download required</p>
            </div>
            <div className="trust-card glass-card">
              <div className="trust-value text-gradient">♾️</div>
              <div className="trust-label">Lifetime ID</div>
              <p>A dog's nose print is stable from 2 months of age for life</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta-section">
        <div className="container text-center">
          <div className="glass-card cta-card">
            <h2>Found a Stray Dog?</h2>
            <p>
              Scan their nose — it takes 10 seconds. If they're registered,
              we'll connect you with their family.
            </p>
            <Link to="/identify" className="btn btn-accent btn-lg mt-2">
              🔍 Identify Now — It's Free
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div className="container text-center">
          <p className="footer-text">
            🐾 NosePrints × <strong>PawFriend.in</strong> — Every nose tells a
            story
          </p>
          <p className="footer-sub">
            Built with ❤️ for the dogs of India. Powered by AI biometric
            research.
          </p>
        </div>
      </footer>
    </div>
  );
}
