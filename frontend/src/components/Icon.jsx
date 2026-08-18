/**
 * Icon — Professional SVG icon library for NosePrints × PawFriend.
 * Replaces all emoji icons with clean, consistent SVG icons.
 *
 * Usage: <Icon name="paw" size={24} className="my-class" />
 */

const paths = {
  paw: (
    <>
      <circle cx="7" cy="7" r="2.2" />
      <circle cx="17" cy="7" r="2.2" />
      <circle cx="4" cy="13" r="2.2" />
      <circle cx="20" cy="13" r="2.2" />
      <path d="M12 22c-3 0-5.5-2.5-5.5-5 0-1.5.8-3 2-4a4 4 0 0 1 7 0c1.2 1 2 2.5 2 4 0 2.5-2.5 5-5.5 5Z" />
    </>
  ),
  home: (
    <path d="M3 12.5l9-9 9 9M5 11v8a1 1 0 001 1h4v-5h4v5h4a1 1 0 001-1v-8" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  ),
  register: (
    <>
      <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
      <rect x="9" y="3" width="6" height="4" rx="1" strokeWidth="2" stroke="currentColor" fill="none" />
      <path d="M9 14l2 2 4-4" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  scan: (
    <>
      <path d="M4 8V6a2 2 0 012-2h2M16 4h2a2 2 0 012 2v2M4 16v2a2 2 0 002 2h2M16 20h2a2 2 0 002-2v-2" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
      <circle cx="12" cy="12" r="4" strokeWidth="2" stroke="currentColor" fill="none" />
      <circle cx="12" cy="12" r="1.5" fill="currentColor" />
    </>
  ),
  grid: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1.5" strokeWidth="2" stroke="currentColor" fill="none" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" strokeWidth="2" stroke="currentColor" fill="none" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" strokeWidth="2" stroke="currentColor" fill="none" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" strokeWidth="2" stroke="currentColor" fill="none" />
    </>
  ),
  alert: (
    <>
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" strokeWidth="2" stroke="currentColor" fill="none" strokeLinejoin="round" />
      <line x1="12" y1="9" x2="12" y2="13" strokeWidth="2" stroke="currentColor" strokeLinecap="round" />
      <circle cx="12" cy="17" r="0.5" fill="currentColor" stroke="currentColor" />
    </>
  ),
  shield: (
    <>
      <path d="M12 2l8 4v5c0 5.25-3.5 9.74-8 11-4.5-1.26-8-5.75-8-11V6l8-4z" strokeWidth="2" stroke="currentColor" fill="none" strokeLinejoin="round" />
      <path d="M9 12l2 2 4-4" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" strokeWidth="2" stroke="currentColor" fill="none" />
      <path d="M20 21a8 8 0 10-16 0" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
    </>
  ),
  dog: (
    <>
      <path d="M17 8c1.5-1 3-1 4 .5s0 3.5-1 4.5l-2 2v5a1 1 0 01-1 1h-2a1 1 0 01-1-1v-1h-4v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-5L4 13c-1-1-2-3-1-4.5S6.5 7 8 8" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="9" cy="11" r="1" fill="currentColor" />
      <circle cx="15" cy="11" r="1" fill="currentColor" />
    </>
  ),
  camera: (
    <>
      <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z" strokeWidth="2" stroke="currentColor" fill="none" strokeLinejoin="round" />
      <circle cx="12" cy="13" r="4" strokeWidth="2" stroke="currentColor" fill="none" />
    </>
  ),
  check: (
    <>
      <circle cx="12" cy="12" r="10" strokeWidth="2" stroke="currentColor" fill="none" />
      <path d="M8 12l3 3 5-5" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  checkBadge: (
    <>
      <path d="M12 2l2.4 3.6L18 4l-.4 3.8L21 10l-3.2 1.6.4 3.8-3.6-1.4L12 18l-2.6-4L6 15.4l.4-3.8L3 10l3.4-2.2L6 4l3.6 1.6L12 2z" strokeWidth="2" stroke="currentColor" fill="none" strokeLinejoin="round" />
      <path d="M9 12l2 2 4-4" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  searchEmpty: (
    <>
      <circle cx="11" cy="11" r="7" strokeWidth="2" stroke="currentColor" fill="none" />
      <path d="M21 21l-4.35-4.35M8 11h6" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
    </>
  ),
  alertCircle: (
    <>
      <circle cx="12" cy="12" r="10" strokeWidth="2" stroke="currentColor" fill="none" />
      <line x1="12" y1="8" x2="12" y2="12" strokeWidth="2" stroke="currentColor" strokeLinecap="round" />
      <circle cx="12" cy="16" r="0.5" fill="currentColor" stroke="currentColor" />
    </>
  ),
  phone: (
    <>
      <rect x="5" y="2" width="14" height="20" rx="2" strokeWidth="2" stroke="currentColor" fill="none" />
      <circle cx="12" cy="18" r="1" fill="currentColor" />
      <line x1="9" y1="5" x2="15" y2="5" strokeWidth="2" stroke="currentColor" strokeLinecap="round" />
    </>
  ),
  cpu: (
    <>
      <rect x="4" y="4" width="16" height="16" rx="2" strokeWidth="2" stroke="currentColor" fill="none" />
      <rect x="9" y="9" width="6" height="6" rx="1" strokeWidth="2" stroke="currentColor" fill="none" />
      <line x1="9" y1="1" x2="9" y2="4" strokeWidth="2" stroke="currentColor" />
      <line x1="15" y1="1" x2="15" y2="4" strokeWidth="2" stroke="currentColor" />
      <line x1="9" y1="20" x2="9" y2="23" strokeWidth="2" stroke="currentColor" />
      <line x1="15" y1="20" x2="15" y2="23" strokeWidth="2" stroke="currentColor" />
      <line x1="20" y1="9" x2="23" y2="9" strokeWidth="2" stroke="currentColor" />
      <line x1="20" y1="15" x2="23" y2="15" strokeWidth="2" stroke="currentColor" />
      <line x1="1" y1="9" x2="4" y2="9" strokeWidth="2" stroke="currentColor" />
      <line x1="1" y1="15" x2="4" y2="15" strokeWidth="2" stroke="currentColor" />
    </>
  ),
  heart: (
    <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z" strokeWidth="2" stroke="currentColor" fill="none" strokeLinejoin="round" />
  ),
  heartPaw: (
    <>
      <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z" strokeWidth="2" stroke="currentColor" fill="none" strokeLinejoin="round" />
      <circle cx="10" cy="11" r="1" fill="currentColor" />
      <circle cx="14" cy="11" r="1" fill="currentColor" />
      <circle cx="12" cy="14.5" r="1.3" fill="currentColor" />
    </>
  ),
  fingerprint: (
    <>
      <path d="M12 2a10 10 0 00-7 3" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
      <path d="M19 5a10 10 0 012 6c0 2-0.5 4-1.5 5.5" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
      <path d="M12 6a6 6 0 016 6c0 1.5-0.4 3-1 4" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
      <path d="M6 8a6 6 0 000 8" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
      <path d="M12 10a2 2 0 012 2c0 2-0.5 4-1.5 5.5" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
      <path d="M10 12a2 2 0 000 4" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" strokeWidth="2" stroke="currentColor" fill="none" />
      <path d="M21 21l-4.35-4.35" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
    </>
  ),
  arrowRight: (
    <path d="M5 12h14M12 5l7 7-7 7" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  ),
  arrowLeft: (
    <path d="M19 12H5M12 19l-7-7 7-7" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  ),
  refresh: (
    <>
      <path d="M1 4v6h6" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3.51 15a9 9 0 102.13-9.36L1 10" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  x: (
    <path d="M18 6L6 18M6 6l12 12" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
  ),
  clipboard: (
    <>
      <path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2" strokeWidth="2" stroke="currentColor" fill="none" />
      <rect x="8" y="2" width="8" height="4" rx="1" strokeWidth="2" stroke="currentColor" fill="none" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4" strokeWidth="2" stroke="currentColor" fill="none" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
    </>
  ),
  ruler: (
    <path d="M3 5h18v14H3zM3 9h4M3 13h4M3 17h4M7 5v14" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  ),
  target: (
    <>
      <circle cx="12" cy="12" r="9" strokeWidth="2" stroke="currentColor" fill="none" />
      <circle cx="12" cy="12" r="5" strokeWidth="2" stroke="currentColor" fill="none" />
      <circle cx="12" cy="12" r="1" fill="currentColor" />
    </>
  ),
  hand: (
    <path d="M18 11V6a2 2 0 00-4 0v3a2 2 0 00-4 0v1a2 2 0 00-4 0v4c0 4.42 3.58 8 8 8h1a7 7 0 007-7v-3a2 2 0 00-4 0z" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  ),
  lock: (
    <>
      <rect x="3" y="11" width="18" height="11" rx="2" strokeWidth="2" stroke="currentColor" fill="none" />
      <path d="M7 11V7a5 5 0 0110 0v4" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
    </>
  ),
  infinity: (
    <path d="M18.2 12c2.4-2.4 2.4-4.8 0-7.2s-4.8-2.4-7.2 0L12 6l-1-1.2c-2.4-2.4-4.8-2.4-7.2 0s-2.4 4.8 0 7.2L12 18l8.2-6z" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  ),
  zeroInstall: (
    <>
      <circle cx="12" cy="12" r="10" strokeWidth="2" stroke="currentColor" fill="none" />
      <path d="M8 12h8M12 8v8" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
    </>
  ),
  staff: (
    <>
      <circle cx="12" cy="8" r="4" strokeWidth="2" stroke="currentColor" fill="none" />
      <path d="M6 21v-2a4 4 0 014-4h4a4 4 0 014 4v2" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
      <path d="M16 3.13a4 4 0 010 7.75" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
      <path d="M21 21v-2a4 4 0 00-3-3.87" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" />
    </>
  ),
  calendar: (
    <>
      <rect x="3" y="4" width="18" height="18" rx="2" strokeWidth="2" stroke="currentColor" fill="none" />
      <line x1="16" y1="2" x2="16" y2="6" strokeWidth="2" stroke="currentColor" strokeLinecap="round" />
      <line x1="8" y1="2" x2="8" y2="6" strokeWidth="2" stroke="currentColor" strokeLinecap="round" />
      <line x1="3" y1="10" x2="21" y2="10" strokeWidth="2" stroke="currentColor" />
    </>
  ),
  mapPin: (
    <>
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" strokeWidth="2" stroke="currentColor" fill="none" />
      <circle cx="12" cy="10" r="3" strokeWidth="2" stroke="currentColor" fill="none" />
    </>
  ),
};

export default function Icon({ name, size = 24, className = "", style = {} }) {
  const content = paths[name];
  if (!content) {
    console.warn(`Icon "${name}" not found`);
    return null;
  }

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`icon icon-${name} ${className}`}
      style={style}
      aria-hidden="true"
    >
      {content}
    </svg>
  );
}
