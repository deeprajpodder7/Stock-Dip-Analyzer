import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Flame, RefreshCw } from "lucide-react";
import SignalBadge from "@/components/SignalBadge";
import { formatINR, formatPct, formatNum } from "@/lib/format";
import { getDiscover, addTicker } from "@/lib/api";
import { toast } from "sonner";

export const DiscoveryFeed = ({ onOpenDetail, onWatchlistChange }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [includeWeak, setIncludeWeak] = useState(false);
  const [addingTicker, setAddingTicker] = useState(null);

  const load = async (weak = includeWeak) => {
    setLoading(true);
    try {
      const d = await getDiscover(12, weak);

      setData(
        d || {
          results: [],
          strong_count: 0,
          universe_size: 0,
        }
      );
    } catch {
      toast.error("Failed to load market discovery");
      setData({
        results: [],
        strong_count: 0,
        universe_size: 0,
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(false);
  }, []);

  const toggleWeak = (v) => {
    setIncludeWeak(v);
    load(v);
  };

  const handleAdd = async (ticker, e) => {
    e.stopPropagation();
    if (!ticker) return;

    setAddingTicker(ticker);
    try {
      await addTicker(ticker);
      toast.success(`${ticker} added`);
      await load(includeWeak);
      onWatchlistChange?.();
    } catch (err) {
      const msg = err?.response?.data?.detail || "Failed to add ticker";
      toast.error(msg);
    } finally {
      setAddingTicker(null);
    }
  };

  const results = Array.isArray(data?.results) ? data.results : [];
  const strongCount = data?.strong_count || 0;
  const universeSize = data?.universe_size || 0;

  return (
    <section className="space-y-4">
      <div className="flex justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs">
            <Flame className="h-4 w-4" />
            Market Scan
          </div>
          <h2 className="text-xl font-semibold">Best scored right now</h2>
          <p className="text-sm">
            {strongCount} strong · scanning {universeSize}
          </p>
        </div>

        <div className="flex gap-2">
          <Switch checked={includeWeak} onCheckedChange={toggleWeak} />
          <Button onClick={() => load(includeWeak)} disabled={loading}>
            <RefreshCw className={loading ? "animate-spin" : ""} />
          </Button>
        </div>
      </div>

      {loading && <Card className="p-4">Loading...</Card>}

      {results.length === 0 && !loading && (
        <Card className="p-4">No opportunities</Card>
      )}

      {results.map((r, idx) => {
        const ticker = r?.ticker || `t-${idx}`;

        return (
          <Card
            key={ticker}
            className="p-4 cursor-pointer"
            onClick={() => onOpenDetail?.(ticker)}
          >
            <div className="flex justify-between">
              <div>
                <div>{ticker}</div>
                <div>{formatINR(r?.price)}</div>
              </div>
              <SignalBadge signal={r?.signal_strength} />
            </div>

            <div className="text-sm mt-2">
              Score: {formatNum(r?.score ?? 0, 1)}
            </div>

            {!r?.in_watchlist && (
              <Button
                size="sm"
                onClick={(e) => handleAdd(ticker, e)}
                disabled={addingTicker === ticker}
              >
                Add
              </Button>
            )}
          </Card>
        );
      })}
    </section>
  );
};

export default DiscoveryFeed;
