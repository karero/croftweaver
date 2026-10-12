#!/usr/bin/env node
// create-croftweaver: `npm create croftweaver` installs the Croftweaver skills for an AI
// coding assistant. It downloads the latest release zip from GitHub and puts each folder of
// skills/ into the assistant's skills folder as a real copy. Run it again to update.
//
// It is plain Node with no dependencies and calls no other program (no bash, git or unzip),
// so it also runs in a Windows terminal, where scripts/install.sh needs Git Bash or WSL.
//
// What it does with a folder that is already there under a skill's name:
// - a working link (what scripts/install.sh leaves, or a pin): left alone, and reported.
//   The link's folder is where those skills update from. --force replaces it with a copy.
// - a copy an earlier run of this installer made (listed in .croftweaver.json): replaced.
// - anything else: moved to a backup folder BESIDE the skills folder, never inside it,
//   where the assistant would load it as a second skill of the same name.
// A skill an earlier run installed and the release no longer has is removed.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import zlib from 'node:zlib';

const ZIP_URL = process.env.CROFTWEAVER_ZIP_URL
  || 'https://github.com/karero/croftweaver/releases/latest/download/croftweaver.zip';
const MANIFEST = '.croftweaver.json';
const SKILL_NAME = /^[a-z0-9][a-z0-9-]*$/;
const RELEASE_NAME = /^v?[0-9][0-9A-Za-z.-]*$/;
const USAGE = 'usage: npm create croftweaver [-- [--codex | --antigravity] [--force]]';
const TIMEOUT = 300_000;   // npm's own default for a download; a slow line needs the room

// The same folders, and the same two overrides, as scripts/install.sh, scripts/install-codex.sh
// and docs/ANTIGRAVITY.md.
const ASSISTANTS = {
  claude: { label: 'Claude Code', flag: '', dir: () => process.env.CLAUDE_SKILLS_DIR || path.join(os.homedir(), '.claude', 'skills') },
  codex: { label: 'Codex', flag: '--codex ', dir: () => process.env.CODEX_SKILLS_DIR || path.join(os.homedir(), '.agents', 'skills') },
  antigravity: { label: 'Antigravity', flag: '--antigravity ', dir: () => path.join(os.homedir(), '.gemini', 'config', 'skills') },
};

function parseArgs(argv) {
  let assistant = null;
  let force = false;
  for (const arg of argv) {
    if (arg === '--help' || arg === '-h') { console.log(USAGE); process.exit(0); }
    if (arg === '--force') force = true;
    else if ((arg === '--codex' || arg === '--antigravity') && !assistant) assistant = arg.slice(2);
    else { console.error(USAGE); process.exit(2); }
  }
  return { assistant: assistant || 'claude', force };
}

// GitHub answers the "latest" address with a redirect that names the release. Read the name
// from it, then follow.
async function download(url) {
  let res = await fetch(url, { redirect: 'manual', signal: AbortSignal.timeout(TIMEOUT) });
  let release = null;
  const next = res.headers.get('location');
  if (res.status >= 300 && res.status < 400 && next) {
    const name = /\/download\/([^/]+)\//.exec(next)?.[1] ?? '';
    if (RELEASE_NAME.test(name)) release = name;
    res = await fetch(new URL(next, url), { signal: AbortSignal.timeout(TIMEOUT) });
  }
  if (!res.ok) throw new Error(`the server answered ${res.status}`);
  return { release, zip: Buffer.from(await res.arrayBuffer()) };
}

