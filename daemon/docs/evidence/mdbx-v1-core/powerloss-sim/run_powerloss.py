#!/usr/bin/env python3
"""Build libmdbx variants and run the power-loss and kill -9 experiments.

Usage: run_powerloss.py <upstream-0.14.4-src-dir> <mdbx.c-patch-or-none> <workdir> [trials]

A power cut can leave on disk any subset of the pages dirtied since the last
completed sync, because the kernel writes dirty pages back in any order. Each
trial builds such an image from D0 (file at the last explicit sync) and D1 (page
cache just before the "power cut"), then erases the boot id in the meta pages, as
a reboot would make it stale, and runs the verifier. mdbx_chk is built but chk()
is never called.

KNOWN DEFECT: the model assumes D0 is the only steady checkpoint. Under SAFE_NOSYNC
libmdbx took later steady checkpoints during the "unsynced" phase (see the "gen"
lines in the report), so those images are not legal power-loss states and the
SAFE_NOSYNC power-loss outcomes mean nothing. See daemon/audit/mdbx-v1-core.md.
"""
import collections, json, os, random, shutil, signal, struct, subprocess, sys, time

SRC, PATCH, WORK = sys.argv[1], sys.argv[2], sys.argv[3]
TRIALS = int(sys.argv[4]) if len(sys.argv) > 4 else 60
HERE = os.path.dirname(os.path.abspath(__file__))

WRITEMAP, SAFE, UTTERLY, NOMETA, NOSTICKY, NOMEMINIT, LIFO, NORDAHEAD = (
    0x80000, 0x10000, 0x110000, 0x40000, 0x200000, 0x1000000, 0x4000000, 0x800000)
CONFIGS = {
  # name: (libmdbx build, env flags, page size, metas-from-D0 legal?)
  "v1-pr-24 patched mdbx.c, WRITEMAP|UTTERLY_NOSYNC|NOMETASYNC": ("patched", WRITEMAP|UTTERLY|NOMETA|LIFO|NOSTICKY|NOMEMINIT, 8192, True),
  "upstream mdbx.c, WRITEMAP|UTTERLY_NOSYNC|NOMETASYNC": ("upstream", WRITEMAP|UTTERLY|NOMETA|LIFO|NOSTICKY|NOMEMINIT, 8192, False),
  "core-pr-25 patched mdbx.c, WRITEMAP|SAFE_NOSYNC|NOMETASYNC": ("patched", WRITEMAP|SAFE|NOMETA|LIFO|NORDAHEAD, 4096, True),
  "ported: upstream mdbx.c, SAFE_NOSYNC|NOMETASYNC": ("upstream", SAFE|NOMETA|LIFO|NOSTICKY|NOMEMINIT, 4096, True),
}

def sh(*a, **k):
    return subprocess.run(a, check=True, capture_output=True, text=True, **k)

def build(variant):
    d = os.path.join(WORK, "build-" + variant)
    os.makedirs(d, exist_ok=True)
    for f in ("mdbx.c", "mdbx.h", "mdbx-internals.h", "mdbx_chk.c", "mdbx-wingetopt.h"):
        shutil.copy(os.path.join(SRC, f), d)
    extra = []
    if variant == "patched":
        sh("patch", "-p3", "-d", d, "-i", os.path.abspath(PATCH))
        extra = ["-DMDBX_CHECKING=-1"]
    objs = os.path.join(d, "mdbx.o")
    sh("cc", "-std=gnu11", "-O2", "-DNDEBUG", "-DMDBX_BUILD_SHARED_LIBRARY=0", '-DMDBX_BUILD_FLAGS="x"',
       *extra, "-w", "-c", "mdbx.c", "-o", "mdbx.o", cwd=d)
    sh("c++", "-std=c++17", "-O2", "-w", "-I.", os.path.join(HERE, "sim.cpp"), "mdbx.o", "-o", "sim", cwd=d)
    sh("cc", "-std=gnu11", "-O1", "-w", "-DMDBX_BUILD_SHARED_LIBRARY=0", '-DMDBX_BUILD_FLAGS="x"',
       "mdbx_chk.c", "mdbx.o", "-o", "mdbx_chk", cwd=d)
    return d

def meta_info(img, page):
    return None

def clear_bootid(img, page):
    """Zero the 16-byte boot id at the end of each of the three meta pages' meta_t."""
    # meta_t follows the 20-byte page header. bootid is the last field; offsets
    # are taken from mdbx_bootid_offset, printed by the helper below.
    with open(img, "r+b") as f:
        for p in range(3):
            f.seek(p * page + 20 + BOOTID_OFFSET)
            f.write(b"\xa5" * 16)

def verify(bindir, case, flags, page):
    r = subprocess.run([os.path.join(bindir, "sim"), "verify", case, hex(flags), str(page)],
                       capture_output=True, text=True, timeout=300)
    out = (r.stdout.strip().splitlines() or [""])[-1]
    if r.returncode < 0:
        return "CRASH signal %d" % -r.returncode
    if r.returncode == 3:
        return "ERROR " + r.stderr.strip().splitlines()[-1]
    return out

def chk(bindir, case):
    r = subprocess.run([os.path.join(bindir, "mdbx_chk"), "-q", "-n", os.path.join(case, "db")],
                       capture_output=True, text=True, timeout=300)
    return r.returncode

def classify(s):
    return s.split(" marker")[0].split(" rc=")[0].split(" signal")[0][:40]

