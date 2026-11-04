# Understanding multi-winner criteria

A criterion is a guarantee over a class of elections. It is not a rating of how good a particular council, shortlist, or project set is. For example, committee monotonicity favors a shortlist that keeps its existing members when another interview becomes possible; proportional representation may instead require a different committee when another representative is available. The intended use matters.

This guide covers every criterion named in the [starting comparison’s multi-winner section](https://en.wikipedia.org/wiki/Comparison_of_electoral_systems#Multi-winner_criteria), splitting its Pareto, unanimity and Condorcet variants. It also defines counting cost, summability, group support monotonicity, and the approval-specific JR/PJR/EJR distinctions. Each of the 19 [method chapters](/multi-methods.md) includes all 28 entries, including explicit qualifications where its ballot format cannot express a test.

## Reading an assessment

| Label | Meaning |
| --- | --- |
| Pass | A result or direct counting argument supports the property under the stated interpretation. |
| Fail | An applicable counterexample exists; the failure need not occur in every election. |
| Conditional | A quota, electorate-size, tie, ballot, outcome, or sampling assumption is essential. |
| Not applicable | The accepted input or outcome model lacks the operation or information in the chosen definition. |
| Unverified | This resource does not establish a result for the exact variant; an incomplete source-table cell is not filled with a guessed theorem. |

<Callout>
A ranked ballot describes candidates one at a time. It does not say how the voter compares &#123;A,D&#125; with &#123;B,C&#125;. A voter might prefer the set containing their favorite, the set with the highest combined utility, or a set representing two different interests. Criteria that compare whole committees need that extra preference model.
</Callout>

Sources can define an algorithm, define an axiom, or prove a result. An explanation based on an elementary tally formula is our deduction from that formula; a source link does not claim every cited document proves every variant. Read the [source notes](/multi-sources.md) for the distinction.

## Three distinctions that prevent misleading comparisons

**Candidate support and group support are different.** On approval ballots, adding support for one already elected candidate may protect that candidate while changing their colleagues. Adding support for a group of elected candidates asks for a stronger guarantee. PAV, sequential PAV and sequential Phragmén satisfy the standard single-candidate approval monotonicity condition but fail the stronger existing-ballot group-support condition. The [approval-voting book](https://arxiv.org/abs/2007.01795) defines these separately. A source column labeled only “monotone” should not be treated as a universal answer to both.

**Pareto depends on what is being compared.** On approval ballots, we compare the number of approved representatives each voter receives. A committee is dominated if another gives everybody at least as many approved members and somebody more. Strong Pareto excludes all dominated committees; the weaker correspondence property requires an improving committee to remain winning too. The Simpson committee literature also studies a candidate-replacement test: when everyone ranks A above B, must a winning committee containing B include A, or must A merely occur in some winning committee? The entries identify this ordinal interpretation instead of treating it as the same utility test.

**The winning correspondence and a chosen committee are different.** Many papers return every equally winning committee. The API chooses one using its [published priorities](/multi-ballots.md#ties-and-fixed-priorities). A weak-unanimity statement may say that the unanimously preferred top set is among the co-winners while permitting a priority to select another set. A strong-unanimity statement permits only that top set. Exact ties must be included in a claim’s assumptions.

## Quotas can change a guarantee

The STV implementation uses integer Droop `floor(N/(k+1)) + 1`. Its fractional transfer arithmetic is exact, but the rounded quota does not scale exactly when the electorate is replicated. Here is a tie-free homogeneity failure for three seats:

| Count | Ranking |
| --- | --- |
| 1 | B > C > A > D |
| 5 | D > A > B > C |
| 7 | B > D > C > A |

STV elects &#123;A,B,D&#125;. Multiply every count by three and it elects &#123;B,C,D&#125;. The examples differ only in replication; a theorem for a scale-invariant unrounded quota does not prove this integer-quota variant homogeneous.

Small electorates reveal another quota boundary. With candidates supplied in priority order D,C,B,A, three seats and a single A > B > C > D ballot, integer Droop is one. A consumes all the vote weight when elected. The zero-weight remainder is resolved by priority and yields &#123;A,C,D&#125;, even though the ballot’s unanimous top set is &#123;A,B,C&#125;. Thus the familiar STV unanimity statement needs its quota and electorate assumptions.

EAR and QBS instead use `q=N/(k+1)+1/(k+1)²`. The additive term is small, but it matters after EAR’s fractional reweighting. For two seats, ballots B > C > A ×1, C > A > B ×14, C > B > A ×12 elect &#123;B,C&#125;; tripling all counts elects &#123;A,C&#125;. QBS uses the quota only to determine integer coalition demands. Those demands are replication-invariant for this chosen epsilon, so QBS has a different homogeneity conclusion. Sharing a quota formula does not mean sharing a counting rule.

## Definitions

Let **N** be represented voters, **m** candidates, **k** seats, and **b** stored ballot groups. Most normative criteria are studied for a nontrivial choice, `1 ≤ k < m`, and a nonempty electorate. The API additionally accepts the trivial all-candidates committee. A consensus theorem can require N≥k to avoid zero-support ambiguity; approval criteria refer to submitted approval sets, not inferred thresholds.

<a id="proportionality-solid-coalitions"></a>

### Proportionality for solid coalitions

For every positive integer ℓ, a group of at least ℓN/k voters who all rank every member of a set T above every outsider must receive at least min(ℓ, |T|) members of T in a size-k committee. This is Hare-PSC; quota-based versions replace N/k by a stated q.

[Definition or framework](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf).

<a id="solid-coalition"></a>

### Solid coalition

If at least N/k voters put the same candidate uniquely first, every winning size-k committee must contain that candidate. This single-candidate requirement is weaker than full proportionality for solid coalitions.

[Definition or framework](https://arxiv.org/abs/1506.02891).

<a id="candidate-monotonicity"></a>

### Candidate monotonicity

Raising an elected candidate in rankings, or adding that candidate to an existing approval ballot, must not remove that candidate from all winning committees. Other candidates retain their relative positions. This is a single-candidate property, not group support monotonicity.

[Definition or framework](https://arxiv.org/abs/2007.01795).

<a id="support-monotonicity"></a>

### Group support monotonicity

For approval ballots, adding support for a set X of already elected candidates should keep X together in a winning committee. This is stronger than candidate monotonicity; adding voters and changing existing ballots are distinct versions. Here the existing-ballot version is used.

[Definition or framework](https://arxiv.org/abs/2007.01795).

<a id="weak-pareto"></a>

### Weak Pareto

The outcome correspondence must not exclude an improving outcome. For approval ballots, if W wins and W′ gives every voter at least as many approved representatives and one voter more, W′ must also win. For the ordinal candidate-replacement test, if everyone ranks A above B and some winner contains B, at least one winning committee must contain A. The applicable interpretation is stated per method.

[Definition or framework](https://arxiv.org/abs/2007.01795).

<a id="strong-pareto"></a>

### Strong Pareto

For approval ballots no selected committee may be dominated by another size-k committee in approved-representative counts. For the ordinal replacement test, if everyone ranks A above B, every winning committee that contains B must also contain A. These are different tests, not interchangeable definitions of committee utility.

[Definition or framework](https://arxiv.org/abs/2007.01795).

<a id="consensus-committee"></a>

### Consensus committee

If every voter ranks a member of a size-k set W first and those first-choice totals differ by at most one, W must be the unique winning committee. Small-electorate and quota conventions can matter.

[Definition or framework](https://arxiv.org/abs/1506.02891).

<a id="fishburn-condorcet"></a>

### Fishburn Condorcet committee

If a size-k committee defeats every other size-k committee by a strict voter majority, it should be selected. Comparing two committees requires an explicit extension of individual preferences: for approval ballots the number of approved members is one such extension. Rankings of candidates alone do not uniquely specify committee rankings.

[Definition or framework](https://arxiv.org/abs/2007.01795).

<a id="gehrlein-condorcet"></a>

### Gehrlein Condorcet committee

If a size-k set exists whose every member beats every outsider by strict pairwise majority, elect that set. This is an inside-versus-outside test on individual candidates, not a head-to-head vote between whole committees.

[Definition or framework](https://flore.unifi.it/handle/2158/1175914).

<a id="condorcet-winning-set"></a>

### Condorcet winning set

For every candidate x outside the committee, more than half of voters must rank at least one committee member above x. Different voters may rely on different committee members. The requirement is applied when a qualifying size-k set exists.

[Definition or framework](https://www.lamsade.dauphine.fr/~lang/papers/elkind-lang-saffidine-11.pdf).

<a id="smith"></a>

### Smith requirement for committees

A multiwinner Smith claim needs a stated majority relation. For Schulze-STV it concerns the majority-dominant set of committees in its own comparison graph; it does not mean every elected candidate must belong to the single-winner Smith set, which may contain fewer than k candidates.

[Definition or framework](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf).

<a id="committee-monotonicity"></a>

### Committee monotonicity

Increasing the requested size from k to k+1 should allow each winning size-k committee to extend to a winning size-(k+1) committee, and each winning larger committee to contain a winning smaller one. For a deterministic fixed-priority implementation, the selected committees should be nested; other independent options are held fixed.

[Definition or framework](https://arxiv.org/abs/1506.02891).

<a id="iia"></a>

### Independence of irrelevant alternatives

Removing an unelected candidate while retaining enough candidates and keeping preferences over all others unchanged must leave the elected committee unchanged. For cardinal ballots, unchanged submitted grades or approvals is an essential assumption. This chosen-set removal property is weaker than some social-ranking versions of IIA.

[Definition or framework](https://arxiv.org/abs/2007.01795).

<a id="consistency"></a>

### Consistency

If two disjoint electorates have common winning committees for the same candidate set and seat count, the winners after combining them should be exactly those common committees. A fixed-priority selector is an additional layer; seeded samples are not the outcome correspondence.

[Definition or framework](https://arxiv.org/abs/2007.01795).

<a id="participation"></a>

### Participation

Submitting an honest ballot should not make the outcome worse for that voter than abstaining. To compare committees or lotteries, specify how the voter evaluates sets or probabilities. Candidate rankings alone leave this preference extension unspecified.

[Definition or framework](https://arxiv.org/abs/2007.01795).

<a id="clone-independence"></a>

### Clone independence

Replacing a candidate by similar copies should not create a benefit or harm for an unrelated faction under a stated multiwinner clone definition. With several seats, more than one clone can be elected, so single-winner clone definitions cannot simply be reused.

[Definition or framework](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf).

<a id="homogeneity"></a>

### Homogeneity

Replicating every ballot the same positive integer number of times should preserve the winning committees, or the lottery distribution. The tie flag, intermediate tallies and a particular pseudorandom sample need not be identical.

[Definition or framework](https://arxiv.org/abs/1506.02891).

<a id="favorite-betrayal"></a>

### No favorite betrayal

A voter should never need to put a less-preferred candidate strictly above a sincere favorite to obtain a better outcome. Approval ties at the top are allowed; the voter’s preference over complete committees must be specified before assessing this guarantee.

[Definition or framework](https://arxiv.org/abs/2007.01795).

<a id="semi-honest"></a>

### Semi-honest strategy

For fixed other ballots, a voter should have a best-response ballot that does not reverse any strict preference between candidates; equal ratings or truncation may be allowed in the general rule. This is an existence-of-best-response claim, not strategyproofness. Committee utility and permitted ballots must be stated.

[Definition or framework](https://arxiv.org/abs/2007.01795).

<a id="universally-liked"></a>

### Universally liked candidates

When no more than k candidates are universally top-supported, those candidates should be included. Adding a universally supported candidate together with an extra seat should not change how the other seats are allocated. On rankings, uniquely first is the clear special case; on approvals it means approved by everybody. Exact ties and multiple universal candidates must be stated.

[Definition or framework](https://arxiv.org/abs/2007.01795).

<a id="weak-unanimity"></a>

### Weak unanimity

If all voters rank the same size-k set W above every outsider, in any internal order, W must be at least one of the winning committees. It need not be the only winning committee.

[Definition or framework](https://arxiv.org/abs/1506.02891).

<a id="strong-unanimity"></a>

### Strong unanimity

If all voters rank the same size-k set W above every outsider, in any internal order, W must be the unique winning committee. This strengthens weak unanimity.

[Definition or framework](https://arxiv.org/abs/1506.02891).

<a id="fixed-majority"></a>

### Fixed majority

If the same strict majority of voters ranks every member of a size-k set W above every outsider, elect W uniquely. This is a majoritarian demand and can conflict with representing substantial minorities.

[Definition or framework](https://arxiv.org/abs/1506.02891).

<a id="polynomial-time"></a>

### Polynomial counting time

Can this implementation count an election using a number of arithmetic operations polynomial in candidates, stored ballot groups and seats? Exact rational bit complexity is additional; a fixed input cap does not turn an exhaustive algorithm into a general polynomial algorithm.

[Definition or framework](https://arxiv.org/abs/2007.01795).

<a id="summability"></a>

### Summability

Can summaries counted independently at precincts be added before choosing the committee? Specify summary size: candidate totals O(m), pairwise counts O(m²), full approval types O(2^m), and complete ranking types O(m!) are materially different.

[Definition or framework](https://arxiv.org/abs/2007.01795).

<a id="jr"></a>

### Justified representation (JR)

Any group of at least N/k voters sharing an approved candidate must include at least one voter with an approved elected representative. This definition uses approval sets, not inferred approvals from rankings or scores.

[Definition or framework](https://arxiv.org/abs/2007.01795).

<a id="pjr"></a>

### Proportional justified representation (PJR)

If a group has at least ℓN/k voters and at least ℓ candidates approved by every member, the committee must contain at least ℓ candidates approved by somebody in the group. PJR implies JR.

[Definition or framework](https://arxiv.org/abs/2007.01795).

<a id="ejr"></a>

### Extended justified representation (EJR)

For each such ℓ-cohesive group, at least one group member must approve at least ℓ elected candidates. This strengthens PJR, which can satisfy the group collectively without giving any one voter ℓ representatives.

[Definition or framework](https://arxiv.org/abs/2007.01795).

## Metrics answer a different question

A logical criterion asks whether a guarantee always holds on its declared domain. An empirical metric measures a particular outcome or a frequency under a chosen model. Neither substitutes for the other.

| Metric | What it measures | Required assumptions |
| --- | --- | --- |
| Condorcet committee efficiency (CCE) | The fraction of tested elections in which a method elects the relevant Condorcet committee, usually conditional on such a committee existing. | State whether Fishburn, Gehrlein, or another committee comparison is used, how ties count, and how elections are sampled. |
| Gallagher least-squares index | `sqrt(½ × Σ(vᵢ − sᵢ)²)`, comparing each party’s vote share vᵢ with its seat share sᵢ. | Declare parties, mutually exclusive vote shares, thresholds and treatment of independents. Percentage inputs produce percentage-point output. |
| Loosemore–Hanby index | `½ × Σ|vᵢ − sᵢ|`, the total absolute vote-seat mismatch. | Use the same declared vote and seat-share conventions; it weighs deviations differently from the least-squares measure. |
| Unrepresented or wasted support | For an approval profile, one possible measure is the share of voters approving no elected candidate. Other “wasted vote” definitions count excess support, subquota ballots, or district-level losses. | State the definition before comparing values. A voter with one approved representative may still be underrepresented, and transferred STV weight is not automatically a wasted ballot. |

For example, if vote shares are 60% and 40% but a two-seat committee gives both seats to the first party, both listed disproportionality indices equal 40 percentage points. That number does not tell us how individual voters ranked candidates or how a district system produced those seats. [Gallagher’s original analysis](https://www.tcd.ie/Political_Science/about/people/michael_gallagher/ElectoralStudies1991.pdf) discusses the measurement choices.

These API requests contain candidate ballots, not party labels or a model of sincere utility. The server counts the submitted election; it does not invent party shares, estimate CCE from a representative population, or produce a universal wasted-vote score. Such an analysis needs explicitly supplied data and modeling assumptions.

## Summaries and computational cost

For fixed k, independent candidate totals give O(m) precinct summaries for approval, SNTV, Bloc, k-Borda, limited and cumulative voting. The pairwise support matrix has O(m²) entries and suffices for both minimax rules. Transfer and prefix rules can always preserve the complete ranking histogram, but that can require O(m!) entries. Approval reweighting can preserve all approval subsets in O(2^m) entries; RRV can preserve all score vectors, O(g^m) with g grades. Calling all of these “summable” without the summary size hides a substantial difference.

Exact PAV and committee Maximin enumerate committees. CPO-STV compares committee pairs; Schulze STV also builds a graph and solves voter-support allocation problems. Their small [API caps](/multi-api.md#limits) prevent unexpectedly large teaching runs. The caps are implementation limits, not claims that the mathematical rules only exist for small committees. Conversely, a successful bounded example does not establish polynomial counting complexity.

[Method catalog](/multi-methods.md) · [Ballot and tie conventions](/multi-ballots.md) · [Sources](/multi-sources.md)
