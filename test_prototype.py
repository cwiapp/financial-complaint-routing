import unittest

from prototype import PRODUCTS, normalize, route, score


class PrototypeTests(unittest.TestCase):
    def test_normalize_whitespace_and_case(self):
        self.assertEqual(normalize(" Credit\n CARD  "), "credit card")

    def test_nonstring_input_rejected(self):
        with self.assertRaises(TypeError):
            route(None)

    def test_empty_text_to_review(self):
        self.assertEqual(route("  \n ")["reason"], "empty_text")

    def test_short_text_to_review(self):
        self.assertEqual(route("credit card")["reason"], "too_short")

    def test_long_text_to_review(self):
        self.assertEqual(route("mortgage " * 3000)["reason"], "too_long")

    def test_debt_route(self):
        result = route("A debt collector called me repeatedly about a debt I do not owe.")
        self.assertEqual(result["product"], PRODUCTS[0])
        self.assertEqual(result["status"], "auto")

    def test_credit_reporting_route(self):
        result = route("My credit report from Experian shows a wrong account.")
        self.assertEqual(result["product"], PRODUCTS[5])

    def test_checking_route(self):
        self.assertEqual(route("My checking account was blocked without any warning.")["product"], PRODUCTS[1])

    def test_credit_card_route(self):
        self.assertEqual(route("The credit card issuer charged an incorrect fee.")["product"], PRODUCTS[2])

    def test_transfer_route(self):
        self.assertEqual(route("My wire transfer was never delivered to the recipient.")["product"], PRODUCTS[3])

    def test_mortgage_route(self):
        self.assertEqual(route("The mortgage servicer mishandled my monthly payment.")["product"], PRODUCTS[4])

    def test_word_boundaries(self):
        self.assertEqual(route("The cardholder was unable to contact the support office.")["reason"], "no_rule_match")

    def test_ambiguous_route_to_review(self):
        result = route("My mortgage and debt are both listed incorrectly.")
        self.assertEqual(result["reason"], "ambiguous")

    def test_no_rule_match_to_review(self):
        self.assertEqual(route("I cannot resolve this problem with the company.")["reason"], "no_rule_match")

    def test_evaluation_rejects_empty_set(self):
        with self.assertRaises(ValueError):
            score([])


if __name__ == "__main__":
    unittest.main()
