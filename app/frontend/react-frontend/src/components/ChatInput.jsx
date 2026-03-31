import { useState, useRef } from "react";

export default function ChatInput({ onSend, isProcessing, isWaiting, interruptPayload }) {
  const [text, setText] = useState("");
  const [attachedFile, setAttachedFile] = useState(null);
  const [attachedJson, setAttachedJson] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const interruptType = String(interruptPayload?.type || "").trim().toLowerCase();
  const isEmploymentPrompt = isWaiting && interruptType === "employment_status";
  const isExistingEmiChoicePrompt = isWaiting && interruptType === "existing_emi_choice";
  const showQuickOptions = isEmploymentPrompt || isExistingEmiChoicePrompt;

  const quickOptions = Array.isArray(interruptPayload?.options) && interruptPayload.options.length
    ? interruptPayload.options
    : isEmploymentPrompt
      ? ["Employed", "Self-employed/Business", "Unemployed"]
      : ["Yes", "No"];

  const placeholder = isEmploymentPrompt
    ? "Choose an option below or type your employment status..."
    : isExistingEmiChoicePrompt
      ? "Choose Yes or No, or type your response..."
    : isWaiting
      ? "Reply to continue..."
      : "Ask something or share your details...";
  const canSend = !isProcessing && (text.trim() || attachedJson);

  function parseFile(file) {
    if (!file || !file.name.endsWith(".json")) {
      alert("Please upload a valid .json document.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result);
        parsed._fileName = file.name;
        setAttachedFile(file.name);
        setAttachedJson(parsed);
      } catch {
        alert("Invalid JSON file.");
      }
    };
    reader.readAsText(file);
  }

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (file) parseFile(file);
    e.target.value = "";
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) parseFile(file);
  }

  function removeAttachment() {
    setAttachedFile(null);
    setAttachedJson(null);
  }

  function handleSubmit(e) {
    e?.preventDefault();
    if (!canSend) return;
    onSend({ text: text.trim(), jsonDocument: attachedJson, isResume: isWaiting });
    setText("");
    setAttachedFile(null);
    setAttachedJson(null);
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); }
  }

  function handleQuickOption(option) {
    if (isProcessing) return;
    onSend({ text: String(option || "").trim(), jsonDocument: null, isResume: true });
    setText("");
    setAttachedFile(null);
    setAttachedJson(null);
  }

  return (
    <div
      className={`input-zone ${dragOver ? "input-zone--drag" : ""}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      {dragOver && (
        <div className="drag-overlay">
          <span className="drag-overlay-icon">📄</span>
          <span>Drop your JSON document here</span>
        </div>
      )}

      {attachedFile && (
        <div className="attachment-pill">
          <span className="attachment-pill-icon">📄</span>
          <span className="attachment-pill-name">{attachedFile}</span>
          <button className="attachment-pill-remove" onClick={removeAttachment}>✕</button>
        </div>
      )}

      {isWaiting && (
        <div className="input-zone-banner">
          <span className="input-zone-banner-dot" />
          Waiting for your reply to continue the application
        </div>
      )}

      {showQuickOptions && (
        <div className="quick-options">
          {quickOptions.map((option) => (
            <button
              key={option}
              type="button"
              className="quick-option-btn"
              onClick={() => handleQuickOption(option)}
              disabled={isProcessing}
            >
              {option}
            </button>
          ))}
        </div>
      )}

      <form className="input-form" onSubmit={handleSubmit}>
        {/* Upload button */}
        <button
          type="button"
          className="input-icon-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={isProcessing}
          title="Upload JSON document"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
          </svg>
        </button>

        <input ref={fileInputRef} type="file" accept=".json" onChange={handleFileChange} style={{ display: "none" }} />

        <input
          className="input-field"
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isProcessing}
          autoFocus
        />

        {/* Processing spinner or send button */}
        {isProcessing ? (
          <div className="input-spinner" title="Processing...">
            <div className="spinner-ring" />
          </div>
        ) : (
          <button
            type="submit"
            className={`input-send-btn ${canSend ? "input-send-btn--active" : ""}`}
            disabled={!canSend}
            title="Send"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        )}
      </form>

      <p className="input-hint">Drag & drop a JSON doc · Enter to send</p>
    </div>
  );
}
