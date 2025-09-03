import axios from "axios";

// Dev:   VITE_BACKEND_URL (default http://localhost:5000)
// Prod:  same origin as the page (Flask serves the built React app)
export const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ?? (import.meta.env.PROD ? "" : "http://localhost:5000");

const apiClient = axios.create({
  baseURL: BACKEND_URL,
  timeout: 300000, // batch validation on large real datasets can take a while
});

apiClient.interceptors.response.use(
  (r) => r,
  (err) => {
    const msg = err.response?.data?.message || err.message || "Request failed";
    err.userMessage = msg;
    return Promise.reject(err);
  }
);

export default apiClient;
