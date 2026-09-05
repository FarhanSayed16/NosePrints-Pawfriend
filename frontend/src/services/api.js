/**
 * API service — communicates with the FastAPI backend.
 */
import axios from "axios";

function resolveApiBaseUrl() {
  const fromEnv = import.meta.env.VITE_API_URL;
  if (fromEnv) return fromEnv.replace(/\/$/, "");
  // Same origin — Vite proxies /api/v1 to FastAPI (avoids HTTPS mixed-content on mobile)
  return `${window.location.origin}/api/v1`;
}

const API_BASE_URL = resolveApiBaseUrl();

export function apiOrigin() {
  return API_BASE_URL.replace(/\/api\/v1\/?$/, "");
}

export function mediaUrl(path) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  if (path.startsWith("blob:") || path.startsWith("data:")) return path;
  const origin = apiOrigin();
  return path.startsWith("/") ? origin + path : `${origin}/${path}`;
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 120000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("staff_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // FormData must set its own Content-Type (with boundary). A bare
  // "multipart/form-data" header breaks optional file parts on the server.
  if (config.data instanceof FormData) {
    delete config.headers["Content-Type"];
  }
  return config;
});

export function formatApiError(err, fallback = "Request failed") {
  const detail = err.response?.data?.detail;
  if (detail == null) return err.message || fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item.msg || item.message || JSON.stringify(item))
      .join("; ");
  }
  if (typeof detail === "object") {
    return detail.message || JSON.stringify(detail);
  }
  return fallback;
}

// ── Registration (preferred public path) ──
export const registerOwnerAndDog = (data) => api.post("/register", data);

// ── Owners (list/get/update/delete require staff JWT) ──
export const createOwner = (data) => api.post("/owners/", data);
export const getOwners = (page = 1) =>
  api.get("/owners/", { params: { page } });
export const getOwner = (id) => api.get(`/owners/${id}`);
export const updateOwner = (id, data) => api.patch(`/owners/${id}`, data);
export const deleteOwner = (id) => api.delete(`/owners/${id}`);

// ── Dogs ──
export const createDog = (data) => api.post("/dogs/", data);
export const getDogs = (params = {}) => api.get("/dogs/", { params });
export const getDog = (id) => api.get(`/dogs/${id}`);
export const updateDog = (id, data) => api.patch(`/dogs/${id}`, data);
export const deleteDog = (id) => api.delete(`/dogs/${id}`);
export const getLostDogs = (page = 1) =>
  api.get("/dogs/lost", { params: { page } });
export const getFoundDogs = (page = 1) =>
  api.get("/dogs/found", { params: { page } });
export const reportDogLost = (id, data) =>
  api.post(`/dogs/${id}/report-lost`, data);
export const foundDogIntake = (data) => api.post("/dogs/found-intake", data);

// ── Nose Prints ──
export const uploadNosePrint = (dogId, file, { preCropped = false } = {}) => {
  const formData = new FormData();
  const named = file instanceof File ? file : new File([file], "nose.jpg", { type: file.type || "image/jpeg" });
  formData.append("file", named, named.name || "nose.jpg");
  return api.post(`/noseprints/upload/${dogId}`, formData, {
    params: { pre_cropped: preCropped },
  });
};

export const checkImageQuality = (file, { preCropped = false } = {}) => {
  const formData = new FormData();
  const named = file instanceof File ? file : new File([file], "nose.jpg", { type: file.type || "image/jpeg" });
  formData.append("file", named, named.name || "nose.jpg");
  return api.post("/noseprints/quality-check", formData, {
    params: { pre_cropped: preCropped },
  });
};

export const getNosePrints = (dogId) => api.get(`/noseprints/${dogId}`);

// ── Matching ──
export const detectNosePreview = (file) => {
  const formData = new FormData();
  const named = file instanceof File ? file : new File([file], "preview.jpg", { type: file.type || "image/jpeg" });
  formData.append("file", named, named.name || "preview.jpg");
  return api.post("/match/detect-preview", formData);
};

export const identifyDog = (file, appearanceFile, { preCropped = false, forceAppearance = false } = {}) => {
  const formData = new FormData();
  const named = file instanceof File ? file : new File([file], "nose.jpg", { type: file.type || "image/jpeg" });
  formData.append("file", named, named.name || "nose.jpg");
  if (appearanceFile) {
    const look =
      appearanceFile instanceof File
        ? appearanceFile
        : new File([appearanceFile], "look.jpg", { type: appearanceFile.type || "image/jpeg" });
    formData.append("appearance", look, look.name || "look.jpg");
  }
  return api.post("/match/identify", formData, {
    params: { pre_cropped: preCropped, force_appearance: forceAppearance },
  });
};

export const checkLookPhoto = (file) => {
  const formData = new FormData();
  const named = file instanceof File ? file : new File([file], "look.jpg", { type: file.type || "image/jpeg" });
  formData.append("file", named, named.name || "look.jpg");
  return api.post("/dogs/look-check", formData);
};

export const uploadProfilePhoto = (dogId, file, { force = false } = {}) => {
  const formData = new FormData();
  const named = file instanceof File ? file : new File([file], "look.jpg", { type: file.type || "image/jpeg" });
  formData.append("file", named, named.name || "look.jpg");
  return api.post(`/dogs/${dogId}/profile-photo`, formData, {
    params: { force },
  });
};

export const getMatchQueue = (params = {}) =>
  api.get("/match/queue", { params });
export const confirmMatch = (data) => api.post("/match/confirm", data);

// ── Auth ──
export const staffLogin = (data) => api.post("/auth/login", data);
export const staffBootstrap = (data) => api.post("/auth/bootstrap", data);
export const staffMe = () => api.get("/auth/me");

export function setStaffToken(token) {
  if (token) localStorage.setItem("staff_token", token);
  else localStorage.removeItem("staff_token");
}

export function getStaffToken() {
  return localStorage.getItem("staff_token");
}

// ── Health ──
export const getHealth = () => axios.get(`${window.location.origin}/health`);

export default api;
