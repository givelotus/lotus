/** Source target selection. eCash emits a direct script, never a Lotus policy. */
import { compileContract, parseModuleSource, type CompileOptions, type ContractArtifact, type Expr, type Stmt, type ValueType } from './generic.js';
import { DiagnosticBag, SourceManager } from './diagnostics.js';
import { resolveTarget, checkCapabilities, type SemanticCapability, type SourceSpan, type TargetDescriptor, type TargetDiagnostic } from './targets.js';
import { validateSemanticProgram, type SemanticProgram, type SemanticExpr, type SemanticStmt, type SemanticType } from './semantic-ir.js';
import { compileEcash, type EcashArtifact } from './ecash.js';

export type TargetCompileOptions = Omit<CompileOptions, 'target'> & { target?: string; method?: string };
export type TargetArtifact = ContractArtifact | EcashArtifact;

export function compileTargetContract(source: string, options: TargetCompileOptions, file = '<source>'): TargetArtifact {
  const sources = new SourceManager(); sources.add(file, source);
  const bag = new DiagnosticBag(sources, file);
  function fail(code: string, message: string, span?: SourceSpan): never { return bag.raise(code, message, span); }
  if (!options || typeof options.contract !== 'string' || !options.bindings || typeof options.bindings !== 'object' || Array.isArray(options.bindings))
    fail('E0601', 'compile options require contract and bindings');
  const target: TargetDescriptor = (() => {
    try { return resolveTarget(options.target === undefined ? 'lotus-v2' : options.target); }
    catch (error) { return fail('E1200', (error as Error).message); }
  })();
  if (target.id === 'lotus-v2') {
    if (options.method !== undefined) fail('E1202', 'Lotus compilation commits the complete contract policy; method selection is available only for the eCash script target.');
    return compileContract(source, { ...options, target: 'lotus-v2' }, file);
  }
  if (options.optimize === true || (options.optimizerVersion !== undefined && options.optimizerVersion !== 'none'))
    fail('E1203', 'The eCash backend has no optimizer; omit optimize or set optimize:false. Lotus optimizations are not applied to eCash bytecode.');
  const program = parseModuleSource(source, true, file, sources);
  if (program.imports.length) fail('E1203', 'eCash source compilation does not yet link packages or imported helpers.', program.imports[0]!.span);
  const contract = program.contracts.get(options.contract);
  if (!contract) fail('E0605', `unknown contract ${options.contract}`);
  const diagnostic = (error: TargetDiagnostic): never => fail(
    error.code.startsWith('semantic-ir-') ? 'E1204' : error.code, error.message, error.span);
  const unsupported = (capability: SemanticCapability, span: SourceSpan): never => {
    const [error] = checkCapabilities(target, [{ capability, span }]);
    if (error) diagnostic(error);
    fail('E1203', `eCash source lowering for ${capability} is not implemented.`, span);
  };
  if (contract.kind === 'token') unsupported('lotus-token', contract.span);
  if (options.method !== undefined && typeof options.method !== 'string') fail('E1202', 'selected method must be a string', contract.span);
  if (options.method === undefined && contract.methods.length !== 1) fail('E1202', 'eCash requires an explicit selected method when a contract has multiple methods; no dispatcher or combined policy is emitted.', contract.span);
  const method = options.method === undefined ? contract.methods[0]! : contract.methods.find(m => m.name === options.method);
  if (!method) fail('E1202', `unknown selected method ${contract.name}.${options.method}`, contract.span);
  const type = (value: ValueType, span: SourceSpan): SemanticType => {
    if (value === 'Bool') return { kind: 'bool' };
    if (value === 'Bytes32') return { kind: 'bytes', length: 32 };
    const sized = /^Bytes\(([0-9]+)\)$/.exec(value);
    if (sized) return fail('E1203', `Source ${value} is a maximum byte bound; the current eCash IR requires exact lengths. Use Bytes32 for an exact 32-byte argument or wait for bounded-byte lowering.`, span);
    if (value === 'Int' || value === 'Amount') return unsupported('lotus-int128', span);
    if (value === 'PublicKey' || value === 'Signature') return unsupported('transaction-signature', span);
    if (value === 'TokenId') return unsupported('lotus-token', span);
    return unsupported('transaction-reflection', span);
  };
  const constants = new Map<string, SemanticExpr>();
  const bound = options.bindings[contract.name] ?? {};
  if (!bound || typeof bound !== 'object' || Array.isArray(bound) || Object.keys(bound).length !== contract.params.length)
    fail('E0602', `constructor arity mismatch for ${contract.name}`, contract.span);
  for (const p of contract.params) {
    if (!Object.hasOwn(bound, p.name)) fail('E0603', `missing constructor binding ${contract.name}.${p.name}`, p.span);
    const t = type(p.type, p.span), value = bound[p.name];
    if (t.kind === 'bool') {
      if (typeof value !== 'boolean') fail('E0604', `${p.name} requires a Boolean constructor binding`, p.span);
      constants.set(p.name, { kind: 'bool', value, span: p.span });
    } else {
      if (typeof value !== 'string' || !/^(?:[0-9a-fA-F]{2})*$/.test(value) || value.length !== t.length * 2)
        fail('E0604', `${p.name} requires exactly ${t.length} bytes of hexadecimal`, p.span);
      constants.set(p.name, { kind: 'bytes', hex: value.toLowerCase(), span: p.span });
    }
  }
  const args = method.params.map(p => {
    if (constants.has(p.name)) fail('E0205', `method parameter shadows constructor parameter ${p.name}`, p.span);
    return { name: p.name, type: type(p.type, p.span), span: p.span };
  });
  const expression = (expr: Expr): SemanticExpr => {
    const span = expr.span;
    if (expr.kind === 'bool') return { kind: 'bool', value: expr.value === 'true', span };
    if (expr.kind === 'name') {
      const constant = constants.get(expr.value!);
      return constant ? { ...constant, span } : { kind: 'arg', name: expr.value!, span };
    }
    if (expr.kind === 'number') return unsupported('lotus-int128', span);
    if (expr.kind === 'binary' && expr.value === '==') return { kind: 'equal', left: expression(expr.left!), right: expression(expr.right!), span };
    if (expr.kind === 'call') {
      if ((expr.value === 'sha256' || expr.value === 'hash256') && expr.args?.length === 1)
        return { kind: expr.value, value: expression(expr.args[0]!), span };
      if (expr.value === 'checksig') return unsupported('transaction-signature', span);
      if (program.helpers.has(expr.value!)) fail('E1203', `eCash source helper inlining is not implemented; selected call ${expr.value} must be expressed in the method body. Lotus helper compilation remains available.`, span);
      if (/^(input|output|utxo|branch|leaf|contract|check_lock|check_sequence|merkle)/i.test(expr.value!)) return unsupported('transaction-reflection', span);
      fail('E1203', `function ${expr.value} is not implemented by the eCash byte/hash source slice`, span);
    }
    fail('E1203', `operator ${expr.value ?? expr.kind} is not implemented by the eCash byte/hash source slice; no Lotus instruction is substituted`, span);
  };
  const statements = (body: Stmt[]): SemanticStmt[] => body.map(stmt => {
    if (stmt.kind === 'require') return { kind: 'require', condition: expression(stmt.expr!), span: stmt.span };
    if (stmt.kind === 'if') return { kind: 'if', condition: expression(stmt.expr!), then: statements(stmt.then!), otherwise: statements(stmt.otherwise!), span: stmt.span };
    if (stmt.kind === 'for') return unsupported('lotus-loop', stmt.span);
    fail('E1203', 'eCash source assignments are not implemented in the portable expression slice.', stmt.span);
  });
  const ir: SemanticProgram = { schema: 'lotus/semantic-ir/1', entrypoint: method.name, args, body: statements(method.body), span: method.span };
  const checked = validateSemanticProgram(ir);
  if (!checked.ok) diagnostic(checked.diagnostics[0]!);
  const result = compileEcash(ir);
  if (!result.ok) return diagnostic(result.diagnostics[0]!);
  return result.artifact;
}
