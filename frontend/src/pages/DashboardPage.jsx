import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { detectAccident, fetchHistory, logoutUser } from "../api";
import {
  ALLOWED_EXTENSIONS,
  MAX_SIZE_MB,
} from "../constants/detection";
import ChatWidget from "../components/ChatWidget";
import AnalysisResultPanel from "../components/dashboard/AnalysisResultPanel";
import DashboardHeader from "../components/dashboard/DashboardHeader";
import DashboardTabs from "../components/dashboard/DashboardTabs";
import FeatureHighlights from "../components/dashboard/FeatureHighlights";
import HistorySection from "../components/dashboard/HistorySection";
import UploadPanel from "../components/dashboard/UploadPanel";
import LoadingOverlay from "../components/LoadingOverlay";
import { useToast } from "../components/ToastProvider";
import { formatFileSize } from "../lib/formatters";
import { clearSession, getUserEmail, getUserName } from "../lib/session";

export default function DashboardPage() {
  const navigate = useNavigate();
  const { pushToast } = useToast();

  const fileInputRef = useRef(null);

  const [activeTab, setActiveTab] = useState("analyze");
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");

  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState(0);

  const [result, setResult] = useState(null);
  const [historyItems, setHistoryItems] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  useEffect(() => {
    if (activeTab === "history") {
      loadHistory();
    }
  }, [activeTab]);

  function setFile(file) {
    const ext = file.name.split(".").pop()?.toLowerCase() || "";
    if (!ALLOWED_EXTENSIONS.has(ext)) {
      pushToast("Invalid video format. Use MP4, AVI, MOV, MKV, or WEBM.", "error");
      return;
    }

    const sizeMb = file.size / (1024 * 1024);
    if (sizeMb > MAX_SIZE_MB) {
      pushToast(`File exceeds ${MAX_SIZE_MB} MB limit.`, "error");
      return;
    }

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    pushToast(`Loaded ${file.name}`, "success");
  }

  function clearFile() {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    setPreviewUrl("");
    setSelectedFile(null);
  }

  async function loadHistory() {
    setHistoryLoading(true);
    try {
      const data = await fetchHistory();
      setHistoryItems(data.history || []);
    } catch (error) {
      pushToast(error.message, "error");
    } finally {
      setHistoryLoading(false);
    }
  }

  async function analyzeVideo() {
    if (!selectedFile || loading) {
      return;
    }

    setLoading(true);
    setPhase(0);

    const timer = window.setInterval(() => {
      setPhase((current) => Math.min(current + 1, 3));
    }, 1600);

    try {
      const data = await detectAccident(selectedFile);
      setResult(data);
      pushToast(
        data.accident_detected ? "Potential accident detected" : "No accident detected in sampled frames",
        data.accident_detected ? "error" : "success"
      );
    } catch (error) {
      pushToast(error.message, "error");
    } finally {
      window.clearInterval(timer);
      setPhase(3);
      window.setTimeout(() => {
        setLoading(false);
      }, 400);
    }
  }

  async function handleLogout() {
    try {
      await logoutUser();
    } finally {
      clearSession();
      navigate("/login", { replace: true });
    }
  }

  return (
    <div className="dashboard-shell">
      <div className="dashboard-bg" />
      <LoadingOverlay visible={loading} phase={phase} />

      <DashboardHeader
        userName={getUserName()}
        userEmail={getUserEmail()}
        onLogout={handleLogout}
      />

      <FeatureHighlights />

      <DashboardTabs activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === "analyze" && (
        <section className="analysis-layout">
          <UploadPanel
            fileInputRef={fileInputRef}
            selectedFile={selectedFile}
            previewUrl={previewUrl}
            loading={loading}
            onFileSelected={setFile}
            onClearFile={clearFile}
            onAnalyze={analyzeVideo}
            formatFileSize={formatFileSize}
          />
          <AnalysisResultPanel result={result} />
        </section>
      )}

      {activeTab === "history" && (
        <HistorySection loading={historyLoading} items={historyItems} />
      )}

      <ChatWidget />
    </div>
  );
}
