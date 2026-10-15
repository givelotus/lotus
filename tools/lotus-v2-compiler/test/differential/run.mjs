import { readFileSync } from 'node:fs';
import { corpus,signedCases,runCorpus,saveReport } from './harness.mjs';
const [directory,seed='79225',file]=process.argv.slice(2);
if(!directory)throw Error('usage: node test/differential/run.mjs OUTPUT_DIRECTORY [SEED] [CORPUS_JSON]');
const input=file?JSON.parse(readFileSync(file,'utf8')):corpus(Number(seed));
if(!file)input.cases.push(...signedCases());
const report=runCorpus(input,{native:process.env.LOTUS_V2_NATIVE_VM});saveReport(report,directory);
console.log(JSON.stringify({cases:report.cases.length,discrepancies:report.cases.filter(c=>c.discrepancies.length).length,unsupported:report.cases.filter(c=>c.native.status==='unsupported').length}));
process.exitCode=report.cases.some(c=>c.discrepancies.length||c.python.status==='tool-error'||c.native.status==='tool-error')?1:0;
