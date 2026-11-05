/* Evaluate on the built simulator page. Faults are injected only into a
 * disposable DOM fixture. Real counting is tested by simulator_browser.js. */
(async () => {
  const {initSimulator, LIMITS} = await import(new URL('./_assets/simulator.mjs', location.href));
  const native = {Worker: window.Worker, setTimeout: window.setTimeout, clearTimeout: window.clearTimeout};
  const data = document.getElementById('simulator-data').textContent;
  const workers = [], timers = new Map(), fixtures = [];
  let nextTimer = -1, rejectConstructor = false, checks = 0;
  const assert = (condition, message) => { if (!condition) throw Error(message); checks++; };
  const fixture = () => {
    const root = document.createElement('div');
    for (const [id, tag] of [['status', 'p'], ['controls', 'div'], ['data', 'script']]) {
      const element = document.createElement(tag); element.id = `simulator-${id}`;
      if (id === 'controls') element.hidden = true;
      if (id === 'data') { element.type = 'application/json'; element.textContent = data; }
      root.append(element);
    }
    document.body.append(root);
    const controller = initSimulator(root);
    fixtures.push({root, controller});
    return {root, controller, get: id => root.querySelector(`#simulator-${id}`)};
  };
  class FakeWorker {
    constructor() { if (rejectConstructor) throw Error('Blocked worker'); workers.push(this); }
    postMessage(message) { this.request = message; }
    terminate() { this.terminated = true; }
    ready() { this.onmessage({data: {type: 'ready'}}); }
  }
  const expire = () => { const callbacks = [...timers.values()]; assert(callbacks.length === 1, 'Expected one lifecycle timer'); timers.clear(); callbacks[0](); };
  try {
    window.Worker = FakeWorker;
    window.setTimeout = (callback, ms, ...args) => {
      if (ms !== LIMITS.timeout) return native.setTimeout.call(window, callback, ms, ...args);
      const id = nextTimer--; timers.set(id, callback); return id;
    };
    window.clearTimeout = id => { if (!timers.delete(id)) native.clearTimeout.call(window, id); };
    const f = fixture();
    let worker = workers.at(-1);
    assert(f.get('controls').hidden, 'Controls exposed before startup');
    expire();
    assert(worker.terminated && f.get('run').disabled, 'Startup timeout did not terminate worker');
    assert(!f.get('retry').hidden && !f.get('controls').contains(f.get('retry')), 'Startup retry hidden inside disabled controls');
    f.get('retry').click(); worker = workers.at(-1); worker.ready();
    assert(!f.get('controls').hidden && !f.get('run').disabled, 'Startup recovery failed');
    assert(f.get('retry').hidden, 'Retry remains visible after recovery');
    f.get('run').click(); const stale = worker, staleId = worker.request.id;
    expire(); worker = workers.at(-1);
    assert(stale.terminated && worker !== stale, 'Count timeout did not replace worker');
    worker.ready();
    assert(f.get('status').textContent.includes('Time limit reached') && !f.get('run').disabled, 'Timeout reason lost on recovery');
    stale.onmessage({data: {id: staleId, result: {method: 'stale'}}});
    assert(f.get('result').textContent === '', 'Stale worker overwrote result');
    f.get('run').click();
    worker.onmessage({data: {id: worker.request.id, error: '<img src=x onerror=alert(1)>'}});
    assert(f.get('status').textContent.includes('<img') && !f.root.querySelector('img'), 'Unsafe worker error rendering');
    worker.onerror({preventDefault() {}});
    assert(worker.terminated && f.get('run').disabled, 'Worker error failed to stop counting');
    rejectConstructor = true;
    f.get('reset').click();
    assert(f.get('run').disabled && f.get('status').textContent.includes('could not start'), 'Constructor failure escaped reset');
    rejectConstructor = false;
    f.get('reset').click(); workers.at(-1).ready();
    assert(!f.get('run').disabled, 'Constructor failure not recoverable');
    f.controller.destroy();
    rejectConstructor = true;
    const blocked = fixture();
    assert(blocked.get('controls').hidden && !blocked.get('retry').hidden, 'Initial constructor failure lacks accessible retry');
    rejectConstructor = false;
    blocked.get('retry').click(); workers.at(-1).ready();
    assert(!blocked.get('controls').hidden, 'Initial constructor failure could not recover');
    blocked.controller.destroy();
    window.Worker = undefined;
    const unsupported = fixture();
    assert(unsupported.controller === null && unsupported.get('controls').hidden, 'Unsupported Worker must preserve static fallback');
    return {status: 'PASS', checks, faults: ['startup timeout', 'count timeout', 'stale response', 'worker error', 'constructor exception', 'unsupported worker']};
  } finally {
    for (const {root, controller} of fixtures) { controller?.destroy(); root.remove(); }
    window.Worker = native.Worker; window.setTimeout = native.setTimeout; window.clearTimeout = native.clearTimeout;
  }
})()
