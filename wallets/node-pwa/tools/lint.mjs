#!/usr/bin/env node
// Small custom lint for src/ (Node stdlib only):
//  - every .js/.mjs file parses (node --check);
//  - no HTML-string sinks or dynamic code: innerHTML, outerHTML,
//    insertAdjacentHTML, document.write, dangerouslySetInnerHTML, eval,
//    new Function, string setTimeout/setInterval;
//  - no inline event handlers, inline scripts or inline styles in index.html;
//  - no http(s):// URLs in src/ outside vendor/ (the app never fetches remote
//    content; the SVG XML namespace is the one allowed literal).
// Vendored files are checked only for their hashes (test/unit/vendor.test.js).

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../src/', import.meta.url));

export function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir).sort()) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else out.push(p);
  }
  return out;
}

const BANNED = [
  [/\binnerHTML\b/, 'innerHTML'],
  [/\bouterHTML\b/, 'outerHTML'],
  [/\binsertAdjacentHTML\b/, 'insertAdjacentHTML'],
  [/\bdocument\.write(ln)?\s*\(/, 'document.write'],
  [/\bdangerouslySetInnerHTML\b/, 'dangerouslySetInnerHTML'],
  [/(^|[^.\w])eval\s*\(/, 'eval'],
  [/\bnew\s+Function\s*\(/, 'new Function'],
  [/\bset(Timeout|Interval)\s*\(\s*['"`]/, 'string timer'],
];
const ALLOWED_URLS = new Set(['http://www.w3.org/2000/svg']);

/** @returns {string[]} problems in one file's text */
export function lintText(rel, text) {
  const problems = [];
  const isVendor = rel.startsWith('vendor/');
  if (!isVendor && /\.(m?js)$/.test(rel)) {
    text.split('\n').forEach((line, i) => {
      for (const [re, what] of BANNED) if (re.test(line)) problems.push(`${rel}:${i + 1}: ${what} is not allowed`);
    });
  }
  if (rel.endsWith('.html')) {
    if (/\son[a-z]+\s*=/i.test(text)) problems.push(`${rel}: inline event handler attribute`);
    if (/<script(?![^>]*\ssrc=)[^>]*>/i.test(text)) problems.push(`${rel}: inline <script>`);
    if (/<style[\s>]/i.test(text) || /\sstyle\s*=/i.test(text)) problems.push(`${rel}: inline style`);
  }
  if (!isVendor) {
    for (const m of text.matchAll(/https?:\/\/[^\s'"`)<>]+/g)) {
      if (!ALLOWED_URLS.has(m[0])) problems.push(`${rel}: remote URL ${m[0]}`);
    }
  }
  return problems;
}

function main() {
  const problems = [];
  for (const file of walk(root)) {
    const rel = relative(root, file).split('\\').join('/');
    if (/\.(png|ico|woff2|wasm)$/.test(rel)) continue;
    const text = readFileSync(file, 'utf8');
    problems.push(...lintText(rel, text));
    if (/\.(m?js)$/.test(rel)) {
      try {
        execFileSync(process.execPath, ['--check', file], { stdio: 'pipe' });
      } catch (e) {
        problems.push(`${rel}: syntax error\n${e.stderr}`);
      }
    }
  }
  if (problems.length) {
    console.error(problems.join('\n'));
    process.exit(1);
  }
  console.log('lint: ok');
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) main();
