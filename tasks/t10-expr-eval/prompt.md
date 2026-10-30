`exprkit.evaluate(text, variables=None)` evaluates a small integer expression language. Today it only
handles `+ - * /` and parentheses, and it gets some of those wrong. Extend and fix it to meet this
spec. All values are Python `int`s.

**Syntax**

R1. Literals are non-negative decimal integers (`0`, `42`, `007` is 7). Whitespace between tokens is
    ignored. Identifiers (`[A-Za-z_][A-Za-z0-9_]*`) are variables, looked up in the `variables` dict
    (values are ints; the dict is never modified). An undefined variable raises `EvalError`.
R2. Operators, from tightest to loosest binding:

    1. `**` (power)
    2. unary `-`, unary `+`, `!`
    3. `*`, `/`, `%`
    4. binary `+`, `-`
    5. `<`, `<=`, `>`, `>=`, `==`, `!=`
    6. `&&`
    7. `||`
    8. `cond ? a : b`

    Parentheses group. Binary operators at levels 3 to 7 are left-associative. `**` is
    right-associative, and its right operand may carry a unary operator, so `2 ** 3 ** 2` is 512 and
    `2 ** -0` is 1. Because unary operators bind looser than `**`, `-2 ** 2` is -4. The conditional
    is right-associative: `a ? b : c ? d : e` means `a ? b : (c ? d : e)`.

**Meaning**

R3. `/` truncates toward zero (`-7 / 2` is -3). `%` is the matching remainder, so `a == (a / b) * b +
    a % b` always holds and `-7 % 2` is -1, `7 % -2` is 1. Division or remainder by zero raises
    `EvalError`.
R4. `a ** b` with `b < 0` raises `EvalError`. `0 ** 0` is 1.
R5. Comparisons and `!` produce 1 or 0. `!x` is 1 if `x` is 0, else 0. Comparisons are left-associative
    like any other binary operator, with no chaining: `3 > 2 > 1` is `(3 > 2) > 1`, which is 0.
R6. `&&` and `||` treat any non-zero value as true and always produce 1 or 0. They short-circuit: the
    right operand is not evaluated if the left one decides the result, so `0 && 1 / 0` is 0 and
    `1 || undefined_name` is 1. In `c ? a : b` only the chosen branch is evaluated.
R7. Calls: `min(a, b, ...)` and `max(a, b, ...)` take one or more arguments, `abs(x)` takes exactly one.
    All arguments of a call are evaluated. Calling an unknown function, or a known one with a wrong
    number of arguments, raises `EvalError` when that call is evaluated (so `1 || foo(2)` is 1).

**Errors**

R8. `ParseError` is a subclass of `EvalError`, and both are exported from `exprkit`. Malformed input
    raises `ParseError`: empty or blank text, unbalanced parentheses, a missing operand, a missing `:`
    in a conditional, an empty argument in a call (`min(1,)`), leftover tokens (`1 2`), or a character
    that is not part of the language (`1 = 1`, `&`, `$`). The whole text is parsed before anything is
    evaluated, so `0 && (1 +` raises `ParseError`, not 0.

Standard library only. Existing tests are in `tests/`.
