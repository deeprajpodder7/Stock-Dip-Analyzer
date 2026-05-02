import { useEffect, useState } from "react";
import { Bell, Clock, Radio } from "lucide-react";
import { getStatus, sendTestNotification } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

/**
 * Header with app title, status indicators (scheduler + ntfy), and test-notify button.
 */
export const Header = ({ lastUpdated }) => {
  const [status, setStatus] = useState(null);
  const [sending, setSending] = useState(false);

  const loadStatus = async () => {
    try {
      const s = await getStatus();
      setStatus(s);
    } catch {
      setStatus(null);
    }
  };

  useEffect(() => {
    loadStatus();
    const t = setInterval(loadStatus, 60000);
    return () => clearInterval(t);
  }, []);

  const testNotify = async () => {
    setSending(true);
    try {
      const r = await sendTestNotification();
      if (r.ok) {
        toast.success(`Test alert sent to ntfy.sh/${r.topic}`);
      } else {
        toast.error("Test notification failed (check ntfy topic)");
      }
    } catch (e) {
      toast.error("Test notification failed");
    } finally {
      setSending(false);
    }
  };

  const schedOk = status?.scheduler?.running;
  const notifOk = status?.notifier?.enabled;

  return (
    <header
      data-testid="app-header"
      className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur"
    >
      <div className="mx-auto max-w-7xl px-6 py-5 flex items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-md bg-primary text-primary-foreground flex items-center justify-center">
            <Radio className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-semibold tracking-tight" style={{ fontFamily: "Outfit" }}>
              Stock Dip Analyzer
            </h1>
            <p className="text-xs text-muted-foreground uppercase tracking-[0.2em]">
              Long-term India · Signal quality first
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div
            data-testid="status-scheduler"
            className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground"
            title={status?.scheduler?.next_run ? `Next run: ${new Date(status.scheduler.next_run).toLocaleString()}` : ""}
          >
            <Clock className="h-3.5 w-3.5" />
            <span
              className={`dot-pulse h-2 w-2 rounded-full ${schedOk ? "bg-emerald-500" : "bg-red-500"}`}
            />
            <span className="uppercase tracking-wider">Scheduler</span>
          </div>

          <div
            data-testid="status-notifier"
            className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground"
            title={status?.notifier?.topic ? `ntfy topic: ${status.notifier.topic}` : ""}
          >
            <Bell className="h-3.5 w-3.5" />
            <span
              className={`dot-pulse h-2 w-2 rounded-full ${notifOk ? "bg-emerald-500" : "bg-red-500"}`}
            />
            <span className="uppercase tracking-wider">Ntfy</span>
          </div>

          {lastUpdated && (
            <div className="hidden md:block text-xs text-muted-foreground" data-testid="last-updated">
              Updated {new Date(lastUpdated).toLocaleTimeString()}
            </div>
          )}

          <Button
            data-testid="test-notification-button"
            variant="outline"
            size="sm"
            onClick={testNotify}
            disabled={sending}
          >
            <Bell className="mr-1.5 h-3.5 w-3.5" />
            {sending ? "Sending…" : "Test Alert"}
          </Button>
        </div>
      </div>
    </header>
  );
};

export default Header;
