import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import SignalBadge from "@/components/SignalBadge";
import { formatINR, formatPct, formatNum } from "@/lib/format";
import { TrendingDown, TrendingUp } from "lucide-react";

/**
 * Safe + crash-proof Analysis Table
 */
export const AnalysisTable = ({ rows = [], onRowClick }) => {
  // 🛡️ SAFE ARRAY
  const safeRows = Array.isArray(rows) ? rows : [];

  return (
    <div className="overflow-x-auto rounded-md border border-border bg-card">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Ticker</TableHead>
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
          {safeRows.map((r, idx) => {
            const ticker = r?.ticker || `row-${idx}`;
            const price = r?.price ?? null;
            const prev = r?.previous_price ?? null;
            const change = r?.change_percent ?? 0;
            const drawdown = r?.drawdown_percent ?? null;
            const rsi = r?.rsi ?? null;
            const score = r?.score ?? 0;
            const signal = r?.signal_strength || "Weak";

            return (
              <TableRow
                key={ticker}
                onClick={() => onRowClick?.(ticker)}
                className="cursor-pointer"
              >
                <TableCell>
                  <div className="font-medium">{ticker}</div>
                  {r?.is_default && (
                    <div className="text-xs text-muted-foreground">default</div>
                  )}
                </TableCell>

                <TableCell className="text-right">
                  {price ? formatINR(price) : "-"}
                </TableCell>

                <TableCell className="text-right text-muted-foreground">
                  {prev ? formatINR(prev) : "-"}
                </TableCell>

                <TableCell className="text-right">
                  <span
                    className={`inline-flex items-center gap-1 ${
                      change < 0 ? "text-[#b33a20]" : "text-[#337a54]"
                    }`}
                  >
                    {change < 0 ? (
                      <TrendingDown className="h-3 w-3" />
                    ) : (
                      <TrendingUp className="h-3 w-3" />
                    )}
                    {formatPct(change)}
                  </span>
                </TableCell>

                <TableCell className="text-right text-[#b33a20]">
                  {drawdown ? formatPct(drawdown) : "-"}
                </TableCell>

                <TableCell className="text-right">
                  {rsi ? formatNum(rsi, 1) : "-"}
                </TableCell>

                <TableCell className="text-right font-medium">
                  {formatNum(score, 1)}
                  <span className="text-xs text-muted-foreground">/100</span>
                </TableCell>

                <TableCell>
                  <SignalBadge signal={signal} />
                </TableCell>
              </TableRow>
            );
          })}

          {safeRows.length === 0 && (
            <TableRow>
              <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                No data yet. Click refresh.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
};

export default AnalysisTable;
