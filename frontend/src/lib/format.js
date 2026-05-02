/**
 * Signal badge styling based on signal strength.
 * Strong=red (terracotta), Medium=yellow (ochre), Weak=green (sage)
 */
export const signalClass = (signal) => {
  if (signal === "Strong") return "signal-strong";
  if (signal === "Medium") return "signal-medium";
  return "signal-weak";
};

export const formatINR = (v) => {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

export const formatPct = (v, digits = 2) => {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const n = Number(v);
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(digits)}%`;
};

export const formatNum = (v, digits = 2) => {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return Number(v).toFixed(digits);
};
