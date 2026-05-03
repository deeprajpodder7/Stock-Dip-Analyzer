import { useEffect, useState } from "react";
import { Bell, Clock, Radio } from "lucide-react";
import { getStatus, sendTestNotification } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export const Header = ({ lastUpdated }) => {
  const [status, setStatus] = useState(null);
  const [sending, setSending] = useState(false);

  const loadStatus = async () => {
    try {
      const s = await getStatus();

      // 🛡️ SAFE DEFAULT
      setStatus(
        s || {
          scheduler: { running: false },
          notifier: { enabled: false },
        }
      );
    } catch {
      setStatus({
        scheduler: { running: false },
        notifier: { enabled: false },
      });
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

      if (r?.ok) {
        toast.success(`Test alert sent`);
      } else {
        toast.error("Notification failed");
      }
    } catch {
      toast.error("Notification failed");
    } finally {
      setSending(false);
    }
  };

  // 🛡️ SAFE VALUES
  const schedOk = status?.scheduler?.running || false;
  const notifOk = status?.notifier?.enabled || false;

  const nextRun = status?.scheduler?.next_run;
  const topic = status?.notifier?.topic;

  const safeTime = lastUpdated
    ? new Date(lastUpdated).toLocaleTimeString()
    : null;

  const nextRunText =
    nextRun && !isNaN(new Date(nextRun))
      ? new Date(nextRun).toLocaleString()
      : "";

  return (
    <header className="sticky top-0 border-b bg-background/80 backdrop-blur">
      <div className="mx-auto max-w-7xl px-6 py-5 flex justify-between">

        {/* LEFT */}
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-md bg-primary text-white flex items-center justify-center">
            <Radio className="h-5 w-5" />
          </div>

          <div>
            <h1 className="text-xl font-semibold">
              Stock Dip Analyzer
            </h1>
            <p className="text-xs text-muted-foreground">
              Signal-based investing
            </p>
          </div>
        </div>

        {/* RIGHT */}
        <div className="flex items-center gap-4">

          {/* Scheduler */}
          <div title={nextRunText} className="flex items-center gap-2 text-xs">
            <Clock className="h-4 w-4" />
            <span
              className={`h-2 w-2 rounded-full ${
                schedOk ? "bg-green-500" : "bg-red-500"
              }`}
            />
            Scheduler
          </div>

          {/* Notifier */}
          <div title={topic || ""} className="flex items-center gap-2 text-xs">
            <Bell className="h-4 w-4" />
            <span
              className={`h-2 w-2 rounded-full ${
                notifOk ? "bg-green-500" : "bg-red-500"
              }`}
            />
            Ntfy
          </div>

          {/* Last Updated */}
          {safeTime && (
            <div className="text-xs">
              Updated {safeTime}
            </div>
          )}

          {/* Button */}
          <Button onClick={testNotify} disabled={sending}>
            <Bell className="mr-1 h-4 w-4" />
            {sending ? "Sending..." : "Test"}
          </Button>
        </div>
      </div>
    </header>
  );
};

export default Header;
