type LoadingStateProps = {
  label?: string;
};

export function LoadingState({ label = "Loading" }: LoadingStateProps) {
  return (
    <div
      role="status"
      className="flex min-h-12 items-center gap-3 rounded-2xl border border-line bg-card px-4 py-3 text-sm"
    >
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-aqua motion-reduce:animate-none"
        aria-hidden="true"
      />
      <span>{label}</span>
    </div>
  );
}
