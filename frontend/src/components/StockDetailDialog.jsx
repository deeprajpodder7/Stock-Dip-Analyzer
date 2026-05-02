import { useEffect, useState } from "react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { getStockDetail } from "@/lib/api";
import { formatINR, formatNum, formatPct } from "@/lib/format";
import SignalBadge from "@/components/SignalBadge";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend, ReferenceLine, AreaChart, Area,
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
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [open, ticker]);

  const a = data?.analysis;
  const history = data?.history ?? [];
  // Sample to last ~1y and reduce density for chart perf
  const priceData = history.map((h) => ({
    date: h.date,
    close: h.close,
    ma50: h.ma50,
    ma200: h.ma200,
  }));
  const rsiData = history.map((h) => ({ date: h.date, rsi: h.rsi }));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        data-testid="stock-detail-dialog"
        className="max-w-5xl max-h-[90vh] overflow-y-auto"
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3" style={{ fontFamily: "Outfit" }}>
            <span className="text-2xl">{ticker}</span>
            {a && <SignalBadge signal={a.signal_strength} />}
          </DialogTitle>
          <DialogDescription>
            {a?.recommendation || "Loading details…"}
          </DialogDescription>
        </DialogHeader>

        {loading && (
          <div className="py-12 text-center text-muted-foreground">Loading history…</div>
        )}

        {!loading && a && (
          <div className="space-y-6">
            {/* Why this is a dip */}
            <div
              data-testid="dip-reasoning"
              className="rounded-md border border-border bg-secondary/40 p-5"
            >
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground mb-3">
                <Sparkles className="h-3.5 w-3.5" />
                Why this is a dip
              </div>
              <ul className="space-y-2 mb-4" data-testid="dip-reasons-list">
                {(a.reasons || []).map((r, i) => (
                  <li
                    key={i}
                    data-testid={`dip-reason-${i}`}
                    className="flex items-start gap-2 text-sm"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-[#b33a20] flex-shrink-0" />
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
              <div className="pt-3 border-t border-border">
                <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-1">
                  Conclusion
                </div>
                <div
                  data-testid="dip-conclusion"
                  className="flex items-center gap-2 text-base font-medium"
                  style={{ fontFamily: "Outfit" }}
                >
                  <CheckCircle2
                    className="h-4 w-4"
                    style={{
                      color:
                        a.signal_strength === "Strong"
                          ? "#b33a20"
                          : a.signal_strength === "Medium"
                          ? "#a67c00"
                          : "#337a54",
                    }}
                  />
                  {a.conclusion || a.recommendation}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 tabular-nums">
              <Stat label="Price" value={formatINR(a.price)} />
              <Stat label="Prev" value={formatINR(a.previous_price)} />
              <Stat label="52w High" value={formatINR(a.high_52w)} />
              <Stat label="Drawdown" value={formatPct(a.drawdown_percent)} accent="#b33a20" />
              <Stat label="RSI (14)" value={formatNum(a.rsi, 1)} />
              <Stat label="MA50" value={formatINR(a.ma50)} />
              <Stat label="MA200" value={formatINR(a.ma200)} />
              <Stat label="Score" value={`${formatNum(a.score, 1)}/100`} accent="#1f4236" />
            </div>

            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">
                Price · MA50 · MA200 (1y)
              </div>
              <div className="h-64 w-full" data-testid="price-chart">
                <ResponsiveContainer>
                  <LineChart data={priceData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                    <XAxis dataKey="date" hide />
                    <YAxis tick={{ fill: "#666", fontSize: 11 }} />
                    <Tooltip contentStyle={{ fontSize: 12 }} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Line type="monotone" dataKey="close" name="Close" stroke={CHART_COLORS.price} strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="ma50" name="MA50" stroke={CHART_COLORS.ma50} strokeWidth={1.5} dot={false} />
                    <Line type="monotone" dataKey="ma200" name="MA200" stroke={CHART_COLORS.ma200} strokeWidth={1.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">
                RSI (14)
              </div>
              <div className="h-44 w-full" data-testid="rsi-chart">
                <ResponsiveContainer>
                  <AreaChart data={rsiData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="rsi-gradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={CHART_COLORS.rsi} stopOpacity={0.35} />
                        <stop offset="100%" stopColor={CHART_COLORS.rsi} stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                    <XAxis dataKey="date" hide />
                    <YAxis domain={[0, 100]} tick={{ fill: "#666", fontSize: 11 }} />
                    <Tooltip contentStyle={{ fontSize: 12 }} />
                    <ReferenceLine y={70} stroke="#b33a20" strokeDasharray="4 4" label={{ value: "70", fontSize: 10, fill: "#b33a20" }} />
                    <ReferenceLine y={30} stroke="#337a54" strokeDasharray="4 4" label={{ value: "30", fontSize: 10, fill: "#337a54" }} />
                    <Area type="monotone" dataKey="rsi" stroke={CHART_COLORS.rsi} strokeWidth={2} fill="url(#rsi-gradient)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {a.components && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-border">
                <Stat label="Drawdown Score" value={formatNum(a.components.drawdown_score, 1)} />
                <Stat label="MA Score" value={formatNum(a.components.ma_score, 1)} />
                <Stat label="RSI Score" value={formatNum(a.components.rsi_score, 1)} />
                <Stat label="Confidence" value={formatNum(a.components.confidence_score, 1)} />
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

const Stat = ({ label, value, accent }) => (
  <div className="rounded-md border border-border bg-secondary/50 px-3 py-2">
    <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">{label}</div>
    <div className="text-base font-medium" style={accent ? { color: accent } : undefined}>{value}</div>
  </div>
);

export default StockDetailDialog;
