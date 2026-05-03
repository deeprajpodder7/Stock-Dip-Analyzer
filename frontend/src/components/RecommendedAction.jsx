import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Zap, Clock, Coffee, ArrowRight, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { getRecommendedAction } from "@/lib/api";
import { formatINR, formatPct, formatNum } from "@/lib/format";

export const RecommendedAction = ({ onOpenDetail }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getRecommendedAction();
      setData(res || {});
    } catch {
      toast.error("Failed to load recommendation");
      setData({});
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const toneConfig = {
    strong: {
      icon: Zap,
      bg: "bg-green-50 border-green-200",
      text: "text-green-700",
    },
    medium: {
      icon: Clock,
      bg: "bg-yellow-50 border-yellow-200",
      text: "text-yellow-700",
    },
    weak: {
      icon: Coffee,
      bg: "bg-gray-50 border-gray-200",
      text: "text-gray-600",
    },
  };

  const tone = data?.tone || "weak";
  const cfg = toneConfig[tone];
  const Icon = cfg.icon;

  const picks = data?.picks || [];
  const topPick = picks[0];

  return (
    <section>
      <Card className={`p-6 rounded-2xl border ${cfg.bg}`}>
        {loading && <div>Loading...</div>}

        {!loading && (
          <div className="space-y-5">

            {/* 🔥 HERO ACTION */}
            <div className="flex items-start justify-between">
              <div>
                <div className={`flex items-center gap-2 text-xs uppercase ${cfg.text}`}>
                  <Icon className="h-4 w-4" />
                  Recommended Action
                </div>

                <div className="text-3xl font-semibold mt-1">
                  {data?.action || "Wait"}
                </div>

                <p className="text-sm text-muted-foreground mt-1">
                  {data?.message || "No recommendation available"}
                </p>
              </div>

              <Button onClick={load} disabled={loading} size="sm" variant="outline">
                <RefreshCw className="mr-1 h-4 w-4" />
                Refresh
              </Button>
            </div>

            {/* ⭐ TOP PICK */}
            {topPick && (
              <div
                onClick={() => onOpenDetail?.(topPick?.ticker)}
                className="p-4 rounded-xl border bg-white shadow-sm cursor-pointer hover:shadow-md transition"
              >
                <div className="flex justify-between items-center">
                  <div>
                    <div className="text-lg font-semibold">
                      {topPick.ticker}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Top opportunity
                    </div>
                  </div>

                  <div className="text-lg font-semibold">
                    {formatNum(topPick.score, 1)}
                  </div>
                </div>

                <div className="flex gap-5 text-sm mt-3">
                  <div>{formatINR(topPick.price)}</div>
                  <div className="text-red-600">
                    {formatPct(topPick.drawdown_percent)}
                  </div>
                  <div>{formatNum(topPick.rsi, 1)}</div>
                </div>
              </div>
            )}

            {/* 📊 OTHER PICKS */}
            {picks.length > 1 && (
              <div className="grid gap-3">
                {picks.slice(1).map((p) => (
                  <div
                    key={p?.ticker}
                    onClick={() => onOpenDetail?.(p?.ticker)}
                    className="p-3 rounded-lg border bg-white cursor-pointer hover:bg-muted/30 transition"
                  >
                    <div className="flex justify-between">
                      <div className="font-medium">{p?.ticker}</div>
                      <div>{formatNum(p?.score, 1)}</div>
                    </div>

                    <div className="flex gap-4 text-xs mt-2 text-muted-foreground">
                      <div>{formatINR(p?.price)}</div>
                      <div>{formatPct(p?.drawdown_percent)}</div>
                      <div>{formatNum(p?.rsi, 1)}</div>
                    </div>

                    <div className="text-xs mt-2 flex items-center">
                      View <ArrowRight className="ml-1 h-3 w-3" />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {picks.length === 0 && (
              <div className="text-sm text-muted-foreground">
                No strong opportunities right now. Stay patient.
              </div>
            )}

          </div>
        )}
      </Card>
    </section>
  );
};

export default RecommendedAction;
