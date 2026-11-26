/**
 * Authored sample content for the overview layout.
 * These values are not measurements, tariff results, or savings calculations.
 * Every figure rendered from this file must keep a visible "Demo data" label.
 */

export const demoDailyUnits = [
  { label: "1 Nov", units: 6 },
  { label: "2 Nov", units: 8 },
  { label: "3 Nov", units: 7 },
  { label: "4 Nov", units: 9 },
  { label: "5 Nov", units: 8 },
  { label: "6 Nov", units: 5 },
  { label: "7 Nov", units: 10 },
  { label: "8 Nov", units: 7 },
  { label: "9 Nov", units: 8 },
  { label: "10 Nov", units: 11 },
  { label: "11 Nov", units: 9 },
  { label: "12 Nov", units: 6 },
  { label: "13 Nov", units: 8 },
  { label: "14 Nov", units: 12 },
  { label: "15 Nov", units: 7 },
  { label: "16 Nov", units: 9 },
  { label: "17 Nov", units: 8 },
  { label: "18 Nov", units: 10 },
] as const;

/** Pre-totaled with the series above. The client must not derive a bill from it. */
export const demoUnitsSoFar = 148;

const seriesTotal = demoDailyUnits.reduce((total, point) => total + point.units, 0);

if (seriesTotal !== demoUnitsSoFar) {
  throw new Error(
    "Demo daily units do not match the authored total. Update the sample copy together. Do not calculate a bill in the client.",
  );
}

export const demoOverview = {
  household: {
    greetingName: "Ayesha",
    fullName: "Ayesha Khan",
    initials: "AK",
    place: "Gulberg, Lahore",
    urduTagline: "بل آنے کا انتظار مت کیجیے۔",
  },
  cycle: {
    label: "1–30 November 2026",
    day: 18,
    length: 30,
    progressPercent: 60,
    illustratedThrough: "18 November 2026",
  },
  bill: {
    amountPkr: 7150,
  },
  action: {
    title: "Wash a full load, then air-dry it",
    detail:
      "Switch the water pump off once the tank is full. These are ordinary household habits, and they do not depend on a tariff slab.",
    illustrativeSavingPkr: 350,
  },
  reading: {
    registerKwh: 15482,
    submittedOn: "18 November 2026",
  },
} as const;
