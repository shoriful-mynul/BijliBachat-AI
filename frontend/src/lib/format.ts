const grouped = new Intl.NumberFormat("en-PK", {
  maximumFractionDigits: 0,
});

/** Groups an authored integer for display. This does not calculate a charge. */
export function formatGrouped(value: number): string {
  return grouped.format(value);
}

/** Presents an authored rupee amount. This does not calculate a bill. */
export function formatPkr(value: number): string {
  return `PKR ${formatGrouped(value)}`;
}
