/** Deterministic dependency jobs for the contract compiler. */
export type SchedulerEvent = {
  kind: 'start' | 'await' | 'resolve' | 'reject';
  job: string;
  dependency?: string;
  error?: string;
  source?: { start: number; end: number };
};

export type SchedulerLimits = { maxJobs: number; maxEdges: number; maxDepth: number };
type Job<T> = { dependencies?: string[]; discover: () => string[]; run: () => T | Promise<T>; source?: SchedulerEvent['source'] };

export class PromiseScheduler<T> {
  private readonly jobs = new Map<string, Job<T>>();
  private readonly promises = new Map<string, Promise<T>>();
  private edges = 0;
  private readonly limits: SchedulerLimits;
  constructor(private readonly onEvent?: (event: SchedulerEvent) => void, limits: Partial<SchedulerLimits> = {}) {
    this.limits = { maxJobs: limits.maxJobs ?? 1024, maxEdges: limits.maxEdges ?? 8192, maxDepth: limits.maxDepth ?? 256 };
  }

  private emit(event: SchedulerEvent): void {
    // Trace observers cannot interrupt dependency attachment or strand sibling jobs.
    try { this.onEvent?.(event); } catch { /* observer is advisory */ }
  }

  register(name: string, dependencies: string[] | (() => string[]), run: Job<T>['run'], source?: SchedulerEvent['source']): void {
    if (this.jobs.has(name)) throw new Error(`duplicate compiler job ${name}`);
    if (this.jobs.size >= this.limits.maxJobs) throw new Error(`compiler job limit exceeded (${this.limits.maxJobs})`);
    this.jobs.set(name, { discover: typeof dependencies === 'function' ? dependencies : () => dependencies, run, source });
  }

  private dependencies(name: string, job: Job<T>): string[] {
    if (job.dependencies) return job.dependencies;
    const dependencies = [...new Set(job.discover())];
    this.edges += dependencies.length;
    if (this.edges > this.limits.maxEdges) throw new Error(`compiler dependency edge limit exceeded (${this.limits.maxEdges}) at ${this.label(name)}`);
    job.dependencies = dependencies;
    return dependencies;
  }

  private label(name: string): string {
    const source = this.jobs.get(name)?.source;
    return source ? `${name}@UTF-8 bytes ${source.start}..${source.end}` : name;
  }

  private check(name: string, active: string[], visited: Set<string>): void {
    const at = active.indexOf(name);
    if (at >= 0) throw new Error(`dependency cycle: ${[...active.slice(at), name].map(part => this.label(part)).join(' -> ')}`);
    if (visited.has(name)) return;
    const job = this.jobs.get(name);
    if (!job) throw new Error(`unknown compiler job ${name}`);
    if (active.length >= this.limits.maxDepth) throw new Error(`compiler dependency depth limit exceeded (${this.limits.maxDepth}) at ${this.label(name)}`);
    active.push(name);
    for (const dependency of this.dependencies(name, job)) this.check(dependency, active, visited);
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
    this.emit({ kind: 'start', job: name, source: job.source });
    const dependencies = job.dependencies!.map(dependency => {
      this.emit({ kind: 'await', job: name, dependency, source: job.source });
      return this.start(dependency);
    });
    const promise = Promise.all(dependencies).then(() => job.run()).then(
      value => { this.emit({ kind: 'resolve', job: name, source: job.source }); return value; },
      error => { this.emit({ kind: 'reject', job: name, error: (error as Error).message, source: job.source }); throw error; },
    );
    this.promises.set(name, promise);
    return promise;
  }
}
