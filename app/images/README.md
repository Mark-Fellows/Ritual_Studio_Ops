# Portal images

Drop tile images here. The index page references them by filename:

| Filename | Used by tile | Notes |
|---|---|---|
| `ritual-logo.png` | Ritual Website tile | Square or oval works; rendered at 36 px high. Transparent background preferred. |
| `fitness-passport.png` | Fitness Passport tile | Same sizing. |

If the file is missing the index page falls back to a unicode glyph automatically (no broken-image icon).

To replace a logo, save the new file under the same name and hard-refresh (Ctrl+F5) the page. Cloudflare Pages picks up the new asset on the next deploy.
