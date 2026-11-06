// Shared guards also run inside the isolated worker before invoking the engine.
export const LIMITS = Object.freeze({bytes: 65536, candidates: 12, groups: 100, voters: 1000, timeout: 3000});
export function parseRequest(text, scope) {
  if (!['single', 'multi'].includes(scope)) throw Error('Unknown election domain');
  if (new TextEncoder().encode(text).length > LIMITS.bytes) throw Error('Browser request limit: 65536 UTF-8 bytes');
  const input = JSON.parse(text);
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw Error('Request must be an object');
  const n = input.candidates?.length;
  if (!Array.isArray(input.candidates) || n < 1 || n > LIMITS.candidates) throw Error('Browser limit: 1–12 candidates');
  if (!Array.isArray(input.ballots) || input.ballots.length > LIMITS.groups) throw Error('Browser limit: 100 ballot groups');
  let voters = 0;
  for (const ballot of input.ballots) {
    const count = ballot?.count ?? 1;
    if (!Number.isSafeInteger(count) || count < 1) throw Error('Ballot count must be a positive safe integer');
    voters += count;
  }
  if (voters > LIMITS.voters) throw Error('Browser limit: 1000 represented voters');
  const caps = scope === 'single' ? {'kemeny-young': 6, dodgson: 3, 'maximal-lotteries': 5} : {'proportional-approval': 6, 'minimax-external-opposition': 6, 'cpo-stv': 4, 'schulze-stv': 4, 'quota-borda': 6};
  if (n > (caps[input.method] ?? LIMITS.candidates)) throw Error(`Browser safety limit for ${input.method}: ${caps[input.method]} candidates`);
  if (scope === 'single' && input.method === 'dodgson' && voters > 7) throw Error('Browser Dodgson limit: 7 represented voters');
  if (scope === 'multi' && ['cpo-stv', 'schulze-stv'].includes(input.method) && (input.ballots.length > 20 || voters > 100)) throw Error('Browser exact STV limit: 20 groups and 100 voters');
  return input;
}

export function initSimulator(root) {
  const status = root.querySelector('#simulator-status');
  const controls = root.querySelector('#simulator-controls');
  let worker, timer, serial = 0, ready = false;
  const say = text => { status.textContent = text; };
  try {
    const data = JSON.parse(root.querySelector('#simulator-data').textContent);
    if (typeof Worker === 'undefined') throw Error('Web Workers are unavailable');
    const node = (tag, text) => { const el = document.createElement(tag); if (text) el.textContent = text; return el; };
    const field = (id, label, tag) => { const el = node(tag); el.id = id; const wrapper = node('label', label); wrapper.htmlFor = id; wrapper.append(el); controls.append(wrapper); return el; };
    const scope = field('simulator-scope', 'Election domain', 'select');
    for (const key of ['single', 'multi']) { const option = node('option', data[key].label); option.value = key; scope.append(option); }
    const method = field('simulator-method', 'Method (changing domain or method replaces the editor)', 'select');
    const description = node('p'); controls.append(description);
    const editor = field('simulator-request', 'Editable JSON request', 'textarea'); editor.rows = 18; editor.spellcheck = false;
    const run = node('button', 'Run locally'); run.type = 'button'; run.id = 'simulator-run';
    const reset = node('button', 'Reset sample'); reset.type = 'button'; reset.id = 'simulator-reset';
    const retry = node('button', 'Retry interactive counting'); retry.type = 'button'; retry.id = 'simulator-retry'; retry.hidden = true; controls.before(retry);
    const result = node('pre'); result.id = 'simulator-result'; result.setAttribute('aria-label', 'Simulation result');
    controls.append(run, reset, node('p', 'Browser limits: 64 KiB, 12 candidates, 100 groups, 1000 voters, 3 seconds. Exhaustive methods have smaller safety caps. Seeds make random examples reproducible. The JSON method must match the selected method.'), result);
    const stop = () => { clearTimeout(timer); worker?.terminate(); worker = null; ready = false; serial++; run.disabled = true; };
    const fail = message => { stop(); retry.hidden = false; say(`${message} Static examples remain available; use Retry interactive counting.`); };
    const create = (readyMessage = 'Ready. Requests run locally in an isolated worker.') => {
      stop(); retry.hidden = true;
      let current;
      try { current = new Worker(new URL('./simulator-worker.mjs', import.meta.url), {type: 'module'}); }
      catch { fail('Interactive worker could not start.'); return; }
      worker = current;
      timer = setTimeout(() => { if (worker === current) fail('Worker startup timed out.'); }, LIMITS.timeout);
      current.onerror = event => { event.preventDefault(); if (worker !== current) return; fail('Interactive worker failed.'); };
      current.onmessage = ({data: message}) => {
        if (worker !== current) return;
        if (message.type === 'ready') { clearTimeout(timer); ready = true; run.disabled = false; controls.hidden = false; say(readyMessage); return; }
        if (message.id !== serial) return;
        clearTimeout(timer); run.disabled = false;
        if (message.error) { result.textContent = ''; say(`Error: ${message.error}`); }
        else { result.textContent = JSON.stringify(message.result, null, 2); say('Simulation complete. Structured result follows the controls.'); }
      };
    };
    const sample = () => {
      const item = data[scope.value].methods.find(m => m.id === method.value);
      editor.value = JSON.stringify(item.request, null, 2);
      description.textContent = `${item.family} · ${item.ballot}. ${item.summary} ${item.tieNotes} Counting cost: ${item.complexity}`;
      result.textContent = ''; create();
    };
    const domain = () => { method.replaceChildren(); for (const item of data[scope.value].methods) { const option = node('option', item.name); option.value = item.id; method.append(option); } sample(); };
    scope.addEventListener('change', domain); method.addEventListener('change', sample);
    retry.addEventListener('click', () => create());
    reset.addEventListener('click', () => { sample(); editor.focus(); });
    run.addEventListener('click', () => {
      try {
        const input = parseRequest(editor.value, scope.value);
        if (input.method !== method.value) throw Error('JSON method must match the selected method');
        if (!ready) throw Error('Worker is not ready; reset to retry');
        const id = ++serial; run.disabled = true; result.textContent = ''; say('Counting locally…');
        worker.postMessage({id, scope: scope.value, text: editor.value});
        timer = setTimeout(() => { const message = 'Time limit reached. Worker terminated; simplify the request or reset. A new worker is ready.'; create(message); if (worker) say('Time limit reached. Worker terminated; restarting for another request.'); }, LIMITS.timeout);
      } catch (error) { result.textContent = ''; say(`Error: ${error.message}`); }
    });
    domain();
    return {destroy: stop};
  } catch (error) { worker?.terminate(); clearTimeout(timer); controls.hidden = true; say(`Interactive counting unavailable: ${error.message}. All static examples remain available.`); return null; }
}
if (typeof document !== 'undefined') {
  const root = document.getElementById('simulator-root');
  if (root) initSimulator(root);
}
