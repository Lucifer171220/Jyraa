'use client';

const shards = [
  'left-[6%] top-[12%] h-40 w-40 rotate-[18deg] bg-[linear-gradient(180deg,rgba(56,189,248,0.26),rgba(14,165,233,0.02))] [animation-delay:-2s]',
  'right-[10%] top-[18%] h-56 w-56 -rotate-[12deg] bg-[linear-gradient(180deg,rgba(34,197,94,0.18),rgba(16,185,129,0.02))] [animation-delay:-7s]',
  'left-[18%] bottom-[14%] h-48 w-48 rotate-[32deg] bg-[linear-gradient(180deg,rgba(251,191,36,0.18),rgba(245,158,11,0.02))] [animation-delay:-11s]',
  'right-[18%] bottom-[10%] h-36 w-36 -rotate-[24deg] bg-[linear-gradient(180deg,rgba(99,102,241,0.2),rgba(79,70,229,0.02))] [animation-delay:-5s]',
];

export function AmbientBackground() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 overflow-hidden [perspective:1400px]"
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.7),transparent_38%),radial-gradient(circle_at_20%_20%,rgba(14,165,233,0.16),transparent_28%),radial-gradient(circle_at_80%_12%,rgba(16,185,129,0.14),transparent_25%),radial-gradient(circle_at_50%_100%,rgba(15,23,42,0.08),transparent_30%)]" />

      <div className="ambient-grid absolute left-1/2 top-[8%] h-[78vh] w-[78vw] min-w-[780px] -translate-x-1/2 rounded-[3.5rem] border border-white/30 opacity-60" />

      <div className="absolute inset-x-0 top-[-8%] h-[34rem] bg-[radial-gradient(circle,rgba(125,211,252,0.22),transparent_58%)] blur-3xl" />
      <div className="absolute bottom-[-12%] left-[12%] h-[28rem] w-[28rem] rounded-full bg-cyan-300/12 blur-3xl ambient-drift" />
      <div className="absolute right-[10%] top-[30%] h-[24rem] w-[24rem] rounded-full bg-emerald-300/12 blur-3xl ambient-drift [animation-delay:-9s]" />

      {shards.map((shardClass) => (
        <div
          key={shardClass}
          className={`ambient-shard absolute rounded-[2rem] border border-white/20 shadow-[0_30px_80px_rgba(15,23,42,0.08)] backdrop-blur-[2px] ${shardClass}`}
        />
      ))}

      <div className="ambient-ring absolute left-[14%] top-[22%] h-48 w-48 rounded-full border border-white/30" />
      <div className="ambient-ring absolute bottom-[18%] right-[16%] h-64 w-64 rounded-full border border-sky-200/50 [animation-delay:-10s]" />
    </div>
  );
}
