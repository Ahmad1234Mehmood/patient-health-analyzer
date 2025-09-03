import api from "./client";

export const healthCheck = () => api.get("/health");
export const getDatasetSummary = () => api.get("/api/v1/datasets/summary");

// ---- ECG
export const listEcgRecords = () => api.get("/api/v1/ecg/records");
export const analyzeEcg = (payload) => api.post("/api/v1/ecg/analyze", payload);
export const uploadEcg = (files, fs) => {
  const fd = new FormData();
  files.forEach((f) => fd.append("files", f));
  if (fs) fd.append("fs", fs);
  return api.post("/api/v1/ecg/upload", fd);
};
export const getFilterResponse = (params) => api.get("/api/v1/ecg/filter-response", { params });

// ---- X-ray
export const listXrays = () => api.get("/api/v1/xray/images");
export const analyzeXray = (payload) => api.post("/api/v1/xray/analyze", payload);
export const uploadXray = (file) => {
  const fd = new FormData();
  fd.append("file", file);
  return api.post("/api/v1/xray/upload", fd);
};
export const evaluateXray = (params) => api.get("/api/v1/xray/evaluate", { params });

// ---- History
export const getHistory = () => api.get("/api/v1/history");
export const deleteHistory = (id) => api.delete(`/api/v1/history/${id}`);
export const clearHistory = () => api.delete("/api/v1/history");
