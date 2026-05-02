import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { TrendingDown, Plus, Check, Flame, RefreshCw } from "lucide-react";
import SignalBadge from "@/components/SignalBadge";
import { formatINR, formatPct, formatNum } from "@/lib/format";
import { getDiscover, addTicker } from "@/lib/api";
import { toast } from "sonner";

/**
 * Discovery feed: scans curated NSE universe and shows top-scored dip opportunities.
 */
export const DiscoveryFeed = ({ onOpenDetail, onWatchlistChange }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [includeWeak, setIncludeWeak] = useState(false);
  const [addingTicker, setAddingTicker] = useState(null);

  const load = async (weak = includeWeak) => {
    setLoading(true);
    try {
      const d = await getDiscover(12, weak);
      setData(d);
    } catch {
      toast.error("Failed to load market discovery");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleWeak = (v) => {
    setIncludeWeak(v);
    load(v);
  };

  const handleAdd = async (ticker, e) => {
    e.stopPropagation();
    setAddingTicker(ticker);
    try {
      await addTicker(ticker);
      toast.success(`${ticker} added to watchlist`);
      // Refresh discover to update in_watchlist flags
      await load(includeWeak);
      onWatchlistChange?.();
    } catch (err) {
      const msg = err?.response?.data?.detail || "Failed to add ticker";
      toast.error(msg);
    } finally {
      setAddingTicker(null);
    }
  };

  const results = data?.results ?? [];
  const strongCount = data?.strong_count ?? 0;

  return (
    <section data-testid="section-discovery" className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground mb-1">
            <Flame className="h-3.5 w-3.5 text-[#b33a20]" />
            Top Dip Opportunities · Market scan
          </div>
          <h2
            className="text-2xl sm:text-3xl font-semibold tracking-tight"
            style={{ fontFamily: "Outfit" }}
          >
            Best scored right now
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Live scoring across {data?.universe_size ?? "—"} curated NSE stocks and ETFs ·
            <span className="text-[#b33a20] font-medium ml-1">
              {strongCount} strong
            </span>{" "}
            signal{strongCount === 1 ? "" : "s"} detected
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Switch
              id="include-weak-toggle"
              data-testid="include-weak-toggle"
              checked={includeWeak}
              onCheckedChange={toggleWeak}
            />
            <Label
              htmlFor="include-weak-toggle"
              className="text-xs uppercase tracking-wider cursor-pointer"
            >
              Show weak
            </Label>
          </div>
          <Button
            data-testid="discovery-refresh-button"
            variant="outline"
            size="sm"
            onClick={() => load(includeWeak)}
            disabled={loading}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {loading && !data && (
        <Card className="p-8 border border-border">
          <div className="text-sm text-muted-foreground uppercase tracking-[0.2em]">
            Scanning market…
          </div>
        </Card>
      )}

      {!loading && results.length === 0 && (
        <Card
          className="p-8 border border-border"
          data-testid="discovery-empty"
        >
          <div className="text-sm text-muted-foreground">
            No Medium or Strong dips in the scanned universe right now. Toggle "Show weak" to see the
            full ranking.
          </div>
        </Card>
      )}

      {results.length > 0 && (
        <div
          data-testid="discovery-grid"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
        >
          {results.map((r, idx) => (
            <Card
              key={r.ticker}
              data-testid={`discovery-card-${r.ticker}`}
              className="p-5 border border-border card-lift cursor-pointer relative overflow-hidden"
              onClick={() => onOpenDetail?.(r.ticker)}
            >
              <div className="absolute top-3 right-3 text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                #{idx + 1}
              </div>

              <div className="flex items-start justify-between gap-2 mb-3">
                <div>
                  <div
                    className="text-lg font-semibold tracking-tight"
                    style={{ fontFamily: "Outfit" }}
                  >
                    {r.ticker.replace(".NS", "")}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    {r.ticker}
                  </div>
                </div>
                <SignalBadge signal={r.signal_strength} />
              </div>

              <div className="grid grid-cols-3 gap-3 tabular-nums mb-4">
                <div>
                  <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                    Price
                  </div>
                  <div className="text-sm font-medium">{formatINR(r.price)}</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                    52w ↓
                  </div>
                  <div className="text-sm font-medium text-[#b33a20] flex items-center gap-0.5">
                    <TrendingDown className="h-3 w-3" />
                    {formatPct(r.drawdown_percent)}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                    RSI
                  </div>
                  <div className="text-sm font-medium">{formatNum(r.rsi, 1)}</div>
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-border">
                <div className="flex items-baseline gap-1">
                  <span
                    className="text-2xl font-semibold tabular-nums"
                    style={{ fontFamily: "Outfit" }}
                  >
                    {formatNum(r.score, 1)}
                  </span>
                  <span className="text-xs text-muted-foreground">/100</span>
                </div>
                {r.in_watchlist ? (
                  <span
                    data-testid={`in-watchlist-${r.ticker}`}
                    className="inline-flex items-center gap-1 text-xs text-[#337a54] font-medium"
                  >
                    <Check className="h-3.5 w-3.5" /> In watchlist
                  </span>
                ) : (
                  <Button
                    data-testid={`add-to-watchlist-${r.ticker}`}
                    size="sm"
                    variant="secondary"
                    onClick={(e) => handleAdd(r.ticker, e)}
                    disabled={addingTicker === r.ticker}
                  >
                    <Plus className="mr-1 h-3.5 w-3.5" />
                    {addingTicker === r.ticker ? "Adding…" : "Watch"}
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </section>
  );
};

export default DiscoveryFeed;
