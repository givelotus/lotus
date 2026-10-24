"""ASERT half-life comparison. Illustrative model only: Poisson block arrival, exact real-valued
ASERT on the parent, no reward-difficulty coupling and no timestamp manipulation.
Run: python3 docs/lotus-v2/tools/asert_sim.py   (standard library only, about a minute)"""
import math
import random
import statistics as st

TAU = 120.0
HALF_LIVES = [('1h', 3600), ('6h', 21600), ('1d', 86400), ('2d', 172800), ('4d', 345600)]


def run(half_life, blocks, seed, hashrate=1.0, lag=0.0, elastic=0.0):
    """difficulty = 2^(-(t_parent - TAU*h_parent)/H). With elastic > 0, switching miners set
    hashrate = difficulty(t - lag)^(-elastic), bounded to 0.1x..10x."""
    rng, t, out, hist, j = random.Random(seed), 0.0, [], [(0.0, 1.0)], 0
    for h in range(blocks):
        d = 2.0 ** (-(t - TAU * h) / half_life)
        r = hashrate
        if elastic:
            while j + 1 < len(hist) and hist[j + 1][0] <= t - lag:
                j += 1
            r = min(10.0, max(0.1, hist[j][1] ** (-elastic)))
        dt = rng.expovariate(r / (TAU * d))
        out.append((t, d, r, dt))
        t += dt
        hist.append((t, d))
    return out


def main():
    print('A. steady hashrate: spread of difficulty')
    for name, hl in HALF_LIVES:
        logs = [math.log2(d) for _, d, _, _ in run(hl, 300000, 1)[20000:]]
        print(f'  {name:>3}: stdev {100 * (2 ** st.pstdev(logs) - 1):5.1f}%  worst {100 * (2 ** max(abs(x) for x in logs) - 1):5.1f}%')
    for mult, label in ((0.1, 'B. 90% of hashrate leaves'), (0.5, 'B2. half leaves'), (10, 'C. hashrate grows tenfold')):
        print(label)
        for name, hl in HALF_LIVES:
            near, close, week = [], [], []
            for seed in range(15):
                o = run(hl, 400000 if mult > 1 else 60000, 100 + seed, hashrate=mult)
                near.append(next(t for t, d, r, _ in o if (d / r <= 2.0 if mult < 1 else d / r >= 0.5)))
                close.append(next(t for t, d, r, _ in o if (d / r <= 1.25 if mult < 1 else d / r >= 0.8)))
                week.append(sum(1 for t, *_ in o if t < 7 * 86400))
            print(f'  {name:>3}: within 2x of target after {st.median(near) / 86400:5.2f} d, within 25% after '
                  f'{st.median(close) / 86400:5.2f} d; blocks in 7 days {st.median(week):6.0f} (schedule 5040)')
    print('D. profit-switching miners: difficulty swing and hashrate range')
    for elastic, lag in ((3, 3600), (10, 3600), (10, 6 * 3600), (30, 6 * 3600)):
        print(f'  elasticity {elastic}, lag {lag // 3600}h')
        for name, hl in HALF_LIVES:
            o = run(hl, 100000, 7, lag=lag, elastic=elastic)[10000:]
            logs = [math.log2(d) for _, d, _, _ in o]
            rates = [r for _, _, r, _ in o]
            gaps = sorted(dt for *_, dt in o)
            print(f'    {name:>3}: difficulty +/-{100 * (2 ** (2 * st.pstdev(logs)) - 1):.0f}%, hashrate '
                  f'{min(rates):.2f}-{max(rates):.2f}x, 99.9th percentile gap {gaps[int(.999 * len(gaps))] / 60:.0f} min')


if __name__ == '__main__':
    main()
