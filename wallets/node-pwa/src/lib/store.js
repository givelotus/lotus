// Tiny observable state container (no library).

/**
 * @template T
 * @param {T} initial
 */
export function createStore(initial) {
  let state = initial;
  const subs = new Set();
  return {
    /** @returns {T} */
    get: () => state,
    /** Shallow-merge a patch (or the result of fn(state)) and notify. */
    set(patch) {
      const p = typeof patch === 'function' ? patch(state) : patch;
      if (!p) return;
      let changed = false;
      for (const k of Object.keys(p)) if (state[k] !== p[k]) { changed = true; break; }
      if (!changed) return;
      state = { ...state, ...p };
      for (const fn of [...subs]) fn(state);
    },
    /** @returns {() => void} */
    subscribe(fn) {
      subs.add(fn);
      return () => subs.delete(fn);
    },
  };
}
