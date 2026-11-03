import React from 'react';
import { LucideIcon, Inbox } from 'lucide-react';

export const LoadingSkeleton: React.FC<{ rows?: number }> = ({ rows = 3 }) => {
  return (
    <div className="space-y-3 w-full animate-pulse">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="glass-card p-5 rounded-2xl border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <div className="h-4 bg-slate-800 rounded w-1/4"></div>
            <div className="h-3 bg-slate-800 rounded w-16"></div>
          </div>
          <div className="h-3 bg-slate-800/60 rounded w-full"></div>
          <div className="h-3 bg-slate-800/40 rounded w-5/6"></div>
        </div>
      ))}
    </div>
  );
};

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Inbox,
  title,
  description,
  actionText,
  onAction,
}) => {
  return (
    <div className="glass-card p-12 rounded-2xl border border-slate-800/80 text-center flex flex-col items-center justify-center space-y-4 my-6">
      <div className="w-14 h-14 rounded-2xl bg-purple-950/40 border border-purple-800/30 flex items-center justify-center text-purple-400">
        <Icon className="w-7 h-7" />
      </div>
      <div className="max-w-md space-y-1">
        <h3 className="text-base font-semibold text-slate-200">{title}</h3>
        <p className="text-xs text-slate-400 leading-relaxed">{description}</p>
      </div>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="mt-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-md shadow-purple-600/20 transition"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  onConfirm,
  onCancel,
  danger = false,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="glass-card max-w-md w-full rounded-2xl p-6 border border-slate-800 space-y-4 shadow-2xl">
        <h3 className="font-semibold text-base text-white">{title}</h3>
        <p className="text-xs text-slate-300 leading-relaxed">{message}</p>
        <div className="flex justify-end gap-3 pt-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white bg-slate-900 border border-slate-800 transition"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 rounded-xl text-xs font-semibold text-white transition ${
              danger
                ? 'bg-rose-600 hover:bg-rose-500 shadow-md shadow-rose-600/20'
                : 'bg-purple-600 hover:bg-purple-500 shadow-md shadow-purple-600/20'
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

