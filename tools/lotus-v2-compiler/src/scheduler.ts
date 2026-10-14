/** Deterministic dependency jobs for the contract compiler. */
export type SchedulerEvent = {
  kind: 'start' | 'await' | 'resolve' | 'reject';
  job: string;
  dependency?: string;
  error?: string;
};

type Job<T> = { dependencies: string[]; run: () => T | Promise<T> };

export class PromiseScheduler<T> {
  private readonly jobs = new Map<string, Job<T>>();
  private readonly promises = new Map<string, Promise<T>>();
  constructor(private readonly onEvent?: (event: SchedulerEvent) => void) {}

  register(name: string, dependencies: string[], run: Job<T>['run']): void {
    if (this.jobs.has(name)) throw new Error(`duplicate compiler job ${name}`);
    this.jobs.set(name, { dependencies: [...new Set(dependencies)], run });
  }

  private check(name: string, active: string[], visited: Set<string>): void {
    const at = active.indexOf(name);
    if (at >= 0) throw new Error(`dependency cycle: ${[...active.slice(at), name].join(' -> ')}`);
    if (visited.has(name)) return;
    const job = this.jobs.get(name);
    if (!job) throw new Error(`unknown compiler job ${name}`);
    active.push(name);
    for (const dependency of job.dependencies) this.check(dependency, active, visited);
    active.pop();
    visited.add(name);
  }

  run(name: string): Promise<T> {
    // Validate the whole reachable graph before creating promises. In particular,
    // a cycle can never turn into two promises waiting on each other forever.
    this.check(name, [], new Set());
    return this.start(name);
  }

  private start(name: string): Promise<T> {
    const prior = this.promises.get(name);
    if (prior) return prior;
    const job = this.jobs.get(name)!;
    this.onEvent?.({ kind: 'start', job: name });
    const dependencies = job.dependencies.map(dependency => {
      this.onEvent?.({ kind: 'await', job: name, dependency });
      return this.start(dependency);
    });
    const promise = Promise.all(dependencies).then(() => job.run()).then(
      value => { this.onEvent?.({ kind: 'resolve', job: name }); return value; },
      error => { this.onEvent?.({ kind: 'reject', job: name, error: (error as Error).message }); throw error; },
    );
    this.promises.set(name, promise);
    return promise;
  }
}
