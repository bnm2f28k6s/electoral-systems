package multi

// CountApproval validates and counts a approval election.
func CountApproval(request any) (map[string]any, error) {
	return run(request, "approval", countApproval)
}

// CountProportionalApproval validates and counts a proportional-approval election.
func CountProportionalApproval(request any) (map[string]any, error) {
	return run(request, "proportional-approval", countProportionalApproval)
}

// CountSequentialProportionalApproval validates and counts a sequential-proportional-approval election.
func CountSequentialProportionalApproval(request any) (map[string]any, error) {
	return run(request, "sequential-proportional-approval", countSequentialProportionalApproval)
}

// CountReweightedRange validates and counts a reweighted-range election.
func CountReweightedRange(request any) (map[string]any, error) {
	return run(request, "reweighted-range", countReweightedRange)
}

// CountStv validates and counts a stv election.
func CountStv(request any) (map[string]any, error) { return run(request, "stv", countStv) }

// CountCpoStv validates and counts a cpo-stv election.
func CountCpoStv(request any) (map[string]any, error) { return run(request, "cpo-stv", countCpoStv) }

// CountSchulzeStv validates and counts a schulze-stv election.
func CountSchulzeStv(request any) (map[string]any, error) {
	return run(request, "schulze-stv", countSchulzeStv)
}

// CountPhragmen validates and counts a phragmen election.
func CountPhragmen(request any) (map[string]any, error) {
	return run(request, "phragmen", countPhragmen)
}

// CountKBorda validates and counts a k-borda election.
func CountKBorda(request any) (map[string]any, error) { return run(request, "k-borda", countKBorda) }

// CountBloc validates and counts a bloc election.
func CountBloc(request any) (map[string]any, error) { return run(request, "bloc", countBloc) }

// CountQuotaBorda validates and counts a quota-borda election.
func CountQuotaBorda(request any) (map[string]any, error) {
	return run(request, "quota-borda", countQuotaBorda)
}

// CountExpandingApprovals validates and counts a expanding-approvals election.
func CountExpandingApprovals(request any) (map[string]any, error) {
	return run(request, "expanding-approvals", countExpandingApprovals)
}

// CountMinimax validates and counts a minimax election.
func CountMinimax(request any) (map[string]any, error) { return run(request, "minimax", countMinimax) }

// CountMinimaxExternalOpposition validates and counts a minimax-external-opposition election.
func CountMinimaxExternalOpposition(request any) (map[string]any, error) {
	return run(request, "minimax-external-opposition", countMinimaxExternalOpposition)
}

// CountSingleNonTransferable validates and counts a single-non-transferable election.
func CountSingleNonTransferable(request any) (map[string]any, error) {
	return run(request, "single-non-transferable", countSingleNonTransferable)
}

// CountLimitedVote validates and counts a limited-vote election.
func CountLimitedVote(request any) (map[string]any, error) {
	return run(request, "limited-vote", countApproval)
}

// CountCumulative validates and counts a cumulative election.
func CountCumulative(request any) (map[string]any, error) {
	return run(request, "cumulative", countCumulative)
}

// CountSortition validates and counts a sortition election.
func CountSortition(request any) (map[string]any, error) {
	return run(request, "sortition", countSortition)
}

// CountMultipleRandomBallots validates and counts a multiple-random-ballots election.
func CountMultipleRandomBallots(request any) (map[string]any, error) {
	return run(request, "multiple-random-ballots", countMultipleRandomBallots)
}

// Simulate dispatches a multi-winner request to its method-specific counter.
func Simulate(request any) (map[string]any, error) {
	r, ok := request.(map[string]any)
	if !ok {
		return nil, invalid("Request must be an object")
	}
	m, _ := r["method"].(string)
	switch m {
	case "approval":
		return CountApproval(request)
	case "proportional-approval":
		return CountProportionalApproval(request)
	case "sequential-proportional-approval":
		return CountSequentialProportionalApproval(request)
	case "reweighted-range":
		return CountReweightedRange(request)
	case "stv":
		return CountStv(request)
	case "cpo-stv":
		return CountCpoStv(request)
	case "schulze-stv":
		return CountSchulzeStv(request)
	case "phragmen":
		return CountPhragmen(request)
	case "k-borda":
		return CountKBorda(request)
	case "bloc":
		return CountBloc(request)
	case "quota-borda":
		return CountQuotaBorda(request)
	case "expanding-approvals":
		return CountExpandingApprovals(request)
	case "minimax":
		return CountMinimax(request)
	case "minimax-external-opposition":
		return CountMinimaxExternalOpposition(request)
	case "single-non-transferable":
		return CountSingleNonTransferable(request)
	case "limited-vote":
		return CountLimitedVote(request)
	case "cumulative":
		return CountCumulative(request)
	case "sortition":
		return CountSortition(request)
	case "multiple-random-ballots":
		return CountMultipleRandomBallots(request)
	}
	return nil, invalid("Unknown multi-winner method")
}
