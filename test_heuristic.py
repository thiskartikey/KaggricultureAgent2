import unittest
import math
import heuristic

class TestHeuristicUnit(unittest.TestCase):

    def test_price_calculation(self):
        """Test market price function for all products."""
        for prod in heuristic.PRODUCTS:
            p_i0 = heuristic.price(prod, 10000)
            base_p = heuristic.MARKET_PARAMS[prod][0]
            self.assertEqual(p_i0, base_p, f"Price at I0 for {prod} should equal base price")
            
            p_low = heuristic.price(prod, 1000)
            self.assertGreaterEqual(p_low, base_p, f"Price below I0 for {prod} should be >= base price")
            
            p_high = heuristic.price(prod, 20000)
            self.assertLessEqual(p_high, base_p, f"Price above I0 for {prod} should be <= base price")

    def test_sell_and_buy_cost(self):
        """Test sell revenue and buy cost functions."""
        rev, inv2 = heuristic.sell_revenue("WHEAT", 10000, 5)
        self.assertGreater(rev, 0)
        self.assertEqual(inv2, 10005)

        cost, inv3 = heuristic.buy_cost("WHEAT", 10000, 5)
        self.assertGreater(cost, 0)
        self.assertEqual(inv3, 9995)

    def test_hire_cost_fibonacci(self):
        """Test worker hiring cost progression."""
        self.assertEqual(heuristic.hire_cost(0), 1)
        self.assertEqual(heuristic.hire_cost(1), 1)
        self.assertEqual(heuristic.hire_cost(2), 2)
        self.assertEqual(heuristic.hire_cost(3), 3)
        self.assertEqual(heuristic.hire_cost(4), 5)
        self.assertEqual(heuristic.hire_cost(5), 8)

    def test_movement_helpers(self):
        """Test Manhattan distance and step direction."""
        self.assertEqual(heuristic.manhattan((0, 0), (3, 4)), 7)
        self.assertEqual(heuristic.step_toward((0, 0), (3, 0)), "EAST")
        self.assertEqual(heuristic.step_toward((3, 0), (0, 0)), "WEST")
        self.assertEqual(heuristic.step_toward((0, 0), (0, 4)), "SOUTH")
        self.assertEqual(heuristic.step_toward((0, 4), (0, 0)), "NORTH")

    def test_day0_hour1_opening_playbook(self):
        """Test Day 0 Hour 1 macro execution in _make_market_orders."""
        dummy_tiles = [[None for _ in range(10)] for _ in range(10)]
        obs = {
            "player": 0,
            "day": 0,
            "hour": 0,
            "farms": [{
                "money": 3000,
                "unlocked_quadrants": ["NW"],
                "tiles": dummy_tiles,
                "hires_today": 0,
                "hands": []
            }],
            "private": {"shed": {}, "seeds": {}},
            "market": {"inventory": {}}
        }
        orders = heuristic._make_market_orders(obs, player=0)
        expected_orders = [
            ["HIRE"],
            ["HIRE"],
            ["HIRE"],
            ["HIRE"],
            ["HIRE"],
            ["BUY_ANIMAL", "COW", 2],
            ["BUY_ANIMAL", "SHEEP", 2],
            ["BUY_SEED", "MELON", 11],
            ["BUY_SEED", "WHEAT", 7],
            ["BUY_PRODUCT", "WHEAT", 8],
        ]
        self.assertEqual(orders, expected_orders, "Day 0 Hour 0 should execute opening playbook")

    def test_agent_fallback_on_exception(self):
        """Test agent fallback to default pass action on invalid input."""
        res = heuristic.agent({"corrupted": True})
        self.assertEqual(res, {"farmer": ["PASS"], "hands": [], "market": []})

if __name__ == "__main__":
    unittest.main()
