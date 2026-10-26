# Compiler pipeline demonstration

This example exercises the promise-based semantic scheduler and the symbolic
optimizer over lowered P03 stack instructions. Parsing happens once, synchronously;
method and root compilation run as dependency jobs over that retained program.

From `tools/lotus-v2-compiler`:

```sh
npm ci
npm run build
python3 -m venv /tmp/lotus-compiler-demo-venv
/tmp/lotus-compiler-demo-venv/bin/pip install -r ../lotus-v2-reference/requirements-vm.txt
LOTUS_V2_PYTHON=/tmp/lotus-compiler-demo-venv/bin/python \
  node examples/compiler-pipeline/run.mjs /tmp/lotus-compiler-pipeline
```

Python is used only for independent VM verification. Compiling and generating
TypeScript/Python clients require Node and the package's npm dependencies.

The reviewed example prints `Opcodes: 31 -> 11` and `Bytes: 95 -> 75`.
Both valid branches succeed; both malformed Boolean cases fail. The shared
`Base.check` job starts once. With that Python environment already installed,
`LOTUS_V2_PYTHON=/tmp/lotus-compiler-demo-venv/bin/python npm run demo:pipeline`
rebuilds and reruns the demonstration.

The demonstration checks:

- Forward references: `Demonstration` appears before `Left`, `Right`, `Base`, and
  the `same` helper.
- Shared work: `Left.check` and `Right.check` await the same `Base.check` job,
  which starts once.
- Determinism: scheduled and synchronous compilation produce identical artifacts.
- Symbolic stack analysis: repeated reads of the same argument and facts learned
  from a validated branch condition can eliminate redundant work.
- Execution: both Boolean branches succeed in the reference VM; noncanonical and
  incorrectly sized Boolean arguments fail with optimization enabled or disabled.
- Cycle reporting: a self-dependent contract root fails with a dependency path
  and UTF-8 declaration spans.

The output directory contains `optimized.json`, `unoptimized.json`, `trace.json`,
and `summary.json`. Artifacts include bytecode, opcode source maps, method hashes,
proofs, and resource reports. The summary includes the complete VM results and
before/after opcode lists. The explicit demonstration cost schedule charges one
unit per opcode plus structural bytes; these are not frozen consensus prices.

Hash comparisons in this example commit to other compiled methods. They do not
invoke those methods at runtime. This demonstration checks individual invocations,
not full transaction or block acceptance.
