using System.Threading.Tasks;
using Hammer5Tools.Core.Format.SmartProps.Evaluation;

namespace Hammer5Tools.Core.Tests.SmartProps;

public class SmartPropExpressionEvaluatorTest
{
    [Test]
    public async Task EvaluatesVariablesPlacementAndArithmetic()
    {
        var context = new SmartPropEvaluationContext(
            new Dictionary<string, SmartPropValue>
            {
                ["spacing"] = SmartPropValue.FromFloat(16f),
                ["offset"] = SmartPropValue.FromVector3(new Vector3(2f, 3f, 4f)),
            },
            placement: new SmartPropPlacement(2, 5, 0.5f));

        await Assert.That(SmartPropExpressionEvaluator.Evaluate("spacing * InstanceIndex()", context)).IsEqualTo(32f);
        await Assert.That(SmartPropExpressionEvaluator.Evaluate("offset.y + InstanceCount()", context)).IsEqualTo(8f);
        await Assert.That(SmartPropExpressionEvaluator.Evaluate("LinearScale()", context)).IsEqualTo(0.5f);
    }

    [Test]
    public async Task RandomFunctionsAreStableForTheSameContext()
    {
        var context = new SmartPropEvaluationContext(seed: 42);
        var first = SmartPropExpressionEvaluator.Evaluate("RandomFloat(10, 20)", context);
        var second = SmartPropExpressionEvaluator.Evaluate("RandomFloat(10, 20)", context);

        await Assert.That(first).IsEqualTo(second);
        await Assert.That(first).IsGreaterThanOrEqualTo(10f);
        await Assert.That(first).IsLessThanOrEqualTo(20f);
    }
}
