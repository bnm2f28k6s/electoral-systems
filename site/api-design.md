# Run the simulation API

The local server executes the Python counting engine and returns an inspectable result. It implements every method in the [catalog](/methods.md). The HTTP requests below require that local server; GitHub Pages does not host an API backend. To count a small example without installing anything, use the optional [browser simulator](/simulator.md), which runs the compiled TypeScript engine locally in your browser.

## Start the server

From the repository root, using Python 3.9 or newer:

```sh
python3 python/server.py
```

The server listens on `127.0.0.1:8000`. Use `--port 8081` to choose another port. In a separate terminal, discover the accepted identifiers:

```sh
curl http://127.0.0.1:8000/systems
```

This returns an object with a `methods` array. The [OpenAPI reference](/api/reference) documents the common facade and ballot-family endpoints and includes an executed request and response for every method on the facade.

## Choose a ballot-family endpoint

`POST /simulate` remains the common facade. For homogeneous ballots it dispatches
to the same family contract as these specialized routes:

| Route | Required ballot field | Compatible methods |
| --- | --- | --- |
| `/simulate/ranked` | `ranking` | All complete-ranking methods, including plurality, anti-plurality, and random-ballot |
| `/simulate/marked` | `choice` | plurality, anti-plurality, random-ballot |
| `/simulate/approval` | `approvals` | approval |
| `/simulate/scored` | `scores` | score, star, majority-judgment |
| `/simulate/quadratic` | `credits` | quadratic |
| `/simulate/none` | No ballots; `ballots: []` | sortition |

The request and result fields do not change. For example, send the ranked IRV
request below to `/simulate/ranked` instead of `/simulate`. Each specialized
route rejects other formats and mixed-format profiles, even when the selected
method accepts both formats separately. Method compatibility is checked even
when `ballots` is empty. A non-sortition method still requires at least one
ballot. A `choice` on anti-plurality marks the candidate to oppose; a complete
ranking opposes its last candidate. No format is silently converted.

The facade retains legacy support for profiles mixing `choice` and `ranking`
on plurality, anti-plurality, and random-ballot. Canonical engine validation,
options, resource limits, error statuses, and result semantics apply to every
route. The OpenAPI family schemas narrow the existing method-specific request
unions rather than accepting arbitrary objects.

Python callers can import `simulate_request(request, family=None)` from
`python/api.py`. TypeScript callers can import `simulateRequest(input, family?)`
and `FAMILY_METHODS` from `typescript/api.ts`. Family names are the route suffixes.

## Count an election

Save this as `election.json`:

```json
{
  "method": "instant-runoff",
  "candidates": ["A", "B", "C"],
  "ballots": [
    {"ranking": ["A", "B", "C"], "count": 4},
    {"ranking": ["B", "C", "A"], "count": 3},
    {"ranking": ["C", "B", "A"], "count": 2}
  ]
}
```

```sh
curl --fail-with-body http://127.0.0.1:8000/simulate \
  -H 'Content-Type: application/json' \
  --data-binary @election.json
```

A has four first choices, B has three, and C has two. No candidate has more than half. C is eliminated; its two ballots transfer to B. The response names B, with five of the nine votes, and includes both rounds in `trace`.

```json
{
  "method": "instant-runoff",
  "winners": ["B"],
  "tie": false,
  "trace": [
    {"active": ["A", "B", "C"], "tally": {"A": 4, "B": 3, "C": 2}, "eliminated": ["C"]},
    {"active": ["A", "B"], "tally": {"A": 4, "B": 5}}
  ]
}
```

## Call it from a program

These clients use only standard libraries or built-in runtime APIs. They assume the local server is already running.

<CodeSelect title="Call the local simulation server">

```python
# Python 3.9+: save as client.py and run python3 client.py
import json
from urllib.request import Request, urlopen

payload = {
    "method": "approval",
    "candidates": ["A", "B", "C"],
    "ballots": [
        {"approvals": ["A", "B"], "count": 4},
        {"approvals": ["B", "C"], "count": 3},
        {"approvals": ["C"], "count": 2},
    ],
}
request = Request("http://127.0.0.1:8000/simulate",
                  data=json.dumps(payload).encode("utf-8"),
                  headers={"Content-Type": "application/json"}, method="POST")
with urlopen(request, timeout=10) as response:
    print(json.dumps(json.load(response), indent=2))  # B has seven approvals.
```

