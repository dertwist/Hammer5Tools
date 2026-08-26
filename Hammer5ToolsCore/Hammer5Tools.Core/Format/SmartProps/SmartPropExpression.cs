namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Evaluates the numeric SmartProp expression subset used by preview fields.
/// </summary>
public static class SmartPropExpression
{
    /// <summary>
    /// Evaluates an expression, returning <paramref name="defaultValue"/> when it is malformed.
    /// </summary>
    public static float Evaluate(string? expression, SmartPropContext? context = null, float defaultValue = 0.0f)
    {
        if (string.IsNullOrWhiteSpace(expression))
            return defaultValue;

        try
        {
            return new Parser(expression, context ?? new SmartPropContext()).Parse();
        }
        catch (InvalidOperationException)
        {
            return defaultValue;
        }
    }

    private sealed class Parser(string expression, SmartPropContext context)
    {
        private readonly Lexer Lexer = new(expression);
        private Token Token;

        public float Parse()
        {
            Token = Lexer.Next();
            var value = ParseTernary(true);
            Expect(TokenKind.End);
            return value;
        }

        private float ParseTernary(bool evaluate)
        {
            var condition = ParseOr(evaluate);
            if (!Accept("?"))
                return condition;

            var conditionIsTrue = evaluate && IsTrue(condition);
            var whenTrue = ParseTernary(conditionIsTrue);
            Expect(":");
            var whenFalse = ParseTernary(evaluate && !conditionIsTrue);
            return conditionIsTrue ? whenTrue : whenFalse;
        }

        private float ParseOr(bool evaluate)
        {
            var value = ParseAnd(evaluate);
            while (Accept("||"))
            {
                var valueIsTrue = evaluate && IsTrue(value);
                var right = ParseAnd(evaluate && !valueIsTrue);
                value = evaluate && (valueIsTrue || IsTrue(right)) ? 1.0f : 0.0f;
            }
            return value;
        }

        private float ParseAnd(bool evaluate)
        {
            var value = ParseComparison(evaluate);
            while (Accept("&&"))
            {
                var valueIsTrue = evaluate && IsTrue(value);
                var right = ParseComparison(evaluate && valueIsTrue);
                value = evaluate && valueIsTrue && IsTrue(right) ? 1.0f : 0.0f;
            }
            return value;
        }

        private float ParseComparison(bool evaluate)
        {
            var value = ParseAdditive(evaluate);
            while (Token.Value is "==" or "!=" or "<" or ">" or "<=" or ">=")
            {
                var operation = Token.Value;
                Next();
                var right = ParseAdditive(evaluate);
                value = !evaluate ? 0.0f : operation switch
                {
                    "==" => value == right ? 1.0f : 0.0f,
                    "!=" => value != right ? 1.0f : 0.0f,
                    "<" => value < right ? 1.0f : 0.0f,
                    ">" => value > right ? 1.0f : 0.0f,
                    "<=" => value <= right ? 1.0f : 0.0f,
                    _ => value >= right ? 1.0f : 0.0f,
                };
            }
            return value;
        }

        private float ParseAdditive(bool evaluate)
        {
            var value = ParseMultiplicative(evaluate);
            while (Token.Value is "+" or "-")
            {
                var operation = Token.Value;
                Next();
                var right = ParseMultiplicative(evaluate);
                value = !evaluate ? 0.0f : operation == "+" ? value + right : value - right;
            }
            return value;
        }

        private float ParseMultiplicative(bool evaluate)
        {
            var value = ParseUnary(evaluate);
            while (Token.Value is "*" or "/" or "%")
            {
                var operation = Token.Value;
                Next();
                var right = ParseUnary(evaluate);
                value = !evaluate ? 0.0f : operation switch
                {
                    "*" => value * right,
                    "/" when right != 0.0f => value / right,
                    "%" when right != 0.0f => value % right,
                    _ => 0.0f,
                };
            }
            return value;
        }

