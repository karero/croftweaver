// The hero carousel's words (the website-hero-carousel skill), installed as
// src/components/hero-carousel-text.ts. The component (HeroCarousel.astro) and its test
// (tests/hero-carousel.spec.ts) import it, so a language is added, or a word changed, here
// and nowhere else. In German the texts address nobody, so they fit a "du" site and a "Sie" site.
//
//   pause, resume   the Pause button's two labels (pause mode "button" only)
//   photo           the name of one dot, for a screen reader: the photo's number, the count and
//                   the label the site gave the slide ("Photo 2 of 3: The old mill")
//   slide           the name of one slide, "2 of 3"
type Texts = {
  pause: string; resume: string;
  photo: (i: number, n: number, label: string) => string;
  slide: (i: number, n: number) => string;
};
export const TEXT = {
  en: {
    pause: 'Pause', resume: 'Resume',
    photo: (i, n, label) => `Photo ${i} of ${n}: ${label}`,
    slide: (i, n) => `${i} of ${n}`,
  },
  de: {
    pause: 'Pause', resume: 'Weiter',
    photo: (i, n, label) => `Foto ${i} von ${n}: ${label}`,
    slide: (i, n) => `${i} von ${n}`,
  },
} satisfies Record<string, Texts>;

export type Language = keyof typeof TEXT;

// Whether there are texts for a language. Own keys only: "constructor" is not one.
export const hasText = (lang: string): lang is Language => Object.hasOwn(TEXT, lang);
