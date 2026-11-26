# Design system — Blue Hour

Blue Hour is the visual language for BijliBachat AI. It should feel like a calm household finance product: readable type, quiet surfaces, and accents only where a status or a figure needs them.

Dark is the brand appearance. Light is a full alternative, not an afterthought. Both themes use the same semantic tokens.

## Color

### Surfaces

| Token | Hex | Use |
| --- | --- | --- |
| Background | `#182B43` | Page |
| Sidebar | `#203A57` | Navigation column and mobile bar |
| Card | `#294967` | Default panels |
| Raised | `#365A78` | Pressed, active, and secondary controls |
| Ice panel | `#DCECF3` | One lighter panel, used for the next action |
| Ink | `#0B1E33` | Text on ice, aqua, and other light fills |

Light theme remaps the semantic surfaces: page `#E6F0F5`, sidebar `#F7FBFD`, cards white, raised `#E8F1F6`. Ink and the ice panel stay the same. Accent hex values do not change between themes.

### Accents

| Name | Hex | Role |
| --- | --- | --- |
| Aqua | `#42C8E8` | Primary action, chart bars, focus ring |
| Teal | `#28C5B0` | Cycle progress, verified trust |
| Mint | `#8BE0B0` | Safe |
| Lime | `#C7E86B` | Reserved |
| Lavender | `#B9AEFF` | Extracted trust, needs verification |
| Amber | `#FFC36B` | Estimated trust, approaching |
| Coral | `#FF7D83` | High risk |

Distribution target: about 70% blue surfaces, 20% lighter neutral or ice, 10% accent. Accents sit on chips, the chart, the cycle bar, the primary button, and the bill card's left edge.

Muted text in the dark theme is `#C9D8E2`, chosen so body copy stays above a 4.5:1 contrast on background, sidebar, card, and raised surfaces. Do not use raw accent colors for small text on blue cards. Coral on a card does not meet that bar. Put the accent in an icon disc with ink text, and write the label in the surface's foreground color.

### Glow

Glow is reserved for a live forecast line and the Cliff Guard gauge once those visualizations represent real data. This version does not use it. The sample chart is a solid aqua bar series. The Cliff Guard ring is a dashed, empty placeholder because no tariff is verified. Glowing that ring would look like a measurement.

## Typography

Loaded with `next/font/google` and self-hosted by Next.js. The app does not request font CSS from a third-party stylesheet at runtime.

| Role | Family |
| --- | --- |
| Headings and prominent rupee amounts | Manrope |
| Interface text | Inter |
| Meter readings and technical values | JetBrains Mono |
| Urdu | Noto Nastaliq Urdu |

Urdu is marked `lang="ur"` and `dir="rtl"`. Nastaliq needs loose line height. Do not set Urdu in Inter.

Avoid oversized page titles. The shell title is about 18–20px. The sample bill is the one large figure.

## Components

Components live in `frontend/src/components/ui` and share a small prop style: `className` for layout overrides, explicit variants, and a visible label for fields.

| Component | Notes |
| --- | --- |
| Button | `primary`, `secondary`, `ghost`, `danger`. Minimum height 48px. `href` renders a link. Danger keeps foreground text and adds a coral inset edge, so the word still carries the meaning. |
| Card | `default`, `raised`, or `ice`. Border plus a very soft shadow in the light theme only. |
| Badge | Neutral label. "Demo data" uses this, not a trust color. |
| DataTrustChip | Exactly Verified, Calculated, Extracted, Estimated, Unavailable. Each has its own icon and disc color. |
| Risk indicator | Safe, Approaching, High risk, Needs verification. Color, icon, and word. |
| Input and Select | Label, optional hint, optional error. Errors use an icon and the word "Error", not color alone. Controls are 48px tall. |
| SectionHeader | Title, short description, optional actions. |
| StatCard | One figure, optional demo badge and trust chip. |
| EmptyState | Used for a missing page and for short empty explanations. |
| FeaturePlaceholder | A page that names what a later section will do, and says it is not available yet. |
| LoadingState | Text plus a spinner, with a `status` role. |

Lucide is the only icon set.

## Trust and risk

Demo data and trust status are different. A sample bill is both "Demo data" and "Estimated". A missing tariff is "Unavailable". A risk call that cannot be made is "Needs verification", not a guessed Safe or High risk.

The sample overview follows that split. Cliff Guard does not show a unit threshold or a protected-consumer label.

## Accessibility

- Focus visible is a 2px aqua outline.
- Touch targets for navigation, icon buttons, fields, and buttons are at least 48px.
- The shell has a skip link, a labeled primary nav, and one `h1` per route in the header.
- The chart has a visually hidden data table.
- The cycle bar exposes `aria-valuenow` and a text description.
- `prefers-reduced-motion` shortens animation. The chart does not animate.
- Color is not the only signal for trust, risk, errors, or the active section.

## Responsive layout

Mobile first.

| Viewport | Shell |
| --- | --- |
| 390×844 | Compact top bar, single column, bottom navigation. Four destinations plus More. More opens a sheet for Bill Auditor, Consumption History, and Settings. |
| About 768px | Labeled sidebar, no bottom bar. The sidebar can collapse to icons. Content stays one column until there is room. |
| 1024px and up | Bill and Cliff Guard sit side by side. |
| 1440px | Content column is capped so the page does not stretch into an empty band. |

The mobile bar is designed as a phone navigation, not a squeezed sidebar. Seven text labels do not fit a 390px bar at a 48px target, so the less frequent destinations move into More.

## Motion and surface treatment

Borders are 1px and low contrast. Shadows are restrained and only in the light theme. There is no decorative gradient, no frosted glass, and no neon treatment. Hover states change a surface color without moving the layout.
