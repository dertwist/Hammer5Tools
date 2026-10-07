using ValveKeyValue;

namespace Hammer5Tools.Core.Format.SmartProps.Evaluation;

internal readonly record struct SmartPropModifierResult(
    Matrix4x4 LocalTransform,
    Matrix4x4 WorldTransform,
    Matrix4x4 ModelTransform,
    bool IsFilteredOut,
    Vector4? TintColor,
    string? MaterialGroup);

internal static class SmartPropModifierEvaluator
{
    public static SmartPropModifierResult Evaluate(
        KVObject element,
        SmartPropEvaluationContext context,
        Matrix4x4 parentTransform,
        Vector4? inheritedTint = null,
        string? inheritedMaterialGroup = null,
        List<EvaluatedSmartPropWidget>? widgets = null)
    {
        var elementId = ReadInt32(element, "m_nElementID");
        var localTransform = Matrix4x4.Identity;
        var tint = inheritedTint;
        var materialGroup = inheritedMaterialGroup;

        if (element.TryGetValue("m_Modifiers", out var modifiers) && modifiers.IsArray)
        {
            foreach (var modifier in modifiers.AsArraySpan())
            {
                if (modifier.ValueType != KVValueType.Collection || IsDisabled(modifier))
                {
                    continue;
                }

                var className = SmartPropClass.Read(modifier);
                if (widgets is not null && className is "CreateSizer" or "CreateLocator" or "CreateRotator")
                {
                    var type = className switch { "CreateSizer" => "sizer", "CreateLocator" => "locator", _ => "rotator" };
                    var widgetId = modifier.ContainsKey("m_nElementID") ? ReadInt32(modifier, "m_nElementID") : elementId;
                    widgets.Add(SmartPropEvaluator.CreateWidget(modifier, type, widgetId, localTransform * parentTransform, context));
                }
                if (IsFilter(className) && !EvaluateFilter(modifier, className, context, elementId))
                {
                    return new SmartPropModifierResult(localTransform, parentTransform, parentTransform, true, tint, materialGroup);
                }

                if (className == "SetTintColor")
                {
                    tint = ResolveTint(modifier, context, elementId) ?? tint;
                    continue;
                }

                if (className is "SetMaterialGroup" or "MaterialGroup")
                {
                    materialGroup = context.ResolveString(ReadValue(modifier, "m_MaterialGroup"), materialGroup ?? string.Empty);
                    continue;
                }

                localTransform = ApplyTransform(modifier, className, localTransform, context, elementId);
            }
        }

        var worldTransform = localTransform * parentTransform;
        var modelScale = ResolveModelScale(element, context);
        var modelTransform = Matrix4x4.CreateScale(modelScale) * worldTransform;
        return new SmartPropModifierResult(localTransform, worldTransform, modelTransform, false, tint, materialGroup);
    }

