import { signalClass } from "@/lib/format";

export const SignalBadge = ({ signal }) => {
  const s = signal || "Weak";
  return (
    <span
      data-testid={`signal-badge-${s}`}
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium tracking-wider uppercase ${signalClass(s)}`}
    >
      <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-current opacity-80" />
      {s}
    </span>
  );
};

export default SignalBadge;
