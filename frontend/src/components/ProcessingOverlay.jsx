import "./ProcessingOverlay.css";

export default function ProcessingOverlay({ title, detail, previewUrl }) {
  return (
    <div className="processing-overlay" role="status" aria-live="polite">
      <div className="processing-card glass-card">
        {previewUrl && (
          <img className="processing-preview" src={previewUrl} alt="" aria-hidden="true" />
        )}
        <div className="progress-spinner" />
        <p className="processing-title">{title}</p>
        {detail && <p className="processing-detail">{detail}</p>}
      </div>
    </div>
  );
}
