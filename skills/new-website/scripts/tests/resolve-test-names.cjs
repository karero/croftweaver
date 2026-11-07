// Preloaded into the checker's process by cloudflare-check-workers.test.mjs (node --require, which every supported Node reads): names
// ending in .workers.dev.test resolve to this machine, so one local server can play a Worker's
// workers.dev address and its version links, which differ in their first label only.
const dns = require('node:dns');

const lookup = dns.lookup;
dns.lookup = function (hostname, options, callback) {
  if (!/\.workers\.dev\.test$/i.test(hostname)) return lookup.call(this, hostname, options, callback);
  const cb = typeof options === 'function' ? options : callback;
  const all = typeof options === 'object' && options?.all;
  return process.nextTick(() => (all ? cb(null, [{ address: '127.0.0.1', family: 4 }]) : cb(null, '127.0.0.1', 4)));
};
