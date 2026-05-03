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

      setWatchlist(wl || { tickers: [], max_custom: 10 });

      const results = an?.results || [];

      setAnalyzeData({
        generated_at: new Date().toISOString(),
        results,
        best_buy_today:
          results.sort((a, b) => b.score - a.score)[0] || null,
        strong_count: results.filter(
          (x) => x?.signal_strength === "Strong"
        ).length,
      });
    } catch {
      toast.error("Failed to load analysis");
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
        best_buy_today:
          safeResults.sort((a, b) => b.score - a.score)[0] || null,
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

  const results = analyzeData?.results || [];
  const strongCount = analyzeData?.strong_count || 0;
  const safeWatchlist = watchlist || { tickers: [], max_custom: 10 };

  return (
    <div className="min-h-screen flex flex-col bg-muted/30">
      <Header lastUpdated={analyzeData?.generated_at} />

      <main className="mx-auto max-w-7xl w-full px-6 py-8 flex flex-col gap-10">

        {/* 🔥 HERO */}
        <RecommendedAction onOpenDetail={setSelectedTicker} />

        {/* 🧠 INSIGHTS GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <DiscoveryFeed
            onOpenDetail={setSelectedTicker}
            onWatchlistChange={loadAll}
          />
          <InvestmentPlan onOpenDetail={setSelectedTicker} />
        </div>

        {/* ⭐ BEST BUY */}
        <section>
          <h2 className="text-lg font-semibold mb-3">
            Best Opportunity from Watchlist
          </h2>

          {loading ? (
            <Card className="p-8">Analyzing watchlist…</Card>
          ) : (
            <BestBuyCard
              best={analyzeData?.best_buy_today}
              strongCount={strongCount}
              total={results.length}
              onOpenDetail={setSelectedTicker}
            />
          )}
        </section>

        {/* ⚙️ WATCHLIST + ANALYSIS */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Watchlist */}
          <Card className="p-5 flex flex-col gap-4">
            <div className="flex justify-between items-center">
              <h2 className="font-semibold">Watchlist</h2>

              <Button
                onClick={handleRefresh}
                disabled={refreshing}
                size="sm"
              >
                <RefreshCw
                  className={`mr-2 ${refreshing ? "animate-spin" : ""}`}
                />
                Refresh
              </Button>
            </div>

            <WatchlistManager
              tickers={safeWatchlist.tickers || []}
              maxCustom={safeWatchlist.max_custom || 10}
              onChanged={loadAll}
            />
          </Card>

          {/* Analysis */}
          <div className="lg:col-span-2">
            <Card className="p-5">
              <h2 className="font-semibold mb-4">Signal Analysis</h2>

              <AnalysisTable
                rows={results}
                onRowClick={setSelectedTicker}
              />
            </Card>
          </div>

        </div>

        {/* Footer */}
        <footer className="text-xs text-center text-muted-foreground pt-4">
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
