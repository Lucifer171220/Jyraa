'use client';

type BrandMarkProps = {
  showWordmark?: boolean;
  compact?: boolean;
  className?: string;
};

export function BrandMark({
  showWordmark = true,
  compact = false,
  className = '',
}: BrandMarkProps) {
  return (
    <div className={`flex items-center ${compact ? 'gap-3' : 'gap-4'} ${className}`}>
      <div className="relative flex h-11 w-11 items-center justify-center overflow-hidden rounded-2xl bg-slate-950 shadow-[0_12px_30px_rgba(15,23,42,0.24)]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_25%_20%,rgba(45,212,191,0.75),transparent_42%),radial-gradient(circle_at_80%_75%,rgba(59,130,246,0.72),transparent_48%)]" />
        <svg
          viewBox="0 0 48 48"
          aria-hidden="true"
          className="relative h-8 w-8 text-white"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M12 12H36L20 28H32L16 40"
            stroke="currentColor"
            strokeWidth="4.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      {showWordmark ? (
        <div className="min-w-0">
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.3em] text-cyan-300">
            Work OS
          </p>
          <p className={`font-semibold tracking-[0.12em] text-white ${compact ? 'text-lg' : 'text-xl'}`}>
            ZYRAA
          </p>
        </div>
      ) : null}
    </div>
  );
}
