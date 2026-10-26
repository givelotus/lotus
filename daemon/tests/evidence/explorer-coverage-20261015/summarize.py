#!/usr/bin/env python3
"""Summarize retained coverage exports; no application code or tests modified."""
import gzip, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parent

def read(path):
    if path.exists(): return json.loads(path.read_text())
    return json.loads(gzip.decompress(path.with_suffix(path.suffix+'.gz').read_bytes()))

front=read(ROOT/'frontend/coverage-summary.json')
frontend={('total' if key=='total' else key.split('/explorer/v2/')[-1]):value for key,value in front.items()}
native=read(ROOT/'native/coverage.json')['data'][0]
producer={'totals':native['totals'], 'files':{row['filename'].split('/src/lotus_v2/')[-1]:row['summary'] for row in native['files']},
          'uncovered_branch_outcomes':[{'file':row['filename'].split('/src/lotus_v2/')[-1], 'line':b[0], 'column':b[1], 'true':b[4], 'false':b[5]} for row in native['files'] for b in row['branches'] if b[4]==0 or b[5]==0],
          'unmapped_configuration':'LOTUS_V2_CHRONIK_CXX adapter is not compiled by the standalone suites; node launch/publication wiring excluded'}
result={'frontend':frontend,'native_producer':producer}
if (ROOT/'rust/coverage.lcov').exists():
    files={}; row=None
    for line in (ROOT/'rust/coverage.lcov').read_text().splitlines():
        if line.startswith('SF:'):
            name=line[3:].split('/chronik/')[-1]; row={'lines':{},'functions':{},'branches':[]};files[name]=row
        elif row is not None and line.startswith('DA:'):
            number,count=map(int,line[3:].split(',')[:2]);row['lines'][number]=max(count,row['lines'].get(number,0))
        elif row is not None and line.startswith('FN:'):
            number,name=line[3:].split(',',1);row['functions'].setdefault(name,{'line':int(number),'count':0})
        elif row is not None and line.startswith('FNDA:'):
            count,name=line[5:].split(',',1);row['functions'][name]['count']+=int(count)
        elif row is not None and line.startswith('BRDA:'): row['branches'].append(line[5:])
    # HTTP source contains one inline test module; other scope files use external test modules.
    # Pin and check range against exact86201398e3 source before relying on this exclusion.
    excluded={'chronik-http/src/v2_explorer.rs':[(1199,1314)]}
    rust={}
    for name,row in files.items():
        keep=lambda n:not any(lo<=n<=hi for lo,hi in excluded.get(name,[]))
        lines={n:c for n,c in row['lines'].items() if keep(n)}
        funcs={n:f for n,f in row['functions'].items() if keep(f['line'])}
        rust[name]={'lines':{'covered':sum(c>0 for c in lines.values()),'count':len(lines)},
                    'mapped_function_instances':{'covered':sum(f['count']>0 for f in funcs.values()),'count':len(funcs)},
                    'uncovered_lines':[n for n,c in lines.items() if c==0],
                    'excluded_inline_test_ranges':excluded.get(name,[]),
                    'branch_records':len(row['branches'])}
    result['rust_api']=rust
(ROOT/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
