import { ACCEPTED_VIDEO_TYPES } from "../../constants/detection";

export default function UploadPanel({
  fileInputRef,
  selectedFile,
  previewUrl,
  loading,
  onFileSelected,
  onClearFile,
  onAnalyze,
  formatFileSize,
}) {
  return (
    <article className="panel upload-panel">
      <div className="panel-head">
        <h2>Upload Surveillance Clip</h2>
        <p>Drop a file or browse locally. Max 100 MB.</p>
      </div>

      <div
        className="drop-zone"
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          if (event.dataTransfer.files?.[0]) {
            onFileSelected(event.dataTransfer.files[0]);
          }
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_VIDEO_TYPES}
          onChange={(event) => {
            if (event.target.files?.[0]) {
              onFileSelected(event.target.files[0]);
            }
          }}
        />
        <h3>{selectedFile ? selectedFile.name : "Drop footage here"}</h3>
        <p>
          {selectedFile
            ? `${formatFileSize(selectedFile.size)} | Ready for CNN analysis`
            : "MP4, AVI, MOV, MKV, WEBM"}
        </p>
      </div>

      {selectedFile && (
        <div className="preview-wrap">
          <video src={previewUrl} controls />
          <div className="preview-actions">
            <button type="button" onClick={onClearFile} className="ghost-btn">
              Remove
            </button>
            <button type="button" onClick={onAnalyze} className="primary-btn" disabled={loading}>
              Analyze Clip
            </button>
          </div>
        </div>
      )}

      {!selectedFile && (
        <button type="button" onClick={() => fileInputRef.current?.click()} className="primary-btn stretch">
          Choose Video
        </button>
      )}
    </article>
  );
}
