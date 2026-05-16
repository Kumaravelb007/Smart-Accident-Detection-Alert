import { useState } from "react";

import { chatWithAssistant } from "../api";

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState([
    {
      role: "assistant",
      content:
        "I can explain results, traffic risk levels, and emergency response recommendations. Ask anything.",
    },
  ]);
  const [sending, setSending] = useState(false);

  async function sendMessage() {
    const text = input.trim();
    if (!text || sending) {
      return;
    }

    const nextHistory = [...history, { role: "user", content: text }];
    setHistory(nextHistory);
    setInput("");
    setSending(true);

    try {
      const response = await chatWithAssistant(text, nextHistory.slice(-10));
      setHistory((prev) => [...prev, { role: "assistant", content: response.reply || "No response." }]);
    } catch {
      setHistory((prev) => [...prev, { role: "assistant", content: "AI service unavailable right now." }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className={`chat-widget ${open ? "open" : ""}`}>
      <button className="chat-toggle" onClick={() => setOpen((prev) => !prev)}>
        Safety AI
      </button>

      {open && (
        <div className="chat-window">
          <div className="chat-head">
            <h4>Command Assistant</h4>
            <button type="button" onClick={() => setOpen(false)}>
              X
            </button>
          </div>

          <div className="chat-body">
            {history.map((entry, idx) => (
              <div key={`${entry.role}-${idx}`} className={`chat-bubble ${entry.role}`}>
                {entry.content}
              </div>
            ))}
          </div>

          <div className="chat-input-row">
            <input
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask about the current analysis"
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  sendMessage();
                }
              }}
            />
            <button type="button" onClick={sendMessage} disabled={sending}>
              {sending ? "..." : "Send"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
