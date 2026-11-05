# TypeScript counting algorithms

The engine has no imports or dependencies. With Node.js 22.18+ (Node 26 tested):

```sh
node typescript/cli.ts < examples/requests/borda.json
```

From TypeScript, import `simulate` from `./electoral.ts` and pass the same JSON
request accepted by the Python server. The return value includes the counting
trace and either co-winners or one sampled candidate and its lottery.

For ballot-family dispatch, use the library facade:

```ts
import { simulateRequest, simulateMultiRequest, FAMILY_METHODS,
  MULTI_FAMILY_METHODS } from './api.ts';
import type { BallotFamily, MultiBallotFamily, FamilyRequest,
  MultiFamilyRequest } from './api.ts';

const election = {method: 'plurality', candidates: ['A', 'B'],
  ballots: [{choice: 'A'}]};
const result = simulateRequest(election, 'marked');
const committee = simulateMultiRequest({...election,
  method: 'single-non-transferable', seats: 1}, 'marked');
```

The optional family argument is `ranked`, `marked`, `approval`, `scored`,
`quadratic`, or `none` for single-winner elections. Committee calls replace
`quadratic` with `cumulative`. The exported catalogs list compatible method IDs
per family. Ranked and marked overlap where the engine accepts either input
format. A specified family rejects mixed formats and incompatible methods even
with empty ballots. With no family, the facade infers homogeneous formats and
preserves the engines' legacy mixed choice/ranking acceptance. Engines remain
the source of validation, options, resource limits, and counting algorithms.
Both dispatch functions accept `unknown` so untrusted JSON receives runtime
validation; request/result and family-specific ballot types are also exported.
`FamilyRequest<F>` and `MultiFamilyRequest<F>` restrict both methods and ballot
formats. Options follow the canonical engines' shared option objects and dynamic
checks. Catalog objects and their arrays are frozen against runtime mutation.

Individual family functions are also exported: `simulateRanked`, `simulateMarked`,
`simulateApproval`, `simulateScored`, `simulateQuadratic`, and `simulateNone`.
Committee equivalents use the `simulateMulti` prefix, with
`simulateMultiCumulative` instead of a quadratic function. The common facades
delegate to these functions for homogeneous formats; mixed legacy profiles go
directly to the canonical engine.

These calls match Python's `/simulate/{family}` and
`/multi/simulate/{family}` routes. The original engine imports still work.
Run `node tests/test_family_api.ts < /dev/null` for family regression checks,
and `python3 -m unittest discover -s tests -p test_family_api.py` for real HTTP
checks and Python/TypeScript family parity.

`candidates` is a published fixed priority for intermediate ties: earlier IDs
survive tied eliminations and advance first to runoffs. Equal final tallies
remain co-winners. The complete ranking variant rejects truncated rankings and
equal rankings. Two-round voting assumes the same preferences in both rounds.
STAR uses candidate priority for equal finalist totals and preserves a tied
runoff; this teaching tie policy differs from the recommended STAR tiebreakers.
Quadratic ballots record signed voice votes in `credits`; the sum of their
squares must fit the per-voter budget.

Random methods share a 32-bit linear congruential generator with Python, allowing
reproducible demonstrations. This generator is not a public election draw.
Maximal lotteries use exact BigInt rational arithmetic for vertex feasibility,
then convert probabilities to JSON numbers for display and the seeded draw.
When several maximal lotteries exist, the first feasible vertex in the stated
candidate order is chosen; neutrality properties of the full lottery
correspondence need not survive this extra selection rule.

Resource limits: 32 candidates, 10,000 ballot groups, and 1,000,000 represented
voters. Exact Kemeny enumeration allows 8 candidates; exact Dodgson allows 5
candidates and 8 represented voters; maximal-lottery vertex enumeration allows
6 candidates. Larger inputs fail with an `ElectionError` status of 413.
The other methods use additive counts, pairwise matrices, or bounded grade
histograms and do not expand `count` into individual voters.

Run the independent TypeScript algorithm checks:

```sh
node tests/test_typescript.ts
```

If TypeScript is installed, check the import-free engine with
`tsc -p typescript/tsconfig.json`. The CLI's Node standard-library imports also
need `@types/node` for static checking; no Node typings are needed to run it.
