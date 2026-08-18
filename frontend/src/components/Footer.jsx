import Icon from "./Icon";
import { Link } from "react-router-dom";
import "./Footer.css";

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-top">
          <div className="footer-brand-section">
            <Link to="/" className="footer-logo">
              <Icon name="paw" size={24} />
              <span className="footer-logo-text">
                Nose<span>Prints</span>
              </span>
            </Link>
            <p className="footer-tagline">
              AI-powered nose-print recognition to reunite lost dogs with their families.
              A project by <a href="https://pawfriend.in" target="_blank" rel="noopener noreferrer">PawFriend.in</a>
            </p>
          </div>

          <div className="footer-links-section">
            <div className="footer-col">
              <h4>Quick Links</h4>
              <ul>
                <li><Link to="/register">Register a Dog</Link></li>
                <li><Link to="/identify">Identify a Dog</Link></li>
                <li><Link to="/directory">Dog Directory</Link></li>
                <li><Link to="/lost">Lost Dogs</Link></li>
              </ul>
            </div>
            <div className="footer-col">
              <h4>About</h4>
              <ul>
                <li><a href="https://pawfriend.in" target="_blank" rel="noopener noreferrer">PawFriend.in</a></li>
                <li><Link to="/staff">Staff Portal</Link></li>
              </ul>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          <p>
            © {new Date().getFullYear()} NosePrints × <strong>PawFriend.in</strong> — Every nose tells a story.
          </p>
          <p className="footer-legal">
            Built for the dogs of India. Powered by AI biometric research.
          </p>
        </div>
      </div>
    </footer>
  );
}
