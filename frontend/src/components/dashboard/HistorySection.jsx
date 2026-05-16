import HistoryInsights from "../history/HistoryInsights";
import HistoryRecords from "./HistoryRecords";

export default function HistorySection({ loading, items }) {
  return (
    <section className="panel history-panel">
      <div className="panel-head">
        <h2>Historical Detections</h2>
        <p>Insight dashboard and detailed records from your detection history.</p>
      </div>

      {loading && <p className="loading-text">Loading history...</p>}

      {!loading && items.length === 0 && (
        <div className="empty-state">
          <h3>No detections available</h3>
          <p>Your processed clips will appear here.</p>
        </div>
      )}

      {!loading && items.length > 0 && <HistoryInsights historyItems={items} />}
      {!loading && items.length > 0 && <HistoryRecords items={items} />}
    </section>
  );
}
