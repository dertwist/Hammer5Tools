using System.Threading.Tasks;
using ValveKeyValue;
using Hammer5Tools.Core.Format.SmartProps.Evaluation;

namespace Hammer5Tools.Core.Tests.SmartProps;

public class SmartPropEvaluatorTest
{
    [Test]
    public async Task TraversesModelsWithInheritedTransforms()
    {
        var root = Element("Group", 1);
        var translate = KVObject.Collection();
        translate["generic_data_type"] = new KVObject("CSmartPropOperation_Translate");
        translate["m_vPosition"] = Vector(100f, 0f, 0f);
        var modifiers = KVObject.Array();
        modifiers.Add(translate);
        root["m_Modifiers"] = modifiers;

        var model = Element("Model", 2);
        model["m_sModelName"] = new KVObject("models/example.vmdl");
        var children = KVObject.Array();
        children.Add(model);
        root["m_Children"] = children;

        var result = SmartPropEvaluator.Evaluate(root);

        await Assert.That(result.Models).Count().IsEqualTo(1);
        await Assert.That(result.Models[0].ModelName).IsEqualTo("models/example.vmdl");
        await Assert.That(result.Models[0].Transform.Translation).IsEqualTo(new Vector3(100f, 0f, 0f));
    }

    [Test]
    public async Task ResolvesNestedPropsAndStopsCycles()
    {
        var root = Element("SmartProp", 1);
        root["m_sSmartProp"] = new KVObject("nested.vsmart");

        var nested = Element("Group", 2);
        var model = Element("Model", 3);
        model["m_sModelName"] = new KVObject("models/nested.vmdl");
        var cycle = Element("SmartProp", 4);
        cycle["m_sSmartProp"] = new KVObject("nested.vsmart");
        var children = KVObject.Array();
        children.Add(model);
        children.Add(cycle);
        nested["m_Children"] = children;

        var result = SmartPropEvaluator.Evaluate(root, nestedPropResolver: path => path == "nested.vsmart" ? nested : null);

        await Assert.That(result.Models).Count().IsEqualTo(1);
        await Assert.That(result.Models[0].ModelName).IsEqualTo("models/nested.vmdl");
    }

    [Test]
    public async Task StopsNestedTraversalAtConfiguredDepth()
    {
        var root = Element("SmartProp", 1);
        root["m_sSmartProp"] = new KVObject("recursive.vsmart");

        var result = SmartPropEvaluator.Evaluate(root, nestedPropResolver: _ => root, maxDepth: 0);

        await Assert.That(result.Models).IsEmpty();
    }

    [Test]
    public async Task UsesExplicitPickOneSelection()
    {
        var root = Element("PickOne", 10);
        var children = KVObject.Array();
        for (var i = 0; i < 3; i++)
        {
            var model = Element("Model", i + 1);
            model["m_sModelName"] = new KVObject($"models/{i}.vmdl");
            children.Add(model);
        }

        root["m_Children"] = children;
        var context = new SmartPropEvaluationContext().WithPickOneSelection(10, 2);
        var result = SmartPropEvaluator.Evaluate(root, context);

        await Assert.That(result.Models).Count().IsEqualTo(1);
        await Assert.That(result.Models[0].ModelName).IsEqualTo("models/2.vmdl");
    }

    [Test]
    public async Task PlacesChildrenAtPathIntervals()
    {
        var root = Element("PlaceOnPath", 1);
        root["m_flSpacing"] = new KVObject(5f);
        var path = KVObject.Array();
        path.Add(Vector(0f, 0f, 0f));
        path.Add(Vector(10f, 0f, 0f));
        root["m_DefaultPath"] = path;

        var model = Element("Model", 2);
        model["m_sModelName"] = new KVObject("models/path.vmdl");
        var children = KVObject.Array();
        children.Add(model);
        root["m_Children"] = children;

        var result = SmartPropEvaluator.Evaluate(root);

        await Assert.That(result.Models).Count().IsEqualTo(3);
        await Assert.That(result.Models[0].Transform.Translation.X).IsEqualTo(0f).Within(0.01f);
        await Assert.That(result.Models[1].Transform.Translation.X).IsEqualTo(5f).Within(0.01f);
        await Assert.That(result.Models[2].Transform.Translation.X).IsEqualTo(10f).Within(0.01f);
    }

    [Test]
    public async Task ExposesFitOnLineScaleToChildBindings()
    {
        var root = Element("FitOnLine", 1);
        root["m_vStart"] = Vector(0f, 0f, 0f);
        root["m_vEnd"] = Vector(20f, 0f, 0f);

        var model = Element("Model", 2);
        model["m_sModelName"] = new KVObject("models/fitted.vmdl");
        model["m_flModelScale"] = new KVObject("LinearScale()");
        var criteria = KVObject.Array();
        var length = KVObject.Collection();
        length["generic_data_type"] = new KVObject("CSmartPropSelectionCriteria_LinearLength");
        length["m_flLength"] = new KVObject(10f);
        length["m_bAllowScale"] = new KVObject(true);
        criteria.Add(length);
        model["m_SelectionCriteria"] = criteria;

        var children = KVObject.Array();
        children.Add(model);
        root["m_Children"] = children;

        var result = SmartPropEvaluator.Evaluate(root);

        await Assert.That(result.Models[0].Transform.M11).IsEqualTo(2f).Within(0.001f);
    }

    private static KVObject Element(string className, int elementId)
    {
        var element = KVObject.Collection();
        element["generic_data_type"] = new KVObject($"CSmartPropElement_{className}");
        element["m_nElementID"] = new KVObject(elementId);
        return element;
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
