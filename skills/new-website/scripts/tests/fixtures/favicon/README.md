# Fixtures for favicon-guard.test.mjs

Astro's own icons, exactly as Astro ships them (read 2026-11-18 from withastro/astro,
`examples/minimal/public`; the name carries the git blob id, `git hash-object` of the file).
The same blobs sit in every `examples/*` folder that has a `public/` folder. Do not edit them: the
test checks each file's SHA-256.

| File | What it is |
|---|---|
| `astro-minimal-favicon-f157bd1c.svg` | the logo since 2023-03-09 (viewBox 128) |
| `astro-minimal-favicon-0f390629.svg` | the logo from 2022-08-17 to 2023-03-09 (viewBox 36) |
| `astro-minimal-favicon-7f48a94d.ico` | a PNG with an .ico name, since 2026-01-21 |
| `astro-minimal-favicon-578ad458.ico` | a real ICO, from 2021-08-18 |
| `astro-minimal-favicon-f157bd1c.svgo-4.1.0.svg` | the 2023 logo after `svgo` 4.1.0 (the starter's lockfile version) |
| `astro-minimal-favicon-0f390629.svgo-4.1.0.svg` | the 2022 logo after the same |
| `astro-minimal-favicon-f157bd1c.svgo-4.1.0-absolute.svg` | the 2023 logo after `svgo` 4.1.0 with `preset-default` and `convertPathData: { forceAbsolutePath: true }` (the path in absolute commands) |
| `astro-minimal-favicon-0f390629.svgo-4.1.0-absolute.svg` | the 2022 logo after the same |
| `build-marker.pre-0.36.mjs` | `scripts/build-marker.mjs` as of commit `817a63f6`, which reads no arguments (the next commit, `b91b5bcf`, adds a Workers Builds commit-id line and still reads none) |

`svgo --multipass` gives the same bytes as plain `svgo` on the 2023 logo (blob `53d61c73`), so it
has no file of its own.
