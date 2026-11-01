"""Independent transition exploration of the revised gate implication."""
import json
from collections import deque
BETA=12
# State: preferred side, cumulative IN, cumulative OUT, c, previous side, FINAL.
# Side0=IN, side1=OUT; previous -1=none. No production imports.
def advance(state,side):
    p,di,do,c,prev,final=state
    if final:return state
    if side is None:return (p,di,do,0,prev,False)
    counts=[di,do];counts[side]+=1
    if counts[side]>counts[p]:p=side
    c=min(BETA,c+1) if prev==side else 1
    return p,*counts,c,side,(c==BETA and side==p)
def gate(state):return state[3] if state[4]==0 else 0
state=(1,0,0,0,-1,False)
for side in [0]*11+[1]+[0]*11+[1]*12+[1]:state=advance(state,side)
assert state==(0,22,14,12,1,False)
assert gate(state)==0
blocked=state
for i in range(12):
    state=advance(state,0)
    assert (gate(state)>=BETA)==(i==11)
assert state[0]==0 and state[-1] and gate(state)==12
# Explore all distinct reachable states through24updates, including no-success.
# Each fresh lifetime can start IN or OUT; FINAL accepts no further updates.
seeds=[(p,0,0,0,-1,False) for p in (0,1)]
seen=set(seeds);queue=deque((s,0) for s in seeds);edges=0
while queue:
    s,depth=queue.popleft()
    assert not (s[0]==0 and gate(s)>=BETA) or (s[-1] and s[4]==0)
    if depth==24:continue
    for side in (0,1,None):
        t=advance(s,side);edges+=1
        if t not in seen:seen.add(t);queue.append((t,depth+1))
assert sum([12,0])/2==6 # previous-OUT high c contributes0 to W mean.
print(json.dumps({'blocked_old_witness':blocked,'after_twelve_IN':state,'states_explored_through24':len(seen),'edges_checked':edges,'property':'p=IN and gate_value>=12 implies FINAL-in for every explored reachable state','scope':'transition arithmetic only; not peer-network agreement or SnowstormNode execution'},indent=2))
