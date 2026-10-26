// Public-key-only adapter to the shared compiler and its canonical Payment source.
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const [directory] = process.argv.slice(2);
if (!directory) throw Error('compiler directory required');
const input = readFileSync(0);
if (input.length > 1024) throw Error('public compiler request too large');
const request = JSON.parse(input.toString('utf8'));
if (Object.keys(request).join(',') !== 'owner' || !/^[0-9a-f]{64}$/.test(request.owner))
  throw Error('exact public x-only owner request required');
const { compileContract } = await import(pathToFileURL(resolve(directory, 'dist/generic.js')).href);
const source = readFileSync(resolve(directory, 'examples/gallery/payment.lotus'), 'utf8');
const artifact = compileContract(source, { contract: 'Payment', bindings: { Payment: { owner: request.owner } } });
const method = artifact.methods.find(method => method.name === 'spend');
if (!method || artifact.methods.length !== 1 || method.proof.length !== 0)
  throw Error('native wallet requires the sole compiled Payment spend method');
process.stdout.write(JSON.stringify({ script: method.scriptHex, proof: method.proof, root: artifact.policy.root }) + '\n');
