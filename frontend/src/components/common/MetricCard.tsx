import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  badge?: string;
  color?: 'purple' | 'blue' | 'emerald' | 'amber' | 'slate';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  badge,
  color = 'purple',
}) => {
  const colorStyles = {
    purple: {
      bg: 'from-purple-900/20 to-purple-950/40 border-purple-800/30 text-purple-400',
      iconBg: 'bg-purple-600/20 text-purple-400',
      badge: 'bg-purple-950/60 text-purple-300 border-purple-800/50',
    },
    blue: {
      bg: 'from-blue-900/20 to-blue-950/40 border-blue-800/30 text-blue-400',
      iconBg: 'bg-blue-600/20 text-blue-400',
      badge: 'bg-blue-950/60 text-blue-300 border-blue-800/50',
    },
    emerald: {
      bg: 'from-emerald-900/20 to-emerald-950/40 border-emerald-800/30 text-emerald-400',
      iconBg: 'bg-emerald-600/20 text-emerald-400',
      badge: 'bg-emerald-950/60 text-emerald-300 border-emerald-800/50',
    },
    amber: {
      bg: 'from-amber-900/20 to-amber-950/40 border-amber-800/30 text-amber-400',
      iconBg: 'bg-amber-600/20 text-amber-400',
      badge: 'bg-amber-950/60 text-amber-300 border-amber-800/50',
    },
    slate: {
      bg: 'from-slate-900/40 to-slate-950/60 border-slate-800/50 text-slate-400',
      iconBg: 'bg-slate-800 text-slate-400',
      badge: 'bg-slate-900 text-slate-400 border-slate-800',
    },
  }[color];

  return (
    <div className={`p-5 rounded-2xl border bg-gradient-to-b backdrop-blur-md relative overflow-hidden ${colorStyles.bg}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400">{title}</span>
        <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${colorStyles.iconBg}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>

      <div className="mt-3 flex items-baseline justify-between gap-2">
        <p className="text-2xl font-bold tracking-tight text-white">{value}</p>
        {badge && (
          <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${colorStyles.badge}`}>
            {badge}
          </span>
        )}
      </div>

      {subtitle && <p className="mt-1 text-[11px] text-slate-500 font-medium">{subtitle}</p>}
    </div>
  );
};
