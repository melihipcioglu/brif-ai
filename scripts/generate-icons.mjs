// Generates PWA icons (PNG) without external dependencies.
// Usage: node scripts/generate-icons.mjs
import { deflateSync } from 'node:zlib';
import { mkdirSync, writeFileSync } from 'node:fs';

const OUT = 'public/icons';
mkdirSync(OUT, { recursive: true });

const BG_TOP = [29, 78, 216]; // #1d4ed8
const BG_BOTTOM = [30, 58, 138]; // #1e3a8a
const FG = [255, 255, 255];

function crc32(buf) {
  let c;
  const table = [];
  for (let n = 0; n < 256; n++) {
    c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  let crc = 0xffffffff;
  for (const b of buf) crc = table[(crc ^ b) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const td = Buffer.concat([Buffer.from(type), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(td));
  return Buffer.concat([len, td, crc]);
}

function encodePng(size, rgb) {
  const raw = Buffer.alloc((size * 3 + 1) * size);
  for (let y = 0; y < size; y++) {
    raw[y * (size * 3 + 1)] = 0;
    rgb.copy(raw, y * (size * 3 + 1) + 1, y * size * 3, (y + 1) * size * 3);
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0);
  ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 2; // RGB
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw, { level: 9 })),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

function distToSegment(px, py, ax, ay, bx, by) {
  const dx = bx - ax;
  const dy = by - ay;
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)));
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

// "Y" glyph in unit coordinates. `scale` shrinks it toward the center for maskable icons.
function render(size, scale) {
  const rgb = Buffer.alloc(size * size * 3);
  const SS = 3; // supersampling per axis
  const half = 0.0475 * scale; // half stroke thickness
  const map = ([x, y]) => [0.5 + (x - 0.5) * scale, 0.5 + (y - 0.5) * scale];
  const [tl, tr, c, b] = [
    [0.27, 0.24],
    [0.73, 0.24],
    [0.5, 0.54],
    [0.5, 0.78],
  ].map(map);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      let cov = 0;
      for (let sy = 0; sy < SS; sy++) {
        for (let sx = 0; sx < SS; sx++) {
          const px = (x + (sx + 0.5) / SS) / size;
          const py = (y + (sy + 0.5) / SS) / size;
          const d = Math.min(
            distToSegment(px, py, tl[0], tl[1], c[0], c[1]),
            distToSegment(px, py, tr[0], tr[1], c[0], c[1]),
            distToSegment(px, py, c[0], c[1], b[0], b[1]),
          );
          if (d <= half) cov++;
        }
      }
      const a = cov / (SS * SS);
      const t = y / size;
      for (let ch = 0; ch < 3; ch++) {
        const bg = BG_TOP[ch] + (BG_BOTTOM[ch] - BG_TOP[ch]) * t;
        rgb[(y * size + x) * 3 + ch] = Math.round(bg * (1 - a) + FG[ch] * a);
      }
    }
  }
  return rgb;
}

const targets = [
  ['icon-192.png', 192, 1],
  ['icon-512.png', 512, 1],
  ['icon-maskable-512.png', 512, 0.72],
  ['apple-touch-icon.png', 180, 0.9],
];
for (const [name, size, scale] of targets) {
  writeFileSync(`${OUT}/${name}`, encodePng(size, render(size, scale)));
  console.log('wrote', `${OUT}/${name}`);
}

writeFileSync(
  `${OUT}/icon.svg`,
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1d4ed8"/><stop offset="1" stop-color="#1e3a8a"/></linearGradient></defs><rect width="512" height="512" fill="url(#g)"/><path d="M138 123 L256 277 L374 123 M256 277 L256 399" fill="none" stroke="#fff" stroke-width="49" stroke-linecap="round" stroke-linejoin="round"/></svg>\n`,
);
console.log('wrote', `${OUT}/icon.svg`);
