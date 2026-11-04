"""Independent multi-winner examples, published oracles, and validation checks."""
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from multi_winner import (ElectionError, METHODS, cpo_support, droop_fraction,
                          schulze_strength, simulate)


def election(method, ballots, seats=2, candidates=None, **options):
    return simulate({"method": method, "candidates": candidates or list("ABC"),
                     "seats": seats, "ballots": ballots, "options": options})


class MultiCountingTests(unittest.TestCase):
    def test_ranked_rules_have_independently_calculated_results(self):
        ballots = [{"ranking": list("ABC"), "count": 2}, {"ranking": list("CBA"), "count": 1}]
        for method, expected in {
            "k-borda": list("AB"), "bloc": list("AB"), "single-non-transferable": list("AC"),
            "minimax": list("AB"), "minimax-external-opposition": list("AB"),
            "stv": list("AC"), "quota-borda": list("AB"), "expanding-approvals": list("AB"),
        }.items():
            with self.subTest(method=method):
                self.assertEqual(election(method, ballots)["winners"], expected)
        self.assertEqual(election("k-borda", ballots)["trace"][0]["tally"], {"A": 4, "B": 3, "C": 2})

    def test_approval_rules_differ_from_global_optimization(self):
        # A attracts six approvals. Choosing it first is myopic: the B,C pair
        # serves every voter, with PAV utility 10 versus A,B utility 9.5.
        ballots = [{"approvals": list("AB"), "count": 3}, {"approvals": list("AC"), "count": 3},
                   {"approvals": ["B"], "count": 2}, {"approvals": ["C"], "count": 2}]
        exact = election("proportional-approval", ballots)
        sequential = election("sequential-proportional-approval", ballots)
        self.assertEqual(exact["winners"], list("BC"))
        self.assertEqual(exact["trace"][0]["bestScore"], 10)
        self.assertEqual(sequential["winners"], list("AB"))
        self.assertEqual(sequential["trace"][1]["tally"], {"B": 3.5, "C": 3.5})
        self.assertTrue(sequential["tie"])
        self.assertFalse(exact["tie"])

    def test_additive_and_reweighted_approval_profiles(self):
        ballots = [{"approvals": list("AB"), "count": 3}, {"approvals": ["C"], "count": 2}]
        self.assertEqual(election("approval", ballots)["winners"], list("AB"))
        for method in ["proportional-approval", "sequential-proportional-approval", "phragmen"]:
            self.assertEqual(election(method, ballots)["winners"], list("AC"))
        phragmen = election("phragmen", ballots)
        self.assertAlmostEqual(phragmen["trace"][0]["loadLevels"]["A"], 1/3)
        self.assertEqual(phragmen["trace"][1]["loadLevels"]["C"], .5)
        self.assertAlmostEqual(phragmen["trace"][1]["loadLevels"]["B"], 2/3)

    def test_reweighted_range_uses_score_divisor(self):
        ballots = [{"scores": {"A": 5, "B": 5, "C": 0}, "count": 3},
                   {"scores": {"A": 0, "B": 0, "C": 5}, "count": 2}]
        counted = election("reweighted-range", ballots)
        self.assertEqual(counted["winners"], list("AC"))
        self.assertEqual(counted["trace"][1]["weights"], [.5, 1])
        self.assertEqual(counted["trace"][1]["tally"], {"B": 7.5, "C": 10})

    def test_limited_and_cumulative_votes(self):
        self.assertEqual(election("limited-vote", [{"approvals": ["A"], "count": 3}, {"approvals": ["C"], "count": 2}])["winners"], list("AC"))
        self.assertEqual(election("cumulative", [{"votes": {"A": 6, "B": 4, "C": 0}}, {"votes": {"A": 0, "B": 3, "C": 7}}], budget=10)["winners"], list("BC"))

    def test_simpson_and_external_opposition_are_distinct(self):
        # The paper's unanimous x>y>z example: Simpson's bottom scores tie,
        # whereas external opposition identifies the actual top-two set.
        ballots = [{"ranking": list("ABC")}]
        simpson = election("minimax", ballots)
        external = election("minimax-external-opposition", ballots)
        self.assertEqual(simpson["trace"][1]["simpsonScores"], {"A": 1, "B": 0, "C": 0})
        self.assertTrue(simpson["tie"])
        self.assertEqual(external["winners"], list("AB"))
        self.assertFalse(external["tie"])

    def test_stv_inclusive_gregory_transfer(self):
        ballots = [{"ranking": list("ABC"), "count": 6}, {"ranking": list("CAB"), "count": 4}]
        counted = election("stv", ballots)
        self.assertEqual(counted["winners"], list("AC"))
        self.assertEqual(counted["trace"][0]["quota"], 4)
        self.assertEqual(counted["trace"][1]["tally"], {"A": 6, "B": 0, "C": 4})
        self.assertAlmostEqual(counted["trace"][1]["transferFactor"], 1/3)
        self.assertEqual(counted["trace"][2]["tally"], {"B": 2, "C": 4})

    def test_cpo_transfers_only_common_candidates(self):
        ballots = [{"ranking": list("ABC"), "count": 6}, {"ranking": list("CAB"), "count": 4}]
        # Compare AB to AC: common A retains quota4 and transfers its surplus2
        # to B. Scores therefore AB=6 and AC=8, not AB=6 and AC=10.
        self.assertEqual(cpo_support(list("ABC"), ballots, list("AB"), list("AC"), 4), (6, 8))
        self.assertEqual(election("cpo-stv", ballots)["winners"], list("AC"))

    def test_cpo_records_common_transfer_ties(self):
        ballots = [{"ranking": list("ABCDE"), "count": 4},
                   {"ranking": list("BACDE"), "count": 4},
                   {"ranking": list("CDEAB"), "count": 1}]
        counted = election("cpo-stv", ballots, seats=3, candidates=list("ABCDE"))
        self.assertTrue(counted["trace"][0]["comparisonTies"])
        self.assertTrue(counted["tie"])
        row = counted["trace"][0]["comparisonTies"][0]
        self.assertEqual(row["decisions"][0], {"candidates": list("AB"), "selected": "A"})

    def test_schulze_published_630_voter_example(self):
        # Schulze (2011), section6.3, pp38-42: every listed edge strength and
        # final unique committee provide an oracle external to our code.
        rows = [(60,"abcde"),(45,"acebd"),(30,"adbec"),(15,"aedcb"),
                (12,"baedc"),(48,"bcdea"),(39,"bdace"),(21,"becad"),
                (27,"cadbe"),(9,"cbaed"),(51,"cdeab"),(33,"cebda"),
                (42,"daceb"),(18,"dbeca"),(6,"dcbae"),(54,"deabc"),
                (57,"eabcd"),(36,"ebdac"),(24,"ecadb"),(3,"edcba")]
        ballots = [{"ranking": list(order), "count": count} for count, order in rows]
        expected = [("abc","d",169),("abc","e",152),("abd","c",162),("abd","e",159),
                    ("abe","c",168),("abe","d",153),("acd","b",158),("acd","e",163),
                    ("ace","b",164),("ace","d",157),("ade","b",167),("ade","c",154),
                    ("bcd","a",141),("bcd","e",165),("bce","a",146),("bce","d",160),
                    ("bde","a",151),("bde","c",155),("cde","a",156),("cde","b",150)]
        for committee, outsider, value in expected:
            self.assertEqual(schulze_strength(committee, outsider, ballots), value)
        counted = election("schulze-stv", ballots, 3, list("abcde"))
        self.assertEqual(counted["winners"], list("ade"))
        self.assertFalse(counted["tie"])
        self.assertEqual(counted["trace"][0]["strongestPaths"][0][5], 163)

    def test_schulze_final_disqualification_is_applied(self):
        ballots = [{"ranking": list("ABDC"), "count": 1}, {"ranking": list("BADC"), "count": 3}, {"ranking": list("DCBA"), "count": 2}]
        counted = election("schulze-stv", ballots, candidates=list("ABCD"))
        self.assertEqual(counted["trace"][0]["stageTwoCommittees"], [list("AB"), list("BD")])
        self.assertEqual(counted["trace"][0]["tiedCommittees"], [list("AB")])
        self.assertFalse(counted["tie"])

    def test_schulze_support_matches_independent_fractional_max_flow(self):
        def feasible(committee, outsider, ballots, target):
            n = len(ballots)
            sink = 1+n+len(committee)
            residual = [[Fraction(0) for _ in range(sink+1)] for _ in range(sink+1)]
            for i, b in enumerate(ballots):
                residual[0][i+1] = b["count"]
                for j, candidate in enumerate(committee):
                    if b["ranking"].index(candidate) < b["ranking"].index(outsider):
                        residual[i+1][1+n+j] = b["count"]
            for j in range(len(committee)):
                residual[1+n+j][sink] = target
            flow = Fraction(0)
            while True:
                previous = {0: None}
                queue = [0]
                for node in queue:
                    for nxt, capacity in enumerate(residual[node]):
                        if capacity > 0 and nxt not in previous:
                            previous[nxt] = node
                            queue.append(nxt)
                if sink not in previous:
                    return flow == len(committee)*target
                node, amount = sink, None
                while previous[node] is not None:
                    parent = previous[node]
                    amount = residual[parent][node] if amount is None else min(amount, residual[parent][node])
                    node = parent
                node = sink
                while previous[node] is not None:
                    parent = previous[node]
                    residual[parent][node] -= amount
                    residual[node][parent] += amount
                    node = parent
                flow += amount
        generator = random.Random(215)
        for _ in range(50):
            ballots = [{"ranking": generator.sample(list("ABCD"), 4), "count": generator.randint(1,3)} for _ in range(3)]
            committee = list("ABC")
            strength = schulze_strength(committee, "D", ballots)
            self.assertTrue(feasible(committee, "D", ballots, strength))
            self.assertFalse(feasible(committee, "D", ballots, strength+Fraction(1, 100)))

    def test_ranked_proportional_rules_satisfy_their_coalition_demands(self):
        generator = random.Random(66)
        for method in ["quota-borda", "expanding-approvals"]:
            for _ in range(80):
                c = list("ABCDE")[:generator.randint(2,5)]
                seats = generator.randint(1,len(c))
                ballots = [{"ranking": generator.sample(c,len(c)), "count": generator.randint(1,5)} for _ in range(generator.randint(1,8))]
                counted = election(method, ballots, seats, c)
                quota = droop_fraction(sum(b["count"] for b in ballots), seats)
                for size in range(1,len(c)+1):
                    for group in itertools.combinations(c,size):
                        supporters = sum(b["count"] for b in ballots if set(b["ranking"][:size]) == set(group))
                        demand = min(size, int(Fraction(supporters)/quota))
                        self.assertGreaterEqual(len(set(group)&set(counted["winners"])), demand)
                self.assertEqual(len(counted["winners"]), seats)

    def test_random_methods_share_the_documented_lcg_sequence(self):
        sortition = election("sortition", [], candidates=list("ABCD"), seed=1)
        self.assertEqual(sortition["winners"], list("AC"))
        self.assertEqual([x["state"] for x in sortition["trace"]], [1015568748, 1586005467])
        ballots = [{"ranking": list("ABCD"), "count": 6}, {"ranking": list("CDAB"), "count": 3}, {"ranking": list("DCBA")}]
        self.assertEqual(election("multiple-random-ballots", ballots, candidates=list("ABCD"))["winners"], list("AB"))

    def test_zero_approvals_do_not_divide_by_zero(self):
        counted = election("phragmen", [{"approvals": []}])
        self.assertEqual(counted["winners"], list("AB"))
        self.assertTrue(counted["tie"])
        self.assertEqual(counted["trace"][0]["loadLevels"], {"A": None, "B": None, "C": None})
        json.dumps(counted, allow_nan=False)

    def test_full_and_single_candidate_committees(self):
        for candidates in [["A"], list("ABC")]:
            for method in METHODS:
                if method == "sortition":
                    ballots = []
                elif method in {"approval", "proportional-approval", "sequential-proportional-approval", "phragmen"}:
                    ballots = [{"approvals": candidates}]
                elif method == "limited-vote":
                    ballots = [{"approvals": [candidates[0]]}]
                elif method == "reweighted-range":
                    ballots = [{"scores": dict.fromkeys(candidates, 5)}]
                elif method == "cumulative":
                    ballots = [{"votes": dict.fromkeys(candidates, 1)}]
                else:
                    ballots = [{"ranking": candidates}]
                with self.subTest(method=method, candidates=candidates):
                    counted = election(method, ballots, len(candidates), candidates)
                    self.assertEqual(counted["winners"], candidates)

    def test_weighted_profiles_equal_expansion(self):
        for method in METHODS:
            if method == "sortition":
                continue
            if method in {"approval", "proportional-approval", "sequential-proportional-approval", "phragmen", "limited-vote"}:
                ballots = [{"approvals": ["A"], "count": 3}, {"approvals": ["B"], "count": 2}]
            elif method == "reweighted-range":
                ballots = [{"scores": {"A": 5, "B": 2, "C": 0}, "count": 3}, {"scores": {"A": 0, "B": 3, "C": 5}, "count": 2}]
            elif method == "cumulative":
                ballots = [{"votes": {"A": 5, "B": 2, "C": 0}, "count": 3}, {"votes": {"A": 0, "B": 3, "C": 5}, "count": 2}]
            else:
                ballots = [{"ranking": list("ABC"), "count": 3}, {"ranking": list("CBA"), "count": 2}]
            expanded = [{k:v for k,v in b.items() if k != "count"} for b in ballots for _ in range(b["count"])]
            grouped, individual = election(method, ballots), election(method, expanded)
            self.assertEqual(grouped["winners"], individual["winners"])
            self.assertEqual(grouped["tie"], individual["tie"])

    def test_validation_and_explicit_computation_caps(self):
        valid = {"method": "k-borda", "candidates": list("ABC"), "seats": 2,
                 "ballots": [{"ranking": list("ABC")}]}
        for value in [None, {}, {**valid,"seats":0}, {**valid,"seats":4}, {**valid,"seats":True},
                      {**valid,"method":[]}, {**valid,"ballots":[]}, {**valid,"candidates":["A","A"]},
                      {**valid,"ballots":[{"ranking":list("AB")}]},
                      {**valid,"ballots":[{"ranking":list("ABC"),"count":True}]},
                      {**valid,"options":{"seed":float("nan")}}, {**valid,"options":{"limit":0}},
                      {**valid,"options":{"unknown":1}}, {**valid,"options":None},
                      {**valid,"method":"limited-vote","ballots":[{"approvals":list("AB")}]},
                      {**valid,"method":"cumulative","ballots":[{"votes":{"A":100,"B":1,"C":0}}]},
                      {**valid,"method":"reweighted-range","ballots":[{"scores":{"A":6,"B":1,"C":0}}]}]:
            with self.subTest(value=value), self.assertRaises(ElectionError):
                simulate(value)
        for method, n in [("proportional-approval",9),("minimax-external-opposition",9),("cpo-stv",7),("schulze-stv",7)]:
            c = [str(i) for i in range(n)]
            ballots = [{"approvals": c}] if method == "proportional-approval" else [{"ranking": c}]
            with self.assertRaises(ElectionError) as error:
                election(method, ballots, candidates=c)
            self.assertEqual(error.exception.status, 413)

    def test_cli_executes_and_rejects_nonfinite_json(self):
        request = {"method":"single-non-transferable","candidates":["A","B"],"seats":1,"ballots":[{"choice":"A","count":1.0}],"options":{"seed":1.0}}
        executed = subprocess.run([sys.executable,str(ROOT/"python/multi_winner.py")],input=json.dumps(request),capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(executed.stdout)["winners"],["A"])
        invalid = subprocess.run([sys.executable,str(ROOT/"python/multi_winner.py")],input='{"method": NaN}',capture_output=True,text=True)
        self.assertEqual(invalid.returncode,1)
        self.assertIn("finite",json.loads(invalid.stderr)["error"])


if __name__ == "__main__":
    unittest.main()
