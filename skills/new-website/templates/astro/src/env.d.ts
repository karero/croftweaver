// What a page hands to the components inside it during the build. `lang` is set by
// src/layouts/Base.astro: the page's own language, which can differ from the site's.
declare namespace App {
  interface Locals {
    lang?: string;
  }
}
