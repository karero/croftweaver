# Evidence — phone-images.spec.ts judges every fit

## The CI job phone-images-test, its three steps run locally as written (bash -eo pipefail, macOS, Chromium 156)

```
=== A site from the starter, with images for every case the test must pass
=== Green, the test alone and then the whole suite
phone images — /: 16 judged by width; hidden and under 4 KiB: /fx/hidden.webp
phone images — /impressum: 0 judged by width
phone images — /privacy: 0 judged by width
phone images — /: 16 judged by width; hidden and under 4 KiB: /fx/hidden.webp
  112 passed (17.6s)
=== Each mistake turns this test red
red as expected (/fx/big.webp is 2000px wide, shown at 200px): an oversized lazy image at the end of a long page
red as expected (/fx/big.webp is 2000px wide, shown at 200px): an oversized image in content added late, once the end is reached
red as expected (/ did not settle at its end within 20 s): a page that never stops growing
red as expected (/fx/big.webp is 2000px wide, shown at 100px): an oversized ::before background
red as expected (/fx/paren(1).webp is 600px wide, shown at 50px): a background drawn at 50px by its background-size
red as expected (/fx/zero.webp is downloaded but hidden at 412px): an image downloaded but hidden by its size
red as expected (/fx/vis.webp is downloaded but hidden at 412px): an image downloaded but hidden by visibility
red as expected (/fx/orphan.webp is preloaded and downloaded): an image preloaded and not shown
red as expected (/fx/ghost.webp was downloaded, but nothing on the page shows it): an image a script loads and never shows
red as expected (/fx/orphan.webp is preloaded and downloaded): an image preloaded by imagesrcset and not shown
red as expected (/fx/big.webp is 2000px wide, shown at 200px): an oversized image fitted by object-fit: scale-down
red as expected (/fx/big.webp is 2000px wide, shown at 190px): an oversized background sized by calc()
red as expected (/fx/big.webp is 2000px wide, shown at 200px): an oversized mask image
exit 0
```

## main's spec (origin/main) against the new fixture page: each new case, one edit at a time

```
--- old spec, green page as is
phone images — /: 11 judged; not judged: /fx/hidden.webp (hidden at 412px, under 4 KiB), /fx/calc.webp (size not worked out: calc(100% - 10px) auto), /fx/sd.webp (size not worked out: scale-down), /fx/none.webp (size not worked out: none), /fx/list.webp (used by a CSS property not judged by width), /fx/mask.webp (used by a CSS property not judged by width)
    +   "/fx/poster.webp is 600px wide, shown at 100px: a 3x phone uses at most 330px; a copy that wide saves about 101 KB",
      176 |       console.log(`phone images — ${path}: ${judged} judged${listed.length ? `; not judged: ${listed.join(', ')}` : ''}`);
  1 failed
--- old spec, edit: s|id="fx-sd" src="/fx/sd.webp"|id="fx-sd" src="/fx/big.webp"|
phone images — /: 11 judged; not judged: /fx/hidden.webp (hidden at 412px, under 4 KiB), /fx/calc.webp (size not worked out: calc(100% - 10px) auto), /fx/none.webp (size not worked out: none), /fx/list.webp (used by a CSS property not judged by width), /fx/mask.webp (used by a CSS property not judged by width), /fx/big.webp (size not worked out: scale-down)
    +   "/fx/poster.webp is 600px wide, shown at 100px: a 3x phone uses at most 330px; a copy that wide saves about 101 KB",
      176 |       console.log(`phone images — ${path}: ${judged} judged${listed.length ? `; not judged: ${listed.join(', ')}` : ''}`);
  1 failed
--- old spec, edit: s|url\(/fx/calc.webp\) center / calc|url(/fx/big.webp) center / calc|
phone images — /: 12 judged; not judged: /fx/hidden.webp (hidden at 412px, under 4 KiB), /fx/sd.webp (size not worked out: scale-down), /fx/none.webp (size not worked out: none), /fx/mask.webp (used by a CSS property not judged by width), /fx/list.webp (used by a CSS property not judged by width), /fx/big.webp (size not worked out: calc(100% - 10px) auto)
    +   "/fx/calc.webp is 600px wide, shown at 50px: a 3x phone uses at most 165px; a copy that wide saves about 134 KB",
    +   "/fx/poster.webp is 600px wide, shown at 100px: a 3x phone uses at most 330px; a copy that wide saves about 101 KB",
      176 |       console.log(`phone images — ${path}: ${judged} judged${listed.length ? `; not judged: ${listed.join(', ')}` : ''}`);
  1 failed
--- old spec, edit: s|mask: url\(/fx/mask.webp\)|mask: url(/fx/big.webp)|
phone images — /: 11 judged; not judged: /fx/hidden.webp (hidden at 412px, under 4 KiB), /fx/calc.webp (size not worked out: calc(100% - 10px) auto), /fx/sd.webp (size not worked out: scale-down), /fx/none.webp (size not worked out: none), /fx/list.webp (used by a CSS property not judged by width), /fx/big.webp (used by a CSS property not judged by width)
    +   "/fx/poster.webp is 600px wide, shown at 100px: a 3x phone uses at most 330px; a copy that wide saves about 101 KB",
      176 |       console.log(`phone images — ${path}: ${judged} judged${listed.length ? `; not judged: ${listed.join(', ')}` : ''}`);
  1 failed
--- old spec, edit: s|(<link slot="head" rel="preload" as="image" href="/fx/swap.webp" />)|$1<link slot="head" rel="preload" as="image" imagesrcset="/fx/orphan.webp 600w" imagesizes="200px" />|
phone images — /: 11 judged; not judged: /fx/hidden.webp (hidden at 412px, under 4 KiB), /fx/calc.webp (size not worked out: calc(100% - 10px) auto), /fx/none.webp (size not worked out: none), /fx/sd.webp (size not worked out: scale-down), /fx/mask.webp (used by a CSS property not judged by width), /fx/list.webp (used by a CSS property not judged by width)
    +   "/fx/orphan.webp was downloaded, but nothing on the page shows it",
    +   "/fx/poster.webp is 600px wide, shown at 100px: a 3x phone uses at most 330px; a copy that wide saves about 101 KB",
      176 |       console.log(`phone images — ${path}: ${judged} judged${listed.length ? `; not judged: ${listed.join(', ')}` : ''}`);
  1 failed
--- old spec, edit: s|object-fit: cover"></video>|"></video>|
phone images — /: 11 judged; not judged: /fx/hidden.webp (hidden at 412px, under 4 KiB), /fx/calc.webp (size not worked out: calc(100% - 10px) auto), /fx/none.webp (size not worked out: none), /fx/sd.webp (size not worked out: scale-down), /fx/mask.webp (used by a CSS property not judged by width), /fx/list.webp (used by a CSS property not judged by width)
    +   "/fx/poster.webp is 600px wide, shown at 100px: a 3x phone uses at most 330px; a copy that wide saves about 101 KB",
      176 |       console.log(`phone images — ${path}: ${judged} judged${listed.length ? `; not judged: ${listed.join(', ')}` : ''}`);
  1 failed
```

## Chromium's computed styles (HeadlessChrome/156)

```
video default objectFit: 'contain'; background-size 'calc(100% - 10px) auto' stays unresolved in computed style; mask-image 'url("a.webp")', mask-size '100% auto'
```

## make check

```
all checks passed
```
