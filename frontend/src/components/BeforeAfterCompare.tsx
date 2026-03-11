import { useState } from 'react';

type Props = {
  beforeUrl: string;
  afterUrl: string;
  beforeLabel: string;
  afterLabel: string;
  reductionLabel: string;
};

export function BeforeAfterCompare({ beforeUrl, afterUrl, beforeLabel, afterLabel, reductionLabel }: Props) {
  const [split, setSplit] = useState(50);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 text-slate-900 shadow-sm dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-100">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="text-sm">
          <span className="font-semibold">Before:</span> {beforeLabel}
        </div>
        <div className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200">
          {reductionLabel}
        </div>
        <div className="text-sm text-emerald-700 dark:text-emerald-300">
          <span className="font-semibold">After:</span> {afterLabel}
        </div>
      </div>

      <div className="relative h-72 overflow-hidden rounded-2xl border border-slate-200 bg-slate-100 dark:border-slate-700 dark:bg-slate-950">
        <img src={beforeUrl} alt="Before compression" className="absolute inset-0 h-full w-full object-contain" />
        <div className="absolute inset-0 overflow-hidden" style={{ width: `${split}%` }}>
          <img src={afterUrl} alt="After compression" className="h-full w-full object-contain" />
        </div>
        <div className="absolute top-0 bottom-0 w-1 bg-white/90 shadow" style={{ left: `calc(${split}% - 2px)` }} />
      </div>

      <input
        type="range"
        min={0}
        max={100}
        value={split}
        onChange={(e) => setSplit(Number(e.target.value))}
        className="mt-4 w-full"
      />
    </div>
  );
}
