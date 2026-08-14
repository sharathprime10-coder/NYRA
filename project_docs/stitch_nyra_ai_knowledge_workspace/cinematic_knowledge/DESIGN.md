---
name: Cinematic Knowledge
colors:
  surface: '#11131d'
  surface-dim: '#11131d'
  surface-bright: '#383844'
  surface-container-lowest: '#0c0d18'
  surface-container-low: '#1a1b26'
  surface-container: '#1e1f2a'
  surface-container-high: '#282934'
  surface-container-highest: '#333440'
  on-surface: '#e2e1f0'
  on-surface-variant: '#c7c4d7'
  inverse-surface: '#e2e1f0'
  inverse-on-surface: '#2f303b'
  outline: '#908fa0'
  outline-variant: '#464554'
  surface-tint: '#c0c1ff'
  primary: '#c0c1ff'
  on-primary: '#1000a9'
  primary-container: '#8083ff'
  on-primary-container: '#0d0096'
  inverse-primary: '#494bd6'
  secondary: '#d0bcff'
  on-secondary: '#3c0091'
  secondary-container: '#571bc1'
  on-secondary-container: '#c4abff'
  tertiary: '#2fd9f4'
  on-tertiary: '#00363e'
  tertiary-container: '#008395'
  on-tertiary-container: '#000608'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e1e0ff'
  primary-fixed-dim: '#c0c1ff'
  on-primary-fixed: '#07006c'
  on-primary-fixed-variant: '#2f2ebe'
  secondary-fixed: '#e9ddff'
  secondary-fixed-dim: '#d0bcff'
  on-secondary-fixed: '#23005c'
  on-secondary-fixed-variant: '#5516be'
  tertiary-fixed: '#a2eeff'
  tertiary-fixed-dim: '#2fd9f4'
  on-tertiary-fixed: '#001f25'
  on-tertiary-fixed-variant: '#004e5a'
  background: '#11131d'
  on-background: '#e2e1f0'
  surface-variant: '#333440'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.04em
  display-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  container-padding-mobile: 20px
  container-padding-desktop: 64px
  gutter: 24px
  section-gap: 80px
---

## Brand & Style

The design system is centered on a **Cinematic Glassmorphism** and **Futuristic Minimalism** aesthetic. It targets an audience seeking a high-end, intelligent, and immersive AI experience. The interface should feel like a sentient lens into vast data landscapes, evoking feelings of awe, clarity, and boundless potential.

The visual narrative is driven by deep contrast, where obsidian foundations meet ethereal light. This is achieved through:
- **Atmospheric Depth:** Multi-layered backgrounds featuring topographic wireframes and blurred silhouettes to create a sense of infinite 3D space.
- **Luminescent Flourishes:** Aurora-inspired glows and particle layers that react to user interaction, signifying the "energy" of the AI processing information.
- **Precision Minimalism:** While the backgrounds are rich, the UI foreground remains surgically clean with thin strokes and ample negative space to ensure the AI's "knowledge" is the focal point.

## Colors

The palette is anchored in a deep **Obsidian (#070812)** to provide maximum contrast for the vibrant aurora accents. 

- **Primary & AI States:** Use Indigo and Violet to represent core brand actions and generative AI processes.
- **Knowledge & RAG:** Aurora Cyan is reserved for data-heavy components, search results, and retrieval-augmented generation markers.
- **Gradients:** Utilize multi-stop linear gradients (e.g., Indigo to Cyan) for primary actions to simulate the movement of light. 
- **Surface Tints:** Glass surfaces should have a 1px border using a 10-15% opacity version of the primary or neutral-white to define edges against the dark backdrop.

## Typography

Typography in the design system balances editorial elegance with technical precision. 

- **Plus Jakarta Sans** is used for all branding, headers, and large display text to provide a welcoming yet sophisticated tone.
- **Inter** handles all functional UI elements, body text, and data readouts, ensuring maximum legibility across all information densities.
- **Styling:** Headings should often use tight letter-spacing to feel "contained," while small labels use increased letter-spacing and uppercase styling to evoke a technical, HUD-like (Heads-Up Display) aesthetic.

## Layout & Spacing

The layout philosophy follows a **Fluid Grid** model with generous margins to support the "cinematic" feel. 

- **Desktop:** A 12-column grid with wide 64px outer margins. Content is often centered or offset to create dynamic, asymmetrical compositions.
- **Mobile:** A 4-column grid with 20px margins.
- **Rhythm:** An 8px base unit drives all padding and margin scales. 
- **Safe Areas:** Background artwork (auroras, topographic lines) must always extend to the edge of the viewport, while functional UI is strictly contained within safe margins to maintain professional structure.

## Elevation & Depth

Elevation is conveyed through **Backdrop Blurs** and **Tonal Layering** rather than traditional heavy shadows.

- **The Base:** The Obsidian floor.
- **Level 1 (Cards/Panels):** 40% opacity Obsidian with a 16px backdrop blur and a subtle 1px border (#FFFFFF at 10% opacity).
- **Level 2 (Modals/Popovers):** 60% opacity Obsidian with a 32px backdrop blur. These elements should cast an **Ambient Glow**—a low-opacity shadow tinted with the primary color (#6366F1) rather than black.
- **Interactivity:** Elements should appear to "lift" towards the user via increased blur intensity and brighter border highlights upon hover.

## Shapes

The design system utilizes **Rounded** geometry to soften the futuristic aesthetic, making the AI feel approachable.

- **Standard Elements:** 0.5rem (8px) radius for buttons and input fields.
- **Containers:** 1rem (16px) radius for cards and main UI panels.
- **Logo/Iconography:** The 'N' logo and icons should utilize geometric paths with slight vertex rounding to match the UI language.
- **Consistency:** Avoid pill-shaped buttons for primary actions; reserve pill shapes strictly for status "chips" and tags.

## Components

### Buttons
Primary buttons use a vibrant gradient (Indigo to Violet) with white text. Secondary buttons are "Ghost Glass"—transparent backgrounds with a subtle white border and backdrop blur.

### AI Knowledge Chips
Use the "Knowledge/RAG" Cyan color. These should have a subtle pulse animation or a soft outer glow to indicate they represent "live" or "retrieved" data.

### Input Fields
Inputs are dark with a 1px border. Upon focus, the border transitions to a Cyan-to-Indigo gradient, and a faint glow radiates from the bottom of the field.

### Cards
Cards are the primary vessel for AI responses. They must utilize the glassmorphism specifications defined in the Elevation section. Headers within cards should be separated by a hairline divider (10% opacity white).

### Particle Layers
A non-interactive background component consisting of slow-moving, low-opacity white dots that follow the user's cursor slightly, adding to the "Cinematic Depth" of the interface.