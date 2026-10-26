"""Hash-guarded C4 runtime-only transformation of each original owner tree."""
import hashlib,re
CLASS_SHA='12a9245d7f4fd1fd37c267a114876f95cf6b93e6dd87a2f4e7fac1bed23014cc'
ENVELOPE_SHA='b4aecf0ccb2ed6daf3e17365a3f763818ef49bcb64a15a85ed429428d5c2d25b'
def validation(text):
 start=text.index('class ParallelScriptWorkerPool {');end=text.index('\n};',start)+3
 body=text[start:end];assert hashlib.sha256(body.encode()).hexdigest()==CLASS_SHA
 ns=text.rfind('namespace {',0,start)
 if text[ns:start]=='namespace {\n' and text[end:].startswith('\n} // namespace\n'):
  stop=end+len('\n} // namespace\n');envelope=text[ns:stop-1];assert hashlib.sha256(envelope.encode()).hexdigest()==ENVELOPE_SHA
  text=text[:ns]+text[stop:]
 else:
  assert text[end]=='\n';text=text[:start]+text[end+1:]
 assert '#include <util/parallel_range.h>' not in text
 text=text.replace('#include <util/moneystr.h>','#include <util/moneystr.h>\n#include <util/parallel_range.h>',1)
 pattern=r'(?m)^([ \t]*)ParallelScriptWorkerPool::Instance\(\)\.Run\(num_workers, worker_fn\);'
 def run(m):
  i=m[1];return i+'util::GetParallelRangeExecutor().Run(\n'+i+'    num_workers, 1, [&](size_t begin, size_t end) {\n'+i+'        for (size_t tid = begin; tid < end; ++tid) worker_fn(tid);\n'+i+'    });'
 text,n=re.subn(pattern,run,text);assert n==2,n
 old='ParallelScriptWorkerPool::Instance().Run(threads, [&](size_t) {';assert text.count(old)==1;text=text.replace(old,'util::GetParallelRangeExecutor().Run(threads, 1, [&](size_t, size_t) {',1)
 start=text.index('void RunOnValidationWorkers(');end=text.index('\n}\n',start)+3;part=text[start:end]
 assert part.count('auto work = [&](size_t) {')==1;part=part.replace('auto work = [&](size_t) {','auto work = [&](size_t, size_t) {',1)
 old='if (!ParallelScriptWorkerPool::Instance().TryRun(threads, work)) {\n        work(0);';new='if (!util::GetParallelRangeExecutor().TryRun(\n            std::max<size_t>(threads, 1), 1, work)) {\n        work(0, 1);';assert part.count(old)==1;part=part.replace(old,new,1);text=text[:start]+part+text[end:]
 assert 'ParallelScriptWorkerPool' not in text
 return text
