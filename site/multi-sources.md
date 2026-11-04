# Multi-winner sources and scope

The [starting comparison’s multi-winner table](https://en.wikipedia.org/wiki/Comparison_of_electoral_systems#Criterion_tables) supplies the coverage checklist: 19 entries, including its nonvoting and random-ballot baselines. Each chapter names an exact implemented variant. Broad names such as STV, Phragmén, CPO-STV, and multiple random ballots can describe different procedures; a shared name does not establish identical outcomes or properties.

These chapters use original explanations and synthetic profiles. Primary definitions and mathematical results are separated from the decisions needed for a concrete teaching implementation. The code is self-contained and does not import the research packages cited as definitions or comparison points.

## Ranked rules and committee properties

[Elkind, Faliszewski, Skowron and Slinko, Properties of Multiwinner Voting Rules](https://arxiv.org/abs/1506.02891) develops the strict-ranking committee model and definitions including candidate monotonicity, committee monotonicity, solid coalitions, consensus, and unanimity. It treats winning committees as a correspondence and states electorate-size and quota qualifications where needed. Its SNTV, Bloc, and k-Borda definitions identify the separable counting rules used here.

[Aziz and Lee, The Expanding Approvals Rule: Improving Proportional Representation and Monotonicity](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf) provides the quota, solid-coalition framework, EAR procedure, and the formal strict-preference Quota Borda procedure. Algorithms 1 and 3 are the relevant counting references. Their analysis distinguishes full candidate monotonicity from restricted rank-respecting improvements and distinguishes strong proportionality statements from weaker special cases. The API uses complete strict rankings, not the paper’s full weak-order input model.

[Bubboloni, Diss and Gori, Extensions of the Simpson Voting Rule to the Committee Selection Setting](https://flore.unifi.it/handle/2158/1175914) distinguishes two easily confused rules: top-k Simpson candidate scores and the Minimal Size of External Opposition committee score. They coincide for one seat but can differ for larger committees. The paper’s candidate-replacement Pareto conditions, unanimity results, stability, and committee-monotonicity results concern these precise rules. An [accepted-manuscript mirror](https://scispace.com/pdf/extensions-of-the-simpson-voting-rule-to-the-committee-43ef2wthvq.pdf) provides the same authored text when the institutional file is unavailable.

[Elkind, Lang and Saffidine, Choosing Collectively Optimal Sets of Alternatives Based on the Condorcet Criterion](https://www.lamsade.dauphine.fr/~lang/papers/elkind-lang-saffidine-11.pdf) defines the Condorcet winning set through a majority of voters each preferring at least one member over an outsider. This disjunctive voter-level definition is different from requiring one fixed member to beat that outsider pairwise.

## Approval and scored rules

[Lackner and Skowron, Multi-Winner Voting with Approval Preferences](https://arxiv.org/abs/2007.01795) defines AV, harmonic PAV, sequential PAV, and sequential Phragmén. It explains candidate versus group support monotonicity, approval-count committee Pareto efficiency, consistency, and JR/PJR/EJR. These distinctions prevent transferring a result about a single supported candidate to a whole supported group, or confusing a global optimum with a greedy approximation.

The authors’ [abcvoting documentation](https://abcvoting.readthedocs.io/en/latest/abcrules.html) supplies inspectable rule implementations and descriptions. Our code implements the rules directly; it is not a wrapper around that library.

[Smith, Reweighted Range Voting (2005)](https://rangevoting.org/WarrenSmithPages/homepage/rerange.pdf) defines the reweighting family. The implemented variant normalizes scores to a 0–1 scale and uses weight `1 / (1 + sum of scores for elected candidates)` in those normalized units. Score bounds and the reweighting constant are therefore part of the counting definition, not presentation choices.

Limited voting and cumulative voting are specified explicitly as elementary counting procedures: at-most-limit positive marks, and equal-budget nonnegative integer vote allocations. Their different ballot constraints matter even though both ultimately select high independent candidate totals. A first-choice or ranked proportionality theorem is not inferred from those totals.

## Transfer and committee-comparison rules

[Tideman, The Single Transferable Vote (1995)](https://rangevoting.org/TidemanSTVJEconPersp195.pdf) explains STV and comparison of pairs of outcomes. CPO-STV needs a completion when comparisons cycle. Here that completion minimizes the worst defeat margin; the chapter also states the integer Droop quota and fractional common-candidate transfer convention. A different completion can be a different rule.

[Schulze, the Schulze STV specification](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf) defines the voter-management linear program, neighboring-committee comparisons, strongest paths, and the final disqualification based on the ordinary Schulze order. The bounded solver computes the common-support optimum through the equivalent subset capacity bound: for each nonempty subset of committee members, supporting voter weight divided by subset size bounds the common attainable support. This is an implementation deduction from the allocation problem, not a replacement voting definition. It then follows the strongest-path and final disqualification stages.

For ordinary STV, the API chooses integer Droop, weighted inclusive Gregory surplus transfers, complete rankings, and fixed priorities. These choices do not assert compliance with any jurisdiction’s election rules. Integer rounding can affect small electorates and replication behavior, so statements for an unrounded theoretical variant are qualified in the criterion entries.

## Random rules and metrics

[Preferential Voting Tools’ probabilistic-method documentation](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html) explains the random-dictatorship primitive and the distinction between distributions and sampled outcomes. The multi-seat extension here is stated independently: draw a voter with replacement for each seat, elect their highest remaining candidate, and prevent duplicate elected candidates. The broad source-table label does not supply a unique multi-seat definition, and single-winner strategyproofness is not silently inherited by this extension.

Uniform committee sortition is implemented by uniform candidate draws without replacement. It provides a nonvoting comparison, not a proportional-representation guarantee.

[Gallagher, Proportionality, Disproportionality and Electoral Systems (1991)](https://www.tcd.ie/Political_Science/about/people/michael_gallagher/ElectoralStudies1991.pdf) discusses vote-seat disproportionality, including the least-squares and absolute-deviation approaches. Those empirical measures need declared vote shares and seat shares. Candidate approval totals do not automatically supply mutually exclusive party vote shares. The [criteria guide](/multi-criteria.md) states the metrics separately from logical guarantees.

## Reading evidence responsibly

A source link can define a rule, define an axiom, provide a theorem, or provide a counterexample; it is not a promise that every source proves every variant. Several simple counting properties in the catalog are deductions: fixed candidate totals yield nested top-k committees; additive committee objectives yield consistency; pairwise matrices determine the two minimax rules. More specialized statements identify their required preference and tie conventions.

An **unverified** entry records a missing exact-variant justification. It should be settled by an applicable theorem, a proof from the stated procedure, or a concrete counterexample. A few passing profiles cannot prove an all-profile claim. A **not-applicable** entry means the implemented input does not express the information or operation needed by the chosen definition; it is not a favorable score.

[Ballot and tie conventions](/multi-ballots.md) and [criterion definitions](/multi-criteria.md) make these boundaries part of the learning resource. The documentation uses [Docapella components](https://docapella.com/components), including code language selectors and explanatory callouts, within the site’s existing presentation.
