"""Independent examples, criterion checks, exact-search and HTTP regressions."""
from collections import deque
import http.client
import importlib.util
import itertools
import json
from pathlib import Path
import random
import sys
import threading
import unittest
from http.server import HTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from electoral import ElectionError, METHODS, simulate, smith_set
from server import Handler


CANDIDATES = ["A", "B", "C"]
PROFILE = [
    {"ranking": ["A", "B", "C"], "count": 3},
    {"ranking": ["B", "C", "A"], "count": 2},
    {"ranking": ["C", "B", "A"], "count": 2},
]


def ranked(method, ballots=None, candidates=None, **options):
    return simulate({"method": method, "candidates": candidates or CANDIDATES,
                     "ballots": PROFILE if ballots is None else ballots, "options": options})


class CountingTests(unittest.TestCase):
    def test_all_ranked_methods_have_independent_known_winners(self):
        expected = {
            "plurality": ["A"], "anti-plurality": ["B"], "two-round": ["B"],
            "instant-runoff": ["B"], "coombs": ["B"], "nanson": ["B"],
            "baldwin": ["B"], "tideman-alternative": ["B"], "minimax": ["B"],
            "copeland": ["B"], "black": ["B"], "kemeny-young": ["B"],
            "ranked-pairs": ["B"], "schulze": ["B"], "borda": ["B"],
            "bucklin": ["B"], "dodgson": ["B"], "maximal-lotteries": ["B"],
        }
        for method, winners in expected.items():
            with self.subTest(method=method):
                response = ranked(method)
                self.assertEqual(response["winners"], winners)
                self.assertFalse(response["tie"])
                self.assertTrue(response["trace"])
        self.assertEqual(ranked("borda")["trace"][0]["tally"], {"A": 6, "B": 9, "C": 6})

    def test_cardinal_rules(self):
        for method, ballots, expected in [
            ("approval", [{"approvals": ["A", "B"], "count": 2}, {"approvals": ["B", "C"]}], ["B"]),
            ("score", [{"scores": {"A": 5, "B": 4, "C": 0}, "count": 2}, {"scores": {"A": 0, "B": 5, "C": 3}}], ["B"]),
            ("star", [{"scores": {"A": 5, "B": 4, "C": 0}, "count": 2}, {"scores": {"A": 0, "B": 5, "C": 3}}], ["A"]),
            ("quadratic", [{"credits": {"A": 3, "B": 2, "C": -1}}, {"credits": {"A": -3, "B": 1, "C": 0}}], ["B"]),
            ("majority-judgment", [{"scores": {"A": 5, "B": 4, "C": 0}, "count": 2}, {"scores": {"A": 0, "B": 5, "C": 3}}], ["A"]),
        ]:
            with self.subTest(method=method):
                self.assertEqual(ranked(method, ballots)["winners"], expected)

    def test_ties_remain_ties(self):
        ballots = [{"ranking": ["A", "B"]}, {"ranking": ["B", "A"]}]
        for method in ["plurality", "anti-plurality", "two-round", "instant-runoff", "coombs", "nanson", "baldwin", "tideman-alternative", "minimax", "copeland", "black", "kemeny-young", "ranked-pairs", "schulze", "borda", "bucklin", "dodgson"]:
            with self.subTest(method=method):
                value = ranked(method, ballots, ["A", "B"])
                self.assertEqual(value["winners"], ["A", "B"])
                self.assertTrue(value["tie"])

    def test_equal_intermediate_counts_do_not_end_elimination(self):
        ballots = [{"ranking": list(order)} for order in ["ABC", "BAC", "CAB"]]
        # A and B are both above C on two of the three ballots.
        # Returning all first-round ties would wrongly admit C.
        self.assertEqual(ranked("instant-runoff", ballots)["winners"], ["A"])
        self.assertEqual(ranked("instant-runoff", ballots)["trace"][0]["eliminated"], ["C"])

    def test_smith_closure_matches_independent_subset_oracle(self):
        generator = random.Random(5812)
        for n in range(1, 6):
            candidates = list("ABCDE"[:n])
            for _ in range(100):
                matrix = {x: dict.fromkeys(candidates, 0) for x in candidates}
                for x, y in itertools.combinations(candidates, 2):
                    matrix[x][y] = generator.randrange(7)
                    matrix[y][x] = 6-matrix[x][y]
                oracle = None
                for size in range(1, n+1):
                    for subset in itertools.combinations(candidates, size):
                        if all(matrix[x][y] > matrix[y][x] for x in subset for y in candidates if y not in subset):
                            oracle = list(subset)
                            break
                    if oracle is not None:
                        break
                self.assertEqual(smith_set(candidates, matrix), oracle)

    def test_dodgson_scores_match_full_adjacent_swap_bfs(self):
        # This oracle allows every adjacent swap of every candidate, rather
        # than assuming that promoting the candidate suffices as the DP does.
        orders = list(itertools.permutations(CANDIDATES))
        for profile in itertools.combinations_with_replacement(orders, 3):
            pending = deque([(profile, 0)])
            visited = {profile}
            costs = {}
            while pending and len(costs) < 3:
                state, distance = pending.popleft()
                for x in CANDIDATES:
                    if x not in costs and all(x == y or sum(r.index(x) < r.index(y) for r in state) >= 2 for y in CANDIDATES):
                        costs[x] = distance
                for voter in range(3):
                    for position in range(2):
                        order = list(state[voter])
                        order[position], order[position+1] = order[position+1], order[position]
                        changed = state[:voter] + (tuple(order),) + state[voter+1:]
                        if changed not in visited:
                            visited.add(changed)
                            pending.append((changed, distance+1))
            ballots = [{"ranking": list(order)} for order in profile]
            self.assertEqual(ranked("dodgson", ballots)["trace"][1]["adjacentSwaps"], costs)

    def test_maximal_lottery_nonuniform_cycle(self):
        ballots = [{"ranking": list("ABC"), "count": 2},
                   {"ranking": list("BCA"), "count": 2},
                   {"ranking": list("CAB"), "count": 1}]
        value = ranked("maximal-lotteries", ballots)
        self.assertEqual(value["lottery"], [{"candidate": "A", "probability": .6},
                                           {"candidate": "B", "probability": .2},
                                           {"candidate": "C", "probability": .2}])

    def test_nonterminal_elimination_ties_use_input_priority(self):
        value = ranked("instant-runoff")
        self.assertEqual(value["trace"][0]["eliminated"], ["C"])

    def test_runoff_ties_preserve_original_candidate_order(self):
        # B leads the qualifying score but A and B tie head-to-head.
        scores = [{"scores": {"A": 1, "B": 5, "C": 0}},
                  {"scores": {"A": 2, "B": 0, "C": 0}}]
        self.assertEqual(ranked("star", scores)["winners"], ["A", "B"])
        ballots = [{"ranking": ["B", "A", "C"], "count": 3},
                   {"ranking": ["A", "B", "C"], "count": 2},
                   {"ranking": ["C", "A", "B"]}]
        self.assertEqual(ranked("two-round", ballots)["winners"], ["A", "B"])

    def test_dodgson_scores_are_strict_condorcet_swap_counts(self):
        value = ranked("dodgson", [{"ranking": ["A", "B", "C"], "count": 2}])
        self.assertEqual(value["trace"][1]["adjacentSwaps"], {"A": 0, "B": 2, "C": 4})

    def test_exact_kemeny_cycle_and_dodgson_cycle(self):
        cycle = [{"ranking": ["A", "B", "C"]}, {"ranking": ["B", "C", "A"]}, {"ranking": ["C", "A", "B"]}]
        self.assertEqual(ranked("kemeny-young", cycle)["winners"], CANDIDATES)
        self.assertEqual(ranked("kemeny-young", cycle)["trace"][1]["bestScore"], 5)
        self.assertEqual(ranked("dodgson", cycle)["trace"][1]["adjacentSwaps"], dict.fromkeys(CANDIDATES, 1))
        lottery = ranked("maximal-lotteries", cycle)["lottery"]
        for row in lottery:
            self.assertAlmostEqual(row["probability"], 1/3)

    def test_condorcet_rules_on_all_three_voter_profiles(self):
        orders = list(itertools.permutations(CANDIDATES))
        methods = ["nanson", "baldwin", "tideman-alternative", "minimax", "copeland", "black", "kemeny-young", "ranked-pairs", "schulze", "dodgson", "maximal-lotteries"]
        for profile in itertools.combinations_with_replacement(orders, 3):
            cw = [x for x in CANDIDATES if all(x == y or sum(order.index(x) < order.index(y) for order in profile) >= 2 for y in CANDIDATES)]
            if cw:
                ballots = [{"ranking": list(order)} for order in profile]
                for method in methods:
                    with self.subTest(profile=profile, method=method):
                        self.assertEqual(ranked(method, ballots)["winners"], cw)

    def test_majority_judgment_optimized_removal_matches_naive(self):
        generator = random.Random(312)
        for _ in range(1000):
            n = generator.randint(1, 15)
            columns = {x: sorted(generator.choices(range(6), k=n)) for x in CANDIDATES}
            ballots = [{"scores": {x: columns[x][i] for x in CANDIDATES}} for i in range(n)]
            active = CANDIDATES[:]
            remaining = {x: a[:] for x, a in columns.items()}
            while remaining[active[0]]:
                medians = {x: remaining[x][(len(remaining[x])-1)//2] for x in active}
                high = max(medians.values())
                active = [x for x in active if medians[x] == high]
                if len(active) == 1:
                    break
                for x in active:
                    remaining[x].pop((len(remaining[x])-1)//2)
            self.assertEqual(ranked("majority-judgment", ballots)["winners"], active)

    def test_weighted_ballots_equal_expansion(self):
        expanded = [{"ranking": b["ranking"]} for b in PROFILE for _ in range(b["count"])]
        for method in ["borda", "instant-runoff", "copeland", "dodgson", "maximal-lotteries"]:
            self.assertEqual(ranked(method), ranked(method, expanded))

    def test_seeded_random_rules(self):
        for method, ballots in [("sortition", []), ("random-ballot", PROFILE)]:
            first = ranked(method, ballots, seed=1)
            self.assertEqual(first, ranked(method, ballots, seed=1))
            self.assertEqual(first["winners"], ["A"])
            self.assertAlmostEqual(sum(x["probability"] for x in first["lottery"]), 1)

    def test_one_candidate_every_method(self):
        for method in METHODS:
            if method == "sortition":
                ballots = []
            elif method == "approval":
                ballots = [{"approvals": ["A"]}]
            elif method in {"score", "star", "majority-judgment"}:
                ballots = [{"scores": {"A": 5}}]
            elif method == "quadratic":
                ballots = [{"credits": {"A": 1}}]
            else:
                ballots = [{"ranking": ["A"]}]
            self.assertEqual(ranked(method, ballots, ["A"])["winners"], ["A"])

    def test_integral_json_numbers_are_normalized(self):
        floats = [{"scores": {"A": 5.0, "B": 4.0, "C": 0.0}, "count": 2.0}]
        value = ranked("majority-judgment", floats, maxScore=5.0, seed=1.0, budget=100.0)
        self.assertEqual(value["winners"], ["A"])
        self.assertEqual(ranked("random-ballot", [{"choice": "A", "count": 1.0}], seed=1.0)["winners"], ["A"])

    def test_invalid_inputs_and_resource_guards(self):
        valid = {"method": "borda", "candidates": CANDIDATES, "ballots": PROFILE}
        invalid = [None, {}, {**valid, "method": []}, {**valid, "candidates": ["A", "A"]},
                   {**valid, "ballots": [{"ranking": ["A", "B"]}]},
                   {**valid, "ballots": [{"ranking": CANDIDATES, "count": True}]},
                   {**valid, "ballots": [{"choice": "A"}]},
                   {**valid, "options": {"seed": -1}},
                   {**valid, "unknown": True},
                   {"method": "score", "candidates": CANDIDATES, "ballots": [{"scores": {"A": 0, "B": 1, "C": 6}}]},
                   {"method": "quadratic", "candidates": ["A"], "ballots": [{"credits": {"A": 11}}]}]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ElectionError):
                simulate(value)
        with self.assertRaises(ElectionError) as error:
            ranked("dodgson", [{"ranking": CANDIDATES, "count": 9}])
        self.assertEqual(error.exception.status, 413)


class QuietHandler(Handler):
    body_timeout = 0.05

    def log_message(self, *args):
        pass


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        status, data = response.status, json.loads(response.read())
        connection.close()
        return status, data

    def test_discovery_and_simulation(self):
        status, data = self.request("GET", "/systems")
        self.assertEqual(status, 200)
        self.assertEqual(set(data["methods"]), set(METHODS))
        request = {"method": "borda", "candidates": CANDIDATES, "ballots": PROFILE}
        status, data = self.request("POST", "/simulate", json.dumps(request), {"Content-Type": "application/json"})
        self.assertEqual(status, 200)
        self.assertEqual(data, simulate(request))

    def test_incomplete_request_body_times_out_as_json(self):
        status, data = self.request("POST", "/simulate", "{}", {"Content-Type": "application/json", "Content-Length": "10"})
        self.assertEqual(status, 408)
        self.assertEqual(data, {"error": "Request body timed out"})

    def test_json_errors_and_http_statuses(self):
        self.assertEqual(self.request("POST", "/simulate", "{", {"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.request("POST", "/simulate", '{"unexpected":NaN}', {"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.request("POST", "/simulate", "["*1100+"]"*1100, {"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.request("POST", "/simulate", "{}", {"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("GET", "/absent")[0], 404)
        self.assertEqual(self.request("POST", "/absent", "{}")[0], 404)
        self.assertEqual(self.request("POST", "/simulate", "{}", {"Content-Type": "application/json", "Content-Length": str(1024*1024+1)})[0], 413)


if __name__ == "__main__":
    unittest.main()
