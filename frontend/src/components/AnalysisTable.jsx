import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import SignalBadge from "@/components/SignalBadge";
import { formatINR, formatPct, formatNum } from "@/lib/format";
import { TrendingDown, TrendingUp } from "lucide-react";

/**
 * Watchlist analysis table. Sorted by score desc (server-side).
 * Left-aligned text, right-aligned numerics.
 */
export const AnalysisTable = ({ rows, onRowClick }) => {
  return (
    <div className="overflow-x-auto rounded-md border border-border bg-card">
      <Table data-testid="analysis-table">
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-[140px]">Ticker</TableHead>
            <TableHead className="text-right">Price</TableHead>
            <TableHead className="text-right">Prev</TableHead>
            <TableHead className="text-right">Δ %</TableHead>
            <TableHead className="text-right">From 52w High</TableHead>
            <TableHead className="text-right">RSI</TableHead>
            <TableHead className="text-right">Score</TableHead>
            <TableHead>Signal</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r) => (
            <TableRow
              key={r.ticker}
              data-testid={`stock-row-${r.ticker}`}
              onClick={() => onRowClick?.(r.ticker)}
              className="cursor-pointer"
            >
              <TableCell className="py-4">
                <div className="font-medium">{r.ticker}</div>
                {r.is_default && (
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">default</div>
                )}
              </TableCell>
              <TableCell className="text-right tabular-nums">{formatINR(r.price)}</TableCell>
              <TableCell className="text-right tabular-nums text-muted-foreground">{formatINR(r.previous_price)}</TableCell>
              <TableCell className="text-right tabular-nums">
                <span className={`inline-flex items-center gap-1 ${(r.change_percent ?? 0) < 0 ? "text-[#b33a20]" : "text-[#337a54]"}`}>
                  {(r.change_percent ?? 0) < 0 ? <TrendingDown className="h-3 w-3" /> : <TrendingUp className="h-3 w-3" />}
                  {formatPct(r.change_percent)}
                </span>
              </TableCell>
              <TableCell className="text-right tabular-nums text-[#b33a20]">{formatPct(r.drawdown_percent)}</TableCell>
              <TableCell className="text-right tabular-nums">{formatNum(r.rsi, 1)}</TableCell>
              <TableCell className="text-right tabular-nums font-medium">
                {formatNum(r.score, 1)}
                <span className="text-xs text-muted-foreground">/100</span>
              </TableCell>
              <TableCell>
                <SignalBadge signal={r.signal_strength} />
              </TableCell>
            </TableRow>
          ))}
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                No data yet. Click refresh to analyze.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
};

export default AnalysisTable;
