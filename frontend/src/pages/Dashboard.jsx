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

      // 🛡️ SAFE GUARD
      setWatchlist(wl || { tickers: [], max_custom: 10 });

      setAnalyzeData(
        an || {
          results: [],
          best_buy_today: null,
          strong_count: 0,
        }
      );
    } catch (e) {
      toast.error("Failed to load analysis");

      // fallback safe state
      setWatchlist({ tickers: [], max_custom: 10 });
      setAnalyzeData({
        results: [],
        best_buy_today: null,
        strong_count: 0,
      });
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

      const safeResults = r?.results || [];

      setAnalyzeData({
        generated_at: r?.generated_at,
        results: safeResults,
        best_buy_today: r?.best_buy_today || null,
        strong_count: safeResults.filter(
          (x) => x?.signal_strength === "Strong"
        ).length,
      });

      toast.success("Analysis refreshed");
    } catch {
      toast.error("Refresh failed");
    } finally {
      setRefreshing(false);
    }
  };

  // 🛡️ SAFE DATA
  const results = analyzeData?.results || [];
  const strongCount = analyzeData?.strong_count || 0;
  const safeWatchlist = watchlist || { tickers: [], max_custom: 10 };

  return (
    <div className="min-h-screen flex flex-col">
      <Header lastUpdated={analyzeData?.generated_at} />

      <main className="mx-auto max-w-7xl w-full px-6 py-8 flex-1 flex flex-col gap-10">

        <RecommendedAction onOpenDetail={(t) => setSelectedTicker(t)} />

        <DiscoveryFeed
          onOpenDetail={(t) => setSelectedTicker(t)}
          onWatchlistChange={loadAll}
        />

        <InvestmentPlan onOpenDetail={(t) => setSelectedTicker(t)} />

        {/* Best Buy */}
        <section>
          <h2 className="text-lg font-medium mb-3">Your Watchlist · Best Buy</h2>

          {loading ? (
            <Card className="p-8">
              <div>Analyzing watchlist…</div>
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

        {/* Watchlist */}
        <section>
          <h2 className="text-lg font-medium">Watchlist</h2>

          <Button onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={`mr-2 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>

          <WatchlistManager
            tickers={safeWatchlist.tickers || []}
            maxCustom={safeWatchlist.max_custom || 10}
            onChanged={loadAll}
          />
        </section>

        {/* Analysis */}
        <section>
          <h2 className="text-lg font-medium mb-3">Signal Analysis</h2>

          <AnalysisTable
            rows={results}
            onRowClick={(t) => setSelectedTicker(t)}
          />
        </section>

        <footer className="text-xs text-center text-muted-foreground">
          For informational purposes only — not investment advice.
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
