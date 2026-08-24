using System.Numerics;
using Hammer5Tools.Core.SmartProps;

namespace Hammer5Tools.Core.Tests.SmartProps;

public sealed class SmartPropExpressionTests
{
    [Test]
    [Arguments("1 + 2 * 3", 7.0f)]
    [Arguments("(2 < 1) ? 8 : 4", 4.0f)]
    [Arguments("!false && true", 1.0f)]
    [Arguments("Clamp(10, 2, 6)", 6.0f)]
    [Arguments("Deg2Rad(180)", MathF.PI)]
    [Arguments("1 / 0", 0.0f)]
    public async Task EvaluatesNumericExpressions(string expression, float expected)
    {
        await Assert.That(SmartPropExpression.Evaluate(expression)).IsEqualTo(expected).Within(0.0001f);
    }

    [Test]
    public async Task ResolvesCaseInsensitiveVariablesAndVectorMembers()
    {
        var context = new SmartPropContext(
            new Dictionary<string, float> { ["Block_Type"] = 1.0f },
            new Dictionary<string, Vector4> { ["Tint"] = new(1.0f, 2.0f, 3.0f, 4.0f) },
            instanceIndex: 2,
            instanceCount: 5,
            linearScale: 1.5f);

        await Assert.That(SmartPropExpression.Evaluate("block_type == 1 ? tint.b + InstanceIndex() : 0", context)).IsEqualTo(5.0f);
        await Assert.That(SmartPropExpression.Evaluate("LinearScale()", context)).IsEqualTo(1.5f);
    }

    [Test]
    public async Task ReturnsTheDefaultForMalformedExpressions()
    {
        await Assert.That(SmartPropExpression.Evaluate("1 + )", defaultValue: 9.0f)).IsEqualTo(9.0f);
    }

    [Test]
    public async Task ResolvesNestedValueForms()
    {
        var context = new SmartPropContext(values: new Dictionary<string, SmartPropValue>
        {
            ["Scale"] = SmartPropValue.FromExpression("InstanceIndex() * 2"),
            ["Size"] = SmartPropValue.FromVariable("Scale"),
        }, instanceIndex: 3);
        var vector = SmartPropValue.FromComponents([
            SmartPropValue.FromVariable("Size"),
            SmartPropValue.FromExpression("4 + 1"),
        ]);

        await Assert.That(context.ResolveScalar(SmartPropValue.FromVariable("Size"))).IsEqualTo(6.0f);
        await Assert.That(context.ResolveVector(vector)).IsEqualTo(new Vector3(6.0f, 5.0f, 0.0f));
    }
}
