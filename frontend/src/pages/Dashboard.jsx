import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { RefreshCw } from "lucide-react";
import { toast } from "sonner";

import Header from "@/components/Header";
import BestBuyCard from "@/components/BestBuyCard";
import WatchlistManager from "@/components/WatchlistManager";
import AnalysisTable from "@/components/AnalysisTable";
import StockDetailDialog from "@/components/StockDetailDialog";
import DiscoveryFeed from "@/components/DiscoveryFeed";
import InvestmentPlan from "@/components/InvestmentPlan";
import RecommendedAction from "@/components/RecommendedAction";

import { getAnalyze, getWatchlist, refreshAll } from "@/lib/api";

export default function Dashboard() {
  const [analyzeData, setAnalyzeData] = useState(null);
  const [watchlist, setWatchlist] = useState({ tickers: [], max_custom: 10 });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState(null);

  const loadAll = useCallback(async () => {
    try {
      const [wl, an] = await Promise.all([getWatchlist(), getAnalyze()]);
      setWatchlist(wl);
      setAnalyzeData(an);
    } catch (e) {
      toast.error("Failed to load analysis");
    }
  }, []);

  useEffect(() => {
    (async () => {
      setLoading(true);
      await loadAll();
      setLoading(false);
    })();
  }, [loadAll]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const r = await refreshAll();
      setAnalyzeData({
        generated_at: r.generated_at,
        results: r.results,
        best_buy_today: r.best_buy_today,
        strong_count: r.results.filter((x) => x.signal_strength === "Strong").length,
      });
      toast.success("Analysis refreshed");
    } catch {
      toast.error("Refresh failed");
    } finally {
      setRefreshing(false);
    }
  };

  const results = analyzeData?.results ?? [];
  const strongCount = analyzeData?.strong_count ?? 0;

  return (
    <div className="min-h-screen flex flex-col">
      <Header lastUpdated={analyzeData?.generated_at} />

      <main className="mx-auto max-w-7xl w-full px-6 py-8 flex-1 flex flex-col gap-10">
        {/* Recommended Action banner - top of page */}
        <RecommendedAction onOpenDetail={(t) => setSelectedTicker(t)} />

        {/* Discovery feed - market scan hero */}
        <DiscoveryFeed
          onOpenDetail={(t) => setSelectedTicker(t)}
          onWatchlistChange={loadAll}
        />

        {/* Investment Plan */}
        <InvestmentPlan onOpenDetail={(t) => setSelectedTicker(t)} />

        {/* Best Buy (watchlist-based) */}
        <section data-testid="section-best-buy">
          <div className="flex items-baseline justify-between mb-3">
            <h2 className="text-lg font-medium" style={{ fontFamily: "Outfit" }}>
              Your Watchlist · Best Buy
            </h2>
          </div>
          {loading ? (
            <Card className="p-8 border border-border">
              <div className="text-sm text-muted-foreground uppercase tracking-[0.2em]">Analyzing watchlist…</div>
            </Card>
          ) : (
            <BestBuyCard
              best={analyzeData?.best_buy_today}
              strongCount={strongCount}
              total={results.length}
              onOpenDetail={(t) => setSelectedTicker(t)}
            />
          )}
        </section>

        {/* Watchlist manager + refresh */}
        <section className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4" data-testid="section-watchlist">
          <div>
            <h2 className="text-lg font-medium" style={{ fontFamily: "Outfit" }}>Watchlist</h2>
            <p className="text-sm text-muted-foreground">
              5 defaults always present. Add up to {watchlist.max_custom} custom NSE tickers (use the <code className="text-xs bg-muted px-1 rounded">.NS</code> suffix).
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              data-testid="refresh-data-button"
              onClick={handleRefresh}
              disabled={refreshing}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              {refreshing ? "Refreshing…" : "Refresh"}
            </Button>
          </div>
        </section>

        <section>
          <WatchlistManager
            tickers={watchlist.tickers}
            maxCustom={watchlist.max_custom}
            onChanged={loadAll}
          />
        </section>

        {/* Analysis table */}
        <section data-testid="section-analysis">
          <div className="flex items-baseline justify-between mb-3">
            <h2 className="text-lg font-medium" style={{ fontFamily: "Outfit" }}>Signal Analysis</h2>
            <div className="text-xs text-muted-foreground uppercase tracking-[0.2em]">
              Sorted by score
            </div>
          </div>
          <AnalysisTable rows={results} onRowClick={(t) => setSelectedTicker(t)} />
        </section>

        <footer className="py-6 text-center text-xs text-muted-foreground">
          Data via Yahoo Finance · Alerts via ntfy.sh · For informational purposes only — not investment advice.
        </footer>
      </main>

      <StockDetailDialog
        ticker={selectedTicker}
        open={!!selectedTicker}
        onOpenChange={(v) => !v && setSelectedTicker(null)}
      />
    </div>
  );
}
