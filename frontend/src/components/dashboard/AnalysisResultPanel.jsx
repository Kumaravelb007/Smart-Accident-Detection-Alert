function statusTone(accidentDetected) {
  return accidentDetected ? "danger" : "safe";
}

export default function AnalysisResultPanel({ result }) {
  return (
    <article className="panel result-panel">
      <div className="panel-head">
        <h2>Analysis Result</h2>
        <p>Severity and traffic context from the latest run.</p>
      </div>

      {!result && (
        <div className="empty-state">
          <h3>No result yet</h3>
          <p>Run analysis to view confidence, frame evidence, and traffic metrics.</p>
        </div>
      )}

      {result && (
        <>
          <div className={`status-banner ${statusTone(result.accident_detected)}`}>
            <h3>{result.accident_detected ? "Potential Accident Detected" : "No Accident Detected"}</h3>
            <p>{result.message}</p>
          </div>

          <div className="metric-grid">
            <div>
              <span>Confidence</span>
              <strong>{result.confidence_percent}</strong>
            </div>
            <div>
              <span>Severity</span>
              <strong>{result.severity || "Minor"}</strong>
            </div>
            <div>
              <span>Strategy</span>
              <strong>{result.detection_strategy}</strong>
            </div>
            <div>
              <span>Vehicles</span>
              <strong>{result.vehicle_count ?? 0}</strong>
            </div>
            <div>
              <span>Traffic Density</span>
              <strong>{result.traffic_analysis?.traffic_density || "Low"}</strong>
            </div>
            <div>
              <span>Congestion</span>
              <strong>{result.traffic_analysis?.congestion_detected ? "Yes" : "No"}</strong>
            </div>
          </div>

          {result.frame_url && (
            <div className="evidence-block">
              <img src={result.frame_url} alt="Detected frame" />
              <p>
                Key frame #{result.frame_index} | {result.timestamp}
              </p>
            </div>
          )}

          {result.ai_report && (
            <div className="report-block">
              <h4>AI Incident Summary</h4>
              <p>{result.ai_report}</p>
            </div>
          )}

          <div className="meta-row">
            <span>Email Alert: {result.email_alert?.message || "Not triggered"}</span>
            <span>Location: {result.location}</span>
          </div>
        </>
      )}
    </article>
  );
}