        private float ParseUnary(bool evaluate)
        {
            if (Accept("-"))
                return -ParseUnary(evaluate);
            if (Accept("+"))
                return ParseUnary(evaluate);
            if (Accept("!"))
            {
                var value = ParseUnary(evaluate);
                return evaluate && !IsTrue(value) ? 1.0f : 0.0f;
            }
            return ParsePrimary(evaluate);
        }

        private float ParsePrimary(bool evaluate)
        {
            if (Token.Kind == TokenKind.Number)
            {
                var value = float.Parse(Token.Value, System.Globalization.CultureInfo.InvariantCulture);
                Next();
                return evaluate ? value : 0.0f;
            }

            if (Accept("("))
            {
                var value = ParseTernary(evaluate);
                Expect(")");
                return value;
            }

            if (Token.Kind != TokenKind.Identifier)
                throw new InvalidOperationException();

            var name = Token.Value;
            Next();
            if (Accept("("))
                return Call(name, evaluate);

            if (Accept("."))
            {
                if (Token.Kind != TokenKind.Identifier)
                    throw new InvalidOperationException();

                var component = Token.Value.ToUpperInvariant() switch
                {
                    "X" or "R" => 0,
                    "Y" or "G" => 1,
                    "Z" or "B" => 2,
                    "W" or "A" => 3,
                    _ => throw new InvalidOperationException(),
                };
                Next();
                return evaluate ? context.GetVectorComponent(name, component) : 0.0f;
            }

            return !evaluate ? 0.0f : name.ToUpperInvariant() switch
            {
                "TRUE" => 1.0f,
                "FALSE" => 0.0f,
                "PI" => MathF.PI,
                "E" => MathF.E,
                _ => context.GetVariable(name),
            };
        }

        private float Call(string name, bool evaluate)
        {
            var arguments = new List<float>();
            if (!Accept(")"))
            {
                do
                    arguments.Add(ParseTernary(evaluate));
                while (Accept(","));
                Expect(")");
            }

            if (!evaluate)
                return 0.0f;

            return name.ToUpperInvariant() switch
            {
                "ABS" when arguments.Count >= 1 => MathF.Abs(arguments[0]),
                "MIN" when arguments.Count > 0 => arguments.Min(),
                "MAX" when arguments.Count > 0 => arguments.Max(),
                "CLAMP" when arguments.Count >= 3 => MathF.Max(arguments[1], MathF.Min(arguments[0], arguments[2])),
                "LERP" when arguments.Count >= 3 => arguments[0] + ((arguments[1] - arguments[0]) * arguments[2]),
                "SIGN" when arguments.Count >= 1 => MathF.Sign(arguments[0]),
                "SQRT" when arguments.Count >= 1 && arguments[0] >= 0.0f => MathF.Sqrt(arguments[0]),
                "POW" when arguments.Count >= 2 => MathF.Pow(arguments[0], arguments[1]),
                "FLOOR" when arguments.Count >= 1 => MathF.Floor(arguments[0]),
                "CEIL" when arguments.Count >= 1 => MathF.Ceiling(arguments[0]),
                "ROUND" when arguments.Count >= 1 => MathF.Round(arguments[0]),
                "SIN" when arguments.Count >= 1 => MathF.Sin(arguments[0]),
                "COS" when arguments.Count >= 1 => MathF.Cos(arguments[0]),
                "TAN" when arguments.Count >= 1 => MathF.Tan(arguments[0]),
                "ASIN" when arguments.Count >= 1 => MathF.Asin(Math.Clamp(arguments[0], -1.0f, 1.0f)),
                "ACOS" when arguments.Count >= 1 => MathF.Acos(Math.Clamp(arguments[0], -1.0f, 1.0f)),
                "ATAN" when arguments.Count >= 1 => MathF.Atan(arguments[0]),
                "ATAN2" when arguments.Count >= 2 => MathF.Atan2(arguments[0], arguments[1]),
                "DEG2RAD" when arguments.Count >= 1 => arguments[0] * (MathF.PI / 180.0f),
                "RAD2DEG" when arguments.Count >= 1 => arguments[0] * (180.0f / MathF.PI),
                "INSTANCEINDEX" => context.InstanceIndex,
                "INSTANCECOUNT" => context.InstanceCount,
                "RANDOMINT" when arguments.Count >= 2 => context.NextInteger(arguments[0], arguments[1]),
                "RANDOMFLOAT" when arguments.Count >= 2 => context.NextFloat(arguments[0], arguments[1]),
                "LINEARSCALE" => LinearScale(arguments),
                _ => 0.0f,
            };
        }

