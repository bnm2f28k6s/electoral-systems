# TypeScript counting algorithms

The engine has no imports or dependencies. With Node.js 22.18+ (Node 26 tested):

```sh
node typescript/cli.ts < examples/requests/borda.json
```

From TypeScript, import `simulate` from `./electoral.ts` and pass the same JSON
request accepted by the Python server. The return value includes the counting
trace and either co-winners or one sampled candidate and its lottery.

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
