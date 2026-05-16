export default function DashboardHeader({ userName, userEmail, onLogout }) {
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">Accident Vision Command Center</p>
        <h1>Real-time Incident Monitoring</h1>
      </div>
      <div className="operator-pill">
        <div>
          <strong>{userName || "Operator"}</strong>
          <p>{userEmail}</p>
        </div>
        <button type="button" onClick={onLogout}>
          Logout
        </button>
      </div>
    </header>
  );
}
