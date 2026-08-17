/**
 * API service — communicates with the FastAPI backend.
 */
import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// ── Owners ──
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

// ── Nose Prints ──
export const uploadNosePrint = (dogId, file) => {
  const formData = new FormData();
  formData.append("file", file);
  return api.post(`/noseprints/upload/${dogId}`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const checkImageQuality = (file) => {
  const formData = new FormData();
  formData.append("file", file);
  return api.post("/noseprints/quality-check", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const getNosePrints = (dogId) => api.get(`/noseprints/${dogId}`);

// ── Matching ──
export const identifyDog = (file) => {
  const formData = new FormData();
  formData.append("file", file);
  return api.post("/match/identify", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const confirmMatch = (data) => api.post("/match/confirm", data);

// ── Health ──
export const getHealth = () =>
  axios.get(
    (import.meta.env.VITE_API_URL || "http://localhost:8000") + "/health"
  );

export default api;
