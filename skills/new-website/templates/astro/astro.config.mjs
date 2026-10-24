import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// Set `site` to the real production domain BEFORE first deploy — it drives the
// sitemap, canonical tags and OG URLs. Keep in sync with SITE.url in src/config.ts.
export default defineConfig({
  site: 'https://example.com',
  // Astro 7 defaults compressHTML to 'jsx' rules: a source line-break between two inline
  // elements (or between text and an inline element, e.g. wrapping a sentence across lines
  // around a link) collapses to ZERO characters instead of a space. That's a normal way to
  // write prose, so this silently breaks real content, not just edge-case markup — confirmed
  // on a live site during this toolkit's own Astro 6→7 migration (2026-07-16).
  // `true` restores the old "lossless" behavior (still compresses, just keeps a rendered
  // space where one exists in source).
  compressHTML: true,
  trailingSlash: 'never',           // CONVENTION: clean URLs with NO trailing slash (/about, not /about/)
  build: {
    format: 'file',                 // emit /about.html → Cloudflare Pages serves it at /about (no slash)
    inlineStylesheets: 'always',    // drop the render-blocking CSS request (LCP)
  },
  // The test suite's preview must fail if its port is taken, not slide to the next free
  // one (Vite's default): Playwright would then wait on the wrong port and report a
  // timeout instead of the real cause. See webServer in playwright.config.ts.
  vite: { preview: { strictPort: true } },
  integrations: [
    // No lastmod: stamping build time on every URL tells crawlers all pages changed
    // when none did. /404 needs no filter — @astrojs/sitemap excludes status-code
    // pages itself. If you add any OTHER noindex page, exclude it here, e.g.
    //   sitemap({ filter: (url) => new URL(url).pathname !== '/internal' })
    // — and keep it out of tests/_helpers.ts PAGES (seo.spec.ts compares the two).
    sitemap({ changefreq: 'monthly', priority: 0.7 }),
  ],
});
