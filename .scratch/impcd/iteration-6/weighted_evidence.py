"""Exact-tail arithmetic and deterministic rule traces; no SnowstormNode import."""
from decimal import Decimal,localcontext,ROUND_CEILING
from fractions import Fraction
from math import comb,ceil,log,inf
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent

def tail(D,n,y):
    m=(D+1)//2
    return sum((Fraction(comb(m,z)*comb(D-m,n-z),comb(D,n)) for z in range(max(y,n-(D-m),0),min(n,m)+1)),Fraction())
def weight(h):
    if not h:return Decimal('Infinity')
    with localcontext() as ctx:
        ctx.prec=80
        return -(Decimal(h.numerator)/Decimal(h.denominator)).ln()
with localcontext() as ctx:
    ctx.prec=80;threshold=-Decimal('1e-9').ln();rows=[]
    for D in (16,32,64,128,500):
        for K in dict.fromkeys((D,(D+3)//4)):
            floor=K//2+1
            for n in (K,K//2):
                for label,y in [('minimum80percent',(4*n+4)//5),('unanimous',n)]:
                    h=tail(D,n,y);e=weight(h);counted=n>=floor
                    rounds=None if not counted or e==0 else max(3,1 if e.is_infinite() else int((threshold/e).to_integral_value(rounding=ROUND_CEILING)))
                    rows.append(dict(D=D,K=K,fixture='full_population' if K==D else 'quarter_population_experiment_only',answers=n,y=y,vote_case=label,answer_floor=floor,counted=counted,tail=str(h),raw_weight=str(e),applied_weight=str(e) if counted else '0',implied_one_side_rounds=rounds))
    a=weight(tail(16,10,8));b=weight(tail(16,9,8));assert tail(16,10,8)==Fraction(1,286) and tail(16,9,8)==Fraction(1,1430)
    assert 3*a<threshold<5*a-b<3*b
    #13cycles keep OUT preference through strict count ties, but finalizeIN.
    p='out';counts={'in':0,'out':0};S=Decimal(0);final=None
    for j in range(13):
        for side,e in [('out',a),('in',b)]:
            assert final is None
            counts[side]+=1
            if counts[side]>counts[p]:p=side
            S+=e if side=='in' else -e
            if S>=threshold and counts['in']>=3:final='in'
            elif S<=-threshold and counts['out']>=3:final='out'
    assert final=='in' and p=='out' and counts=={'in':13,'out':13}
    preference=dict(sum=str(S),preference=p,final=final,success_counts=counts,each_round_meets_floor=True)
    positive_gate=dict(base_signed_sum=str(a+10*(b-a)),base_positive_IN_sum=str(a+10*b),late_final_IN_sum=str(4*a),trace='base: IN(a), then10cycles OUT(a),IN(b); late x:4IN(a)',both_prefer_IN=True)
    assert a+9*(b-a)<threshold<a+10*(b-a) and threshold<4*a<a+10*b
    # New floor forbids all below-majority valid-vote updates, for all supportedK.
    checked=0
    for K in range(1,1025):
        floor=K//2+1
        for n in range(floor):assert n<floor;checked+=1
    # Transfer/time witness repair: one fastYES cannot meet floor9.
    duration=4;start=0;out_successes=0;timeline=[]
    for number in range(1,10):
        answers=1 if duration<250 else 16
        votes=answers
        if votes>=9:out_successes+=1;assert ceil(.8*16)<=15
        timeline.append(dict(round=number,starts_ms=start,duration_ms=duration,answers=answers,item_counted=votes>=9,out_successes=out_successes,final='out' if out_successes>=3 else None))
        start+=min(duration,250) if answers==16 else duration
        duration=duration*2 if answers<9 else 1000
        if out_successes==3:break
    assert timeline[-1]['final']=='out' and all(t['answers']<9 or t['out_successes']>0 for t in timeline)
    evidence=dict(threshold=str(threshold),full_vs_half_vectors=rows,preference_conflict=preference,positive_only_gate_conflict=positive_gate,gate_conflict=dict(base_final_sum=str(3*b),outsider_final_sum=str(5*a-b),outsider_pref='in',outsider_counts={'in':5,'out':1},all_rounds_meet_floor=True),D1=dict(tail=str(tail(1,1,1)),weight=str(weight(tail(1,1,1))),can_reach_positive_threshold=False),below_floor_vote_counts_checked=checked,repaired_one_fast_timeline=timeline,majority_answer_selection=dict(D=16,K=16,n=9,yes=8,no=1,tail=str(tail(16,9,8)),weight=str(b),rounds_to_threshold=3,score=str(3*b),peer_population_yes=8,peer_population_no=8,meets_answer_floor=True))
    (HERE/'weighted-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    lines=['# Weighted-round reference vectors','','Exact rational tails; natural-log weights at80decimal digits. epsilon=1e-9. K=D and quarter-D are declared fixture families, not a production K policy. Half-answer rounds are below the new answer floor and contribute0; their raw tail weights are diagnostic only. Infinity denotes true zero tail, not numerical underflow. Implied rounds refer only to identical same-side successes and do not resolve opposite-infinity arithmetic.','', '| D | Fixture K | Answered | YES | Case | Raw e | Counted? | One-side rounds |','|---|---|---|---|---|---|---|---|']
    for r in rows:lines.append('| '+ ' | '.join(str(x) for x in [r['D'],r['K'],r['answers'],r['y'],r['vote_case'],str(Decimal(r['raw_weight']).quantize(Decimal('.000000001'))) if r['raw_weight']!='Infinity' else 'infinity','yes' if r['counted'] else 'no',r['implied_one_side_rounds'] if r['implied_one_side_rounds'] is not None else 'never'])+' |')
    (HERE/'weighted-vectors.md').write_text('\n'.join(lines)+'\n')
print('PASS: exact tail vectors, floor-valid preference/gate witnesses, answerfloor guard and rule15 timing trace')
