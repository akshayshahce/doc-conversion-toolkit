import { motion } from 'framer-motion';
import { ReactNode } from 'react';
import clsx from 'clsx';

type Props = {
  title: string;
  description: string;
  active: boolean;
  onClick: () => void;
  icon: ReactNode;
};

export function ToolCard({ title, description, active, onClick, icon }: Props) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      whileHover={{ y: -2 }}
      className={clsx(
        'rounded-2xl border p-4 text-left transition shadow-sm',
        active
          ? 'border-brand-500 bg-white/90 dark:bg-slate-900/90 shadow-glass'
          : 'border-slate-200 bg-white/70 dark:border-slate-800 dark:bg-slate-900/60'
      )}
    >
      <div className="mb-3 inline-flex rounded-lg bg-brand-100 p-2 text-brand-700 dark:bg-brand-700/20 dark:text-brand-100">
        {icon}
      </div>
      <h3 className="font-display text-lg font-semibold">{title}</h3>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{description}</p>
    </motion.button>
  );
}
