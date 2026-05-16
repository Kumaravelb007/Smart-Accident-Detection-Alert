export default function DashboardTabs({ activeTab, onChange }) {
  return (
    <div className="tab-row">
      <button
        type="button"
        className={activeTab === "analyze" ? "active" : ""}
        onClick={() => onChange("analyze")}
      >
        New Analysis
      </button>
      <button
        type="button"
        className={activeTab === "history" ? "active" : ""}
        onClick={() => onChange("history")}
      >
        History
      </button>
    </div>
  );
}
