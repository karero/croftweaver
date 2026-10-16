// Shared by the test files: builds a zip in memory.
import zlib from 'node:zlib';

// A zip from { name: text } or { name: { data, mode, store, crc } }. It writes what the reader
// has to cope with, including what no zip tool writes on request: a path that climbs out, a
// link, a wrong checksum.
export function makeZip(files) {
  const locals = [];
  const centrals = [];
  let offset = 0;
  for (const [entryName, spec] of Object.entries(files)) {
    const { data = '', mode = 0o100644, store = false, crc } = typeof spec === 'string' ? { data: spec } : spec;
    const name = Buffer.from(entryName);
    const plain = Buffer.from(data);
    const body = store ? plain : zlib.deflateRawSync(plain);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(store ? 0 : 8, 8);
    local.writeUInt32LE(crc ?? zlib.crc32(plain), 14);
    local.writeUInt32LE(body.length, 18);
    local.writeUInt32LE(plain.length, 22);
    local.writeUInt16LE(name.length, 26);
    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE((3 << 8) | 30, 4);   // made on unix, so the mode below counts
    central.writeUInt16LE(20, 6);
    central.writeUInt16LE(store ? 0 : 8, 10);
    central.writeUInt32LE(crc ?? zlib.crc32(plain), 16);
    central.writeUInt32LE(body.length, 20);
    central.writeUInt32LE(plain.length, 24);
    central.writeUInt16LE(name.length, 28);
    central.writeUInt32LE((mode << 16) >>> 0, 38);
    central.writeUInt32LE(offset, 42);
    locals.push(local, name, body);
    centrals.push(central, name);
    offset += 30 + name.length + body.length;
  }
  const directory = Buffer.concat(centrals);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(centrals.length / 2, 8);
  end.writeUInt16LE(centrals.length / 2, 10);
  end.writeUInt32LE(directory.length, 12);
  end.writeUInt32LE(offset, 16);
  return Buffer.concat([...locals, directory, end]);
}
