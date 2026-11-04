# Single-winner method catalog

Choose a rule by the information voters provide and the counting steps you want to understand. Every method below has a worked example, complete Python, TypeScript, and Go, all 25 criterion entries, and an executable API request.

Coverage follows every method row in the [starting comparison](https://en.wikipedia.org/wiki/Comparison_of_electoral_systems#Compliance_of_selected_single-winner_methods), including random selection and the specified quadratic demonstration. This is a coverage map, not a ranking of methods.

| Method | Ballot | Basic idea |
| --- | --- | --- |
| [Plurality (first past the post)](/methods/plurality.md) | choice or ranking | Each voter supports one candidate. The largest total wins, even when that total is below half. |
| [Anti-plurality (veto)](/methods/anti-plurality.md) | choice or ranking | Each voter vetoes one candidate. The candidate with the fewest vetoes wins. A veto is opposition, not support. |
| [Two-round system](/methods/two-round.md) | ranking | First choose the two leaders by first preferences. If nobody already has a majority, compare those finalists. |
| [Instant-runoff voting (IRV)](/methods/instant-runoff.md) | ranking | Voters rank candidates. Remove the candidate with least current first-choice support and transfer those ballots to their next remaining choice. |
| [Coombs’ method](/methods/coombs.md) | ranking | Keep a candidate who has a first-choice majority; otherwise remove the candidate most voters rank last. |
| [Nanson’s method](/methods/nanson.md) | ranking | Repeatedly remove candidates whose Borda points are at or below the current average. |
| [Baldwin’s method](/methods/baldwin.md) | ranking | Repeatedly remove the candidate with the fewest Borda points, recalculating points after each removal. |
| [Tideman alternative (Smith)](/methods/tideman-alternative.md) | ranking | Alternate between restricting the field to its Smith set and eliminating the candidate with least first-choice support. |
| [Minimax (margins)](/methods/minimax.md) | ranking | Judge each candidate by their worst head-to-head defeat. Prefer the candidate whose worst defeat is smallest. |
| [Copeland](/methods/copeland.md) | ranking | Give each candidate a point for a head-to-head win and half a point for a tie. The largest total wins. |
| [Black’s method](/methods/black.md) | ranking | Choose a candidate who beats every rival head-to-head; if nobody does, use Borda points. |
| [Kemeny–Young](/methods/kemeny-young.md) | ranking | Find a full social ranking that agrees with as many voter pairwise comparisons as possible. Its first candidate wins. |
| [Ranked pairs](/methods/ranked-pairs.md) | ranking | Consider stronger head-to-head victories first. Keep a victory unless it would create a directed cycle. |
| [Schulze (beatpaths)](/methods/schulze.md) | ranking | A path from A to B is as strong as its weakest victory. Compare the strongest available path in each direction. |
| [Borda count](/methods/borda.md) | ranking | Ranked positions earn points, so a broadly acceptable candidate can defeat the first-choice leader. |
| [Bucklin voting](/methods/bucklin.md) | ranking | Expand the number of ranked positions counted until somebody reaches a strict majority, then prefer the largest cumulative total. |
| [Dodgson’s method](/methods/dodgson.md) | ranking | Count the fewest adjacent ranking swaps needed to turn each candidate into a Condorcet winner. Prefer the smallest swap count. |
| [Approval voting](/methods/approval.md) | approvals | Approve any subset of candidates. Every approval is one point; the largest total wins. |
| [Majority judgment](/methods/majority-judgment.md) | scores | Use each candidate’s middle grade rather than their average. Break equal middle grades by repeatedly removing one occurrence of that grade. |
| [Score voting (range voting)](/methods/score.md) | scores | Voters grade every candidate on a common bounded scale. The largest sum wins. |
| [STAR voting](/methods/star.md) | scores | Use scores to choose two finalists, then count which finalist each voter scored higher. |
| [Quadratic voting (credit budget)](/methods/quadratic.md) | credits | A voter may cast multiple signed voice votes, paying the square of each amount from a fixed personal budget. Sum voice votes to select the winner. |
| [Random ballot (random dictatorship)](/methods/random-ballot.md) | choice or ranking | Choose a voter uniformly at random and elect that voter’s first choice. A ballot group with count 5 represents five opportunities, not one. |
| [Maximal lotteries](/methods/maximal-lotteries.md) | ranking | Turn majority margins into a zero-sum game. Choose probabilities that cannot be beaten in expected pairwise margin by any rival lottery. |
| [Sortition (uniform candidate lottery)](/methods/sortition.md) | none | Choose a candidate uniformly, without using ballots. This comparison baseline is not a vote aggregation rule. |

Read [ballot formats](/ballots.md) and [criteria](/criteria.md) to understand the assumptions behind comparisons. [Sources](/sources.md) explain the research boundaries.
