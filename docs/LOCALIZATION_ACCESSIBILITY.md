# Localization and accessibility

English and Urdu are available on every route. English is the default. Urdu uses a right-to-left layout. The language choice is stored in this browser and does not change tariff math, forecasts, meter checks, appliance calculations, or history comparisons.

This is not a formal WCAG certification. The interface is built toward WCAG 2.2 AA: labels, keyboard access, focus, text alternatives for charts, and reflow at a narrow width. A full audit was not commissioned.

## Languages

| Code | Direction | Default |
| --- | --- | --- |
| `en` | `ltr` | Yes, including when nothing is stored |
| `ur` | `rtl` | No |

The Settings page has a language control and the existing theme control. The current language is named under the control. Changing it updates the open page. A refresh keeps the choice.

Storage key: `bijlibachat.language.v1`. The value is JSON, `"en"` or `"ur"`. A raw `en` or `ur`, or `{ "language": "ur" }`, is also accepted. Any other value is removed and English is used. The theme key `bb-theme` is not read or written by this preference.

An inline script in the document head sets `lang` and `dir` before paint, the same way the theme script sets `data-theme`.

## Translation architecture

Dictionaries live in `frontend/src/lib/i18n/messages.ts`.

- `en` is the typed source. Its keys are `MessageKey`.
- `ur` must contain every one of those keys. TypeScript fails the build when a key is missing.
- `translate(language, key, values)` returns the Urdu string, or the English string when the Urdu string is empty.
- `t("nav.history.label")` from `useI18n()` is what components call. Pages are not duplicated per language.
- `{name}` placeholders receive numbers and short values. Meter readings, kWh, and PKR stay in Western digits (`0–9`). `Intl` is not asked for Urdu digits.
- A known English sentence can be translated later with `messageKeyForEnglish`. That covers a validation sentence the page already stored before the language changed.
- Sentences returned by the API stay in English. In Urdu they are wrapped so the bidirectional algorithm does not reorder them. They are the calculation service's wording. The interface does not rewrite them into a different claim.

Do not translate storage keys, trust enum values sent to the API (`verified`, `calculated`, `extracted`, `estimated`, `unavailable`), tariff method names, or text a person typed: appliance names, meter numbers, provider codes, and extracted bill lines. Display labels for the trust and risk enums are translated. The values are not.

## Adding or changing a string

1. Add the English sentence to `en` in `frontend/src/lib/i18n/messages.ts`.
2. Add the same key to `ur`. Use ordinary Pakistani household Urdu. Keep familiar words such as kWh, PKR, GST, and کلف گارڈ when a forced translation would be less clear, and explain them in the surrounding sentence.
3. Call `t("the.key")` from the component. Do not add `language === "ur" ? ... : ...` in the page.
4. Run `npx tsc --noEmit` in `frontend/`. A missing Urdu key fails there.

## Urdu layout and type

When `lang` is `ur`:

- `dir` is `rtl`.
- The UI font is Noto Nastaliq Urdu, already loaded as `--font-nastaliq` and applied through `--font-urdu`.
- Body line height is 1.9 so Nastaliq lines do not collide. Headings, buttons, links, and labels use 1.55.
- Numbers that use `font-mono` or `tabular-nums` stay left-to-right and use the mono face, so a register and a PKR amount remain readable.

RTL is layout direction, not only aligned text. The sidebar sits on the start edge (`border-inline-end`). Active navigation and danger buttons use an inset rail that flips. Collapse icons flip. The collapsed-sidebar tooltip opens toward the content. Menus use `end-0`. Form chevrons use `end-3`. Chart plots use `direction: ltr` so a numeric axis is not mirrored.

## Accessibility decisions

- The shell has a skip link, a `header`, a primary `nav`, and a `main`. The service line is a `footer`.
- Icon-only controls have accessible names: theme, notifications, account, close, and sidebar collapse.
- Inputs and selects use a real `label`, `aria-invalid`, and `aria-describedby` for the hint and the error. The error is an alert and includes the word for "Error", so it does not depend on color. A `required` field adds the word "Required" to the label.
- The More sheet is a modal dialog. Escape closes it, Tab stays inside it, and focus returns to the More button. Notification and account menus also close on Escape and return focus.
- Focus uses a 2px aqua outline with a 2px offset.
- Trust and risk states pair a word with an icon. Color is not the only signal.
- `prefers-reduced-motion: reduce` shortens animation. Charts do not animate. The loading spinner does not spin when motion is reduced.
- Buttons and icon controls are at least 48px on the shorter side.
- A language change is announced once in a polite live region. It is not announced on the first paint.
- Upload, save, and calculation errors use `role="alert"`. Extraction and Cliff Guard calculation use `role="status"` where the page is waiting or has read a document.

## Charts

Each Recharts view keeps its existing data. The plot is `dir="ltr"`. A heading or an `aria-label` names the chart. A table under the chart repeats the points: day and kWh for the sample overview, observed and estimated points for the forecast, measured kWh and a saved forecast for history, and daily kWh plus share for appliances. Appliance names in that table stay as typed.

History uses two bar colors and a sentence that says which color is measured use and which is a saved forecast. The forecast lines are solid for observed points and dashed for the estimate, and the legend names both. An empty history chart says that no cycle is saved and that missing cycles are not filled in.

## Keyboard

Tab reaches the skip link first, then the sidebar or header controls, then the page. On a phone, the tab bar and More button are buttons and links. Escape closes the More sheet, the notification dialog, and the account menu.

## Testing

Frontend:

```bash
cd frontend
npm test
npm run lint
npx tsc --noEmit
npm run build
```

`npm test` runs the language cases and the existing history storage cases with Node's test runner. The language cases cover the English default, Urdu, switching back, the versioned storage value, a corrupt value, `lang` and `dir`, English fallback, navigation strings, form error attributes, keyboard dialog markup, and chart captions.

Backend, unchanged by this part:

```bash
cd backend
pytest
```

Browser checks on the running app covered `/dashboard`, `/settings`, `/meter-readings`, `/prediction`, `/history`, `/action-plan`, `/bill-auditor`, and `/cliff-guard` at 390×844, 768×1024, and 1440×900, in English and Urdu, in both themes. The same routes were also opened at a 320px width, which is the CSS width of a 1280px page at 400% zoom. No horizontal overflow remained after styles loaded. The meter register field exposed its label and description. The first Tab stop was the skip link.

## Known limitations

- API explanations, insight titles, extraction notes, and validation sentences produced by Python stay in English. Urdu layout isolates them. They are not retranslated, so a limitation is not silently softened.
- The browser tab title stays the English page name from server metadata. The visible heading is translated.
- Sample dates such as "18 Nov" and "1–30 November 2026" stay in the authored sample. The surrounding sentences are translated, and the cards stay marked as demo data.
- Complaint draft text is whatever the API returned. The labels around it are translated. The draft is still not submitted.
- This document does not claim a certified WCAG audit. Contrast of the Blue Hour tokens was left as already shipped. A new color pair was not introduced for this part.
