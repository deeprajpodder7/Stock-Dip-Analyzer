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
    strong: { icon: Zap },
    medium: { icon: Clock },
    weak: { icon: Coffee },
  };

  const cfg = toneConfig[data?.tone || "weak"];
  const Icon = cfg.icon;

  const picks = data?.picks || [];

  return (
    <section>
      <Card className="p-6">
        {loading && <div>Loading...</div>}

        {!loading && (
          <>
            <div className="mb-4">
              <div className="flex items-center gap-2 text-xs uppercase">
                <Icon className="h-4 w-4" />
                Recommended Action
              </div>

              <div className="text-2xl font-semibold">
                {data?.action || "Wait"}
              </div>

              <p className="text-sm">
                {data?.message || "No recommendation available"}
              </p>

              <Button onClick={load} disabled={loading} size="sm">
                <RefreshCw className="mr-1 h-4 w-4" />
                Refresh
              </Button>
            </div>

            {picks.length === 0 ? (
              <div>No opportunities right now</div>
            ) : (
              <div className="grid gap-3">
                {picks.map((p) => (
                  <button
                    key={p?.ticker}
                    onClick={() => onOpenDetail?.(p?.ticker)}
                    className="border p-3 rounded text-left"
                  >
                    <div className="flex justify-between">
                      <div>
                        <div>{p?.ticker}</div>
                      </div>
                      <div>{formatNum(p?.score, 1)}</div>
                    </div>

                    <div className="flex gap-4 text-xs mt-2">
                      <div>{formatINR(p?.price)}</div>
                      <div>{formatPct(p?.drawdown_percent)}</div>
                      <div>{formatNum(p?.rsi, 1)}</div>
                    </div>

                    <div className="text-xs mt-2 flex items-center">
                      View <ArrowRight className="ml-1 h-3 w-3" />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </Card>
    </section>
  );
};

export default RecommendedAction;
