# Sources and scope

The [Wikipedia comparison](https://en.wikipedia.org/wiki/Comparison_of_electoral_systems#Compliance_of_selected_single-winner_methods) supplies the coverage checklist: 25 rows spanning single-mark, ranked, graded, credit-budget and lottery methods. Sortition is included as its nonvoting baseline. Multiwinner systems and empirical utility rankings are outside these single-winner counting chapters.

The site uses original explanations, synthetic examples and self-contained implementations. The comparison is a starting map, not a copied specification. Its incomplete cells, ballot assumptions and distinctions between related variants require further checking. Each chapter names the precise implemented variant, cites its definitions and lists every criterion with an explanation or explicit research limit.

## Definitions and reference implementations

[Preferential Voting Tools](https://pref-voting.readthedocs.io/en/stable/) is maintained as an academic voting-method library. Its documentation provides definitions and inspectable source code, including tie-handling distinctions. Our implementations do not import that package, and matching a method’s name does not imply matching every library default.

- [Positional scoring rules](https://pref-voting.readthedocs.io/en/stable/scoring_methods.html): score-vector definitions for plurality, anti-plurality and Borda.
- [Iterative methods](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html): elimination procedures, Nanson and Baldwin variants, and repeated Smith restriction.
- [Pairwise majority methods](https://pref-voting.readthedocs.io/en/stable/c1_methods.html): Copeland scores and majority-dominant candidate sets.
- [Margin methods](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html): minimax and graph-based pairwise rules.
- [Combined methods](https://pref-voting.readthedocs.io/en/stable/combined_methods.html): Black’s Condorcet-then-Borda rule.
- [Other methods](https://pref-voting.readthedocs.io/en/stable/other_methods.html): consensus ranking and cumulative-ranking rules.
- [Probabilistic methods](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html): random dictatorship and the distinction between a lottery and a sampled outcome.
- [Axiom documentation](https://pref-voting.readthedocs.io/en/stable/axioms_overview.html): definitions and violation-check interfaces; these are not proofs that our code passes every property.

## Research and original method sources

| Source | What it helps establish |
| --- | --- |
| [Freeman, Brill and Conitzer, On the Axiomatic Characterization of Runoff Voting Rules (2014)](https://www.cs.cmu.edu/~arielpro/comsoc-14/papers/FreemanBrillConitzer2014.pdf) | Formal elimination rules and the distinction between scoring-based runoff procedures. |
| [Narodytska, Walsh and Xia, Manipulation of Nanson’s and Baldwin’s Rules (2011)](https://ojs.aaai.org/index.php/AAAI/article/view/7872) | The Borda elimination family and manipulation complexity. Difficulty manipulating a rule is separate from difficulty counting it. |
| [Schulze, The Schulze Method of Voting (2018)](https://arxiv.org/abs/1804.02973) | Beatpath construction and proofs concerning monotonicity, clones, reversal symmetry, Condorcet consistency and counting. |
| [Tideman, Independence of Clones as a Criterion for Voting Rules (1987)](https://www.condorcet.vote/assets/DOCS/IndependenceofClones.pdf) | The clone criterion and its role in IRV and ranked pairs. |
| [Zavist and Tideman, Complete Independence of Clones in the Ranked Pairs Rule (1989)](https://www.condorcet.vote/assets/DOCS/CompleteIndependenceofClones.pdf) | Why ranked-pairs clone guarantees depend on the handling of tied victories. |
| [Brandt, Some Remarks on Dodgson’s Voting Rule](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf) | Counterexamples to appealing guarantees sometimes assumed for the exact Dodgson rule. |
| [Caragiannis et al., Dodgson’s Rule Approximations and Absurdity (2010)](https://drops.dagstuhl.de/storage/00lipics/lipics-vol008-fsttcs2010/LIPIcs.FSTTCS.2010.459/LIPIcs.FSTTCS.2010.459.pdf) | Integer adjacent-swap distance and the distinction from fractional or homogeneous approximations. |
| [Balinski and Laraki, A Theory of Measuring, Electing, and Ranking (2007)](https://doi.org/10.1073/pnas.0702634104) | The grading model underlying majority judgment. Grade distributions are different information from strict rankings. |
| [Lalley and Weyl, Quadratic Voting](https://bfi.uchicago.edu/working-paper/quadratic-voting/) | Quadratic vote costs and the original binary vote-purchase model. The equal-budget, multiple-candidate example here states its additional assumptions. |
| [Brandl, Brandt and Seedig, Consistent Probabilistic Social Choice (2016)](https://arxiv.org/abs/1503.00694) | Maximal lotteries as symmetric zero-sum-game strategies, lottery consistency and efficient general computation. |
| [Brandt, Geist and Peters, Optimal Bounds for the No-Show Paradox via SAT Solving (2016)](https://arxiv.org/abs/1602.08063) | Why Condorcet consistency and participation cannot both be promised on an unrestricted domain. Bounds depend on the precise outcome convention. |
| [Woodall, Monotonicity and Single-Seat Election Rules (1996)](https://www.votingmatters.org.uk/issue6/P4.HTM) | Original definitions of later-no-harm, later-no-help and related monotonicity properties. |
| [Small, Geometric Construction of Voting Methods That Protect Voters’ First Choices (2010)](https://arxiv.org/abs/1008.4331) | Favorite-betrayal variants, including the distinction between allowing equal top preferences and requiring a unique favorite. |
| [Handbook of Computational Social Choice (2016)](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf) | Broader definitions, relationships between rules, and counting-complexity context. |

The [official STAR Voting instructions](https://www.starvoting.org/) define the score-then-runoff procedure, and its [FAQ](https://www.starvoting.org/faq) describes precinct summaries. The demonstration follows the core count but uses the published candidate priority for finalist ties; it does not claim to implement the complete official tiebreak protocol.

## How to interpret claims

Most descriptions explain what the included code does, using elementary tally reasoning. For example, adding two sets of score totals preserves positive score margins, and restricted Borda totals can be reconstructed from pairwise support. These are deductions from the formulas, not empirical performance claims.

A result about complete strict rankings does not automatically extend to tied or incomplete ballots. A statement about absolute grades does not establish independence if voters rescale those grades after candidates enter. A result about a lottery correspondence does not automatically hold for one arbitrary selector or one pseudorandom sample. A final tie also needs an outcome preference before a participation claim is meaningful.

“Unverified” in a chapter records a missing exact-variant justification. It should be resolved using a proof, a concrete counterexample, or a directly applicable source rather than inferred from nearby methods or a handful of successful tests. The [criteria guide](/criteria.md) explains these qualifications and gives executable-size counterexamples to common misconceptions.

## Documentation components

The site keeps Docapella’s existing layout. [Docapella’s component reference](https://docapella.com/components) supplies `CodeSelect` for Python/TypeScript examples and callouts for assumptions that readers need before running a count. Components support the explanations; they do not implement or host the API.
