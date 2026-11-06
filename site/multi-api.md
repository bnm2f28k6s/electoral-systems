# Simulate a multi-winner election

The committee API executes the same Python algorithms as the multi-winner chapters. Every request names a method and an explicit number of seats. The response contains one selected committee with exactly that many distinct members and an inspectable count trace.

The existing [single-winner API](/api-design.md) remains available. Its final co-winner convention differs from choosing a committee of a fixed size, so committee requests use separate endpoints.

For small examples without a local server, use the optional [browser simulator](/simulator.md). It runs the compiled TypeScript committee engine locally in your browser; GitHub Pages does not host an HTTP API backend.

## Start the server

From the repository root, with Python 3.9 or newer:

```sh
python3 python/server.py
```

The server listens at `127.0.0.1:8000`; `--port 8081` selects another port. Discover the 19 committee method identifiers:

```sh
curl http://127.0.0.1:8000/multi/systems
```

The response is an object with a `methods` array. The [OpenAPI reference](/api/reference) includes a request and an executed response for every method.

## Choose a ballot-family endpoint

`POST /multi/simulate` remains the common facade. These specialized routes use
the same request, including required `seats`, and return the same committee result:

| Route | Required ballot field | Compatible methods |
| --- | --- | --- |
| `/multi/simulate/ranked` | `ranking` | stv, cpo-stv, schulze-stv, k-borda, bloc, quota-borda, expanding-approvals, minimax, minimax-external-opposition, single-non-transferable, multiple-random-ballots |
| `/multi/simulate/marked` | `choice` | single-non-transferable |
| `/multi/simulate/approval` | `approvals` | approval, proportional-approval, sequential-proportional-approval, phragmen, limited-vote |
| `/multi/simulate/scored` | `scores` | reweighted-range |
| `/multi/simulate/cumulative` | `votes` | cumulative |
| `/multi/simulate/none` | No ballots; `ballots: []` | sortition |

Ranked and marked describe input formats, not exclusive groups of methods.
Single non-transferable vote accepts either separately. Specialized endpoints
reject mixed formats and incompatible methods, including incompatible requests
with an empty ballot array. They do not coerce ballots. The facade preserves
legacy profiles mixing `choice` and `ranking` for single non-transferable vote.
All canonical validation, dynamic option checks, computation limits, status
codes, and committee tie semantics remain unchanged. Limited vote uses the
approval format with a per-voter mark limit, not the single-choice format.

Python callers can import `simulate_multi_request(request, family=None)` from
`python/api.py`. TypeScript callers can import
`simulateMultiRequest(input, family?)` and `MULTI_FAMILY_METHODS` from
`typescript/api.ts`. Family names match the route suffixes. OpenAPI documents
each specialized route with a narrowed method-specific request union.

## Count a committee

Save this request as `committee.json`:

```json
{
  "method": "stv",
  "candidates": ["A", "B", "C", "D"],
  "seats": 2,
  "ballots": [
    {"ranking": ["A", "B", "C", "D"], "count": 6},
    {"ranking": ["C", "D", "A", "B"], "count": 3},
    {"ranking": ["D", "C", "B", "A"], "count": 1}
  ]
}
```

```sh
curl --fail-with-body http://127.0.0.1:8000/multi/simulate \
  -H 'Content-Type: application/json' \
  --data-binary @committee.json
```

The integer Droop quota is four. A's six votes elect A and leave a surplus of two, which transfers to B. D is then eliminated and its one vote transfers to C. C reaches four, so the selected committee is A and C.

```json
{
  "method": "stv",
  "seats": 2,
  "winners": [
    "A",
    "C"
  ],
  "tie": false,
  "trace": [
    {
      "quota": 4
    },
    {
      "tally": {
        "A": 6.0,
        "B": 0.0,
        "C": 3.0,
        "D": 1.0
      },
      "elected": "A",
      "tied": [
        "A"
      ],
      "transferFactor": 0.3333333333333333
    },
    {
      "tally": {
        "B": 2.0,
        "C": 3.0,
        "D": 1.0
      },
      "eliminated": "D",
      "tied": [
        "D"
      ]
    },
    {
      "tally": {
        "B": 2.0,
        "C": 4.0
      },
      "elected": "C",
      "tied": [
        "C"
      ],
      "transferFactor": 0.0
    }
  ]
}
```

The fractional transfer factor is displayed as a JSON number. Decisions inside the engine use exact rational arithmetic.

## Call from Python or TypeScript

These complete client programs assume the local server is already running. Both send an approval profile to proportional approval voting: the selected committee is A and D.

<CodeSelect title="Call the committee simulation API">

```python
# Python 3.9+: save as client.py and run python3 client.py
import json
from urllib.request import Request, urlopen

payload = {
    "method": "proportional-approval",
    "candidates": ["A", "B", "C", "D"],
    "seats": 2,
    "ballots": [
        {"approvals": ["A", "B"], "count": 6},
        {"approvals": ["C", "D"], "count": 3},
        {"approvals": ["D"], "count": 1},
    ],
}
request = Request("http://127.0.0.1:8000/multi/simulate",
                  data=json.dumps(payload).encode("utf-8"),
                  headers={"Content-Type": "application/json"}, method="POST")
with urlopen(request, timeout=10) as response:
    print(json.dumps(json.load(response), indent=2))
```