// The entries of a zip, read from its central directory. It reads what `zip -r` writes
// (stored and deflated files) and refuses the rest: zip64, encryption, links.
function* zipEntries(buf) {
  let end = -1;
  for (let i = buf.length - 22; i >= Math.max(0, buf.length - 22 - 0xffff); i--) {
    if (buf.readUInt32LE(i) === 0x06054b50) { end = i; break; }
  }
  if (end < 0) throw new Error('it is not a complete zip file');
  const count = buf.readUInt16LE(end + 10);
  let p = buf.readUInt32LE(end + 16);
  if (count === 0xffff || p === 0xffffffff) throw new Error('it is a zip64 file');
  for (let n = 0; n < count; n++) {
    if (buf.readUInt32LE(p) !== 0x02014b50) throw new Error('its list of files is damaged');
    const unix = buf.readUInt16LE(p + 4) >> 8 === 3;
    const encrypted = buf.readUInt16LE(p + 8) & 1;
    const method = buf.readUInt16LE(p + 10);
    const crc = buf.readUInt32LE(p + 16);
    const packed = buf.readUInt32LE(p + 20);
    const size = buf.readUInt32LE(p + 24);
    const nameLength = buf.readUInt16LE(p + 28);
    const mode = unix ? buf.readUInt32LE(p + 38) >>> 16 : 0;
    const local = buf.readUInt32LE(p + 42);
    const name = buf.toString('utf8', p + 46, p + 46 + nameLength);
    p += 46 + nameLength + buf.readUInt16LE(p + 30) + buf.readUInt16LE(p + 32);
    if (encrypted || (method !== 0 && method !== 8) || (mode & 0o170000) === 0o120000) {
      throw new Error(`${JSON.stringify(name)} is stored in a way this installer does not read`);
    }
    yield {
      name,
      mode: mode & 0o777,
      read() {
        if (buf.readUInt32LE(local) !== 0x04034b50) throw new Error(`${JSON.stringify(name)} is damaged`);
        const start = local + 30 + buf.readUInt16LE(local + 26) + buf.readUInt16LE(local + 28);
        const raw = buf.subarray(start, start + packed);
        let data = null;
        try { data = method === 0 ? raw : zlib.inflateRawSync(raw); } catch { /* reported below */ }
        if (data?.length !== size || zlib.crc32(data) !== crc) throw new Error(`${JSON.stringify(name)} is damaged`);
        return data;
      },
    };
  }
}

// Writes every skills/<name>/… entry of the zip under `staging` and returns the skill names.
function unpackSkills(zip, staging) {
  const names = new Set();
  for (const entry of zipEntries(zip)) {
    const parts = entry.name.split('/');
    if (parts[0] !== 'skills' || parts.length < 3) continue;
    const out = path.resolve(staging, ...parts.slice(1));
    // Nothing is written outside `staging`. A backslash separates folders on Windows only, so
    // it is refused everywhere: a release must not unpack on one system and fail on another.
    if (!SKILL_NAME.test(parts[1]) || entry.name.includes('\\') || !out.startsWith(staging + path.sep)) {
      throw new Error(`${JSON.stringify(entry.name)} does not belong in a Croftweaver release`);
    }
    names.add(parts[1]);
    if (entry.name.endsWith('/')) { fs.mkdirSync(out, { recursive: true }); continue; }
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, entry.read(), { mode: entry.mode || 0o644 });
  }
  if (!fs.existsSync(path.join(staging, 'new-website', 'SKILL.md'))) {
    throw new Error('it holds no Croftweaver skills');
  }
  return [...names].sort();
}

// The skills an earlier run copied here. No list, or one that cannot be read, means none:
// folders found under a skill's name are then moved to the backup rather than replaced.
function installedBefore(dest) {
  try {
    const { skills } = JSON.parse(fs.readFileSync(path.join(dest, MANIFEST), 'utf8'));
    return skills.filter((s) => typeof s === 'string' && SKILL_NAME.test(s));
  } catch {
    return [];
  }
}

// Every step leaves a state a second run finishes from: the list of copies is written after
// the last folder that is not ours has been moved away, and before the first copy lands.
function install(staging, names, dest, release, force) {
  const before = installedBefore(dest);
  const result = { copied: [], kept: [], moved: [], removed: [], backup: null };
  for (const name of before) {
    const target = path.join(dest, name);
    const found = fs.lstatSync(target, { throwIfNoEntry: false });
    if (names.includes(name) || !found || found.isSymbolicLink()) continue;
    fs.rmSync(target, { recursive: true });
    result.removed.push(name);
  }
  for (const name of names) {
    const target = path.join(dest, name);
    const found = fs.lstatSync(target, { throwIfNoEntry: false });
    if (found?.isSymbolicLink()) {
      // existsSync follows the link: a dangling one is dead either way, so it is replaced.
      if (!force && fs.existsSync(target)) { result.kept.push(name); continue; }
      fs.rmSync(target);
    } else if (found && before.includes(name)) {
      fs.rmSync(target, { recursive: true });
    } else if (found) {
      result.backup ??= fs.mkdtempSync(path.join(path.dirname(dest), 'skills-before-croftweaver-'));
      fs.renameSync(target, path.join(result.backup, name));
      result.moved.push(name);
    }
    result.copied.push(name);
  }
  fs.writeFileSync(path.join(dest, MANIFEST), `${JSON.stringify({ release, skills: result.copied }, null, 2)}\n`);
  for (const name of result.copied) fs.renameSync(path.join(staging, name), path.join(dest, name));
  return result;
}

