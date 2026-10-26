// Coverage instrumentation only: existing server tests terminate children via SIGTERM.
// Flush V8 coverage before exit so successful server requests enter the denominator.
import {takeCoverage} from 'node:v8';
if (process.argv[1]?.endsWith('/server.mjs') || process.argv[1] === 'server.mjs') {
  process.once('SIGTERM', () => { takeCoverage(); process.exit(143); });
}
