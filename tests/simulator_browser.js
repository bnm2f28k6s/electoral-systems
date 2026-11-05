/* Serve the production build, open simulator.html, and evaluate this script
 * in the browser console. The returned promise reports all canonical runs.
 */
(async () => {
  const root = document.getElementById('simulator-root');
  const assert = (value, message) => { if (!value) throw Error(message); };
  const equivalent = (actual, expected, path) => {
    if (typeof expected === 'number') {
      assert(typeof actual === 'number' && Math.abs(actual - expected) <= 1e-10 * Math.max(1, Math.abs(expected)), `${path}: number differs`);
    } else if (Array.isArray(expected)) {
      assert(Array.isArray(actual) && actual.length === expected.length, `${path}: array differs`);
      expected.forEach((value, index) => equivalent(actual[index], value, `${path}/${index}`));
    } else if (expected !== null && typeof expected === 'object') {
      assert(actual && JSON.stringify(Object.keys(actual).sort()) === JSON.stringify(Object.keys(expected).sort()), `${path}: fields differ`);
      for (const key of Object.keys(expected)) equivalent(actual[key], expected[key], `${path}/${key}`);
    } else assert(actual === expected, `${path}: value differs`);
  };
  const wait = async predicate => {
    const start = performance.now();
    while (!predicate()) {
      if (performance.now() - start > 10000) throw Error('Simulator regression timed out');
      await new Promise(resolve => setTimeout(resolve, 25));
    }
  };
  const get = id => root.querySelector(`#simulator-${id}`);
  await wait(() => get('controls') && !get('controls').hidden && !get('run').disabled);
  const data = JSON.parse(get('data').textContent);
  const set = (id, value) => { get(id).value = value; get(id).dispatchEvent(new Event('change', {bubbles: true})); };
  const report = {runs: 0, domains: []};
  for (const scope of ['single', 'multi']) {
    set('scope', scope);
    for (const method of data[scope].methods) {
      set('method', method.id);
      await wait(() => !get('run').disabled);
      assert(JSON.parse(get('request').value).method === method.id, 'Sample scope mismatch');
      get('run').click();
      await wait(() => !get('run').disabled);
      assert(get('status').textContent.startsWith('Simulation complete'), `${scope}/${method.id}: ${get('status').textContent}`);
      const actual = JSON.parse(get('result').textContent);
      assert(JSON.stringify(actual.winners) === JSON.stringify(method.result.winners), `${scope}/${method.id}: incorrect winners`);
      equivalent(actual, method.result, `${scope}/${method.id}`);
      report.runs++;
    }
    report.domains.push(scope);
  }
  get('request').value = '{'; get('run').click();
  assert(get('status').textContent.startsWith('Error:'), 'Malformed JSON error missing');
  get('request').value = '<img src=x onerror=alert(1)>'; get('run').click();
  assert(!get('controls').querySelector('img'), 'Unsafe error rendering');
  get('reset').click();
  assert(document.activeElement === get('request'), 'Reset focus');
  await wait(() => !get('run').disabled);
  // Switching during an in-flight request must never display the old result.
  get('run').click(); set('scope', 'single');
  await wait(() => !get('run').disabled);
  assert(get('result').textContent === '', 'Stale result after domain switch');
  get('run').click(); await wait(() => !get('run').disabled);
  assert(JSON.parse(get('result').textContent).method === 'plurality', 'Worker recovery');
  assert(root.querySelectorAll('[data-example]').length === report.runs, 'Incomplete static baseline');
  report.status = 'PASS';
  return report;
})()
