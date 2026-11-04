// Site-local progressive enhancement. No packages or network requests.
export const statuses = {
  pass: "Pass", fail: "Fail", conditional: "Conditional",
  unverified: "Unverified", "not-applicable": "Not applicable",
};

export function filterMethods(methods, state) {
  const query = state.query.trim().toLocaleLowerCase();
  return methods.filter(method =>
    (!query || [method.name, method.id, method.summary].join(" ").toLocaleLowerCase().includes(query)) &&
    (!state.family || method.family === state.family) &&
    (!state.ballot || method.ballot === state.ballot) &&
    Object.entries(state.requirements).every(([id, status]) =>
      !status || method.criteria[id]?.status === status));
}

export function sortMethods(methods, key = "name", direction = "asc") {
  const field = ["name", "family", "ballot"].includes(key) ? key : "name";
  const compare = (a, b) => a.localeCompare(b, "en", { sensitivity: "base" });
  return [...methods].sort((a, b) => (direction === "desc" ? -1 : 1) *
    (compare(a[field], b[field]) || compare(a.name, b.name) || compare(a.id, b.id)));
}

const defaultColumns = {
  single: ["majority-ranked", "condorcet-winner", "monotonicity", "clone-independence", "participation"],
  multi: ["proportionality-solid-coalitions", "candidate-monotonicity", "committee-monotonicity", "jr"],
};

export function initializeComparison(root) {
  const data = JSON.parse(root.querySelector("#comparison-data").textContent);
  const controls = root.querySelector("#comparison-controls");
  const count = root.querySelector("#comparison-count");
  const empty = root.querySelector("#comparison-empty");
  const state = { scope: "single", query: "", family: "", ballot: "", requirements: {}, sort: "name", direction: "asc" };
  let visible = new Set();
  const sections = new Map([...root.querySelectorAll("[data-scope]")].map(section => [section.dataset.scope, section]));
  const rows = new Map([...sections].map(([scope, section]) => [scope,
    new Map([...section.querySelectorAll("tbody tr")].map(row => [row.dataset.method, row]))]));

  function element(tag, text, attrs = {}) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    for (const [name, value] of Object.entries(attrs)) node.setAttribute(name, value);
    return node;
  }

  function select(label, id, entries, value, onChange, parent = controls) {
    const wrapper = element("label", label, { for: id });
    const input = element("select", "", { id });
    for (const [key, text] of entries) {
      const option = element("option", text, { value: key });
      input.append(option);
    }
    input.value = value;
    input.addEventListener("change", () => onChange(input.value));
    wrapper.append(input);
    parent.append(wrapper);
    return input;
  }

  function render() {
    const catalog = data[state.scope];
    const methods = sortMethods(filterMethods(catalog.methods, state), state.sort, state.direction);
    for (const [scope, section] of sections) section.hidden = scope !== state.scope;
    const current = sections.get(state.scope);
    const selected = new Set(methods.map(method => method.id));
    for (const [id, row] of rows.get(state.scope)) row.hidden = !selected.has(id);
    const body = current.querySelector("tbody");
    for (const method of methods) body.append(rows.get(state.scope).get(method.id));
    for (const cell of current.querySelectorAll("[data-criterion]")) cell.hidden = !visible.has(cell.dataset.criterion);
    const active = Object.values(state.requirements).filter(Boolean).length;
    count.textContent = `${methods.length} of ${catalog.methods.length} ${catalog.label.toLowerCase()} methods. ${active} criterion filters active; ${visible.size} criterion columns shown.`;
    empty.hidden = methods.length !== 0;
  }

  function buildControls() {
    controls.replaceChildren();
    const catalog = data[state.scope];
    visible = new Set(defaultColumns[state.scope].filter(id => catalog.criteria.some(c => c.id === id)));
    select("Election type", "comparison-scope", Object.entries(data).map(([key, value]) => [key, value.label]), state.scope, scope => {
      state.scope = scope;
      state.family = state.ballot = "";
      state.requirements = {};
      buildControls();
      render();
      root.querySelector("#comparison-scope").focus();
    });
    const searchLabel = element("label", "Search methods", { for: "comparison-search" });
    const search = element("input", "", { id: "comparison-search", type: "search", placeholder: "Name, identifier, or basic idea" });
    search.value = state.query;
    search.addEventListener("input", () => { state.query = search.value; render(); });
    searchLabel.append(search);
    controls.append(searchLabel);
    for (const [key, label] of [["family", "Counting family"], ["ballot", "Ballot format"]]) {
      const values = [...new Set(catalog.methods.map(method => method[key]))].sort();
      select(label, `comparison-${key}`, [["", "All"], ...values.map(value => [value, value])], state[key], value => { state[key] = value; render(); });
    }
    select("Sort by", "comparison-sort", [["name", "Method name"], ["family", "Counting family"], ["ballot", "Ballot format"]], state.sort, value => { state.sort = value; render(); });
    select("Sort direction", "comparison-direction", [["asc", "Ascending"], ["desc", "Descending"]], state.direction, value => { state.direction = value; render(); });
    const reset = element("button", "Reset comparison", { type: "button" });
    reset.addEventListener("click", () => {
      Object.assign(state, { scope: "single", query: "", family: "", ballot: "", requirements: {}, sort: "name", direction: "asc" });
      buildControls();
      render();
      root.querySelector("#comparison-scope").focus();
    });
    controls.append(reset);
    const panel = element("details", "", { class: "comparison-criteria" });
    panel.append(element("summary", "Criteria: columns and filters"));
    panel.append(element("p", "Every active requirement must match. Hiding a column keeps its filter active. Conditional, unverified, and not applicable never count as pass or fail."));
    const actions = element("div", "", { class: "comparison-actions" });
    for (const [label, show] of [["Show all columns", true], ["Hide all criterion columns", false]]) {
      const button = element("button", label, { type: "button" });
      button.addEventListener("click", () => {
        visible = new Set(show ? catalog.criteria.map(c => c.id) : []);
        for (const input of panel.querySelectorAll('input[type="checkbox"]')) input.checked = show;
        render();
      });
      actions.append(button);
    }
    panel.append(actions);
    const groups = new Map();
    for (const criterion of catalog.criteria) {
      if (!groups.has(criterion.category)) {
        const group = element("fieldset");
        group.append(element("legend", criterion.category));
        groups.set(criterion.category, group);
        panel.append(group);
      }
      const item = element("div", "", { class: "comparison-criterion" });
      const label = element("label", "", { for: `column-${criterion.id}` });
      const checkbox = element("input", "", { type: "checkbox", id: `column-${criterion.id}` });
      checkbox.checked = visible.has(criterion.id);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) visible.add(criterion.id); else visible.delete(criterion.id);
        render();
      });
      label.append(checkbox, document.createTextNode(` Show ${criterion.name}`));
      const definition = element("p", criterion.definition, { class: "comparison-definition" });
      item.append(label, definition);
      select(`Require ${criterion.name}`, `require-${criterion.id}`, [["", "Any assessment"], ...Object.entries(statuses)], state.requirements[criterion.id] || "", value => {
        state.requirements[criterion.id] = value;
        render();
      }, item);
      groups.get(criterion.category).append(item);
    }
    controls.append(panel);
  }

  buildControls();
  render();
  controls.hidden = false;
}

if (typeof document !== "undefined") {
  const root = document.getElementById("voting-comparison");
  if (root) initializeComparison(root);
}
