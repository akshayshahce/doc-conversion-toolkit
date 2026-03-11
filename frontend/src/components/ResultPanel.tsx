type Props = {
  message: string;
  error?: string;
  beforeSize?: string;
  afterSize?: string;
};

export function ResultPanel({ message, error, beforeSize, afterSize }: Props) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white/70 p-4 text-slate-900 dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-100">
      {error ? (
        <p className="text-sm text-rose-600 dark:text-rose-300">{error}</p>
      ) : (
        <>
          <p className="text-sm text-emerald-600 dark:text-emerald-300">{message}</p>
          {(beforeSize || afterSize) && (
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              {beforeSize ? `Original: ${beforeSize}` : ''}
              {beforeSize && afterSize ? ' | ' : ''}
              {afterSize ? `Output: ${afterSize}` : ''}
            </p>
          )}
        </>
      )}
    </div>
  );
}
