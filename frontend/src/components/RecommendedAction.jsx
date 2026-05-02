import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Zap, TrendingDown, Clock, Coffee, ArrowRight, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { getRecommendedAction } from "@/lib/api";
import { formatINR, formatPct, formatNum } from "@/lib/format";

/**
 * Top-of-dashboard "Recommended Action" banner.
 * - score >= 70 → Buy Now (strong/red)
 * - score 60-70 → Accumulate Slowly (medium/ochre)
 * - else → No good opportunities today (weak/sage)
 */
export const RecommendedAction = ({ onOpenDetail }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      setData(await getRecommendedAction());
    } catch {
      toast.error("Failed to load recommendation");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  // Tone-specific styles and icon
  const toneConfig = {
    strong: {
      icon: Zap,
      iconColor: "#b33a20",
      bgClass: "signal-strong",
      accent: "#b33a20",
    },
    medium: {
      icon: Clock,
      iconColor: "#a67c00",
      bgClass: "signal-medium",
      accent: "#a67c00",
    },
    weak: {
      icon: Coffee,
      iconColor: "#337a54",
      bgClass: "signal-weak",
      accent: "#337a54",
    },
  };

  const cfg = toneConfig[data?.tone ?? "weak"];
  const Icon = cfg.icon;

  return (
    <section data-testid="section-recommended-action">
      <Card
        data-testid="recommended-action-card"
        className={`border overflow-hidden ${loading ? "p-8" : "p-0"}`}
      >
        {loading && !data && (
          <div className="text-sm text-muted-foreground uppercase tracking-[0.2em]">
            Checking market…
          </div>
        )}

        {data && (
          <div className="flex flex-col lg:flex-row">
            {/* Left: action badge */}
            <div
              className={`${cfg.bgClass} p-6 sm:p-8 lg:w-[340px] flex flex-col justify-between border-r border-border/50`}
            >
              <div>
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.25em] opacity-80 mb-3">
                  <Icon className="h-3.5 w-3.5" />
                  Recommended Action
                </div>
                <div
                  data-testid="recommended-action-label"
                  className="text-3xl sm:text-4xl font-semibold tracking-tight leading-tight"
                  style={{ fontFamily: "Outfit" }}
                >
                  {data.action}
                </div>
                <p className="text-sm mt-3 opacity-80" data-testid="recommended-action-message">
                  {data.message}
                </p>
              </div>
              <Button
                data-testid="recommended-action-refresh"
                variant="ghost"
                size="sm"
                onClick={load}
                disabled={loading}
                className="mt-6 self-start hover:bg-black/5"
              >
                <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
                Re-check
              </Button>
            </div>

            {/* Right: top picks */}
            <div className="flex-1 p-6 sm:p-8">
              {data.picks.length === 0 ? (
                <div
                  data-testid="recommended-no-picks"
                  className="h-full flex flex-col justify-center"
                >
                  <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">
                    What to do
                  </div>
                  <p className="text-base text-foreground max-w-md">
                    No stocks are trading in a meaningful dip zone right now. Don't chase —
                    keep your SIPs running and re-check in a few hours.
                  </p>
                </div>
              ) : (
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-3">
                    Top {data.picks.length === 1 ? "pick" : "picks"}
                  </div>
                  <div
                    data-testid="recommended-picks"
                    className="grid grid-cols-1 sm:grid-cols-2 gap-3"
                  >
                    {data.picks.map((p) => (
                      <button
                        key={p.ticker}
                        data-testid={`recommended-pick-${p.ticker}`}
                        onClick={() => onOpenDetail?.(p.ticker)}
                        className="text-left rounded-md border border-border bg-secondary/30 p-4 hover:bg-secondary transition-colors group"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div>
                            <div
                              className="text-lg font-semibold"
                              style={{ fontFamily: "Outfit" }}
                            >
                              {p.name}
                            </div>
                            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                              {p.ticker}
                            </div>
                          </div>
                          <div className="text-right tabular-nums">
                            <div
                              className="text-2xl font-semibold"
                              style={{ fontFamily: "Outfit", color: cfg.accent }}
                            >
                              {formatNum(p.score, 1)}
                            </div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider">
                              score
                            </div>
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-2 tabular-nums text-xs pt-2 border-t border-border">
                          <div>
                            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Price</div>
                            <div className="font-medium">{formatINR(p.price)}</div>
                          </div>
                          <div>
                            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">52w ↓</div>
                            <div className="font-medium text-[#b33a20] flex items-center gap-0.5">
                              <TrendingDown className="h-3 w-3" />
                              {formatPct(p.drawdown_percent)}
                            </div>
                          </div>
                          <div>
                            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">RSI</div>
                            <div className="font-medium">{formatNum(p.rsi, 1)}</div>
                          </div>
                        </div>
                        <div className="flex items-center justify-end mt-3 text-xs text-muted-foreground group-hover:text-foreground transition-colors">
                          View details <ArrowRight className="ml-1 h-3 w-3" />
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </Card>
    </section>
  );
};

export default RecommendedAction;
