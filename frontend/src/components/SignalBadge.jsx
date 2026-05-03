import { signalClass } from "@/lib/format";

/**
 * Safe Signal Badge
 */
export const SignalBadge = ({ signal }) => {
  // 🛡️ Normalize + fallback
  const normalized =
    typeof signal === "string"
      ? signal.charAt(0).toUpperCase() + signal.slice(1).toLowerCase()
      : "Weak";

  // 🛡️ Allow only valid values
  const allowed = ["Strong", "Medium", "Weak"];
  const s = allowed.includes(normalized) ? normalized : "Weak";

  return (
    <span
      data-testid={`signal-badge-${s}`}
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium tracking-wider uppercase ${
        signalClass(s) || ""
      }`}
    >
      <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-current opacity-80" />
      {s}
    </span>
  );
};

export default SignalBadge;
