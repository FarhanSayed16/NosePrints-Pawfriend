import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import Icon from "./Icon";
import "./Navbar.css";

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  const links = [
    { to: "/", label: "Home", icon: "home" },
    { to: "/register", label: "Register", icon: "register" },
    { to: "/identify", label: "Identify", icon: "scan" },
    { to: "/directory", label: "Directory", icon: "grid" },
    { to: "/lost", label: "Lost Dogs", icon: "alert" },
    { to: "/staff", label: "Staff", icon: "shield" },
  ];

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="navbar-brand">
          <div className="brand-mark">
            <Icon name="paw" size={18} />
          </div>
          <div className="brand-info">
            <span className="brand-name">NosePrints</span>
            <span className="brand-org">by PawFriend.in</span>
          </div>
        </Link>

        <button
          className={`hamburger ${menuOpen ? "active" : ""}`}
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle navigation"
        >
          <span></span>
          <span></span>
          <span></span>
        </button>

        <div className={`nav-menu ${menuOpen ? "open" : ""}`}>
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={`nav-item ${location.pathname === link.to ? "active" : ""}`}
              onClick={() => setMenuOpen(false)}
            >
              <Icon name={link.icon} size={15} className="nav-item-icon" />
              <span className="nav-item-label">{link.label}</span>
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
