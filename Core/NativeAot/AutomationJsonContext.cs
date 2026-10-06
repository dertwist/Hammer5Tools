using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

namespace Hammer5Tools.Core;

[JsonSerializable(typeof(string))]
[JsonSerializable(typeof(bool))]
[JsonSerializable(typeof(int))]
[JsonSerializable(typeof(long))]
[JsonSerializable(typeof(float))]
[JsonSerializable(typeof(double))]
[JsonSerializable(typeof(JsonObject))]
[JsonSerializable(typeof(JsonArray))]
internal sealed partial class AutomationJsonContext : JsonSerializerContext;
