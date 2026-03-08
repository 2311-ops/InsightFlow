import axios from "axios";

const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || "http://localhost:5000/api",
});

// Attach JWT token to every request if present
API.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auth
export const register = (data) => API.post("/auth/register", data);
export const login = (data) => API.post("/auth/login", data);

// Datasets
export const uploadDataset = (companyId, file) => {
  const form = new FormData();
  form.append("file", file);
  form.append("companyId", companyId);
  return API.post("/datasets/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};
export const getDatasets = (companyId) =>
  API.get(`/datasets?companyId=${companyId}`);

// Insights
export const getInsights = (datasetId) =>
  API.get(`/insights?datasetId=${datasetId}`);
export const askQuestion = (datasetId, question) =>
  API.post(`/insights/ask`, { datasetId, question });

export default API;
