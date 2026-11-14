import { test, expect } from '@playwright/test';
import { readdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// The Worker's config (wrangler.jsonc) has the four settings the site relies on: no script of its
// own (`main`), no live workers.dev address (workers_dev: false, D4: only Previews answer before
// the domain is attached), Preview links on (preview_urls: true) and the built files from ./dist.
// A site still on Cloudflare Pages has no such config, so there the test skips and says why.
//
// The Workers config is the root .json or .jsonc file that holds `assets` and no
// `pages_build_output_dir` (a Pages config holds that key), as the move tools find it.
const ROOT = fileURLToPath(new URL('../', import.meta.url));

// Wrangler's JSONC: comments outside strings are dropped, then JSON.parse.
function parseJsonc(text: string): unknown {
  let out = '';
  for (let i = 0; i < text.length; ) {
    const c = text[i];
    if (c === '"') {
      let j = i + 1;
      while (j < text.length && text[j] !== '"') j += text[j] === '\\' ? 2 : 1;
      out += text.slice(i, j + 1);
      i = j + 1;
    } else if (c === '/' && text[i + 1] === '/') {
      while (i < text.length && text[i] !== '\n') i++;
    } else if (c === '/' && text[i + 1] === '*') {
      const j = text.indexOf('*/', i + 2);
      if (j < 0) throw new Error('a comment never ends');
      i = j + 2;
    } else {
      out += c;
      i++;
    }
  }
  return JSON.parse(out);
}

function workersConfigs(): { file: string; conf: Record<string, unknown> }[] {
  const found: { file: string; conf: Record<string, unknown> }[] = [];
  for (const file of readdirSync(ROOT).filter((f) => /\.jsonc?$/.test(f)).sort()) {
    let conf: unknown;
    try {
      conf = parseJsonc(readFileSync(ROOT + file, 'utf8'));
    } catch (e) {
      // A Wrangler file that does not parse is a failure; any other .json file is not ours to judge.
      if (file.startsWith('wrangler.')) throw new Error(`${file} is not JSON with comments: ${(e as Error).message}`);
      continue;
    }
    if (conf && typeof conf === 'object' && 'assets' in conf && !('pages_build_output_dir' in conf)) {
      found.push({ file, conf: conf as Record<string, unknown> });
    }
  }
  return found;
}

const configs = workersConfigs();

test.describe('Workers config', () => {
  test.skip(
    configs.length === 0,
    'no Workers config in the site folder (a .json or .jsonc with "assets" and no "pages_build_output_dir"): this site is on Cloudflare Pages, which needs none',
  );

  for (const { file, conf } of configs) {
    test(`${file}: a Worker with static assets, no script, no live workers.dev address`, () => {
      expect(conf.main, `${file} sets "main": a script would run before the static files`).toBeUndefined();
      expect(conf.workers_dev, `${file} needs "workers_dev": false, or the live workers.dev address is public before launch`).toBe(false);
      expect(conf.preview_urls, `${file} needs "preview_urls": true: Previews are how a site is looked at before launch`).toBe(true);
      const assets = conf.assets as { directory?: string } | undefined;
      expect(assets?.directory, `${file} must serve the built files from ./dist`).toBe('./dist');
    });
  }
});
