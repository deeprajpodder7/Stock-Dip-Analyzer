import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Wallet, PieChart, RefreshCw, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import SignalBadge from "@/components/SignalBadge";
import { formatINR, formatNum } from "@/lib/format";
import { getInvestmentPlan } from "@/lib/api";

/**
 * Investment Plan section — allocates a small budget (default ₹5000) across top 1-2
 * qualifying dip opportunities (score >= 60). Falls back to NIFTYBEES if none qualify.
 */
export const InvestmentPlan = ({ onOpenDetail }) => {
  const [budget, setBudget] = useState(5000);
  const [pendingBudget, setPendingBudget] = useState("5000");
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async (b = budget) => {
    setLoading(true);
    try {
      const data = await getInvestmentPlan(b);
      setPlan(data);
    } catch (e) {
      const msg = e?.response?.data?.detail || "Failed to build investment plan";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(budget);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const apply = (e) => {
    e.preventDefault();
    const n = parseInt(pendingBudget, 10);
    if (Number.isNaN(n) || n < 500) {
      toast.error("Budget must be at least ₹500");
      return;
    }
    setBudget(n);
    load(n);
  };

  const allocations = plan?.allocations ?? [];
  const fallback = allocations[0]?.is_fallback;

  // Color per allocation stripe (primary + accent palette)
  const STRIPE = ["#1f4236", "#a67c00"];

  return (
    <section data-testid="section-investment-plan" className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground mb-1">
            <Wallet className="h-3.5 w-3.5" />
            Investment Plan
          </div>
          <h2
            className="text-2xl sm:text-3xl font-semibold tracking-tight"
            style={{ fontFamily: "Outfit" }}
          >
            Where to put {formatINR(budget)} today
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Concentrated allocation across up to 2 high-quality dips (score ≥ 60). Higher score → more money.
          </p>
        </div>

        <form onSubmit={apply} className="flex items-center gap-2">
          <div className="flex items-center rounded-md border border-border bg-card px-2">
            <span className="text-muted-foreground text-sm pr-1">₹</span>
            <Input
              data-testid="plan-budget-input"
              value={pendingBudget}
              onChange={(e) => setPendingBudget(e.target.value.replace(/[^0-9]/g, ""))}
              className="border-0 focus-visible:ring-0 px-1 w-24 tabular-nums"
              inputMode="numeric"
            />
          </div>
          <Button
            data-testid="plan-apply-button"
            type="submit"
            size="sm"
            variant="outline"
            disabled={loading}
          >
            Update
          </Button>
          <Button
            data-testid="plan-refresh-button"
            type="button"
            size="sm"
            variant="outline"
            onClick={() => load(budget)}
            disabled={loading}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </form>
      </div>

      <Card className="p-6 sm:p-7 border border-border">
        {loading && !plan && (
          <div className="text-sm text-muted-foreground uppercase tracking-[0.2em] py-6">
            Building plan…
          </div>
        )}

        {plan && (
          <div className="space-y-5">
            {/* Allocation bar */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                <PieChart className="h-3.5 w-3.5" />
                Allocation
              </div>
              <div
                data-testid="plan-allocation-bar"
                className="flex w-full h-3 rounded-full overflow-hidden border border-border"
              >
                {allocations.map((a, i) => (
                  <div
                    key={a.ticker}
                    className="h-full transition-all"
                    style={{
                      width: `${a.percent}%`,
                      backgroundColor: fallback ? "#337a54" : STRIPE[i] || "#666",
                    }}
                    title={`${a.name}: ${a.percent}%`}
                  />
                ))}
              </div>
            </div>

            {/* Allocations list */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4" data-testid="plan-allocations">
              {allocations.map((a, i) => (
                <button
                  key={a.ticker}
                  data-testid={`plan-allocation-${a.ticker}`}
                  onClick={() => onOpenDetail?.(a.ticker)}
                  className="text-left rounded-md border border-border bg-secondary/30 p-4 hover:bg-secondary transition-colors group"
                >
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span
                          className="h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: fallback ? "#337a54" : STRIPE[i] || "#666" }}
                        />
                        <span
                          className="text-lg font-semibold"
                          style={{ fontFamily: "Outfit" }}
                        >
                          {a.name}
                        </span>
                      </div>
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground mt-0.5">
                        {a.ticker}
                      </div>
                    </div>
                    {a.signal_strength && <SignalBadge signal={a.signal_strength} />}
                  </div>

                  <div className="flex items-baseline gap-2 mb-3">
                    <span
                      className="text-3xl font-semibold tabular-nums"
                      style={{ fontFamily: "Outfit" }}
                    >
                      {formatINR(a.amount)}
                    </span>
                    <span className="text-xs text-muted-foreground tabular-nums">
                      {a.percent}%
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 tabular-nums text-xs pt-3 border-t border-border">
                    <div>
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                        Price
                      </div>
                      <div className="font-medium">{formatINR(a.price)}</div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                        Score
                      </div>
                      <div className="font-medium">
                        {a.score != null ? formatNum(a.score, 1) : "—"}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                        Shares
                      </div>
                      <div className="font-medium">≈ {a.estimated_shares ?? "—"}</div>
                    </div>
                  </div>

                  <div className="flex items-center justify-end mt-3 text-xs text-muted-foreground group-hover:text-foreground transition-colors">
                    View details <ArrowRight className="ml-1 h-3 w-3" />
                  </div>
                </button>
              ))}
            </div>

            {/* Reason */}
            <div
              data-testid="plan-reason"
              className={`rounded-md border p-3 text-sm ${
                fallback
                  ? "signal-weak"
                  : "bg-secondary/40 border-border text-foreground"
              }`}
            >
              {plan.reason}
            </div>

            <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t border-border">
              <span data-testid="plan-total">
                Total allocated:{" "}
                <span className="text-foreground font-medium tabular-nums">
                  {formatINR(plan.total_allocated)}
                </span>
              </span>
              <span>
                <span className="text-foreground font-medium tabular-nums">
                  {plan.qualifying_count}
                </span>{" "}
                qualifying dip{plan.qualifying_count === 1 ? "" : "s"} found
              </span>
            </div>
          </div>
        )}
      </Card>
    </section>
  );
};

export default InvestmentPlan;
