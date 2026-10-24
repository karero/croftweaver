#!/usr/bin/env node
// Cross-platform launcher for generate_og_cards.py — the `npm run og` entry point.
//
// Why a Node wrapper instead of a shell `python3 … || py -3 … || python …` chain:
//  1. `npm run og -- --check` appends `--check` to the END of the whole command, so in a
//     `||` chain it binds to the LAST interpreter only — when `python3` succeeds the
//     generator runs WITHOUT `--check`. This forwards every arg to whichever Python runs.
//  2. It only tries the next interpreter when the current one is NOT FOUND (ENOENT); a real
//     script failure (e.g. Pillow missing) is propagated, not masked behind a later attempt.
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const script = join(dirname(fileURLToPath(import.meta.url)), 'generate_og_cards.py');
const args = process.argv.slice(2); // forward --check and anything else, verbatim
const candidates = [['python3', []], ['py', ['-3']], ['python', []]];

for (const [cmd, pre] of candidates) {
  const res = spawnSync(cmd, [...pre, script, ...args], { stdio: 'inherit' });
  if (res.error?.code === 'ENOENT') continue; // interpreter not installed → try the next
  process.exit(res.status ?? 1);              // it ran — propagate its exit code (incl. --check)
}
console.error('No Python interpreter found (tried: python3, py -3, python). Install Python 3 + Pillow (pip install Pillow).');
process.exit(1);
