"""
Safe evaluator for the Source 2 SmartProp expression language.

SmartProp fields can hold an ``m_Expression`` string such as
``(block_type == 1) ? 16 : 0`` or ``InstanceIndex() * 32``.  Hammer evaluates
these at compile time; the 3D viewport preview needs the same so a bound field
resolves to a real number instead of collapsing to 0.

Design
------
A tiny recursive-descent parser builds an AST, then the AST is walked to produce
a float.  We deliberately do NOT use Python ``eval`` / ``ast.literal_eval`` — the
grammar has C-style operators (``&& || ! ? :``) and named functions that Python
would misparse, and evaluating arbitrary Python would be unsafe.  Only the nodes
below are ever produced, so nothing outside this grammar can execute.

Supported
---------
* literals: numbers, ``true`` / ``false`` / ``pi`` / ``e``
* operators: ``+ - * / %``, unary ``- !``, ``== != < > <= >=``, ``&& || !``,
  ternary ``cond ? a : b``
* member access on vector variables: ``myvec.x`` / ``.y`` / ``.z`` (also r/g/b)
* functions (case-insensitive): abs min max clamp lerp sign
  sin cos tan asin acos atan atan2 sqrt pow floor ceil round
  deg2rad rad2deg (+ Hammer aliases Deg2rad / Rad2deg / Tan / Sin / Cos)
* context functions: InstanceIndex() InstanceCount() RandomInt(a,b)
  RandomFloat(a,b) LinearScale(v,inLo,inHi,outLo,outHi)
* bare names resolve to variable values from the eval context; unknown names -> 0

The public entry point never raises: any parse/eval failure returns ``default``.
"""

import math
import random
import re


class EvalError(Exception):
    """Raised internally for malformed expressions; always caught at the top."""


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------
_WS = re.compile(r"\s+")
_TOKEN = re.compile(
    r"(?P<num>\d+\.\d+|\.\d+|\d+)"
    r"|(?P<id>[A-Za-z_]\w*)"
    r"|(?P<op>\|\||&&|==|!=|<=|>=|[-+*/%<>!?:().,])"
)


def _strip_comments(text):
    """Remove ``//`` line comments (the expression editor permits them)."""
    out = []
    for line in text.splitlines():
        idx = line.find("//")
        if idx != -1:
            line = line[:idx]
        out.append(line)
    return " ".join(out)


def _tokenize(text):
    tokens = []
    pos, n = 0, len(text)
    while pos < n:
        ws = _WS.match(text, pos)
        if ws:
            pos = ws.end()
            continue
        if pos >= n:
            break
        m = _TOKEN.match(text, pos)
        if not m:
            raise EvalError(f"Unexpected character: {text[pos:pos + 8]!r}")
        pos = m.end()
        if m.group("num") is not None:
            tokens.append(("num", float(m.group("num"))))
        elif m.group("id") is not None:
            tokens.append(("id", m.group("id")))
        else:
            tokens.append(("op", m.group("op")))
    tokens.append(("eof", None))
    return tokens


# ---------------------------------------------------------------------------
# Parser -> AST (tuples)
# ---------------------------------------------------------------------------
_MEMBERS = {"x": 0, "y": 1, "z": 2, "w": 3, "r": 0, "g": 1, "b": 2, "a": 3}