```typescript
// Node 22.18+: save as client.ts and run node client.ts
const payload = {
  method: "approval",
  candidates: ["A", "B", "C"],
  ballots: [
    {approvals: ["A", "B"], count: 4},
    {approvals: ["B", "C"], count: 3},
    {approvals: ["C"], count: 2},
  ],
};
const response = await fetch("http://127.0.0.1:8000/simulate", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify(payload),
});
const result = await response.json();
if (!response.ok) throw new Error(JSON.stringify(result));
console.log(JSON.stringify(result, null, 2)); // B has seven approvals.
```

</CodeSelect>

## Use the same engine without HTTP

```sh
python3 python/electoral.py < election.json
node typescript/cli.ts < election.json
```

The Python module exports `simulate(request)`. TypeScript exports the same operation from `typescript/electoral.ts`. Each [method chapter](/methods.md) also includes a standalone algorithm with its own sample input and helpers. Those Python snippets demonstrate counting valid profiles; the full engine and server perform validation first.

## Interpret a result

| Field | Meaning |
| --- | --- |
| `method` | Exact identifier of the counting variant. |
| `winners` | Final co-winners, or one sampled winner for a lottery method. |
| `tie` | Whether the final `winners` array contains more than one candidate. |
| `trace` | Intermediate method-specific totals, eliminations, pairwise counts, or decisions. |
| `lottery` | For randomized methods: candidate probabilities, including zero probabilities. |

A final tie is a result requiring an additional election policy. Internal decisions that must continue the count use the published [candidate priority](/ballots.md#ties). Lottery feasibility is calculated exactly using rational arithmetic; only the returned probabilities and the seeded sampling threshold use floating point. A degenerate maximal-lottery game can have several solutions: the implementation chooses the first feasible vertex in its documented constraint enumeration order.

## Validation and computation limits

Unknown fields and incompatible ballot formats are errors. Scores and credit maps must explicitly name every candidate. All numeric inputs described as integers must have integral values. The [ballot guide](/ballots.md) defines the accepted formats, defaults, and seed procedure.

| Input or method | Enforced bound |
| --- | --- |
| HTTP body | At most 1 MiB of UTF-8 JSON. `Content-Length` required; transfer encoding unsupported. |
| Candidates | 1–32 distinct identifiers; each contains 1–100 characters and must not be entirely whitespace. |
| Ballot groups | At most 10,000. Non-sortition requests need at least one. |
| Voters | At most 1,000,000 after adding all positive integer `count` values. |
| `maxScore` | Integer 1–100; default 5. Individual scores are integers 0–`maxScore`. |
| `budget` | Integer 1–1,000,000; default 100. Each quadratic ballot's sum of squared voice votes must fit. |
| `seed` | Integer 0–4,294,967,295; default 1. |
| Kemeny–Young | At most 8 candidates; enumerates every candidate order. |
| Dodgson | At most 5 candidates and 8 represented voters; exact upward-swap dynamic programming. |
| Maximal lotteries | At most 6 candidates; exact enumeration of active constraints. |

The other methods process compressed ballot groups rather than expanding one entry per voter. Majority judgment stores grade histograms and batches identical median removals. These limits bound teaching examples; they are not statements that the mathematical method only works for small elections. Public deployments would need their own workload and concurrency policies.

## Errors

Errors have the shape `{"error":"explanation"}`.

| HTTP status | Meaning |
| --- | --- |
| 400 | Invalid JSON, missing fields, invalid ballot, unsupported option, or invalid numeric value. |
| 404 | Endpoint does not exist. |
| 408 | Request body read timed out. |
| 413 | Body, candidate/profile size, or exact-search limit exceeded. |
| 415 | Content type is not `application/json`. |

The server binds loopback and keeps profiles in memory only for the request. It does not persist elections. It is a teaching service for synthetic profiles, with no authentication, voter eligibility, secrecy, or official audit workflow. The [source and variant notes](/sources.md) explain what the algorithms do and what their criteria claims assume.
