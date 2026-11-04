package single

// Simulate validates and dispatches a JSON-decoded election request.
func Simulate(request any) (map[string]any, error) {
	r, ok := request.(map[string]any)
	if !ok {
		return nil, invalid("Request must be an object")
	}
	method, _ := r["method"].(string)
	switch method {
	case "plurality":
		return CountPlurality(request)
	case "anti-plurality":
		return CountAntiPlurality(request)
	case "two-round":
		return CountTwoRound(request)
	case "instant-runoff":
		return CountInstantRunoff(request)
	case "coombs":
		return CountCoombs(request)
	case "nanson":
		return CountNanson(request)
	case "baldwin":
		return CountBaldwin(request)
	case "tideman-alternative":
		return CountTidemanAlternative(request)
	case "minimax":
		return CountMinimax(request)
	case "copeland":
		return CountCopeland(request)
	case "black":
		return CountBlack(request)
	case "kemeny-young":
		return CountKemenyYoung(request)
	case "ranked-pairs":
		return CountRankedPairs(request)
	case "schulze":
		return CountSchulze(request)
	case "borda":
		return CountBorda(request)
	case "bucklin":
		return CountBucklin(request)
	case "dodgson":
		return CountDodgson(request)
	case "approval":
		return CountApproval(request)
	case "majority-judgment":
		return CountMajorityJudgment(request)
	case "score":
		return CountScore(request)
	case "star":
		return CountStar(request)
	case "quadratic":
		return CountQuadratic(request)
	case "random-ballot":
		return CountRandomBallot(request)
	case "maximal-lotteries":
		return CountMaximalLotteries(request)
	case "sortition":
		return CountSortition(request)
	}
	return nil, invalid("Unknown method")
}

// CountPlurality counts a validated plurality request.
func CountPlurality(request any) (map[string]any, error) { return run(request, "plurality", plurality) }

// CountAntiPlurality counts a validated anti-plurality request.
func CountAntiPlurality(request any) (map[string]any, error) {
	return run(request, "anti-plurality", antiPlurality)
}

// CountTwoRound counts a validated two-round request.
func CountTwoRound(request any) (map[string]any, error) { return run(request, "two-round", twoRound) }

// CountInstantRunoff counts a validated instant-runoff request.
func CountInstantRunoff(request any) (map[string]any, error) {
	return run(request, "instant-runoff", instantRunoff)
}

// CountCoombs counts a validated coombs request.
func CountCoombs(request any) (map[string]any, error) { return run(request, "coombs", coombs) }

// CountNanson counts a validated nanson request.
func CountNanson(request any) (map[string]any, error) { return run(request, "nanson", nanson) }

// CountBaldwin counts a validated baldwin request.
func CountBaldwin(request any) (map[string]any, error) { return run(request, "baldwin", baldwin) }

// CountTidemanAlternative counts a validated tideman-alternative request.
func CountTidemanAlternative(request any) (map[string]any, error) {
	return run(request, "tideman-alternative", tidemanAlternative)
}

// CountMinimax counts a validated minimax request.
func CountMinimax(request any) (map[string]any, error) { return run(request, "minimax", minimax) }

// CountCopeland counts a validated copeland request.
func CountCopeland(request any) (map[string]any, error) { return run(request, "copeland", copeland) }

// CountBlack counts a validated black request.
func CountBlack(request any) (map[string]any, error) { return run(request, "black", black) }

// CountKemenyYoung counts a validated kemeny-young request.
func CountKemenyYoung(request any) (map[string]any, error) {
	return run(request, "kemeny-young", kemenyYoung)
}

// CountRankedPairs counts a validated ranked-pairs request.
func CountRankedPairs(request any) (map[string]any, error) {
	return run(request, "ranked-pairs", rankedPairs)
}

// CountSchulze counts a validated schulze request.
func CountSchulze(request any) (map[string]any, error) { return run(request, "schulze", schulze) }

// CountBorda counts a validated borda request.
func CountBorda(request any) (map[string]any, error) { return run(request, "borda", borda) }

// CountBucklin counts a validated bucklin request.
func CountBucklin(request any) (map[string]any, error) { return run(request, "bucklin", bucklin) }

// CountDodgson counts a validated dodgson request.
func CountDodgson(request any) (map[string]any, error) { return run(request, "dodgson", dodgson) }

// CountApproval counts a validated approval request.
func CountApproval(request any) (map[string]any, error) { return run(request, "approval", approval) }

// CountMajorityJudgment counts a validated majority-judgment request.
func CountMajorityJudgment(request any) (map[string]any, error) {
	return run(request, "majority-judgment", majorityJudgment)
}

// CountScore counts a validated score request.
func CountScore(request any) (map[string]any, error) { return run(request, "score", score) }

// CountStar counts a validated star request.
func CountStar(request any) (map[string]any, error) { return run(request, "star", star) }

// CountQuadratic counts a validated quadratic request.
func CountQuadratic(request any) (map[string]any, error) { return run(request, "quadratic", quadratic) }

// CountRandomBallot counts a validated random-ballot request.
func CountRandomBallot(request any) (map[string]any, error) {
	return run(request, "random-ballot", randomBallot)
}

// CountMaximalLotteries counts a validated maximal-lotteries request.
func CountMaximalLotteries(request any) (map[string]any, error) {
	return run(request, "maximal-lotteries", maximalLotteries)
}

// CountSortition counts a validated sortition request.
func CountSortition(request any) (map[string]any, error) { return run(request, "sortition", sortition) }
