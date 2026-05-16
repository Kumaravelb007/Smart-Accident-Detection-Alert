export default function LoadingOverlay({ visible, phase }) {
  if (!visible) {
    return null;
  }

  const phases = [
    "Uploading surveillance clip",
    "Extracting and sampling frames",
    "Running CNN + traffic analytics",
    "Preparing emergency summary",
  ];

  return (
    <div className="loading-overlay">
      <div className="loading-card">
        <div className="pulse-dot" />
        <h3>Processing footage</h3>
        <p>Real-time accident intelligence pipeline is active.</p>
        <div className="loading-steps">
          {phases.map((step, index) => (
            <div key={step} className={`loading-step ${phase > index ? "done" : ""} ${phase === index ? "active" : ""}`}>
              <span>{phase > index ? "OK" : phase === index ? ".." : "--"}</span>
              {step}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
