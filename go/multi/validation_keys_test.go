package multi

import "testing"

func TestUnknownKeysCannotCombineAllowedNames(t *testing.T) {
	for _, test := range []struct{ target, key string }{
		{"request", "method|candidates"},
		{"request", "method|candidates|seats"},
		{"options", "maxScore|budget"},
		{"options", "limit|seed"},
		{"ballot", "ranking|approvals"},
		{"ballot", "votes|count"},
	} {
		t.Run(test.target+"/"+test.key, func(t *testing.T) {
			request := decode(t, `{"method":"bloc","candidates":["A","B"],"seats":1,"ballots":[{"ranking":["A","B"]}]}`).(map[string]any)
			switch test.target {
			case "request":
				request[test.key] = true
			case "options":
				request["options"] = map[string]any{test.key: 1}
			case "ballot":
				request["ballots"].([]any)[0].(map[string]any)[test.key] = true
			}
			_, err := Simulate(request)
			election, ok := err.(*ElectionError)
			if !ok || election.Status != 400 {
				t.Fatalf("accepted unknown %s key %q: %v", test.target, test.key, err)
			}
		})
	}
}
