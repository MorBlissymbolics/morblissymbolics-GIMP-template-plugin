# MorBlissymbolics Template (GIMP 3.0 Python plug-in)

A sibling of `mor-dictionary-entry-template`, but for learning Blissymbolics. It lays a card out on the current image: blissymbol (SVG), headword · part of speech, etymology/decomposition in italics, a divider, then the wrapped definition.

## Install

Linux:

```
mkdir -p ~/.config/GIMP/3.0/plug-ins/mor-blissymbolics-template
cp mor-blissymbolics-template.py profiles.json ~/.config/GIMP/3.0/plug-ins/mor-blissymbolics-template/
chmod +x ~/.config/GIMP/3.0/plug-ins/mor-blissymbolics-template/mor-blissymbolics-template.py
```

The folder name must match the .py name (GIMP 3 rule). Restart GIMP.

## Use

1. Create a canvas: 1920x1080 for landscape or 1080x1920 for TikTok/Reels/Shorts. Fill the background however you like; text uses the current foreground color, same as the dictionary plug-in.
2. Filters → Render → MorBlissymbolics Template...
3. Fill in headword, part of speech, etymology (the Bliss decomposition, e.g. `(person + play_(theatre))`), definition, and pick the blissymbol SVG file. Everything lands on separate layers (`blissymbol`, `headword`, `etymology`, `divider`, `definition`) so you can nudge afterwards.

## Profiles

`profiles.json` is re-read on every run — edit sizes/gaps and re-run the filter, no reinstall. It's searched for next to the .py first, then in `~/.config/morblissymbolics/profiles.json`. Profiles match on both width and height ranges:

- `hd_landscape` (1920x1080): symbol left, text right, both vertically centered.
- `tiktok` (1080x1920): symbol top-center, text centered below. `symbol_top_ratio` keeps it clear of TikTok's UI chrome.
- `custom`: ratio-based fallback for any other canvas; `layout: auto` picks side-by-side for landscape and stacked for portrait.

Sizes and gaps are Pango points; `*_rise` nudges a field up/down; `*_ratio` values are fractions of the canvas.

## SVG note

The blissymbol SVGs (like `actor_blissymbol.svg`) declare their size in inches, so GIMP rasterizes them at the image's DPI and the plug-in then scales the layer to fit `symbol_max_w_ratio` × `symbol_max_h_ratio`. At 72 DPI on a 1080p canvas that means a modest upscale, which is usually fine for video. For extra-crisp strokes, set the canvas resolution to 150–300 DPI (Image → Print Size) *before* running the plug-in — the SVG will rasterize larger and scale down instead of up.
