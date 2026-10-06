using System.Threading.Tasks;
using ValveKeyValue;
using Hammer5Tools.Core.Format.SmartProps.Evaluation;

namespace Hammer5Tools.Core.Tests.SmartProps;

public class SmartPropModifierEvaluatorTest
{
    [Test]
    public async Task AppliesTransformsInModifierOrder()
    {
        var element = KVObject.Collection();
        var modifiers = KVObject.Array();
        modifiers.Add(Modifier("Translate", "m_vPosition", Vector(10f, 20f, 30f)));
        modifiers.Add(Modifier("Scale", "m_vScale", Vector(2f, 3f, 4f)));
        element["m_Modifiers"] = modifiers;

        var result = SmartPropModifierEvaluator.Evaluate(element, new SmartPropEvaluationContext(), Matrix4x4.Identity);
        var origin = Vector3.Transform(Vector3.Zero, result.WorldTransform);

        await Assert.That(origin).IsEqualTo(new Vector3(10f, 20f, 30f));
        await Assert.That(result.IsFilteredOut).IsFalse();
    }

    [Test]
    public async Task FiltersAgainstTypedVariables()
    {
        var element = KVObject.Collection();
        var modifiers = KVObject.Array();
        var filter = KVObject.Collection();
        filter["generic_data_type"] = new KVObject("CSmartPropFilter_VariableValue");
        filter["m_VariableName"] = new KVObject("visible");
        filter["m_Comparison"] = new KVObject("EQUAL");
        filter["m_Value"] = new KVObject(true);
        modifiers.Add(filter);
        element["m_Modifiers"] = modifiers;

        var context = new SmartPropEvaluationContext(new Dictionary<string, SmartPropValue>
        {
            ["visible"] = SmartPropValue.FromBoolean(false),
        });
        var result = SmartPropModifierEvaluator.Evaluate(element, context, Matrix4x4.Identity);

        await Assert.That(result.IsFilteredOut).IsTrue();
    }

    private static KVObject Modifier(string name, string propertyName, KVObject propertyValue)
    {
        var modifier = KVObject.Collection();
        modifier["generic_data_type"] = new KVObject($"CSmartPropOperation_{name}");
        modifier[propertyName] = propertyValue;
        return modifier;
    }

    private static KVObject Vector(params float[] components)
    {
        var value = KVObject.Array();
        foreach (var component in components)
        {
            value.Add(new KVObject(component));
        }

        return value;
    }
}
