# Ballots, ties, and reproducibility

A ballot records what a voter is allowed to express. A counting rule decides what to do with that information. To compare rules fairly, keep these two decisions separate: a ranking does not tell us how strongly a voter feels, and an approval list does not order its approved candidates.

## Common request fields

Every simulation has a `method`, a list of distinct `candidates`, and `ballots`. Candidate identifiers are nonempty strings. `count` is a positive integer: a ballot with `count: 4` represents four identical voters. It is a compact way to enter a profile, not extra voting power awarded to one voter. Omitting `count` means one voter.

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

Each ballot uses one format. Unknown candidate identifiers and duplicate entries are errors. A blank approval ballot is valid; a ranked ballot must list every candidate exactly once. All ballots must use a format accepted by the selected method. Plurality, anti-plurality, and random ballot also allow a mixture of single marks and rankings, since they read only one position.

## Ballot formats

| Format | Example ballot | Meaning |
| --- | --- | --- |
| Single mark | `{"choice":"A"}` | Support A under plurality or random ballot; oppose A under anti-plurality. Those methods also accept complete rankings, using the first or last position. |
| Complete ranking | `{"ranking":["A","B","C"]}` | Prefer A to B and B to C. All candidates appear exactly once. |
| Approval | `{"approvals":["A","B"]}` | Support both A and B equally; do not approve C. An empty list approves nobody. |
| Scores or grades | `{"scores":{"A":5,"B":3,"C":0}}` | Give each candidate an integer from zero to `maxScore` (default 5). Higher is better. Every candidate needs an explicit score. |
| Quadratic voice votes | `{"credits":{"A":5,"B":3,"C":0}}` | Cast signed integer voice votes. This ballot costs 5² + 3² = 34 credits, within `budget` (default 100). Every candidate needs an explicit value. |
| No ballots | `[]` | Sortition samples uniformly from the candidate list. |

Scores feed [score](/methods/score.md), [STAR](/methods/star.md), and [majority judgment](/methods/majority-judgment.md) differently. The same numbers therefore need not produce the same result. Grade names can be mapped to increasing integers for majority judgment; equal gaps between grade numbers have no meaning there.

The quadratic field is called `credits` for the API, but its values are **voice votes**, not credits spent. The cost is the sum of their squares. Negative votes oppose a candidate. This single-winner demonstration uses equal budgets and elects the highest net voice total; it does not model money, credit trading, or a sequence of policy decisions.

## The nine-voter example

Most ranked chapters use four voters with A > B > C, three with B > C > A, and two with C > B > A. A leads the first-choice count with four votes. But five voters prefer B to A, and seven prefer B to C: B beats each rival in a head-to-head comparison. This explains why plurality selects A while a Condorcet method selects B.

For approval and score chapters, we supply approvals or scores explicitly. Those choices are additional information, not a conversion that can be uniquely inferred from the rankings.

## Ties

`winners` contains all candidates tied at the final decision, in input order; `tie` tells you whether that list has more than one name. A single-winner rule can leave a tied result. This API does not silently declare one of those candidates elected.

Some rules need an intermediate decision to continue, such as choosing two finalists or eliminating one of several tied candidates. The candidate list is a fixed priority order: earlier candidates get priority when choosing finalists or locking equally strong pairs; later candidates are eliminated first when a rule must eliminate just one. The trace records those decisions. Nanson can eliminate several candidates at once, and an all-equal round remains a final tie.

A fixed priority can affect fairness properties in exact ties. Criteria statements normally concern the mathematical rule under specified tie assumptions; read the qualifications on the method page.

## Randomness

Random ballot, maximal lotteries, and sortition return a probability distribution as well as a sampled winner. `options.seed` defaults to 1 and must be an integer from 0 to 4,294,967,295. Both languages use the same small pseudorandom generator:

```text
state = (1664525 × state + 1013904223) modulo 2³²
u = state / 2³²
```

Select the first candidate whose cumulative probability is strictly greater than `u`. This makes demonstrations reproducible; it is not a source of secure public randomness. A seed controls the draw, not which lottery is considered optimal. Candidate order also fixes a representative when several maximal lotteries exist.

## What validation protects

The API checks ballot structure, numeric bounds, valid candidate references, and computation limits before counting. It cannot check whether the submitted profile represents real voters or sincere preferences. Small limits on exhaustive methods prevent a classroom request from accidentally starting an impractical search; see the [API guide](/api-design.md).
