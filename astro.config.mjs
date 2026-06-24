import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://seteley.github.io',
  base: '/blog',
  markdown: {
    syntaxHighlight: false,
  },
});
