import { useMemo } from "react";

function parseTimestamp(value) {
  if (!value) return null;
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

function toSeverity(item) {
  const severity = (item.severity || "").toLowerCase();
  if (severity === "critical" || severity === "moderate" || severity === "minor") {
    return severity;
  }
  const conf = Number(item.confidence || 0);
  if (conf >= 0.78) return "critical";
  if (conf >= 0.5) return "moderate";
  return "minor";
}

function formatNumber(value, digits = 1) {
  return Number(value || 0).toFixed(digits);
}

function buildTrendPath(values, width, height, pad = 18) {
  if (!values.length) return "";
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const span = Math.max(max - min, 0.0001);
  return values
    .map((value, index) => {
      const x = pad + (index * (width - pad * 2)) / Math.max(values.length - 1, 1);
      const y = height - pad - ((value - min) / span) * (height - pad * 2);
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

function buildAreaPath(values, width, height, pad = 18) {
  const line = buildTrendPath(values, width, height, pad);
  if (!line) return "";
  const firstX = pad;
  const lastX = pad + (Math.max(values.length - 1, 0) * (width - pad * 2)) / Math.max(values.length - 1, 1);
  return `${line} L ${lastX.toFixed(2)} ${(height - pad).toFixed(2)} L ${firstX.toFixed(2)} ${(height - pad).toFixed(2)} Z`;
}

function RiskDonut({ accidents, safe }) {
  const total = Math.max(accidents + safe, 1);
  const angle = (accidents / total) * 360;
  const background = `conic-gradient(#ff6f61 0deg ${angle}deg, #3bc87f ${angle}deg 360deg)`;

  return (
    <div className="insight-card donut-card">
      <h4>Accident Ratio</h4>
      <div className="donut-wrap" style={{ background }}>
        <div className="donut-hole">
          <strong>{((accidents / total) * 100).toFixed(1)}%</strong>
          <span>Accident</span>
        </div>
      </div>
      <div className="donut-meta">
        <span>Accidents: {accidents}</span>
        <span>Safe: {safe}</span>
      </div>
    </div>
  );
}

function ConfidenceTrend({ records }) {
  const values = records.map((item) => item.confidencePct);
  const width = 580;
  const height = 210;
  const linePath = buildTrendPath(values, width, height);
  const areaPath = buildAreaPath(values, width, height);

  return (
    <div className="insight-card trend-card">
      <h4>Confidence Trend</h4>
      <svg viewBox={`0 0 ${width} ${height}`} className="trend-svg" role="img" aria-label="Confidence trend chart">
        <defs>
          <linearGradient id="confFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="rgba(29,211,176,0.45)" />
            <stop offset="100%" stopColor="rgba(29,211,176,0.03)" />
          </linearGradient>
        </defs>
        <rect x="0" y="0" width={width} height={height} fill="transparent" />
        <path d={areaPath} fill="url(#confFill)" />
        <path d={linePath} fill="none" stroke="#1dd3b0" strokeWidth="3" strokeLinejoin="round" />
      </svg>
      <p>Historical detection confidence over time.</p>
    </div>
  );
}

function DailyStackedBars({ records }) {
  const daily = useMemo(() => {
    const map = new Map();
    for (const item of records) {
      const key = item.date.toISOString().slice(0, 10);
      if (!map.has(key)) {
        map.set(key, { day: key, accidents: 0, safe: 0 });
      }
      const entry = map.get(key);
      if (item.accident) entry.accidents += 1;
      else entry.safe += 1;
    }
    return [...map.values()].slice(-10);
  }, [records]);

  const maxTotal = Math.max(...daily.map((d) => d.accidents + d.safe), 1);

  return (
    <div className="insight-card bars-card">
      <h4>Daily Incident Mix</h4>
      <div className="stacked-bars">
        {daily.map((day) => {
          const total = day.accidents + day.safe;
          const safeHeight = (day.safe / maxTotal) * 100;
          const accidentHeight = (day.accidents / maxTotal) * 100;
          return (
            <div key={day.day} className="stack-col" title={`${day.day} | Accident ${day.accidents} | Safe ${day.safe}`}>
              <div className="stack-bar">
                <div className="stack-segment safe" style={{ height: `${safeHeight}%` }} />
                <div className="stack-segment danger" style={{ height: `${accidentHeight}%` }} />
              </div>
              <span>{day.day.slice(5)}</span>
              <strong>{total}</strong>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SeverityDistribution({ records }) {
  const totals = { critical: 0, moderate: 0, minor: 0 };
  for (const item of records) {
    totals[item.severity] += 1;
  }
  const maxValue = Math.max(totals.critical, totals.moderate, totals.minor, 1);

  return (
    <div className="insight-card severity-card">
      <h4>Severity Distribution</h4>
      <div className="severity-bars">
        {[
          ["critical", "Critical", "#ff6f61"],
          ["moderate", "Moderate", "#ffba49"],
          ["minor", "Minor", "#3bc87f"],
        ].map(([key, label, color]) => (
          <div key={key} className="severity-row">
            <span>{label}</span>
            <div className="severity-track">
              <div className="severity-fill" style={{ width: `${(totals[key] / maxValue) * 100}%`, background: color }} />
            </div>
            <strong>{totals[key]}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function HourHeatmap({ records }) {
  const bins = Array.from({ length: 24 }, () => ({ total: 0, accidents: 0 }));
  for (const item of records) {
    const hour = item.date.getHours();
    bins[hour].total += 1;
    if (item.accident) bins[hour].accidents += 1;
  }

  const maxAcc = Math.max(...bins.map((bin) => bin.accidents), 1);

  return (
    <div className="insight-card heatmap-card">
      <h4>Hourly Accident Heatmap</h4>
      <div className="hour-grid">
        {bins.map((bin, hour) => {
          const intensity = bin.accidents / maxAcc;
          const alpha = 0.12 + intensity * 0.75;
          const bg = `rgba(255,111,97,${alpha.toFixed(3)})`;
          return (
            <div key={hour} className="hour-cell" style={{ background: bg }} title={`${hour}:00 | Accident ${bin.accidents} | Total ${bin.total}`}>
              <span>{hour.toString().padStart(2, "0")}</span>
              <strong>{bin.accidents}</strong>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ScatterRisk({ records }) {
  const width = 560;
  const height = 260;
  const pad = 30;
  const maxVehicles = Math.max(...records.map((r) => r.vehicleCount), 1);

  return (
    <div className="insight-card scatter-card">
      <h4>Confidence vs Vehicle Load</h4>
      <svg viewBox={`0 0 ${width} ${height}`} className="scatter-svg" role="img" aria-label="Confidence versus vehicle count scatter chart">
        <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="rgba(154,192,205,0.35)" />
        <line x1={pad} y1={pad} x2={pad} y2={height - pad} stroke="rgba(154,192,205,0.35)" />
        {records.map((item) => {
          const x = pad + (item.vehicleCount / maxVehicles) * (width - pad * 2);
          const y = height - pad - (item.confidencePct / 100) * (height - pad * 2);
          const radius = 3.5 + (item.anomalyScore || 0) * 4.5;
          return (
            <circle
              key={item.id}
              cx={x}
              cy={y}
              r={radius}
              fill={item.accident ? "rgba(255,111,97,0.72)" : "rgba(59,200,127,0.62)"}
              stroke="rgba(255,255,255,0.55)"
              strokeWidth="1"
            />
          );
        })}
      </svg>
      <p>X axis vehicle count, Y axis confidence percent, bubble size anomaly score.</p>
    </div>
  );
}

export default function HistoryInsights({ historyItems }) {
  const records = useMemo(() => {
    return (historyItems || [])
      .map((item) => {
        const date = parseTimestamp(item.timestamp);
        if (!date) return null;
        return {
          id: item.id,
          date,
          accident: Boolean(item.accident_detected),
          confidencePct: Number(item.confidence || 0) * 100,
          confidence: Number(item.confidence || 0),
          vehicleCount: Number(item.vehicle_count || 0),
          severity: toSeverity(item),
          anomalyScore: Number(item.anomaly_score || 0),
          congestion: Boolean(item.congestion_detected),
        };
      })
      .filter(Boolean)
      .sort((a, b) => a.date - b.date);
  }, [historyItems]);

  if (!records.length) {
    return null;
  }

  const total = records.length;
  const accidents = records.filter((item) => item.accident).length;
  const safe = total - accidents;
  const avgConf = records.reduce((sum, item) => sum + item.confidencePct, 0) / total;
  const avgVehicles = records.reduce((sum, item) => sum + item.vehicleCount, 0) / total;
  const avgAnomaly = records.reduce((sum, item) => sum + item.anomalyScore, 0) / total;
  const congestionRate = (records.filter((item) => item.congestion).length / total) * 100;
  const riskIndex = Math.min(100, (avgConf * 0.55) + ((accidents / total) * 100 * 0.35) + (avgAnomaly * 100 * 0.10));

  return (
    <section className="history-insights">
      <div className="insight-kpis">
        <article className="kpi-card"><span>Total Analyses</span><strong>{total}</strong></article>
        <article className="kpi-card"><span>Accident Rate</span><strong>{formatNumber((accidents / total) * 100)}%</strong></article>
        <article className="kpi-card"><span>Avg Confidence</span><strong>{formatNumber(avgConf)}%</strong></article>
        <article className="kpi-card"><span>Avg Vehicles</span><strong>{formatNumber(avgVehicles, 2)}</strong></article>
        <article className="kpi-card"><span>Congestion Share</span><strong>{formatNumber(congestionRate)}%</strong></article>
        <article className="kpi-card"><span>Risk Index</span><strong>{formatNumber(riskIndex)} / 100</strong></article>
      </div>

      <div className="insight-layout">
        <RiskDonut accidents={accidents} safe={safe} />
        <ConfidenceTrend records={records} />
        <DailyStackedBars records={records} />
        <SeverityDistribution records={records} />
        <HourHeatmap records={records} />
        <ScatterRisk records={records} />
      </div>
    </section>
  );
}