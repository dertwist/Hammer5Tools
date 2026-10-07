using System.Threading.Tasks;
using Hammer5Tools.Core.Format.SmartProps.Evaluation;
using ValveKeyValue;

namespace Hammer5Tools.Core.Tests.SmartProps;

public class SmartPropValueResolverTest
{
    [Test]
    public async Task ResolvesVariablesExpressionsAndComponentsThroughOnePath()
    {
        var context = new SmartPropEvaluationContext(new Dictionary<string, SmartPropValue>
        {
            ["height"] = SmartPropValue.FromFloat(12f),
        });
        var resolver = new SmartPropValueResolver(context, _ => 7f);

        var variable = KVObject.Collection();
        variable["m_SourceName"] = new KVObject("HEIGHT");

        var expression = KVObject.Collection();
        expression["m_Expression"] = new KVObject("unused");

        var components = KVObject.Collection();
        var componentValues = KVObject.Array();
        componentValues.Add(new KVObject(1f));
        componentValues.Add(new KVObject(2f));
        componentValues.Add(new KVObject(3f));
        components["m_Components"] = componentValues;

        await Assert.That(resolver.ResolveFloat(variable)).IsEqualTo(12f);
        await Assert.That(resolver.ResolveFloat(expression)).IsEqualTo(7f);
        await Assert.That(resolver.ResolveVector3(components)).IsEqualTo(new Vector3(1f, 2f, 3f));
    }
}
