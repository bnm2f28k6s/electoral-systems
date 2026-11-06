// Run with: node --test tests/test_comparison.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { filterMethods, sortMethods, statuses } from "../web/comparison.mjs";

const catalogs = ["methods", "multi_methods"].map(name => JSON.parse(readFileSync(new URL(`../data/${name}.json`, import.meta.url))));
const state = overrides => ({ query: "", family: "", ballot: "", requirements: {}, ...overrides });

test("unfiltered comparison preserves every catalog row, including duplicate IDs across scopes", () => {
  for (const methods of catalogs) assert.deepEqual(filterMethods(methods, state()), methods);
  assert.equal(catalogs.flat().filter(m => m.id === "approval").length, 2);
});

test("each criterion matches exactly one status, never treating conditional or unknown as boolean", () => {
  for (const methods of catalogs) {
    for (const id of Object.keys(methods[0].criteria)) {
      const seen = [];
      for (const status of Object.keys(statuses)) {
        const actual = filterMethods(methods, state({ requirements: { [id]: status } }));
        assert.deepEqual(actual, methods.filter(m => m.criteria[id].status === status));
        seen.push(...actual);
      }
      assert.equal(seen.length, methods.length);
      assert.equal(new Set(seen).size, methods.length);
    }
  }
});

test("requirements combine with AND, and clearing one removes only that constraint", () => {
  const methods = catalogs[0];
  const requirements = { "condorcet-winner": "pass", monotonicity: "pass" };
  const expected = methods.filter(m => Object.entries(requirements).every(([id, status]) => m.criteria[id].status === status));
  assert.ok(expected.length > 0 && expected.length < methods.length);
  assert.deepEqual(filterMethods(methods, state({ requirements })), expected);
  assert.deepEqual(filterMethods(methods, state({ requirements: { "condorcet-winner": "", monotonicity: "pass" } })), methods.filter(m => m.criteria.monotonicity.status === "pass"));
  assert.deepEqual(filterMethods(methods, state({ requirements: { nonexistent: "pass" } })), []);
});

test("search trims whitespace and supports names, IDs and summaries", () => {
  for (const methods of catalogs) {
    for (const method of methods) {
      for (const query of [method.id, method.name.toUpperCase(), `  ${method.summary}  `]) {
        assert.ok(filterMethods(methods, state({ query })).includes(method));
      }
    }
    assert.deepEqual(filterMethods(methods, state({ query: "<nonexistent-method>" })), []);
  }
});

test("family, ballot, search and criterion constraints compose", () => {
  for (const methods of catalogs) {
    for (const method of methods) {
      const [id, claim] = Object.entries(method.criteria)[0];
      const options = state({ query: method.id, family: method.family, ballot: method.ballot, requirements: { [id]: claim.status } });
      const actual = filterMethods(methods, options);
      assert.ok(actual.includes(method));
      assert.ok(actual.every(m => m.family === method.family && m.ballot === method.ballot && m.criteria[id].status === claim.status));
    }
  }
});

test("sorting is deterministic, reversible and does not mutate catalog order", () => {
  for (const methods of catalogs) {
    const original = [...methods];
    for (const key of ["name", "family", "ballot"]) {
      const asc = sortMethods(methods, key, "asc");
      assert.deepEqual(sortMethods(methods, key, "desc"), [...asc].reverse());
      assert.deepEqual(sortMethods([...methods].reverse(), key), asc);
      assert.deepEqual(methods, original);
    }
    assert.deepEqual(sortMethods(methods, "unknown"), sortMethods(methods, "name"));
  }
});