// Removes `from` and its parents up to `upTo`, as far as they are empty.
function removeEmpty(from, upTo) {
  for (let dir = from; dir !== path.dirname(dir); dir = path.dirname(dir)) {
    try { fs.rmdirSync(dir); } catch { return; }
    if (dir === upTo) return;
  }
}

function report({ copied, kept, moved, removed, backup }, dest, release, { label, flag }) {
  const count = (list) => `${list.length} skill${list.length === 1 ? '' : 's'}`;
  if (copied.length) console.log(`Croftweaver ${release ?? '(latest release)'} is installed: ${count(copied)} in ${dest}`);
  else console.log(`Nothing was changed in ${dest}`);
  if (removed.length) console.log(`Removed, no longer part of Croftweaver: ${removed.join(', ')}`);
  if (moved.length) console.log(`Moved aside, not put there by this installer: ${moved.join(', ')}\n  Moved to ${backup}`);
  if (kept.length) {
    console.log(`Left as ${kept.length === 1 ? 'it is' : 'they are'}: ${count(kept)} linked from another folder (${kept[0]} is a link to ${fs.realpathSync(path.join(dest, kept[0]))}).`);
    console.log(`  ${kept.length === 1 ? 'It updates' : 'They update'} from that folder. To replace ${kept.length === 1 ? 'it with a copy' : 'them with copies'}, run: npm create croftweaver -- ${flag}--force`);
  }
  console.log(`\nNext: restart ${label} and open it in your websites folder (Documents/Websites, or\nwherever you keep your projects). Then say:\n\n    new website\n`);
  if (copied.length) console.log('To update later, run this command again.');
}

// The same floor as the site template's package.json, so one Node serves both.
const [major, minor] = process.versions.node.split('.').map(Number);
if (major < 22 || (major === 22 && minor < 12)) {
  console.error(`This installer needs Node 22.12 or newer, and this is Node ${process.versions.node}. Get the current version from https://nodejs.org, then run the command again.`);
  process.exit(1);
}
const { assistant, force } = parseArgs(process.argv.slice(2));
const dest = path.resolve(ASSISTANTS[assistant].dir());
let staging = null;
let made;   // the topmost folder this run had to create for `dest`, if any
let changing = false;
try {
  const { release, zip } = await download(ZIP_URL).catch((e) => {
    throw new Error(`the download from ${ZIP_URL} failed (${e.cause?.code ?? e.message}). Check your internet connection, then run the command again.`);
  });
  made = fs.mkdirSync(dest, { recursive: true });
  staging = fs.mkdtempSync(path.join(dest, '.croftweaver-staging-'));
  let names;
  try {
    names = unpackSkills(zip, staging);
  } catch (e) {
    // A RangeError is a read past the end of the file: a zip cut short or with wrong offsets.
    const why = e instanceof RangeError ? 'it is damaged' : e.message;
    throw new Error(`the download could not be unpacked: ${why}. Nothing in ${dest} was changed.`);
  }
  changing = true;
  report(install(staging, names, dest, release, force), dest, release, ASSISTANTS[assistant]);
} catch (e) {
  console.error(changing
    ? `The install stopped part-way: ${e.message}\nRun the command again to finish it.`
    : `Croftweaver was not installed: ${e.message}`);
  process.exitCode = 1;
} finally {
  if (staging) fs.rmSync(staging, { recursive: true, force: true });
  // "Nothing was changed" holds on a computer without the skills too: no empty folder stays.
  if (made && !changing) removeEmpty(dest, made);
}
