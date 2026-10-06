using System.Threading.Tasks;

using ValveKeyValue;
using Hammer5Tools.Core.Format.SmartProps.Evaluation;

namespace Hammer5Tools.Core.Tests.SmartProps;

public class SmartPropPublicEvaluationTest
{
    [Test]
    public async Task EvaluatesThroughThePublicFacade()
    {
        var root = Element("Model", 7);
        root["m_sModelName"] = new KVObject("models/example.vmdl");

        var result = SmartPropEvaluation.Evaluate(root);

        await Assert.That(result.Models).Count().IsEqualTo(1);
        await Assert.That(result.Models[0].ElementId).IsEqualTo(7);
        await Assert.That(result.Models[0].ModelName).IsEqualTo("models/example.vmdl");
    }

    private static KVObject Element(string className, int id)
    {
        var element = KVObject.Collection();
        element["generic_data_type"] = new KVObject($"CSmartPropElement_{className}");
        element["m_nElementID"] = new KVObject(id);
        return element;
    }
}