class _Parser:
    def __init__(self, tokens):
        self.toks = tokens
        self.i = 0

    def _peek(self):
        return self.toks[self.i]

    def _advance(self):
        t = self.toks[self.i]
        self.i += 1
        return t

    def _accept_op(self, *ops):
        t = self.toks[self.i]
        if t[0] == "op" and t[1] in ops:
            self.i += 1
            return t[1]
        return None

    def _expect_op(self, op):
        if self._accept_op(op) is None:
            raise EvalError(f"Expected '{op}'")

    def parse(self):
        node = self._ternary()
        if self._peek()[0] != "eof":
            raise EvalError("Unexpected trailing tokens")
        return node

    def _ternary(self):
        cond = self._logic_or()
        if self._accept_op("?"):
            a = self._ternary()
            self._expect_op(":")
            b = self._ternary()
            return ("ternary", cond, a, b)
        return cond

    def _logic_or(self):
        node = self._logic_and()
        while self._accept_op("||"):
            node = ("logic", "||", node, self._logic_and())
        return node

    def _logic_and(self):
        node = self._equality()
        while self._accept_op("&&"):
            node = ("logic", "&&", node, self._equality())
        return node

    def _equality(self):
        node = self._relational()
        while True:
            op = self._accept_op("==", "!=")
            if not op:
                return node
            node = ("cmp", op, node, self._relational())

    def _relational(self):
        node = self._additive()
        while True:
            op = self._accept_op("<", ">", "<=", ">=")
            if not op:
                return node
            node = ("cmp", op, node, self._additive())

    def _additive(self):
        node = self._multiplicative()
        while True:
            op = self._accept_op("+", "-")
            if not op:
                return node
            node = ("binop", op, node, self._multiplicative())

    def _multiplicative(self):
        node = self._unary()
        while True:
            op = self._accept_op("*", "/", "%")
            if not op:
                return node
            node = ("binop", op, node, self._unary())

    def _unary(self):
        op = self._accept_op("-", "!", "+")
        if op == "-":
            return ("unary", "-", self._unary())
        if op == "!":
            return ("unary", "!", self._unary())
        if op == "+":
            return self._unary()
        return self._postfix()

    def _postfix(self):
        node = self._primary()
        while self._peek() == ("op", "."):
            self._advance()
            t = self._advance()
            if t[0] != "id":
                raise EvalError("Expected member name after '.'")
            idx = _MEMBERS.get(t[1].lower())
            if idx is None:
                raise EvalError(f"Unknown member .{t[1]}")
            if node[0] != "var":
                raise EvalError("Member access only supported on variables")
            node = ("member", node[1], idx)
        return node

    def _primary(self):
        t = self._peek()
        if t[0] == "num":
            self._advance()
            return ("num", t[1])
        if t[0] == "op" and t[1] == "(":
            self._advance()
            node = self._ternary()
            self._expect_op(")")
            return node
        if t[0] == "id":
            self._advance()
            name = t[1]
            if self._peek() == ("op", "("):
                self._advance()
                args = []
                if self._peek() != ("op", ")"):
                    args.append(self._ternary())
                    while self._accept_op(","):
                        args.append(self._ternary())
                self._expect_op(")")
                return ("call", name, args)
            return ("var", name)
        raise EvalError(f"Unexpected token {t}")


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
class _NullContext:
    """Fallback context used when no EvalContext is supplied."""

    instance_index = 0
    instance_count = 1

    def __init__(self):
        self.rng = random.Random(0)

    def var(self, name):
        return None


def _num(v):
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def _truthy(v):
    if isinstance(v, bool):
        return v
    return _num(v) != 0.0


_CONSTANTS = {"true": 1.0, "false": 0.0, "pi": math.pi, "e": math.e}


def _var_value(ctx, name):
    low = name.lower()
    if low in _CONSTANTS:
        return _CONSTANTS[low]
    v = ctx.var(name)
    if v is None:
        return 0.0
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, (list, tuple)):
        return float(v[0]) if v else 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def _linear_scale(a, ctx=None):
    # LinearScale(value, inLo, inHi, outLo, outHi) -> remap; degrade gracefully.
    # With no args, Source 2 returns the instance's normalized position along the
    # placement (0..1); approximate that from the context's instance index.
    if len(a) >= 5:
        value, in_lo, in_hi, out_lo, out_hi = a[:5]
        if in_hi == in_lo:
            return out_lo
        t = (value - in_lo) / (in_hi - in_lo)
        return out_lo + t * (out_hi - out_lo)
    if len(a) >= 3:
        value, in_lo, in_hi = a[:3]
        if in_hi == in_lo:
            return 0.0
        return (value - in_lo) / (in_hi - in_lo)
    if not a:
        if ctx is not None and ctx.instance_count > 1:
            return ctx.instance_index / (ctx.instance_count - 1)
        return 0.0
    return a[0]


def _make_functions(ctx):
    return {
        # pure math
        "abs": lambda a: abs(a[0]),
        "min": lambda a: min(a) if a else 0.0,
        "max": lambda a: max(a) if a else 0.0,
        "clamp": lambda a: max(a[1], min(a[0], a[2])),
        "lerp": lambda a: a[0] + (a[1] - a[0]) * a[2],
        "sign": lambda a: float((a[0] > 0) - (a[0] < 0)),
        "sqrt": lambda a: math.sqrt(a[0]) if a[0] >= 0 else 0.0,
        "pow": lambda a: math.pow(a[0], a[1]),
        "floor": lambda a: float(math.floor(a[0])),
        "ceil": lambda a: float(math.ceil(a[0])),
        "round": lambda a: float(round(a[0])),
        "sin": lambda a: math.sin(a[0]),
        "cos": lambda a: math.cos(a[0]),
        "tan": lambda a: math.tan(a[0]),
        "asin": lambda a: math.asin(max(-1.0, min(1.0, a[0]))),
        "acos": lambda a: math.acos(max(-1.0, min(1.0, a[0]))),
        "atan": lambda a: math.atan(a[0]),
        "atan2": lambda a: math.atan2(a[0], a[1]),
        "deg2rad": lambda a: math.radians(a[0]),
        "rad2deg": lambda a: math.degrees(a[0]),
        # context-dependent
        "instanceindex": lambda a: float(ctx.instance_index),
        "instancecount": lambda a: float(ctx.instance_count),
        "randomint": lambda a: float(ctx.rng.randint(int(min(a[0], a[1])), int(max(a[0], a[1])))) if len(a) >= 2 else 0.0,
        "randomfloat": lambda a: ctx.rng.uniform(a[0], a[1]) if len(a) >= 2 else 0.0,
        "linearscale": lambda a: _linear_scale(a, ctx),
    }


