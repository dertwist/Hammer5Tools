using System.Threading.Tasks;
using Hammer5Tools.Core.Format.SmartProps.Evaluation;

namespace Hammer5Tools.Core.Tests.SmartProps;

public class SmartPropValueTest
{
    [Test]
    public async Task ConvertsTypedValuesWithoutRuntimeTypeChecks()
    {
        var integer = SmartPropValue.FromInteger(3);
        var vector = SmartPropValue.FromVector3(new Vector3(4f, 5f, 6f));

        await Assert.That(integer.TryGetScalar(out var scalar)).IsTrue();
        await Assert.That(scalar).IsEqualTo(3f);
        await Assert.That(vector.TryGetScalar(out var firstComponent)).IsTrue();
        await Assert.That(firstComponent).IsEqualTo(4f);
        await Assert.That(vector.TryGetVector3(out var vector3)).IsTrue();
        await Assert.That(vector3).IsEqualTo(new Vector3(4f, 5f, 6f));
    }

    [Test]
    public async Task ContextPrefersImmutableOverridesAndPreservesPlacement()
    {
        var variables = new Dictionary<string, SmartPropValue>
        {
            ["Height"] = SmartPropValue.FromFloat(10f),
        };
        var context = new SmartPropEvaluationContext(variables, placement: new SmartPropPlacement(1, 4, 0.5f));
        var overridden = context.WithOverride("height", SmartPropValue.FromFloat(20f));

        await Assert.That(context.TryGetValue("HEIGHT", out var original)).IsTrue();
        await Assert.That(original.TryGetScalar(out var originalHeight)).IsTrue();
        await Assert.That(originalHeight).IsEqualTo(10f);
        await Assert.That(overridden.TryGetValue("HEIGHT", out var overrideValue)).IsTrue();
        await Assert.That(overrideValue.TryGetScalar(out var overrideHeight)).IsTrue();
        await Assert.That(overrideHeight).IsEqualTo(20f);
        await Assert.That(overridden.Placement).IsEqualTo(new SmartPropPlacement(1, 4, 0.5f));
    }
}
