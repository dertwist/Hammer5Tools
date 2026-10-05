using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

namespace Hammer5Tools.Core;

[JsonSerializable(typeof(JsonObject))]
internal sealed partial class SmartPropPreviewJsonContext : JsonSerializerContext;