def _eval_node(node, ctx, funcs):
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "var":
        return _var_value(ctx, node[1])
    if kind == "member":
        v = ctx.var(node[1])
        if isinstance(v, (list, tuple)):
            return float(v[node[2]]) if node[2] < len(v) else 0.0
        if isinstance(v, bool):
            return 1.0 if v else 0.0
        if isinstance(v, (int, float)):
            return float(v)  # a scalar broadcasts to any component (uniform)
        return 0.0
    if kind == "unary":
        val = _eval_node(node[2], ctx, funcs)
        if node[1] == "-":
            return -_num(val)
        return 0.0 if _truthy(val) else 1.0  # '!'
    if kind == "binop":
        a = _num(_eval_node(node[2], ctx, funcs))
        b = _num(_eval_node(node[3], ctx, funcs))
        op = node[1]
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            return a / b if b != 0 else 0.0
        if op == "%":
            return math.fmod(a, b) if b != 0 else 0.0
        raise EvalError(f"Unknown operator {op}")
    if kind == "cmp":
        a = _num(_eval_node(node[2], ctx, funcs))
        b = _num(_eval_node(node[3], ctx, funcs))
        op = node[1]
        res = {
            "==": a == b, "!=": a != b,
            "<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b,
        }[op]
        return 1.0 if res else 0.0
    if kind == "logic":
        if node[1] == "&&":
            return 1.0 if (_truthy(_eval_node(node[2], ctx, funcs)) and
                           _truthy(_eval_node(node[3], ctx, funcs))) else 0.0
        # '||' — short-circuit
        if _truthy(_eval_node(node[2], ctx, funcs)):
            return 1.0
        return 1.0 if _truthy(_eval_node(node[3], ctx, funcs)) else 0.0
    if kind == "ternary":
        if _truthy(_eval_node(node[1], ctx, funcs)):
            return _eval_node(node[2], ctx, funcs)
        return _eval_node(node[3], ctx, funcs)
    if kind == "call":
        fn = funcs.get(node[1].lower())
        if fn is None:
            raise EvalError(f"Unknown function {node[1]}")
        args = [_num(_eval_node(a, ctx, funcs)) for a in node[2]]
        try:
            return fn(args)
        except (IndexError, ValueError, ZeroDivisionError):
            return 0.0
    raise EvalError(f"Unknown node {kind}")


# Cache parsed ASTs — the same expression strings are evaluated every paint.
_AST_CACHE = {}
_AST_CACHE_MAX = 512


def _parse_cached(text):
    node = _AST_CACHE.get(text)
    if node is None:
        node = _Parser(_tokenize(text)).parse()
        if len(_AST_CACHE) >= _AST_CACHE_MAX:
            _AST_CACHE.clear()
        _AST_CACHE[text] = node
    return node


def evaluate_expression(expr, ctx=None, default=0.0):
    """Evaluate a SmartProp expression to a float. Never raises.

    ``ctx`` is an EvalContext (or anything exposing ``var(name)``,
    ``instance_index``, ``instance_count`` and ``rng``).  On any failure the
    ``default`` is returned.
    """
    if expr is None:
        return float(default)
    if isinstance(expr, bool):
        return 1.0 if expr else 0.0
    if isinstance(expr, (int, float)):
        return float(expr)
    text = _strip_comments(str(expr)).strip()
    if text == "":
        return float(default)
    context = ctx if ctx is not None else _NullContext()
    try:
        node = _parse_cached(text)
        funcs = _make_functions(context)
        value = _eval_node(node, context, funcs)
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        return float(value)
    except EvalError:
        return float(default)
    except Exception:
        # Defensive: nothing from the paint loop should ever crash the viewport.
        return float(default)
