import { useEffect, useState } from "react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { getStockDetail } from "@/lib/api";
import { formatINR, formatNum, formatPct } from "@/lib/format";
import SignalBadge from "@/components/SignalBadge";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine, AreaChart, Area,
} from "recharts";
import { Sparkles } from "lucide-react";

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

  const a = data?.analysis || {};
  const history = Array.isArray(data?.history) ? data.history : [];

  // ✅ FIXED DATA (IMPORTANT)
  const chartData = history.map((h) => ({
    date: h?.date,
    price: h?.price ?? 0,
  }));

  const safeReasons = Array.isArray(a?.reasons) ? a.reasons : [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">

        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <span className="text-2xl font-semibold">{ticker}</span>
            <SignalBadge signal={a?.signal_strength} />
          </DialogTitle>

          <DialogDescription className="flex items-center gap-2 text-sm">
            <Sparkles className="h-4 w-4" />
            {a?.recommendation || "Analyzing…"}
          </DialogDescription>
        </DialogHeader>

        {loading && (
          <div className="py-12 text-center">Loading...</div>
        )}

        {!loading && (
          <div className="space-y-6">

            {/* 🔥 ACTION CARD */}
            <div className="p-4 rounded-xl border bg-muted/40">
              <div className="text-xs uppercase text-muted-foreground">
                Suggested Action
              </div>
              <div className="text-xl font-semibold mt-1">
                {a?.action || "Wait"}
              </div>
              <div className="text-sm text-muted-foreground">
                Confidence: {(a?.confidence ?? 0) * 100}%
              </div>
            </div>

            {/* 📊 STATS */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Stat label="Price" value={formatINR(a?.price)} />
              <Stat label="Drawdown" value={formatPct(a?.drawdown_percent)} />
              <Stat label="RSI" value={formatNum(a?.rsi, 1)} />
              <Stat label="Score" value={formatNum(a?.score, 1)} />
            </div>

            {/* 📈 PRICE CHART */}
            <div className="h-64 rounded-xl border p-3">
              <ResponsiveContainer>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" hide />
                  <YAxis />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="price"
                    stroke="#2563eb"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* 📉 RSI */}
            <div className="h-40 rounded-xl border p-3">
              <ResponsiveContainer>
                <AreaChart data={chartData}>
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <ReferenceLine y={70} stroke="red" />
                  <ReferenceLine y={30} stroke="green" />
                  <Area
                    dataKey={() => a?.rsi || 50}
                    fill="#10b981"
                    stroke="#10b981"
                    fillOpacity={0.2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* 💡 REASONS */}
            <div className="border p-4 rounded-xl">
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

          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

const Stat = ({ label, value }) => (
  <div className="border p-3 rounded-xl">
    <div className="text-xs text-muted-foreground">{label}</div>
    <div className="font-semibold">{value || "-"}</div>
  </div>
);

export default StockDetailDialog;
