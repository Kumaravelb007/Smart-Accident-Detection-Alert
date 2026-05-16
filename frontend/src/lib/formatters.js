export function formatFileSize(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function deriveSeverity(item) {
  if (item?.severity) {
    return item.severity;
  }

  const confidence = Number(item?.confidence || 0);
  if (confidence >= 0.78) return "Critical";
  if (confidence >= 0.5) return "Moderate";
  return "Minor";
}
