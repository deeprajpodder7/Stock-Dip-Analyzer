import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API, timeout: 60000 });

export const getAnalyze = () => api.get("/analyze").then((r) => r.data);
export const getDiscover = (top = 12, includeWeak = false) =>
  api
    .get("/discover", { params: { top, include_weak: includeWeak } })
    .then((r) => r.data);
export const getWatchlist = () => api.get("/watchlist").then((r) => r.data);
export const addTicker = (ticker) =>
  api.post("/watchlist", { ticker }).then((r) => r.data);
export const removeTicker = (ticker) =>
  api.delete(`/watchlist/${encodeURIComponent(ticker)}`).then((r) => r.data);
export const refreshAll = () => api.post("/refresh").then((r) => r.data);
export const getStockDetail = (ticker) =>
  api.get(`/stock/${encodeURIComponent(ticker)}`).then((r) => r.data);
export const getStatus = () => api.get("/status").then((r) => r.data);
export const sendTestNotification = () =>
  api.post("/test-notification").then((r) => r.data);
