// Per-origin browser storage. Each node origin (host:port) is its own app
// with its own storage. Every access is wrapped: storage can be missing or
// throw (private windows, blocked site data), and the app must still work.

const PREFIX = 'node-pwa:';

export function load(key, fallback) {
  try {
    const v = globalThis.localStorage?.getItem(PREFIX + key);
    return v === null || v === undefined ? fallback : JSON.parse(v);
  } catch {
    return fallback;
  }
}

export function save(key, value) {
  try {
    globalThis.localStorage?.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    // ignore: convenience state only
  }
}

// Receive-request history lives in IndexedDB, keyed per wallet. If IndexedDB
// is unavailable the history is kept in memory for this page only.

const DB = 'node-pwa';
const STORE = 'requests';
const memory = new Map();
let dbPromise = null;

function openDb() {
  if (!globalThis.indexedDB) return Promise.resolve(null);
  dbPromise ??= new Promise((resolve) => {
    try {
      const req = indexedDB.open(DB, 1);
      req.onupgradeneeded = () => {
        const s = req.result.createObjectStore(STORE, { keyPath: 'id', autoIncrement: true });
        s.createIndex('wallet', 'wallet');
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
      req.onblocked = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
  return dbPromise;
}

/** @param {string} wallet */
export async function listRequests(wallet) {
  const db = await openDb();
  if (!db) return [...(memory.get(wallet) ?? [])].reverse();
  return new Promise((resolve) => {
    try {
      const req = db.transaction(STORE).objectStore(STORE).index('wallet').getAll(wallet);
      req.onsuccess = () => resolve(req.result.sort((a, b) => b.created - a.created));
      req.onerror = () => resolve([]);
    } catch {
      resolve([]);
    }
  });
}

/** @param {{wallet: string, address: string, label: string, amount: string, message: string, created: number}} r */
export async function addRequest(r) {
  const db = await openDb();
  if (!db) {
    const list = memory.get(r.wallet) ?? [];
    list.push({ ...r, id: list.length + 1 });
    memory.set(r.wallet, list);
    return;
  }
  await new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).add(r);
      tx.oncomplete = tx.onerror = tx.onabort = () => resolve();
    } catch {
      resolve();
    }
  });
}

export async function deleteRequest(id, wallet) {
  const db = await openDb();
  if (!db) {
    memory.set(wallet, (memory.get(wallet) ?? []).filter((r) => r.id !== id));
    return;
  }
  await new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).delete(id);
      tx.oncomplete = tx.onerror = tx.onabort = () => resolve();
    } catch {
      resolve();
    }
  });
}
