# ADR-0005: Shared buttons and screenshot frames

Date: 2026-10-30
Status: implemented

## Prior art

The homepage overrode native pill-shaped buttons with small rounded corners, a blue primary action and a transparent outlined secondary action. Interface pages inherited native pill buttons. SVG screenshots used a fixed source-unit radius, so their visible rounding differed when scaled.

## Decision

`surfaces/docs/assets/site-components.css` owns the button styles and screenshot-radius token. The build copies it into the retained workflow prototype and versions its URL by content. Homepage-specific button overrides are removed; only layout rules remain there.

Every `.md-button` uses the homepage dimensions and radius, with fixed geometry and typography through hover/focus/active states. Primary actions are blue; secondary actions are transparent with a light border. Hover changes colors, and keyboard focus has a visible outline. Pending downloads retain the same button shape in a disabled state. Tabs retain native tab styling.

Tab labels use centered flex alignment for text, SVG icons and the GUI's Font Awesome glyphs, matching the navigation's icon alignment rather than inline text baselines.

The homepage frame, guide captures, interface previews and enlarged image dialog use one radius token. SVG geometry converts that CSS radius to source units on resize. Only the image clip and frame round; highlight paths stay square and outside screenshot clipping.

## Validation

Browser checks compare screenshot radii with the homepage frame at desktop/mobile widths, confirm square unclipped highlights, and verify button sizes and typography remain fixed through hover while their colors change. Theme colors and disabled download behavior remain inherited from the existing palettes.

Zensical replaces each tab label's contents with an anchor after page initialization. Icon centering and spacing apply to both the label and this runtime anchor. The browser check measures the real icon-to-text distance after initialization for Font Awesome and SVG icons, rather than checking only the outer label's computed style.

Screenshot rounding scales with image width through one percentage token, including the homepage, interface previews, guides and enlarged views. SVG clips/frames use this fraction in intrinsic image coordinates so circular corners scale naturally with the image. The server-rendered fallback reads the same CSS token. The cropped homepage raster uses matching horizontal/vertical percentages derived from its intrinsic aspect ratio; no viewport-sized or fixed-pixel corner survives on narrow screens. Highlight geometry remains square and its existing display-pixel padding is unchanged.