    private static Matrix4x4 ApplyTransform(
        KVObject modifier,
        string className,
        Matrix4x4 localTransform,
        SmartPropEvaluationContext context,
        int elementId)
    {
        switch (className)
        {
            case "Translate" when modifier.TryGetValue("m_vPosition", out var positionValue):
                var translation = Matrix4x4.CreateTranslation(context.ResolveVector3(positionValue));
                return IsWorldOrParentSpace(modifier) ? localTransform * translation : translation * localTransform;

            case "SetPosition" when modifier.TryGetValue("m_vPosition", out var positionValue):
                var position = context.ResolveVector3(positionValue);
                localTransform.M41 = position.X;
                localTransform.M42 = position.Y;
                localTransform.M43 = position.Z;
                return localTransform;

            case "Rotate" when modifier.TryGetValue("m_vRotation", out var rotationValue):
                var rotation = SmartPropTransformMath.EulerAnglesToRotationMatrix(context.ResolveVector3(rotationValue));
                return IsWorldOrParentSpace(modifier) ? localTransform * rotation : rotation * localTransform;

            case "SetOrientation":
                return SetOrientation(modifier, localTransform, context);

            case "ResetRotation":
                var (resetPosition, resetAngles, resetScale) = SmartPropTransform.DecomposeTRS(localTransform);
                var angles = new Vector3(
                    ReadBoolean(modifier, "m_bResetPitch", true) ? 0f : resetAngles.X,
                    ReadBoolean(modifier, "m_bResetYaw", true) ? 0f : resetAngles.Y,
                    ReadBoolean(modifier, "m_bResetRoll", true) ? 0f : resetAngles.Z);
                return Compose(resetScale, angles, resetPosition);

            case "Scale":
                var scale = modifier.TryGetValue("m_vScale", out var scaleValue)
                    ? context.ResolveVector3(scaleValue, Vector3.One)
                    : new Vector3(context.ResolveScalar(ReadValue(modifier, "m_flScale"), 1f));
                return Matrix4x4.CreateScale(scale) * localTransform;

            case "ResetScale":
                var (scalePosition, scaleAngles, _) = SmartPropTransform.DecomposeTRS(localTransform);
                return Compose(Vector3.One, scaleAngles, scalePosition);

            case "RandomOffset":
                var minOffset = context.ResolveVector3(ReadValue(modifier, "m_vRandomPositionMin"));
                var maxOffset = context.ResolveVector3(ReadValue(modifier, "m_vRandomPositionMax"));
                return Matrix4x4.CreateTranslation(RandomVector(context, minOffset, maxOffset, elementId, 11)) * localTransform;

            case "RandomRotation":
                var minRotation = context.ResolveVector3(ReadValue(modifier, "m_vRandomRotationMin"));
                var maxRotation = context.ResolveVector3(ReadValue(modifier, "m_vRandomRotationMax"));
                var randomRotation = RandomVector(context, minRotation, maxRotation, elementId, 101);
                return SmartPropTransformMath.EulerAnglesToRotationMatrix(randomRotation) * localTransform;

            case "RandomScale":
                var minScale = context.ResolveScalar(ReadValue(modifier, "m_flRandomScaleMin"), 1f);
                var maxScale = context.ResolveScalar(ReadValue(modifier, "m_flRandomScaleMax"), 1f);
                var randomScale = Lerp(minScale, maxScale, context.RandomFloat(elementId ^ 202));
                return Matrix4x4.CreateScale(randomScale) * localTransform;

            default:
                return localTransform;
        }
    }

    private static Matrix4x4 SetOrientation(KVObject modifier, Matrix4x4 localTransform, SmartPropEvaluationContext context)
    {
        var (position, _, scale) = SmartPropTransform.DecomposeTRS(localTransform);
        if (modifier.TryGetValue("m_vRotation", out var rotationValue))
        {
            return Compose(scale, context.ResolveVector3(rotationValue), position);
        }

        if (!modifier.TryGetValue("m_vForwardVector", out var forwardValue)
            || !modifier.TryGetValue("m_vUpVector", out var upValue))
        {
            return localTransform;
        }

        var forward = context.ResolveVector3(forwardValue, Vector3.UnitX);
        var up = context.ResolveVector3(upValue, Vector3.UnitZ);
        var rotation = SmartPropTransform.CreateFrame(Vector3.Zero, forward, up);
        return Matrix4x4.CreateScale(scale) * rotation * Matrix4x4.CreateTranslation(position);
    }

    private static bool EvaluateFilter(
        KVObject filter,
        string className,
        SmartPropEvaluationContext context,
        int elementId)
    {
        if (className is "Filter_Expression" or "Expression")
        {
            return !filter.TryGetValue("m_Expression", out var expression)
                || MathF.Abs(context.ResolveScalar(expression, 1f)) > 1e-6f;
        }

        if (className is "Filter_Probability" or "Probability")
        {
            var probability = context.ResolveScalar(ReadValue(filter, "m_flProbability"), 1f);
            return context.RandomFloat(elementId ^ 777) <= probability;
        }

        if (className is not ("Filter_VariableValue" or "VariableValue")
            && !filter.ContainsKey("m_VariableComparison"))
        {
            return true;
        }

        var comparison = filter.TryGetValue("m_VariableComparison", out var nested)
            && nested.ValueType == KVValueType.Collection
                ? nested
                : filter;
        return EvaluateComparison(comparison, context);
    }

