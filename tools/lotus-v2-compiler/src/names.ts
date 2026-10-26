// One portable surface namespace for generated TypeScript and Python clients.
const RESERVED = new Set(`and as assert async await break case catch class const continue debugger default def del delete do elif else enum except export extends False false finally for from function global if import in instanceof interface is lambda let new nonlocal not null None of or package pass private protected public raise return self static super switch this throw True true try type typeof var void while with yield constructor`.split(/\s+/));

export function assertPortableName(name: string): string {
  if (!/^[A-Za-z_][A-Za-z_0-9]*$/.test(name) || RESERVED.has(name)) throw new Error(`reserved or invalid binding name ${name}`);
  return name;
}
