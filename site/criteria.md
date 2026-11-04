# Understanding single-winner voting criteria

A criterion asks what a voting rule promises across a whole class of elections. A worked example shows one count. It cannot prove that the rule always meets a criterion, and a simulation’s result should not be read as a recommendation for a particular election.

The method chapters cover every single-winner criterion discussed in the [starting comparison](https://en.wikipedia.org/wiki/Comparison_of_electoral_systems#Comparison_of_single-winner_voting_methods), including counting criteria omitted from its main compliance table. We distinguish ranked and rated majority, weak and strong Pareto, and ordinary and local independence. Ballot format appears separately in each chapter because it describes the information voters supply.

<Callout>
A method can meet one criterion and fail another. A head-to-head majority winner, a highest average grade, and a largest first-choice total express different goals. There is no single “best” method implicit in these chapters.
</Callout>

## Reading the criterion tables

| Label | Meaning |
| --- | --- |
| Pass | The stated mathematical rule meets the property on the domain described in the explanation. Check the assumptions before extending it to another ballot format. |
| Fail | The rule admits a counterexample; it does not mean that the problem occurs in every election. |
| Conditional | A ballot, tie, probability, or outcome assumption is essential. This is not an unconditional promise for every possible variant. |
| Not applicable | The model lacks the operation or information required by the definition, such as adding an honest ballot to sortition. |
| Unverified | No claim is established here for this exact variant. An empty cell in a source is not a pass or a fail. |

Criteria normally assume at least two candidates and a nonempty electorate; the API also accepts the trivial one-candidate count. The code uses complete strict rankings, bounded integer grades, or explicitly declared approvals and voice votes. Some abstract properties concern truncated rankings, equal rankings, or complete social orderings that this API does not accept or return. Their entries discuss the general rule where meaningful instead of treating an unavailable operation as a vacuous success. Entries marked unverified are explicit research limits, not invented results.

Sources attached to an entry may define its counting rule or the criterion. A short algebraic explanation in the entry is our reasoning from that definition; it is not a claim that every cited source proves every variant of the property. Papers with direct results are identified in the [source notes](/sources.md).

## Ties are part of the rule

A scoring rule may return several equal leaders. Elimination rules may need to choose a candidate before the final result is known. This demonstration gives earlier candidates priority in those internal choices, and reports a genuine final tie as co-winners. A different tie policy can change some properties, especially clone independence and reversal symmetry. Universal results about a named method must not automatically be transferred to a different tie convention.

For example, the clone-independence literature distinguishes the original ranked-pairs correspondence from specific ways of ordering tied victories. The simulation’s fixed ordering is documented explicitly, so its clone entry is conditional. [Zavist and Tideman’s paper](https://www.condorcet.vote/assets/DOCS/CompleteIndependenceofClones.pdf) explains why tie treatment matters.

For a lottery, the probability distribution is the election outcome being compared mathematically. “Always elects a Condorcet winner” means probability one; “excludes a loser” means probability zero. A reproducible pseudorandom draw can pick the same candidate in two runs without proving consistency, monotonicity, or participation. Maximal lotteries may admit several feasible distributions, and the demonstration’s choice of one distribution does not inherit every property of the entire correspondence.

## Small counterexamples

These are synthetic elections. Each row’s count represents that many voters with the displayed ballot.

### Plurality can elect a majority loser

| Count | Ranking |
| --- | --- |
| 4 | A > B > C |
| 3 | B > C > A |
| 3 | C > B > A |

Plurality gives A four votes and B and C three each. A wins even though six voters rank A last. B also beats A by six votes to four. This separates a largest first-choice total from both majority-loser exclusion and the Condorcet-winner criterion.

### Borda can reject a first-choice majority

| Count | Ranking |
| --- | --- |
| 6 | A > B > C |
| 4 | B > C > A |

With two, one, and zero points, A receives 12, B receives 14, and C receives 4. B wins although six of ten voters put A first. The rule is counting positional support rather than promising first-choice majority rule.

### More support can hurt under IRV

| Count | Original ranking |
| --- | --- |
| 8 | A > B > C |
| 7 | B > C > A |
| 6 | C > A > B |

C starts last and is eliminated. Those six ballots transfer to A, who wins 14 to 7. Now two of the seven B-first voters raise A from last to first while keeping B above C. The first-choice totals become A 10, B 5, C 6. B is eliminated and transfers five votes to C, who wins 11 to 10. A received more support but lost because the elimination order changed. This is a monotonicity failure; it does not contradict IRV’s different later-no-harm property.

### Maximum ratings differ from a first-choice majority

| Count | A | B | C |
| --- | --- | --- | --- |
| 51 | 5 | 4 | 4 |
| 49 | 0 | 5 | 5 |

A is uniquely maximum-rated by 51 voters. Score totals are A 255 and B and C 449. Score therefore fails even the rated-majority version. STAR advances B and C, so it fails that version too. Majority judgment elects A: A’s median is 5 while both rivals have median 4. Approval’s binary scale behaves differently: a uniquely approved favorite means that ballot approves no rival.

### Independence for grades needs a fixed scale

Removing a candidate leaves A’s and B’s submitted score columns unchanged, so their score totals stay the same. That establishes an independence statement about those columns. If a voter instead changes grades after the candidate list changes, the input no longer satisfies the unchanged-grade assumption. Likewise, two adjacent candidates in an underlying ranking need not receive identical grades. Cardinal methods’ conditional independence entries refer to these distinctions.

## Criterion definitions

Definitions below fix the meaning used in the chapters. The [Preferential Voting Tools axiom documentation](https://pref-voting.readthedocs.io/en/stable/axioms_overview.html) provides operational definitions and violation checks for many ranked-ballot properties. Different papers use different extensions to ties, lotteries and weak preferences, so those extensions are stated rather than silently combined.

<a id="majority-ranked"></a>

### Ranked majority

If the same group of more than half of voters each ranks a candidate uniquely first, that candidate must win. This differs from head-to-head victories formed by different majorities.

<a id="majority-rated"></a>

### Rated majority

A candidate uniquely given the maximum permitted rating by more than half of voters must win. This is weaker than ranked majority for cardinal ballots. For ranked ballots use the first-place majority interpretation.

<a id="majority-loser"></a>

### Majority loser

A candidate ranked strictly last by more than half the electorate must not win.

<a id="mutual-majority"></a>

### Mutual majority

If more than half the voters put every member of a set above every outsider, the winner must come from that set.

<a id="condorcet-winner"></a>

### Condorcet winner

A candidate preferred to each rival by a strict head-to-head majority must win. Different voters may form each majority.

<a id="condorcet-loser"></a>

### Condorcet loser

A candidate who loses every head-to-head majority comparison must not win.

<a id="weak-pareto"></a>

### Weak Pareto

If everyone strictly prefers A to B, B must not win. For numeric ballots distinguish strictly larger submitted numbers from hidden preferences.

<a id="strong-pareto"></a>

### Strong Pareto

If everyone weakly prefers A to B and someone strictly prefers A, B must not win. This equals weak Pareto on a domain of complete strict rankings.

<a id="smith"></a>

### Smith set

The winner must lie in the smallest nonempty set whose members each strictly beat every outsider head-to-head. With tied pairwise contests, retain the full smallest strictly dominating set.

<a id="smith-iia"></a>

### Smith independence

Removing candidates outside the Smith set must leave the outcome within the Smith set unchanged. The definition assumes the same comparisons among retained candidates.

<a id="ipda"></a>

### Independence of Pareto-dominated alternatives

Adding or removing an alternative unanimously ranked below another must not change the outcome among the remaining alternatives.

<a id="iia"></a>

### Independence of irrelevant alternatives

Adding or removing a nonwinning candidate must not change the winner among the others when their relative preferences stay fixed. For ratings, unchanged absolute scores are a separate assumption.

<a id="liia"></a>

### Local independence of irrelevant alternatives

In a social ordering, deleting the top or bottom candidate must preserve the relative order of the remaining candidates. A winner-only API does not itself expose this ordering.

<a id="clone-independence"></a>

### Independence of clones

Replace a candidate with a group always adjacent in every ranking: outsiders should keep their winning status, and a winning original should be replaced by a winning group member.

<a id="monotonicity"></a>

### Monotonicity

Raising a winner in some ballots, with other comparisons unchanged, must not make that candidate lose. For a lottery compare winning probabilities.

<a id="consistency"></a>

### Consistency / reinforcement

If the same candidate uniquely wins two separate electorates, that candidate must win their union. For lotteries an extension compares common lottery outcomes instead of sampled winners.

<a id="participation"></a>

### Participation

Joining with an honest ballot must not yield an outcome the new voter likes less than the result without that ballot. Ties and lotteries require an explicit preference extension.

<a id="reversal-symmetry"></a>

### Reversal symmetry

If every strict ranking is reversed, a previous unique winner must not remain the unique winner. For ratings reverse the common numeric scale; lotteries require a probabilistic interpretation.

<a id="homogeneity"></a>

### Homogeneity

Replicating every ballot the same positive integer number of times must preserve the winner set or lottery distribution.

<a id="polynomial-time"></a>

### Polynomial counting time

Can the winner be found in time polynomial in the candidate count and linear in the number of ballots, apart from tally arithmetic? This describes a rule and an algorithm, not the effect of a fixed demonstration cap.

<a id="resolvability"></a>

### Resolvability

Under the usual large-electorate model, does the frequency of unresolved winner ties tend to zero? Deterministic tie-breaking or a fixed random seed alone does not establish this property.

<a id="summability"></a>

### Summability

Can precinct summaries be added before counting the winner? State how the summary size grows with candidate count m; preserving all m! ranking types is very different from m candidate totals.

<a id="later-no-harm"></a>

### Later no harm

Adding a lower preference must never harm a candidate already preferred above it. Completing the restricted ranked ballots accepted by this demo is not an available operation; the general rule is assessed.

<a id="later-no-help"></a>

### Later no help

Adding a lower preference must never help a candidate already preferred above it. This differs from later no harm.

<a id="favorite-betrayal"></a>

### No favorite betrayal

A voter must never need to put somebody strictly above a sincere favorite to obtain a better outcome. Allowing an equal top grade is different from reversing two strict preferences.

## Counting cost and precinct summaries

Let **m** be candidates, **b** stored ballot groups, and **N** the voters represented by their counts. These are different measures: one stored ballot can stand for a million identical votes. Limits in the [API guide](/api-design.md) keep the demonstrations practical, but do not change an exponential algorithm into a polynomial one.

A fixed candidate list lets score, approval, plurality, anti-plurality, Borda and quadratic counts combine candidate totals from separate precincts in O(m) storage. A head-to-head matrix uses O(m²) entries. Adding the matrices is enough for pairwise rules, and for recomputing Borda totals after candidates are removed: a candidate’s Borda points equal their pairwise support summed over the remaining rivals. Thus Nanson and Baldwin also admit this compact summary. Two-round simulation adds first-choice totals to the matrix, and STAR adds score totals.

IRV and Coombs transfers need more information than a matrix: the next active first or last choice depends on combinations of eliminated candidates. Keeping every distinct complete ranking type is sufficient but can take O(m!) entries. This is technically summability with a large summary, not the compact summability available from candidate totals. Dodgson can likewise use a complete ranking histogram before its expensive exact optimization. Majority judgment needs grade-frequency histograms; adding precinct medians gives the wrong information.

The exhaustive Kemeny algorithm tries m! orders, and the exact Dodgson demonstration searches combinations of individual-voter swaps. Their caps are stated in each chapter. The maximal-lottery example enumerates feasible vertices to stay self-contained, although the mathematical problem can be solved using linear programming. Neither a time cap nor one successful example is evidence about general counting complexity.

## Criteria and simulations answer different questions

A logical criterion is an all-profile claim on a specified domain. A simulation can instead estimate how often a rule selects a particular benchmark winner under a chosen model. That estimate depends on the electorate distribution, candidate distribution, voter strategy and benchmark. It cannot prove a logical guarantee, and a criterion failure alone does not report its practical frequency.

This project’s API simulates the counting of submitted ballots. It does not generate a statistically representative electorate or infer sincere utility from a ranking or grade. Keep those tasks separate when comparing results.
