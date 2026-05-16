import { deriveSeverity } from "../../lib/formatters";

export default function HistoryRecords({ items }) {
  return (
    <div className="history-list">
      {items.map((item) => (
        <article key={item.id} className="history-item">
          <div className="thumb-wrap">
            {item.frame_url ? (
              <img src={item.frame_url} alt="Detection frame" />
            ) : (
              <div className="thumb-placeholder">No Frame</div>
            )}
          </div>

          <div className="history-content">
            <div className="history-top">
              <h4>{item.accident_detected ? "Accident Flagged" : "No Accident"}</h4>
              <span className={item.accident_detected ? "chip danger" : "chip safe"}>
                {(Number(item.confidence || 0) * 100).toFixed(1)}%
              </span>
            </div>
            <p>{item.message || "No message available"}</p>
            <div className="history-meta">
              <span>{item.timestamp}</span>
              <span>Vehicles: {item.vehicle_count ?? 0}</span>
              <span>Severity: {deriveSeverity(item)}</span>
              <span>Density: {item.traffic_density || "Low"}</span>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