```typescript
// Node 22.18+: save as client.ts and run node client.ts
const payload = {
  method: "proportional-approval",
  candidates: ["A", "B", "C", "D"],
  seats: 2,
  ballots: [
    {approvals: ["A", "B"], count: 6},
    {approvals: ["C", "D"], count: 3},
    {approvals: ["D"], count: 1},
  ],
};
const response = await fetch("http://127.0.0.1:8000/multi/simulate", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify(payload),
});
const result = await response.json();
if (!response.ok) throw new Error(JSON.stringify(result));
console.log(JSON.stringify(result, null, 2));
```

</CodeSelect>

## Use the engine directly

Both engines accept the same JSON input and return matching results:

```sh
python3 python/multi_winner.py < committee.json
node typescript/multi_cli.ts < committee.json
```

Python exports `simulate(request)` from `python/multi_winner.py`; TypeScript exports `simulate` from `typescript/multi_winner.ts`. Each [method chapter](/multi-methods.md) also supplies a complete program that runs independently of the repository. Those standalone examples count valid data; validation is performed by the full engines and server.

## Inputs

`seats` must be a positive integer no greater than the candidate count. Every candidate identifier must be distinct. A ballot's positive integer `count` represents identical voters; it is not a weight that one voter can choose for themselves.

| Methods | Ballot field | Interpretation |
| --- | --- | --- |
| Approval, PAV, sequential PAV, sequential Phragmén | `approvals` | A subset of supported candidates, including an empty subset. |
| Reweighted range | `scores` | Explicit integer 0–`maxScore` value for every candidate. |
| Limited vote | `approvals` | At most `limit` distinct supported candidates. |
| Cumulative | `votes` | Nonnegative integer allocations to every candidate; their sum cannot exceed `budget`. |
| Single non-transferable | `choice` or `ranking` | One supported candidate, or the first candidate in a complete ranking. These may be mixed across ballots. |
| Sortition | Empty `ballots` array | Draw a committee uniformly from the candidate list. |
| All remaining methods | `ranking` | A complete, strict order of all candidates. |

Read the [ballot guide](/multi-ballots.md) for the distinction between approval, scores, cumulative allocations, and rankings. A ranking cannot uniquely determine the score or approval input that a voter would submit.

## Read a response

| Field | Meaning |
| --- | --- |
| `method` | Exact committee counting identifier. |
| `seats` | Requested committee size. |
| `winners` | Exactly `seats` distinct selected members, listed in input candidate order. Election order is recorded in the trace where relevant. |
| `tie` | Whether a reported selection tie required a priority choice. Electing two people is not itself a tie. Random draws are not counted as ties. |
| `trace` | Intermediate totals, coalitions, weights, loads, committee comparisons, or conditional draw probabilities. |

Earlier candidates receive priority in selection ties; tied STV eliminations remove the latest candidate. Exhaustive optimizers record all their optimal committees in `trace.tiedCommittees` and select the first by candidate priority. EAR first uses its documented rank-vector priority, then input order for equal vectors. A deterministic choice can affect exact-tie properties; it should not be mistaken for a claim that the mathematical rule always has a unique committee.

All fractional decisions use Python fractions or TypeScript BigInt rationals. JSON presents those values as numbers; reusing the rounded display values to continue a count can change a close result. Run the exact algorithm to reproduce the count.

Sortition samples candidates uniformly without replacement. The declared multiple-random-ballots variant independently samples a voter's highest remaining preference for each seat. Both advance the shared 32-bit generator once per seat using `state = (1664525 × state + 1013904223) mod 2³²`; seed 1 is the default. Traces contain the conditional probabilities and state after each draw. These are reproducible teaching draws, not secure public randomness.

## Limits

| Input or algorithm | Enforced bound |
| --- | --- |
| Request body | At most 1 MiB UTF-8 JSON, with `Content-Length`; transfer encoding unsupported. |
| Candidates | 1–32 distinct identifiers, each 1–100 Unicode characters and not entirely whitespace. |
| Seats | 1–candidate count. |
| Ballot groups | At most 10,000; only sortition accepts, and requires, no ballots. |
| Represented voters | At most 1,000,000 after adding positive `count` values. |
| `maxScore` | Integer 1–100, default 5. |
| `budget` | Cumulative votes per voter: integer 1–1,000,000, default 100. |
| `limit` | Integer 1–32; for limited vote, less than `seats`, except one for a one-seat count. Default `max(1, seats−1)`. |
| `seed` | Integer 0–4,294,967,295, default 1. |
| PAV and external-opposition minimax | At most 8 candidates for exact enumeration. |
| CPO-STV and Schulze STV | At most 6 candidates and 100 ballot groups for exact committee comparisons. |

Unknown fields, incompatible ballot formats, missing candidate map entries, nonintegral values, and invalid candidate references are errors. The quota definitions and tie rules are fixed variants, rather than options that silently alter the method.

STV and CPO-STV use integer Droop `floor(N/(seats+1)) + 1` and fractional inclusive Gregory surplus transfer. QBS and EAR use the exact quota `N/(seats+1) + 1/(seats+1)²`, which lies strictly above fractional Droop and at most `N/seats` even in small electorates. These different quota choices matter for the [criteria](/multi-criteria.md), especially homogeneity.

## Errors and hosting

Errors have the shape `{"error":"explanation"}`. Status 400 means invalid input; 404 an unknown endpoint; 408 a body read timeout; 413 a body, size, or algorithm limit; and 415 a content type other than `application/json`.

GitHub Pages serves the documentation. This loopback server executes synthetic profiles locally and does not persist elections. It does not supply authentication, voter eligibility, ballot secrecy, or official election auditing.
