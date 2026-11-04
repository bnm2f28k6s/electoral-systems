# Multi-winner method catalog

A committee has a fixed number of seats. Some rules select the highest individual totals; others try to represent groups with different preferences. Electing several candidates does not automatically make a rule proportional.

This catalog covers all 19 rows in the [starting comparison's multi-winner table](https://en.wikipedia.org/wiki/Comparison_of_electoral_systems#Criterion_tables), with precise counting variants, executable Python and TypeScript, and API requests. The [criteria guide](/multi-criteria.md) explains every comparison criterion, distinctions between committee preferences, and the additional approval-representation criteria used here.

| Method | Ballot | Basic idea |
| --- | --- | --- |
| [Multi-winner approval voting](/multi-methods/approval.md) | approvals | Count support for each candidate independently and elect the k largest totals. This maximizes total approved representatives, not proportional representation. |
| [Proportional approval voting (PAV)](/multi-methods/proportional-approval.md) | approvals | Evaluate whole committees using diminishing returns: a voter gets 1 point for a first approved representative, another 1/2 for a second, another 1/3 for a third, and so on. |
| [Sequential proportional approval voting](/multi-methods/sequential-proportional-approval.md) | approvals | Fill seats one at a time. An approval from a voter already represented by t elected candidates counts as 1/(t+1). |
| [Reweighted range voting](/multi-methods/reweighted-range.md) | scores | Elect a high-scoring candidate, then reduce the influence of ballots that gave strong scores to candidates already elected. |
| [Single transferable vote (STV)](/multi-methods/stv.md) | ranking | Voters rank candidates. Quota winners retain enough vote weight for a seat, surplus weight transfers, and the lowest remaining candidate is eliminated when nobody reaches quota. |
| [CPO-STV](/multi-methods/cpo-stv.md) | ranking | Compare possible committees after transferring surplus votes of candidates common to both. Use those committee contests to resolve the election. |
| [Schulze STV](/multi-methods/schulze-stv.md) | ranking | Compare committees that differ by one candidate using balanced voter support. Strongest paths through the committee graph resolve indirect comparisons. |
| [Phragmén’s sequential rule](/multi-methods/phragmen.md) | approvals | Each elected candidate carries one unit of representation load. Share that load among approving voters while keeping the maximum voter load as small as possible at each step. |
| [k-Borda](/multi-methods/k-borda.md) | ranking | Award m−1 points for first place, m−2 for second, down to zero for last. Elect the k candidates with the largest totals. |
| [Bloc voting](/multi-methods/bloc.md) | ranking | Each voter supports their first k candidates. Count those marks independently and elect the k greatest totals. |
| [Quota Borda system (QBS)](/multi-methods/quota-borda.md) | ranking | Find groups that agree on the same top set, satisfy their proportional seat demands, and use Borda points to choose which candidates represent them. |
| [Expanding approvals rule (EAR)](/multi-methods/expanding-approvals.md) | ranking | Temporarily approve short ranking prefixes. Elect sufficiently supported candidates, spend part of their supporters’ weight, and expand the prefix when more support is needed. |
| [Multi-winner minimax (Simpson)](/multi-methods/minimax.md) | ranking | Give each candidate their weakest head-to-head support count, then elect the k candidates with the highest such scores. |
| [Minimax minimal size of external opposition](/multi-methods/minimax-external-opposition.md) | ranking | Score a whole committee by its weakest member-versus-outsider support. Choose the committee with the strongest weakest external contest. |
| [Single non-transferable vote (SNTV)](/multi-methods/single-non-transferable.md) | choice or ranking | Each voter supports one candidate, and the k highest first-choice totals win. Unused support does not transfer. |
| [Limited voting](/multi-methods/limited-vote.md) | approvals | Each voter may mark fewer candidates than seats. The largest candidate mark totals win, leaving voters fewer marks than a full bloc ballot. |
| [Cumulative voting](/multi-methods/cumulative.md) | votes | Each voter has a budget of positive votes and may concentrate several on the same candidate. Elect the k largest vote totals. |
| [Multi-winner sortition](/multi-methods/sortition.md) | none | Select a uniformly random size-k subset of the candidate list. Voter preferences do not affect selection. |
| [Multiple random ballots](/multi-methods/multiple-random-ballots.md) | ranking | For each seat, sample a voter and elect that ballot’s highest-ranked candidate not already elected. Repeating the draw can represent different voter groups without guaranteeing proportionality. |

Start with [bloc voting](/multi-methods/bloc.md) and [single non-transferable vote](/multi-methods/single-non-transferable.md), then compare [STV](/multi-methods/stv.md) and [proportional approval](/multi-methods/proportional-approval.md). Read the [ballot guide](/multi-ballots.md) before running a count, or return to the [single-winner catalog](/methods.md).
