import { useEffect, useState } from "react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { getStockDetail } from "@/lib/api";
import { formatINR, formatNum, formatPct } from "@/lib/format";
import SignalBadge from "@/components/SignalBadge";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend, ReferenceLine, AreaChart, Area,
} from "recharts";
import { Sparkles, CheckCircle2 } from "lucide-react";

const CHART_COLORS = {
  price: "#1f4236",
  ma50: "#a67c00",
  ma200: "#b33a20",
  rsi: "#337a54",
};

export const StockDetailDialog = ({ ticker, open, onOpenChange }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !ticker) return;

    setLoading(true);
    setData(null);

    getStockDetail(ticker)
      .then((res) => setData(res || {}))
      .catch(() => setData({}))
      .finally(() => setLoading(false));
  }, [open, ticker]);

  // 🛡️ SAFE DATA
  const a = data?.analysis || {};
  const history = Array.isArray(data?.history) ? data.history : [];

  // 🛡️ SANITIZE CHART DATA
  const priceData = history
    .filter((h) => h?.close != null)
    .map((h) => ({
      date: h?.date,
      close: h?.close ?? 0,
      ma50: h?.ma50 ?? 0,
      ma200: h?.ma200 ?? 0,
    }));

  const rsiData = history
    .filter((h) => h?.rsi != null)
    .map((h) => ({
      date: h?.date,
      rsi: h?.rsi ?? 0,
    }));

  const safeReasons = Array.isArray(a?.reasons) ? a.reasons : [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <span className="text-2xl">{ticker || "N/A"}</span>
            {a?.signal_strength && (
              <SignalBadge signal={a.signal_strength} />
            )}
          </DialogTitle>

          <DialogDescription>
            {a?.recommendation || "Loading details…"}
          </DialogDescription>
        </DialogHeader>

        {loading && (
          <div className="py-12 text-center">Loading…</div>
        )}

        {!loading && (
          <div className="space-y-6">

            {/* DIP REASON */}
            <div className="border p-4 rounded">
              <div className="text-xs uppercase mb-2">
                Why this is a dip
              </div>

              {safeReasons.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  No reasoning available
                </div>
              ) : (
                safeReasons.map((r, i) => (
                  <div key={i} className="text-sm">
                    • {r}
                  </div>
                ))
              )}
            </div>

            {/* STATS */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Stat label="Price" value={a?.price ? formatINR(a.price) : "-"} />
              <Stat label="Prev" value={a?.previous_price ? formatINR(a.previous_price) : "-"} />
              <Stat label="Drawdown" value={a?.drawdown_percent ? formatPct(a.drawdown_percent) : "-"} />
              <Stat label="RSI" value={a?.rsi ? formatNum(a.rsi, 1) : "-"} />
              <Stat label="Score" value={formatNum(a?.score ?? 0, 1)} />
            </div>

            {/* PRICE CHART */}
            <div className="h-64">
              <ResponsiveContainer>
                <LineChart data={priceData}>
                  <CartesianGrid stroke="#eee" />
                  <XAxis dataKey="date" hide />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line dataKey="close" stroke={CHART_COLORS.price} dot={false} />
                  <Line dataKey="ma50" stroke={CHART_COLORS.ma50} dot={false} />
                  <Line dataKey="ma200" stroke={CHART_COLORS.ma200} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* RSI CHART */}
            <div className="h-44">
              <ResponsiveContainer>
                <AreaChart data={rsiData}>
                  <CartesianGrid stroke="#eee" />
                  <XAxis dataKey="date" hide />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <ReferenceLine y={70} stroke="red" />
                  <ReferenceLine y={30} stroke="green" />
                  <Area dataKey="rsi" stroke={CHART_COLORS.rsi} fillOpacity={0.2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

const Stat = ({ label, value }) => (
  <div className="border p-2 rounded">
    <div className="text-xs">{label}</div>
    <div className="font-medium">{value}</div>
  </div>
);

export default StockDetailDialog;
