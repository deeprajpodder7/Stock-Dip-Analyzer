import { useState } from "react";
import { addTicker, removeTicker } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Plus, X } from "lucide-react";
import { toast } from "sonner";

/**
 * Add/remove custom tickers. Defaults are shown but not removable.
 */
export const WatchlistManager = ({ tickers = [], onChanged, maxCustom = 5 }) => {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);

  // 🛡️ SAFE GUARD
  const safeTickers = Array.isArray(tickers) ? tickers : [];

  const customCount = safeTickers.filter((t) => !t?.is_default).length;

  const handleAdd = async (e) => {
    e.preventDefault();
    const raw = value.trim().toUpperCase();
    if (!raw) return;

    setBusy(true);
    try {
      await addTicker(raw);
      toast.success(`Added ${raw}`);
      setValue("");
      onChanged?.();
    } catch (err) {
      const msg = err?.response?.data?.detail || "Failed to add ticker";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  };

  const handleRemove = async (ticker) => {
    if (!ticker) return;

    setBusy(true);
    try {
      await removeTicker(ticker);
      toast.success(`Removed ${ticker}`);
      onChanged?.();
    } catch (err) {
      const msg = err?.response?.data?.detail || "Failed to remove ticker";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="watchlist-manager" className="flex flex-col gap-4">
      {/* ADD FORM */}
      <form onSubmit={handleAdd} className="flex items-center gap-2">
        <Input
          data-testid="add-ticker-input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="e.g. HDFCBANK.NS"
          className="max-w-xs"
          disabled={busy || customCount >= maxCustom}
        />

        <Button
          data-testid="add-ticker-button"
          type="submit"
          disabled={busy || !value.trim() || customCount >= maxCustom}
        >
          <Plus className="mr-1 h-4 w-4" /> Add
        </Button>

        <span
          className="text-xs text-muted-foreground ml-2"
          data-testid="watchlist-count"
        >
          {customCount}/{maxCustom} custom
        </span>
      </form>

      {/* TICKER LIST */}
      <div className="flex flex-wrap gap-2">
        {(safeTickers || []).map((t) => (
          <span
            key={t?.ticker || Math.random()}
            data-testid={`ticker-chip-${t?.ticker}`}
            className={`inline-flex items-center gap-1.5 rounded-full border border-border bg-secondary px-3 py-1 text-xs font-medium ${
              t?.is_default ? "opacity-90" : ""
            }`}
          >
            {t?.ticker || "N/A"}

            {t?.is_default ? (
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                default
              </span>
            ) : (
              <button
                data-testid={`remove-ticker-${t?.ticker}`}
                onClick={() => handleRemove(t?.ticker)}
                disabled={busy}
                className="ml-1 rounded-full p-0.5 hover:bg-destructive/10 hover:text-destructive transition-colors"
                aria-label={`Remove ${t?.ticker}`}
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </span>
        ))}
      </div>
    </div>
  );
};

export default WatchlistManager;
