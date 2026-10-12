/* Shared API wrapper used by chat, auth, feedback, notices, admin, and documents. */
const SIH_API_BASE_URL = window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "";

class ApiError extends Error {
  constructor(message, status = 0, code = "NETWORK_ERROR") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function apiMessage(status, code, detail) {
  if (status === 401 || code === "UNAUTHORIZED") return "Your session has expired. Please log in again.";
  if (status === 403 || code === "FORBIDDEN") return "You don't have permission to do this.";
  if (status === 413) return "The file is too large. The maximum upload size is 10 MB.";
  if (code === "DB_UNAVAILABLE") return "Database is temporarily unavailable. Please try again.";
  if (code === "AI_TIMEOUT" || status === 504) return "The AI service took too long to respond. Please try again.";
  if (code === "AI_UNAVAILABLE" || status === 503) return "The service is temporarily unavailable. Please try again.";
  if (code === "AI_INVALID_RESPONSE" || status === 502) return "The AI service returned an invalid response.";
  if (code === "UPLOAD_FAILED") return detail || "Upload failed. Please try again.";
  return detail || "Request failed. Please try again.";
}

async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = window.localStorage.getItem("sih25104_access_token");
  if (token) headers.Authorization = `Bearer ${token}`;
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  let response;
  try {
    response = await fetch(`${SIH_API_BASE_URL}${path}`, { ...options, headers });
  } catch (error) {
    throw new ApiError("Cannot reach the server. Check your connection.");
  }
  let payload = null;
  try {
    payload = response.status === 204 ? null : await response.json();
  } catch (error) {
    payload = null;
  }
  if (response.status === 401) {
    window.localStorage.removeItem("sih25104_access_token");
    window.localStorage.removeItem("sih25104_user");
    window.sessionStorage.setItem("admin_message", "Your session has expired. Please log in again.");
    if (!window.location.pathname.endsWith("login.html")) {
      window.location.href = "login.html";
    }
  }
  if (!response.ok) {
    const code = payload && payload.code ? payload.code : "HTTP_ERROR";
    const detail = payload && typeof payload.detail === "string" ? payload.detail : "";
    throw new ApiError(apiMessage(response.status, code, detail), response.status, code);
  }
  return payload;
}

window.apiFetch = apiFetch;
window.ApiError = ApiError;
