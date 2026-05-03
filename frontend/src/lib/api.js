import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  timeout: 120000, // increased timeout
});

// helper wrapper (IMPORTANT)
const safeCall = async (fn, fallback) => {
  try {
    const res = await fn();
    return res.data;
  } catch (err) {
    console.error("API error:", err);
    return fallback;
  }
};

// APIs
export const getAnalyze = () =>
  safeCall(() => api.get("/analyze"), []);

export const getDiscover = (top = 12, includeWeak = false) =>
  safeCall(
    () =>
      api.get("/discover", {
        params: { top, include_weak: includeWeak },
      }),
    []
  );

export const getWatchlist = () =>
  safeCall(() => api.get("/watchlist"), []);

export const addTicker = (ticker) =>
  safeCall(() => api.post("/watchlist", { ticker }), {});

export const removeTicker = (ticker) =>
  safeCall(
    () => api.delete(`/watchlist/${encodeURIComponent(ticker)}`),
    {}
  );

export const refreshAll = () =>
  safeCall(() => api.post("/refresh"), {});

export const getInvestmentPlan = (budget = 5000) =>
  safeCall(
    () => api.get("/investment-plan", { params: { budget } }),
    { allocations: [] }
  );

export const getRecommendedAction = () =>
  safeCall(() => api.get("/recommended-action"), {});

export const getStockDetail = (ticker) =>
  safeCall(
    () => api.get(`/stock/${encodeURIComponent(ticker)}`),
    {}
  );

export const getStatus = () =>
  safeCall(() => api.get("/status"), {});

export const sendTestNotification = () =>
  safeCall(() => api.post("/test-notification"), {});
