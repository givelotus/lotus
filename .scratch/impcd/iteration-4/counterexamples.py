"""Independent arithmetic/state witnesses; does not execute SnowstormNode."""
from fractions import Fraction
from math import comb
import json

def streak_witness():
    preference='out'; counts={'in':0,'out':0}; c=0; previous=None; final=False
    votes=['in']*11+['out']+['in']*11+['out']*12
    for side in votes:
        assert not final
        counts[side]+=1
        if counts[side]>counts[preference]: preference=side
        c=min(12,c+1) if previous==side else 1
        previous=side
        final=c==12 and side==preference
    assert (counts,preference,c,previous,final)==({'in':22,'out':13},'in',12,'out',False)
    # Body admission preserves state. Next round adds another OUT success.
    counts['out']+=1
    assert counts['out']<counts['in']
    assert preference=='in' and c>=12 and not final
    return dict(counts=counts,preference=preference,c=c,previous=previous,final=final,gate_mean=12,enters=True)

def timing_witness():
    # Fast and silent peers advertise1ms; three slow peers advertise100ms.
    # An8-sample upper median is always1ms: at most3 slow peers can be sampled.
    # Thus slow100ms replies exceed captured4ms fallback, even with accurate slow RTT.
    # One item held by all peers, so only missing the full-K quorum causes gaps.
    q=Fraction(sum(comb(23,y)*comb(9,8-y) for y in range(5,9)),comb(32,8))
    alive=[Fraction(1)]+[Fraction(0)]*11; frozen=Fraction(0)
    for _ in range(25):
        nxt=[Fraction(0)]*12
        for run,prob in enumerate(alive):
            nxt[0]+=prob*(1-q)
            if run==11: frozen+=prob*q
            else:nxt[run+1]+=prob*q
        alive=nxt
    assert frozen+sum(alive)==1
    assert Fraction(50,100)<frozen<Fraction(51,100)
    return dict(round_success=float(q),freeze_by_25=float(frozen),round_success_exact=str(q),assumptions='fresh independent uniform samples; advertised fast/silent RTT1ms, slow RTT100ms; actual fast1ms/slow100ms; no body delays or disagreement')

B=2**21; M=(B-256)//8
cap=min(64*M+4097,(B-116)//28,(B-100-8*M)//28)
assert M==262112 and cap==5
# Complete DIFF with32768 missing IDs fits the wire and has an exact sizing sample.
missing=32768
assert 109+8*missing<B and missing<M
assert (missing+4095)//4096==8>cap
print(json.dumps({'F1':streak_witness(),'F4':{'M':M,'cell_cap':cap,'diff_missing':missing,'conservative_diff_bytes':109+8*missing,'minimum_scaled_quantile':8,'all_CDF_zero_cost':'undefined without an explicit extended-real convention'},'F5':timing_witness()},indent=2))
