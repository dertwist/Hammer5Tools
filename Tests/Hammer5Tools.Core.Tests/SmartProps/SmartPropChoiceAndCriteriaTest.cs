using System.Threading.Tasks;
using ValveKeyValue;
using Hammer5Tools.Core.Format.SmartProps.Evaluation;

namespace Hammer5Tools.Core.Tests.SmartProps;

public class SmartPropChoiceAndCriteriaTest
{
    [Test]
    public async Task AppliesTypedChoiceDefaults()
    {
        var root = KVObject.Collection();
        var choices = KVObject.Array();
        var choice = KVObject.Collection();
        choice["m_Name"] = new KVObject("style");
        choice["m_DefaultOption"] = new KVObject("wide");

        var options = KVObject.Array();
        var option = KVObject.Collection();
        option["m_Name"] = new KVObject("wide");
        var values = KVObject.Array();
        var value = KVObject.Collection();
        value["m_TargetName"] = new KVObject("width");
        value["m_DataType"] = new KVObject("Float");
        value["m_Value"] = new KVObject(32f);
        values.Add(value);
        option["m_VariableValues"] = values;
        options.Add(option);
        choice["m_Options"] = options;
        choices.Add(choice);
        root["m_Choices"] = choices;

        var definitions = SmartPropChoiceMap.ReadChoices(root);
        var variables = new Dictionary<string, SmartPropValue>();
        SmartPropChoiceMap.ApplyChoices(variables, definitions);

        await Assert.That(variables["width"].TryGetScalar(out var width)).IsTrue();
        await Assert.That(width).IsEqualTo(32f);
    }

    [Test]
    public async Task MatchesExpressionCriteriaUsingTypedVariables()
    {
        var child = KVObject.Collection();
        var criteria = KVObject.Array();
        var expression = KVObject.Collection();
        expression["generic_data_type"] = new KVObject("CSmartPropSelectionCriteria_IsValid");
        expression["m_Expression"] = new KVObject("enabled");
        criteria.Add(expression);
        child["m_SelectionCriteria"] = criteria;

        var enabled = new SmartPropEvaluationContext(new Dictionary<string, SmartPropValue>
        {
            ["enabled"] = SmartPropValue.FromBoolean(true),
        });
        var disabled = enabled.WithOverride("enabled", SmartPropValue.FromBoolean(false));

        await Assert.That(SmartPropSelectionCriteria.MatchesSelectionCriteria(child, 0, 1, enabled)).IsTrue();
        await Assert.That(SmartPropSelectionCriteria.MatchesSelectionCriteria(child, 0, 1, disabled)).IsFalse();
    }
}
