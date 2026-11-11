interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  return (
    <div role="alert" className="rounded-xl border border-danger bg-danger-soft p-5">
      <p className="font-semibold text-danger">We couldn’t create your lesson</p>
      <p className="mt-1">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 min-h-11 rounded-lg border border-danger bg-surface px-4 font-semibold text-danger"
        >
          Try again
        </button>
      )}
    </div>
  );
}