        private float LinearScale(List<float> arguments) => arguments.Count switch
        {
            0 => context.LinearScale,
            >= 5 when arguments[2] != arguments[1] => arguments[3] + (((arguments[0] - arguments[1]) / (arguments[2] - arguments[1])) * (arguments[4] - arguments[3])),
            >= 5 => arguments[3],
            >= 3 when arguments[2] != arguments[1] => (arguments[0] - arguments[1]) / (arguments[2] - arguments[1]),
            >= 3 => 0.0f,
            _ => arguments[0],
        };

        private bool Accept(string value)
        {
            if (Token.Value != value)
                return false;

            Next();
            return true;
        }

        private void Expect(string value)
        {
            if (!Accept(value))
                throw new InvalidOperationException();
        }

        private void Expect(TokenKind kind)
        {
            if (Token.Kind != kind)
                throw new InvalidOperationException();
        }

        private void Next() => Token = Lexer.Next();

        private static bool IsTrue(float value) => value != 0.0f;
    }

    private sealed class Lexer(string expression)
    {
        private int Position;

        public Token Next()
        {
            SkipWhitespaceAndComments();
            if (Position >= expression.Length)
                return new(TokenKind.End, string.Empty);

            var start = Position;
            if (char.IsDigit(expression[Position]) || (expression[Position] == '.' && Position + 1 < expression.Length && char.IsDigit(expression[Position + 1])))
            {
                Position++;
                while (Position < expression.Length && (char.IsDigit(expression[Position]) || expression[Position] == '.'))
                    Position++;
                return new(TokenKind.Number, expression[start..Position]);
            }

            if (char.IsLetter(expression[Position]) || expression[Position] == '_')
            {
                Position++;
                while (Position < expression.Length && (char.IsLetterOrDigit(expression[Position]) || expression[Position] == '_'))
                    Position++;
                return new(TokenKind.Identifier, expression[start..Position]);
            }

            Position++;
            var value = expression[start..Position];
            if (Position < expression.Length && value is "|" or "&" or "=" or "!" or "<" or ">")
            {
                var candidate = expression[start..(Position + 1)];
                if (candidate is "||" or "&&" or "==" or "!=" or "<=" or ">=")
                {
                    Position++;
                    value = candidate;
                }
            }

            return value is "+" or "-" or "*" or "/" or "%" or "<" or ">" or "!" or "?" or ":" or "(" or ")" or "." or "," or "||" or "&&" or "==" or "!=" or "<=" or ">="
                ? new(TokenKind.Operator, value)
                : throw new InvalidOperationException();
        }

        private void SkipWhitespaceAndComments()
        {
            while (Position < expression.Length)
            {
                if (char.IsWhiteSpace(expression[Position]))
                {
                    Position++;
                    continue;
                }

                if (Position + 1 < expression.Length && expression[Position] == '/' && expression[Position + 1] == '/')
                {
                    Position += 2;
                    while (Position < expression.Length && expression[Position] != '\n')
                        Position++;
                    continue;
                }

                return;
            }
        }
    }

    private readonly record struct Token(TokenKind Kind, string Value);

    private enum TokenKind
    {
        End,
        Identifier,
        Number,
        Operator,
    }
}
