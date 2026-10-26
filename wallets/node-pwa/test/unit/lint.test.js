import { test } from 'node:test';
import assert from 'node:assert/strict';
import { lintText } from '../../tools/lint.mjs';

test('lint flags HTML sinks, dynamic code and remote URLs', () => {
  const bad = [
    'el.innerHTML = x', 'el.outerHTML', 'el.insertAdjacentHTML("a", b)', 'document.write(x)', 'eval(x)',
    'new Function("x")', 'setTimeout("alert(1)", 1)', '<div dangerouslySetInnerHTML=${x} />', "fetch('https://evil.example/x')",
  ];
  for (const line of bad) assert.ok(lintText('lib/x.js', line).length > 0, line);
  assert.deepEqual(lintText('lib/x.js', 'const ns = "http://www.w3.org/2000/svg"; obj.evaluate(x); retrieval(1)'), []);
  assert.deepEqual(lintText('vendor/x.mjs', 'el.innerHTML = 1 // https://upstream.example'), []);
});

test('lint flags inline handlers, scripts and styles in HTML', () => {
  assert.ok(lintText('index.html', '<body onload="x()">').length);
  assert.ok(lintText('index.html', '<script>alert(1)</script>').length);
  assert.ok(lintText('index.html', '<p style="color:red">').length);
  assert.ok(lintText('index.html', '<style>p{}</style>').length);
  assert.deepEqual(lintText('index.html', '<script type="module" src="main.js"></script>'), []);
});