def powerloss(name, variant, flags, page, metas_d0_ok):
    bindir = os.path.join(WORK, "build-" + variant)
    case = os.path.join(WORK, "gen")
    shutil.rmtree(case, ignore_errors=True)
    os.makedirs(os.path.join(case, "db"))
    gen = sh(os.path.join(bindir, "sim"), "gen", case, hex(flags), str(page))
    d0 = open(os.path.join(case, "D0"), "rb").read()
    d1 = open(os.path.join(case, "D1"), "rb").read()
    d0 = d0 + b"\0" * (len(d1) - len(d0)) if len(d1) > len(d0) else d0
    if len(d0) > len(d1):
        d1 = d1 + d0[len(d1):]
    npages = len(d1) // page
    dirty = [p for p in range(3, npages) if d0[p*page:(p+1)*page] != d1[p*page:(p+1)*page]]
    res = collections.Counter(); chkbad = 0; examples = {}
    rnd = random.Random(1234)
    t = os.path.join(WORK, "trial")
    for i in range(TRIALS):
        prob = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0][i % 6]
        # Which meta pages reached the disk is also arbitrary. Where upstream
        # msyncs the steady-signature wipe before reusing pages, that ordering
        # is guaranteed, so the old metas are not a legal outcome.
        metas_from_d1 = (not metas_d0_ok) or (i % 2 == 1)
        img = bytearray(d0)
        for p in dirty:
            if rnd.random() < prob:
                img[p*page:(p+1)*page] = d1[p*page:(p+1)*page]
        if metas_from_d1:
            img[:3*page] = d1[:3*page]
        shutil.rmtree(t, ignore_errors=True)
        os.makedirs(os.path.join(t, "db"))
        path = os.path.join(t, "db", "mdbx.dat")
        with open(path, "wb") as f:
            f.write(img)
        clear_bootid(path, page)
        out = verify(bindir, t, flags, page)
        c = classify(out); res[c] += 1
        examples.setdefault(c, out)
    return dict(name=name, gen=gen.stdout.strip().splitlines(), file_pages=npages, dirty_pages=len(dirty),
                trials=TRIALS, outcomes=dict(res), examples=examples)

def killtest(name, variant, flags, page, rounds=25):
    bindir = os.path.join(WORK, "build-" + variant)
    case = os.path.join(WORK, "kill")
    shutil.rmtree(case, ignore_errors=True)
    os.makedirs(os.path.join(case, "db"))
    res = collections.Counter(); examples = {}
    rnd = random.Random(99)
    marker = 0
    last = None
    for i in range(rounds):
        args = [os.path.join(bindir, "sim"), "kill-writer", case, hex(flags), str(page)]
        if marker:
            args.append(str(marker))
        p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        time.sleep(rnd.uniform(0.2, 1.2))
        p.send_signal(signal.SIGKILL); p.wait()
        out = verify(bindir, case, flags, page)
        c = classify(out); res[c] += 1
        examples.setdefault(c, out)
        if out.startswith("exact-prefix"):
            marker = int(out.split("marker=")[1]) + 1
        else:
            break
    return dict(name=name, rounds=sum(res.values()), outcomes=dict(res), final_marker=marker, examples=examples)

def bootid_offset():
    # meta_t: magic_and_version 8, reserve16/validator_id/extra_pagehdr/pagesize 4,
    # geometry 20? Avoid guessing: read it from the field layout in mdbx-internals.
    h = open(os.path.join(SRC, "mdbx-internals.h")).read()
    i = h.index("typedef struct meta {")
    return h[i:i+2200]

def find_bootid_offset(bindir):
    """Find the boot id by locating its bytes from a real file and mi_bootid."""
    src = '''#include "mdbx.h"
#include <stdio.h>
int main(int c,char**v){MDBX_env*e;mdbx_env_create(&e);mdbx_env_open(e,v[1],(MDBX_env_flags_t)0,0600);
MDBX_envinfo i;mdbx_env_info_ex(e,0,&i,sizeof(i));
printf("%llx %llx\\n",(unsigned long long)i.mi_bootid.current.x,(unsigned long long)i.mi_bootid.current.y);return 0;}'''
    d = os.path.join(WORK, "bootid"); shutil.rmtree(d, ignore_errors=True); os.makedirs(d + "/db")
    open(d + "/b.c", "w").write(src)
    sh("cc", "-w", "-I" + bindir, d + "/b.c", bindir + "/mdbx.o", "-o", d + "/b")
    x, y = [int(v, 16) for v in sh(d + "/b", d + "/db").stdout.split()]
    if not (x or y):
        raise SystemExit("no boot id on this platform: the rollback path cannot be exercised")
    blob = struct.pack("<QQ", x, y)
    # Create one sync so a meta carries the current boot id.
    sim = os.path.join(bindir, "sim")
    d2 = os.path.join(WORK, "bootid2"); shutil.rmtree(d2, ignore_errors=True); os.makedirs(d2 + "/db")
    subprocess.run([sim, "gen", d2, hex(SAFE|NOMETA), "4096"], capture_output=True)
    data = open(d2 + "/D1", "rb").read()[:3*4096]
    for pg in range(3):
        at = data[pg*4096:(pg+1)*4096].find(blob)
        if at >= 0:
            return at - 20
    raise SystemExit("boot id not found in meta pages")

os.makedirs(WORK, exist_ok=True)
build("upstream"); build("patched")
BOOTID_OFFSET = find_bootid_offset(os.path.join(WORK, "build-upstream"))
report = {"bootid_offset_in_meta": BOOTID_OFFSET, "powerloss": [], "kill9": []}
for name, (variant, flags, page, meta_ok) in CONFIGS.items():
    report["powerloss"].append(powerloss(name, variant, flags, page, meta_ok))
    print(json.dumps(report["powerloss"][-1], indent=1), flush=True)
    report["kill9"].append(killtest(name, variant, flags, page))
    print(json.dumps(report["kill9"][-1], indent=1), flush=True)
json.dump(report, open(os.path.join(WORK, "report.json"), "w"), indent=1)
