# Ballots and committees

A multi-winner election fills a fixed number of seats. Its result is a **committee**, an unordered set of distinct candidates. A committee can be a shortlist, a representative council, or a set of projects; these purposes can call for different rules. Picking the three largest totals and trying to represent three different voter groups are different objectives.

The [multi-winner catalog](/multi-methods.md) uses the same Python and TypeScript languages as the [single-winner chapters](/methods.md). The local server adds `/multi/systems` and `/multi/simulate` alongside the existing single-winner endpoints. The [committee API guide](/multi-api.md) provides executable requests and the enforced limits.

## Common fields

Every request names a `method`, lists unique `candidates`, specifies `seats`, and supplies `ballots`. Seat count is an integer from one to the number of candidates. The output always contains exactly that many distinct `winners`, listed in candidate-input order. This order is a reporting convention, not an elected ranking or an allocation of particular offices.

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

`count` is a positive integer number of identical voters; omitting it means one. Grouping six identical ballots is equivalent to submitting six separate copies. It is not a budget that a voter chooses to increase. The input limits count both stored ballot groups and the voters they represent.

Candidate IDs must be nonempty strings, at most 100 Unicode characters, and cannot be entirely whitespace. Unknown IDs and repeated candidates in a ballot are errors. The engine accepts one ballot format per ballot, appropriate to the chosen method. It does not infer approvals from scores or strength of preference from rankings.

## Formats

| Format | Example ballot | Methods and meaning |
| --- | --- | --- |
| Complete strict ranking | `{"ranking":["A","B","C","D"]}` | Ranked quota, pairwise, and committee-comparison rules; k-Borda; Bloc; multiple random ballots. Every candidate appears once, from most to least preferred. |
| Single choice | `{"choice":"A"}` | SNTV. This method also accepts complete rankings, reading only the first position; the formats may be mixed within its request. |
| Approvals | `{"approvals":["A","B"]}` | Approval, PAV, sequential PAV, and sequential Phragmén. All approved candidates are supported equally. Empty approval lists are valid. |
| Limited marks | `{"approvals":["A"]}` | Limited voting uses approval subsets no larger than `options.limit`. The default is `max(1, seats−1)`; with more than one seat the explicit limit must remain below the seat count. |
| Scores | `{"scores":{"A":5,"B":4,"C":0,"D":0}}` | Reweighted range voting. Every candidate needs an integer from zero to `options.maxScore`, default 5. |
| Cumulative votes | `{"votes":{"A":60,"B":40,"C":0,"D":0}}` | Cumulative voting. Nonnegative integers for every candidate must sum to no more than `options.budget`, default 100. Unspent votes are allowed. |
| No ballots | `[]` | Sortition. Only candidate IDs, seats, and the sampling seed affect the result. |

For Bloc, a ranking is read as exactly `seats` marks for its top candidates. This makes the ballot rule change when the seat count changes. Unrestricted approval voting does not impose that exact-mark condition. Limited voting gives fewer marks than seats, while cumulative voting lets a voter concentrate several votes on one candidate. Their similar-looking candidate totals therefore come from different permitted inputs.

Cumulative votes have a **linear** budget: spending 60 votes on A and 40 on B costs 100. The single-winner quadratic example instead charges squared voice votes. Neither format should be substituted silently for the other.

## Quotas and transferred weight

A quota is a support target for one seat. Let N be the represented voters and k the seats. This STV variant uses integer Droop:

```text
quota = floor(N / (k + 1)) + 1
```

For the ten-voter, two-seat example above, the quota is four. A starts with six, is elected, and retains four units of weight. The remaining two units transfer. Weighted inclusive Gregory transfers apply the same surplus fraction `(total − quota) / total` to every ballot currently assigned to that candidate. Subsequent counts use the transferred fractional weight rather than turning it into an arbitrary subset of whole voters.

The engines compare fractions exactly; JSON trace values may be rounded floating-point displays. The trace helps explain the count but is not a replacement for the exact arithmetic in the executable code. Complete rankings prevent ranking exhaustion while candidates remain, though elected candidates can consume all transferable weight before every seat has been filled. The rule then needs its documented priority and fill decisions.

Quota Borda and expanding approvals use a different explicitly chosen quota:

```text
q = N / (k + 1) + 1 / (k + 1)²
```

This lies above the fractional Droop boundary and at or below the Hare quota N/k for a nonempty electorate. It supports the strict-ranking q-PSC procedures in their source. It is not the integer STV quota. Changing a quota can change both an example and a mathematical guarantee; each method chapter states the convention it implements.

## Ties and fixed priorities

Electing several people is not itself a tie. A tie means the count had equally eligible choices and needed an additional priority to choose a fixed-size result. The multi-winner `tie` flag reports a consequential tied decision during the count or at a final cutoff. It does not add candidates beyond `seats`, and it does not promise that every possible tie path was enumerated.

For ordinary tied candidate choices, earlier candidates in the request have priority. When one candidate must be eliminated from a tied lowest group, the latest-listed candidate is eliminated. Exhaustive committee optimizers order combinations by candidate indices and choose the first optimal one. The trace records relevant scores and decisions; the selected committee is then reported in original candidate order.

EAR first fixes its own **rank-maximal** priority from the original profile: compare first-place totals, then second-place totals, and so on. Candidate input order resolves equal rank vectors. This is part of the specified EAR procedure, rather than recomputing a new preference order after each reweighting.

A mathematical voting rule is often studied as a correspondence returning every equally winning committee. The API selects one committee for a concrete simulation. A theorem about the correspondence does not automatically hold for every selector, especially at exact ties. The [criteria guide](/multi-criteria.md) distinguishes these cases.

## Random draws

Sortition draws uniformly from the remaining candidates without replacement. Every size-k committee therefore has the same conceptual probability. Multiple random ballots instead make independent voter draws with replacement; the chosen ballot elects its highest-ranked unelected candidate. The code aggregates identical current choices rather than physically expanding all represented voters.

Every draw advances the shared pseudorandom state:

```text
state = (1664525 × state + 1013904223) modulo 2³²
u = state / 2³²
```

A candidate is selected at its cumulative conditional probability. `options.seed` defaults to 1 and accepts integers from 0 to 4,294,967,295. Both languages reproduce the same sequence. This is a teaching generator, not a public-election randomness protocol. The trace records conditional draws; it need not enumerate all possible committees.

Compare probability distributions when assessing random-rule properties. A particular seed is one reproducible result. Reusing that seed after changing candidate order or a ballot can change the sampling intervals; that observation alone is neither a proof nor a counterexample to a probabilistic axiom.

[Method catalog](/multi-methods.md) · [Committee criteria](/multi-criteria.md) · [API guide](/multi-api.md)
