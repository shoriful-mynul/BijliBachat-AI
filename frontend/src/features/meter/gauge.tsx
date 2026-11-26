type GaugeProps = {
  consumption: string;
  threshold: string;
  remaining: string | null;
};

/** A 240-degree gauge. Render this only when a verified threshold exists. */
export function ThresholdGauge({ consumption, threshold, remaining }: GaugeProps) {
  const used = Number(consumption);
  const limit = Number(threshold);
  const ratio = Number.isFinite(used) && Number.isFinite(limit) && limit > 0 ? Math.min(used / limit, 1) : 0;
  const start = 150;
  const track = describeArc(100, 108, 78, start, start + 240);
  const value = describeArc(100, 108, 78, start, start + 240 * ratio);
  const notch = polar(100, 108, 78, start + 240);

  return (
    <figure className="max-w-sm">
      <svg viewBox="0 0 200 168" role="img" aria-label={`Cycle consumption ${consumption} kWh of a verified threshold ${threshold} kWh.`}>
        <path d={track} fill="none" stroke="currentColor" strokeOpacity="0.25" strokeWidth="14" strokeLinecap="round" />
        <path d={value} fill="none" className="stroke-aqua" strokeWidth="14" strokeLinecap="round" />
        <circle cx={notch.x} cy={notch.y} r="5" className="fill-amber" />
      </svg>
      <figcaption className="text-sm leading-6">
        Current cycle consumption is {consumption} kWh. The verified threshold is {threshold} kWh.
        {remaining ? ` ${remaining} kWh remain before that threshold.` : " The cycle is already past that threshold."}
        This is not a live meter.
      </figcaption>
    </figure>
  );
}

function polar(cx: number, cy: number, radius: number, angle: number) {
  const radians = ((angle - 90) * Math.PI) / 180;
  return { x: cx + radius * Math.cos(radians), y: cy + radius * Math.sin(radians) };
}

function describeArc(cx: number, cy: number, radius: number, start: number, end: number) {
  const from = polar(cx, cy, radius, end);
  const to = polar(cx, cy, radius, start);
  const large = end - start <= 180 ? 0 : 1;
  return `M ${from.x} ${from.y} A ${radius} ${radius} 0 ${large} 0 ${to.x} ${to.y}`;
}
