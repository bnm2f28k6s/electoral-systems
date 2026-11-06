/* Browser DOM regression, without packages.
 * Serve the production build, open comparison.html, then run this file in the
 * browser console (or evaluate it with a browser automation tool). It throws on
 * failure and returns a report on success. The page is reset afterward.
 */
(() => {
  const root = document.getElementById("voting-comparison");
  if (!root?.querySelector("#comparison-scope")) throw Error("Open the built comparison page with JavaScript enabled first");
  const data = JSON.parse(root.querySelector("#comparison-data").textContent);
  const report = { criterionStatusChecks: 0, scopes: [] };
  const assert = (ok, message) => { if (!ok) throw Error(message); };
  const equal = (actual, expected, message) => assert(JSON.stringify(actual) === JSON.stringify(expected), message);
  const set = (id, value, event = "change") => {
    const node = root.querySelector(`#${id}`);
    assert(node, `Missing control: ${id}`);
    node.value = value;
    node.dispatchEvent(new Event(event, { bubbles: true }));
  };
  const visibleRows = () => [...root.querySelectorAll("section:not([hidden]) tbody tr:not([hidden])")].map(row => row.dataset.method);
  const reset = () => root.querySelector("#comparison-controls button").click();
  try {
    reset();
    for (const scope of ["single", "multi"]) {
      set("comparison-scope", scope);
      equal(visibleRows().sort(), data[scope].methods.map(m => m.id).sort(), `${scope}: initial rows`);
      assert(document.activeElement.id === "comparison-scope", "Scope focus restoration");
      for (const criterion of data[scope].criteria) {
        for (const status of ["pass", "fail", "conditional", "unverified", "not-applicable"]) {
          set(`require-${criterion.id}`, status);
          const expected = data[scope].methods.filter(m => m.criteria[criterion.id].status === status).map(m => m.id).sort();
          equal(visibleRows().sort(), expected, `${scope}/${criterion.id}/${status}`);
          assert(root.querySelector("#comparison-empty").hidden === (expected.length !== 0), "Empty-state visibility");
          report.criterionStatusChecks++;
        }
        set(`require-${criterion.id}`, "");
      }
      // A shared method ID must resolve to this scope's row and chapter link.
      set("comparison-search", "sortition", "input");
      equal(visibleRows(), ["sortition"], `${scope}: shared method ID`);
      const row = root.querySelector(`section[data-scope="${scope}"] tr[data-method="sortition"]`);
      assert(row.querySelector("a").pathname.includes(scope === "single" ? "/methods/" : "/multi-methods/"), "Wrong chapter scope");
      set("comparison-search", "", "input");
      const sample = data[scope].methods[0];
      set("comparison-family", sample.family);
      set("comparison-ballot", sample.ballot);
      equal(visibleRows().sort(), data[scope].methods.filter(m => m.family === sample.family && m.ballot === sample.ballot).map(m => m.id).sort(), "Family/ballot composition");
      set("comparison-family", "");
      set("comparison-ballot", "");
      set("comparison-sort", "family");
      set("comparison-direction", "asc");
      const ascending = visibleRows();
      set("comparison-direction", "desc");
      equal(visibleRows(), [...ascending].reverse(), "Sorting direction");
      report.scopes.push(scope);
    }
    set("require-jr", "pass");
    set("comparison-family", data.multi.methods[0].family);
    set("comparison-scope", "single");
    assert(root.querySelector("#comparison-family").value === "" && root.querySelector("#comparison-ballot").value === "", "Scope attribute reset");
    assert(root.querySelector("#comparison-count").textContent.includes("0 criterion filters active"), "Scope criterion reset");
    set("require-condorcet-winner", "pass");
    set("require-monotonicity", "pass");
    const expected = data.single.methods.filter(m => m.criteria["condorcet-winner"].status === "pass" && m.criteria.monotonicity.status === "pass").map(m => m.id).sort();
    equal(visibleRows().sort(), expected, "AND requirements");
    root.querySelector("#column-monotonicity").click();
    equal(visibleRows().sort(), expected, "Hiding a column changed its filter");
    assert([...root.querySelectorAll('section:not([hidden]) [data-criterion="monotonicity"]')].every(cell => cell.hidden), "Column visibility");
    assert(root.querySelector("#comparison-count").textContent.includes("2 criterion filters active"), "Hidden filter count");
    const actions = root.querySelectorAll(".comparison-actions button");
    actions[0].click();
    assert(root.querySelectorAll('section:not([hidden]) thead [data-criterion]:not([hidden])').length === data.single.criteria.length, "Show all columns");
    actions[1].click();
    assert(root.querySelectorAll('section:not([hidden]) thead [data-criterion]:not([hidden])').length === 0, "Hide all columns");
    equal(visibleRows().sort(), expected, "Column actions changed filters");
    set("comparison-search", "<no-such-method>", "input");
    equal(visibleRows(), [], "No-result search");
    assert(!root.querySelector("#comparison-empty").hidden, "No-result message");
    reset();
    assert(visibleRows().length === data.single.methods.length, "Reset rows");
    assert(document.activeElement.id === "comparison-scope", "Reset focus restoration");
    report.interactions = "PASS: scope isolation, search, family/ballot filters, sort, AND filters, column visibility, empty state, reset and focus";
    return report;
  } finally {
    reset();
  }
})()
