"""Hidden grader for t10. Test names start with the requirement (R1..R8) they check."""
import random
import unittest

from exprkit import EvalError, ParseError, evaluate


class HiddenExpr(unittest.TestCase):
    def check(self, cases, variables=None):
        for text, want in cases.items():
            with self.subTest(text=text):
                self.assertEqual(evaluate(text, variables), want)

    def raises(self, exc, texts, variables=None):
        for text in texts:
            with self.subTest(text=text):
                with self.assertRaises(exc):
                    evaluate(text, variables)

    # R1

    def test_r1_literals_and_whitespace(self):
        self.check({"007": 7, " 4 +  5 ": 9, "1\t+\n2": 3, "0": 0, "12345678901234567890 + 1": 12345678901234567891})

    def test_r1_variables(self):
        env = {"x": 3, "y": 4, "_a1": 10, "b_2": -2}
        before = dict(env)
        self.check({"x * y": 12, "_a1 + b_2": 8, "x": 3, "-x": -3}, env)
        self.assertEqual(env, before)

    def test_r1_undefined_variable(self):
        self.raises(EvalError, ["x", "1 + y"], {"x2": 1})
        self.raises(EvalError, ["x"])
        self.raises(EvalError, ["min"])

    # R2

    def test_r2_binary_precedence(self):
        self.check({"1 + 2 * 3 ** 2": 19, "(1 + 2) * 3": 9, "2 * 3 + 4 * 5": 26, "1 + 2 < 4": 1,
                    "1 + 1 == 2 && 3 * 3 == 9": 1, "10 - 2 * 3": 4})

    def test_r2_power_is_right_associative(self):
        self.check({"2 ** 3 ** 2": 512, "(2 ** 3) ** 2": 64, "2 ** 2 ** 3": 256, "3 ** 2 ** 0": 3})

    def test_r2_unary_binds_looser_than_power(self):
        self.check({"-2 ** 2": -4, "(-2) ** 2": 4, "-2 ** 2 * 3": -12, "!2 ** 2": 0, "!0 ** 2": 1,
                    "- -2 ** 2": 4})

    def test_r2_unary_in_exponent(self):
        self.check({"2 ** -0": 1, "2 ** +3": 8, "2 ** !0": 2, "2 ** !1": 1, "2 ** - -3": 8})

    def test_r2_unary_operators(self):
        self.check({"- - 3": 3, "-+-3": 3, "+-3": -3, "-2 * 3": -6, "2 * -3": -6, "2 - -3": 5, "-2 + 3": 1,
                    "!0 + 1": 2, "!1 + 1": 1, "!!7": 1, "-!0": -1, "!0 == 1": 1})

    def test_r2_left_associativity(self):
        self.check({"10 - 4 - 3": 3, "100 / 10 / 5": 2, "100 % 7 % 3": 2, "2 * 3 % 4": 2, "100 / 5 * 2": 40,
                    "1 < 2 == 1": 1, "5 - 3 + 2": 4})

    def test_r2_logical_precedence(self):
        self.check({"1 || 0 && 0": 1, "0 && 1 || 1": 1, "0 || 0 && 1": 0, "1 && 0 || 0": 0,
                    "2 < 3 && 3 < 4": 1, "1 == 1 || 0": 1})

    def test_r2_conditional(self):
        self.check({"1 ? 2 : 3": 2, "0 ? 2 : 3": 3, "0 ? 2 : 1 ? 4 : 5": 4, "0 ? 2 : 0 ? 4 : 5": 5,
                    "1 ? 0 ? 7 : 8 : 9": 8, "1 ? 2 : 0 ? 3 : 4": 2, "1 ? 2 ? 3 : 4 : 5": 3,
                    "0 || 1 ? 5 : 6": 5, "1 + 1 ? 5 : 6": 5, "2 > 1 ? 10 : 20": 10, "1 - 1 ? 5 : 6": 6,
                    "(1 ? 2 : 3) + 10": 12, "1 ? 2 : 3 + 10": 2})

    def test_r2_parentheses(self):
        self.check({"((1))": 1, "(1 + 2) * (3 + 4)": 21, "-(1 + 2)": -3, "2 ** (1 + 1)": 4})

    # R3

    def test_r3_division_truncates_toward_zero(self):
        self.check({"7 / 2": 3, "-7 / 2": -3, "7 / -2": -3, "-7 / -2": 3, "6 / 3": 2, "-6 / 3": -2, "0 / 5": 0,
                    "1 / 2": 0, "-1 / 2": 0})

    def test_r3_remainder_matches_truncation(self):
        self.check({"7 % 2": 1, "-7 % 2": -1, "7 % -2": 1, "-7 % -2": -1, "6 % 3": 0, "-6 % 3": 0, "0 % 4": 0})

    def test_r3_division_identity(self):
        for a in range(-20, 21):
            for b in range(-20, 21):
                if b == 0:
                    continue
                q = abs(a) // abs(b) * (1 if (a < 0) == (b < 0) else -1)
                env = {"a": a, "b": b}
                self.assertEqual(evaluate("a / b", env), q)
                self.assertEqual(evaluate("a % b", env), a - b * q)
                self.assertEqual(evaluate("a / b * b + a % b", env), a)

    def test_r3_division_by_zero(self):
        self.raises(EvalError, ["1 / 0", "1 % 0", "5 / (3 - 3)", "0 / 0", "0 % 0", "-4 % (2 - 2)"])

    # R4

    def test_r4_negative_exponent(self):
        self.raises(EvalError, ["2 ** -1", "1 ** -1", "0 ** -1", "2 ** (0 - 1)"])

    def test_r4_power_values(self):
        self.check({"0 ** 0": 1, "0 ** 5": 0, "2 ** 10": 1024, "(-2) ** 3": -8, "(-2) ** 2": 4, "5 ** 0": 1,
                    "1 ** 100": 1})

    # R5

    def test_r5_comparisons(self):
        self.check({"5 == 5": 1, "5 != 5": 0, "3 <= 3": 1, "3 < 3": 0, "3 >= 4": 0, "4 >= 4": 1, "1 != 2": 1,
                    "-1 < 0": 1, "2 > 3": 0})

    def test_r5_not_operator(self):
        self.check({"!5": 0, "!0": 1, "!-1": 0, "!(1 - 1)": 1, "!!0": 0})

    def test_r5_no_chaining(self):
        self.check({"3 > 2 > 1": 0, "1 < 2 < 3": 1, "2 < 1 < 1": 1, "1 == 1 == 1": 1, "2 == 2 == 2": 0,
                    "3 != 3 != 0": 0})

    # R6

    def test_r6_logical_results_are_zero_or_one(self):
        self.check({"1 && 5": 1, "5 && 7": 1, "0 || 7": 1, "0 || 0": 0, "3 && 0": 0, "0 && 3": 0, "-4 || 0": 1,
                    "9 || 9": 1, "1 && 2 && 0": 0, "0 || 0 || 5": 1})

    def test_r6_short_circuit_and(self):
        self.check({"0 && 1 / 0": 0, "0 && undefined_name": 0, "(0 && 1 / 0) + 1": 1, "0 && 1 / 0 && 1 / 0": 0})
        self.raises(EvalError, ["1 && undefined_name", "1 && 1 / 0"])

    def test_r6_short_circuit_or(self):
        self.check({"1 || 1 / 0": 1, "1 || undefined_name": 1, "0 || 0 || 1 || 1 / 0": 1, "7 || 1 / 0": 1})
        self.raises(EvalError, ["0 || undefined_name", "0 || 1 / 0"])

    def test_r6_left_operand_always_evaluated(self):
        self.raises(EvalError, ["1 / 0 || 1", "1 / 0 && 0", "undefined_name || 1"])

    def test_r6_conditional_evaluates_only_chosen_branch(self):
        self.check({"1 ? 5 : 1 / 0": 5, "0 ? 1 / 0 : 6": 6, "0 ? x : 2": 2, "1 ? 3 : y": 3})
        self.raises(EvalError, ["1 / 0 ? 1 : 2", "1 ? 1 / 0 : 2", "0 ? 1 : 1 / 0"])

    # R7

    def test_r7_min_max_abs(self):
        self.check({"min(3, 1, 2)": 1, "max(3, 1, 2)": 3, "min(5)": 5, "max(-5)": -5, "abs(-4)": 4, "abs(4)": 4,
                    "abs(0)": 0, "max(min(5, 2), abs(-3) ** 2)": 9, "min(1 ? 7 : 8, 9)": 7, "min(1 + 1, 3 - 2)": 1,
                    "-max(1, 2)": -2, "max(1, 2) ** 2": 4, "min( 4 , 5 )": 4})
        self.check({"min(x, 3)": 1, "max(x, y, 0)": 5}, {"x": 1, "y": 5})

    def test_r7_bad_calls(self):
        self.raises(EvalError, ["abs()", "abs(1, 2)", "min()", "max()", "foo(1)", "sqrt(4)", "foo()"])

    def test_r7_bad_calls_are_lazy(self):
        self.check({"1 || foo(2)": 1, "0 && abs()": 0, "0 ? abs() : 3": 3, "1 ? 4 : min()": 4})

    def test_r7_all_arguments_evaluated(self):
        self.raises(EvalError, ["max(1, 1 / 0)", "min(0, 1 / 0)", "min(0, undefined_name)", "abs(1 / 0)"])

    # R8

    def test_r8_error_classes(self):
        self.assertTrue(issubclass(ParseError, EvalError))
        self.assertTrue(issubclass(EvalError, Exception))

    def test_r8_malformed_input(self):
        self.raises(ParseError, [
            "", "   ", "\n", "(1 + 2", "1 + 2)", "1 +", "* 2", "1 + * 2", "()", "!", "- ",
            "1 ? 2", "1 ? 2 :", "1 ? : 2", "1 : 2", "min(1,)", "min(,1)", "min(1 2)", "min(1", "min(1))",
            "1 2", "2x", "x 1", "(1) (2)", "1 = 1", "1 & 2", "1 | 2", "&", "$", "1 + $", "1 # 2", "2 ^ 3", "1.5",
            "1 ** ", "** 2", "1 <", "1 && ", "|| 1",
        ])

    def test_r8_whole_text_is_parsed_before_evaluating(self):
        self.raises(ParseError, ["0 && (1 +", "1 || 2 +", "0 ? 1 : (", "0 ? 1 / 0 : 2 3", "0 && min(1,)"])

    def test_r8_runtime_errors_are_not_parse_errors(self):
        for text in ["1 / 0", "x", "2 ** -1", "foo(1)"]:
            with self.subTest(text=text):
                try:
                    evaluate(text)
                except ParseError:
                    self.fail("runtime error reported as ParseError")
                except EvalError:
                    pass

    # Random check of R2-R7 against a tree model (seeded)

    def test_r2_to_r7_random_expressions(self):
        rng = random.Random(10)
        names = {"a": 3, "b": -4, "c": 0, "d": 7}
        prec = {"?": 0, "||": 1, "&&": 2, "<": 3, "<=": 3, ">": 3, ">=": 3, "==": 3, "!=": 3,
                "+": 4, "-": 4, "*": 5, "/": 5, "%": 5, "u": 6, "**": 7, "atom": 8}

        class Boom(Exception):
            pass

        def gen(depth):
            r = rng.random()
            if depth == 0 or r < 0.2:
                return ("n", rng.randint(0, 9)) if rng.random() < 0.6 else ("v", rng.choice(sorted(names)))
            if r < 0.35:
                return ("u", rng.choice("-+!"), gen(depth - 1))
            if r < 0.4:
                return ("?", gen(depth - 1), gen(depth - 1), gen(depth - 1))
            op = rng.choice(["+", "-", "*", "/", "%", "<", "<=", ">", ">=", "==", "!=", "&&", "||", "**"])
            if op == "**":
                exp = ("n", rng.randint(0, 3))
                if rng.random() < 0.3:
                    exp = ("u", rng.choice("-+!"), exp)
                return ("b", op, gen(depth - 1), exp)
            return ("b", op, gen(depth - 1), gen(depth - 1))

        def ref(t):
            if t[0] == "n":
                return t[1]
            if t[0] == "v":
                return names[t[1]]
            if t[0] == "u":
                v = ref(t[2])
                return -v if t[1] == "-" else v if t[1] == "+" else int(not v)
            if t[0] == "?":
                return ref(t[2]) if ref(t[1]) else ref(t[3])
            op = t[1]
            if op == "&&":
                return int(bool(ref(t[2])) and bool(ref(t[3])))
            if op == "||":
                return int(bool(ref(t[2])) or bool(ref(t[3])))
            a, b = ref(t[2]), ref(t[3])
            if op in ("/", "%"):
                if b == 0:
                    raise Boom
                q = abs(a) // abs(b) * (1 if (a < 0) == (b < 0) else -1)
                return q if op == "/" else a - b * q
            if op == "**":
                if b < 0:
                    raise Boom
                return a ** b
            return {"+": a + b, "-": a - b, "*": a * b, "<": int(a < b), "<=": int(a <= b), ">": int(a > b),
                    ">=": int(a >= b), "==": int(a == b), "!=": int(a != b)}[op]

        def render(t, need):
            if t[0] == "n":
                s, p = str(t[1]), prec["atom"]
            elif t[0] == "v":
                s, p = t[1], prec["atom"]
            elif t[0] == "u":
                s, p = t[1] + render(t[2], prec["u"]), prec["u"]
            elif t[0] == "?":
                s = f"{render(t[1], 1)} ? {render(t[2], 0)} : {render(t[3], 0)}"
                p = 0
            else:
                op = t[1]
                p = prec[op]
                if op == "**":
                    s = f"{render(t[2], prec['atom'])} ** {render(t[3], prec['u'])}"
                else:
                    s = f"{render(t[2], p)} {op} {render(t[3], p + 1)}"
            if p < need or rng.random() < 0.08:
                s = f"({s})"
            return s

        checked = errors = 0
        for _ in range(2500):
            tree = gen(rng.randint(1, 4))
            text = render(tree, 0)
            try:
                want = ref(tree)
            except Boom:
                want = None
            with self.subTest(text=text):
                if want is None:
                    with self.assertRaises(EvalError):
                        evaluate(text, names)
                    errors += 1
                else:
                    self.assertEqual(evaluate(text, names), want)
                checked += 1
        self.assertGreater(errors, 20)
        self.assertEqual(checked, 2500)


if __name__ == "__main__":
    unittest.main()