    private static bool EvaluateComparison(KVObject comparison, SmartPropEvaluationContext context)
    {
        var name = ReadString(comparison, "m_Name");
        if (name.Length == 0)
        {
            name = ReadString(comparison, "m_VariableName");
        }

        if (name.Length == 0 || !context.TryGetValue(name, out var actual))
        {
            return false;
        }

        var operation = ReadString(comparison, "m_Comparison", "EQUAL").ToUpperInvariant();
        if (!comparison.TryGetValue("m_Value", out var expectedValue))
        {
            return operation is "NOT_EQUAL" or "!=" ? !IsTruthy(actual) : IsTruthy(actual);
        }

        if (actual.TryGetScalar(out var actualNumber))
        {
            var expectedNumber = context.ResolveScalar(expectedValue);
            return operation switch
            {
                "NOT_EQUAL" or "!=" => MathF.Abs(actualNumber - expectedNumber) >= 1e-4f,
                "LESS" or "<" => actualNumber < expectedNumber,
                "LESS_OR_EQUAL" or "<=" => actualNumber <= expectedNumber,
                "GREATER" or ">" => actualNumber > expectedNumber,
                "GREATER_OR_EQUAL" or ">=" => actualNumber >= expectedNumber,
                _ => MathF.Abs(actualNumber - expectedNumber) < 1e-4f,
            };
        }

        var actualText = actual.TryGetString(out var text) ? text : string.Empty;
        var expectedText = context.ResolveString(expectedValue);
        var equal = string.Equals(actualText, expectedText, StringComparison.OrdinalIgnoreCase);
        return operation is "NOT_EQUAL" or "!=" ? !equal : equal;
    }

    private static Vector4? ResolveTint(KVObject modifier, SmartPropEvaluationContext context, int elementId)
    {
        if (modifier.TryGetValue("m_ColorChoices", out var choices) && choices.IsArray)
        {
            var values = choices.AsArraySpan();
            if (values.Length == 0)
            {
                return null;
            }

            var index = Math.Min((int)(context.RandomFloat(elementId ^ 991) * values.Length), values.Length - 1);
            return context.ResolveVector4(values[index], Vector4.One);
        }

        if (modifier.TryGetValue("m_Color", out var color))
        {
            return context.ResolveVector4(color, Vector4.One);
        }

        return null;
    }

    private static Vector3 ResolveModelScale(KVObject element, SmartPropEvaluationContext context)
    {
        if (element.TryGetValue("m_vModelScale", out var vectorScale))
        {
            return context.ResolveVector3(vectorScale, Vector3.One);
        }

        if (element.TryGetValue("m_flUniformModelScale", out var uniformScale)
            || element.TryGetValue("m_flModelScale", out uniformScale))
        {
            return new Vector3(context.ResolveScalar(uniformScale, 1f));
        }

        return Vector3.One;
    }

    private static Vector3 RandomVector(
        SmartPropEvaluationContext context,
        Vector3 min,
        Vector3 max,
        int elementId,
        int salt)
        => new(
            Lerp(min.X, max.X, context.RandomFloat(elementId ^ salt)),
            Lerp(min.Y, max.Y, context.RandomFloat(elementId ^ (salt + 1))),
            Lerp(min.Z, max.Z, context.RandomFloat(elementId ^ (salt + 2))));

    private static Matrix4x4 Compose(Vector3 scale, Vector3 angles, Vector3 position)
        => Matrix4x4.CreateScale(scale)
            * SmartPropTransformMath.EulerAnglesToRotationMatrix(angles)
            * Matrix4x4.CreateTranslation(position);

    private static bool IsTruthy(SmartPropValue value)
    {
        if (value.TryGetScalar(out var scalar))
        {
            return MathF.Abs(scalar) > 1e-6f;
        }

        return value.TryGetString(out var text) && !string.IsNullOrEmpty(text);
    }

    private static bool IsFilter(string className)
        => className.StartsWith("Filter_", StringComparison.Ordinal)
            || className is "VariableValue" or "Expression" or "Probability" or "SurfaceProperties";

    private static bool IsDisabled(KVObject node)
        => node.TryGetValue("m_bEnabled", out var enabled)
            && enabled.ValueType == KVValueType.Boolean
            && !(bool)enabled;

    private static bool IsWorldOrParentSpace(KVObject modifier)
        => ReadString(modifier, "m_CoordinateSpace", "ELEMENT") is "WORLD" or "PARENT";

    private static KVObject? ReadValue(KVObject node, string name)
        => node.TryGetValue(name, out var value) ? value : null;

    private static string ReadString(KVObject node, string name, string defaultValue = "")
        => node.TryGetValue(name, out var value) && value.ValueType == KVValueType.String
            ? (string)value
            : defaultValue;

    private static int ReadInt32(KVObject node, string name)
        => node.TryGetValue(name, out var value)
            && value.ValueType is KVValueType.Int32 or KVValueType.Int64 or KVValueType.UInt32 or KVValueType.UInt64
                ? (int)value
                : 0;

    private static bool ReadBoolean(KVObject node, string name, bool defaultValue)
        => node.TryGetValue(name, out var value) && value.ValueType == KVValueType.Boolean
            ? (bool)value
            : defaultValue;

    private static float Lerp(float min, float max, float amount) => min + ((max - min) * amount);
}
