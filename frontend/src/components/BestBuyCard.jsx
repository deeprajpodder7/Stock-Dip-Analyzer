import { Card } from "@/components/ui/card";
import { TrendingDown, Sparkles } from "lucide-react";
import { formatINR, formatPct, formatNum } from "@/lib/format";
import SignalBadge from "@/components/SignalBadge";

/**
 * "Best Buy Today" hero card. Highlights the top-scoring dip opportunity.
 */
export const BestBuyCard = ({ best, strongCount = 0, total = 0, onOpenDetail }) => {
  // 🛡️ SAFE GUARD
  if (!best || typeof best !== "object") {
    return (
      <Card className="p-6 sm:p-8 border border-border">
        <div className="flex items-center gap-3">
          <Sparkles className="h-5 w-5 text-muted-foreground" />
          <div>
            <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
              Best Buy Today
            </div>
            <div className="text-lg font-medium">
              No meaningful dip across your watchlist.
            </div>
            <div className="text-sm text-muted-foreground mt-1">
              Markets look steady — good time to stay patient.
            </div>
          </div>
        </div>
      </Card>
    );
  }

  // 🛡️ SAFE VALUES
  const ticker = best?.ticker || "N/A";
  const price = best?.price ?? null;
  const drawdown = best?.drawdown_percent ?? null;
  const rsi = best?.rsi ?? null;
  const score = best?.score ?? 0;
  const signal = best?.signal_strength || "Weak";
  const recommendation = best?.recommendation || "No recommendation available";

  return (
    <Card
      className="p-6 sm:p-8 border border-border card-lift cursor-pointer"
      onClick={() => onOpenDetail?.(ticker)}
    >
      <div className="flex flex-col lg:flex-row lg:items-center gap-6">
        <div className="flex-1">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">
            <Sparkles className="h-3.5 w-3.5" />
            Best Buy Today
          </div>

          <div className="flex flex-wrap items-baseline gap-3">
            <div className="text-3xl sm:text-4xl font-semibold">
              {ticker}
            </div>

            <SignalBadge signal={signal} />
          </div>

          <div className="text-sm text-muted-foreground mt-2 max-w-xl">
            {recommendation}
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 tabular-nums">
          <div>
            <div className="text-xs text-muted-foreground">Price</div>
            <div className="text-lg font-medium">
              {price ? formatINR(price) : "-"}
            </div>
          </div>

          <div>
            <div className="text-xs text-muted-foreground">From 52w High</div>
            <div className="text-lg font-medium text-[#b33a20] flex items-center gap-1">
              <TrendingDown className="h-4 w-4" />
              {drawdown ? formatPct(drawdown) : "-"}
            </div>
          </div>

          <div>
            <div className="text-xs text-muted-foreground">RSI</div>
            <div className="text-lg font-medium">
              {rsi ? formatNum(rsi, 1) : "-"}
            </div>
          </div>

          <div>
            <div className="text-xs text-muted-foreground">Score</div>
            <div className="text-lg font-medium">
              {formatNum(score, 1)}
              <span className="text-xs text-muted-foreground">/100</span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 pt-6 border-t border-border flex items-center justify-between text-sm text-muted-foreground">
        <span>
          <span className="font-medium text-foreground">
            {strongCount || 0}
          </span>{" "}
          strong · tracking {total || 0} assets
        </span>
        <span className="text-xs uppercase">Click for details →</span>
      </div>
    </Card>
  );
};

export default BestBuyCard;
