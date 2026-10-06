namespace Hammer5Tools.Core.DetailProps;

using System.IO;

/// <summary>
/// A single model variation within a detail prop type.
/// </summary>
public class DetailPropModel : CommunityToolkit.Mvvm.ComponentModel.ObservableObject
{
    private string ModelNameValue = string.Empty;

    public string ModelName
    {
        get => ModelNameValue;
        set => SetProperty(ref ModelNameValue, value);
    }

    private float MinScaleValue = 1.0f;

    public float MinScale
    {
        get => MinScaleValue;
        set => SetProperty(ref MinScaleValue, value);
    }

    private float MaxScaleValue = 1.0f;

    public float MaxScale
    {
        get => MaxScaleValue;
        set => SetProperty(ref MaxScaleValue, value);
    }

    private bool RandomYawValue = true;

    public bool RandomYaw
    {
        get => RandomYawValue;
        set => SetProperty(ref RandomYawValue, value);
    }

    private bool RandomPitchValue;

    public bool RandomPitch
    {
        get => RandomPitchValue;
        set => SetProperty(ref RandomPitchValue, value);
    }

    private bool RandomRollValue;

    public bool RandomRoll
    {
        get => RandomRollValue;
        set => SetProperty(ref RandomRollValue, value);
    }

    private bool AlignToSurfaceValue;

    public bool AlignToSurface
    {
        get => AlignToSurfaceValue;
        set => SetProperty(ref AlignToSurfaceValue, value);
    }

    private bool UprightValue = true;

    public bool Upright
    {
        get => UprightValue;
        set => SetProperty(ref UprightValue, value);
    }

    private float DensityValue = 1.0f;

    public float Density
    {
        get => DensityValue;
        set => SetProperty(ref DensityValue, value);
    }


    internal ValveKeyValue.KVObject Original { get; set; } = new();

    private string MaterialGroupValue = string.Empty;

    public string MaterialGroup
    {
        get => MaterialGroupValue;
        set => SetProperty(ref MaterialGroupValue, value);
    }

    private float WeightValue = 1f;

    public float Weight
    {
        get => WeightValue;
        set => SetProperty(ref WeightValue, value);
    }

    private float StartFadeSizeValue = 0.02f;

    public float StartFadeSize
    {
        get => StartFadeSizeValue;
        set => SetProperty(ref StartFadeSizeValue, value);
    }

    private float EndFadeSizeValue = 0.0125f;

    public float EndFadeSize
    {
        get => EndFadeSizeValue;
        set => SetProperty(ref EndFadeSizeValue, value);
    }

    private bool WorldSpaceOrientationValue;

    public bool WorldSpaceOrientation
    {
        get => WorldSpaceOrientationValue;
        set => SetProperty(ref WorldSpaceOrientationValue, value);
    }

    private float OrientToSurfaceValue = 1f;

    public float OrientToSurface
    {
        get => OrientToSurfaceValue;
        set => SetProperty(ref OrientToSurfaceValue, value);
    }

    private float MinSurfaceSlopeValue;

    public float MinSurfaceSlope
    {
        get => MinSurfaceSlopeValue;
        set => SetProperty(ref MinSurfaceSlopeValue, value);
    }

    private float MaxSurfaceSlopeValue = 180f;

    public float MaxSurfaceSlope
    {
        get => MaxSurfaceSlopeValue;
        set => SetProperty(ref MaxSurfaceSlopeValue, value);
    }

    private float VerticalOffsetMinValue;

    public float VerticalOffsetMin
    {
        get => VerticalOffsetMinValue;
        set => SetProperty(ref VerticalOffsetMinValue, value);
    }

    private float VerticalOffsetMaxValue;

    public float VerticalOffsetMax
    {
        get => VerticalOffsetMaxValue;
        set => SetProperty(ref VerticalOffsetMaxValue, value);
    }

    private Vector3 RotationMinValue;

    public Vector3 RotationMin
    {
        get => RotationMinValue;
        set => SetProperty(ref RotationMinValue, value);
    }

    private Vector3 RotationMaxValue = new(0, 360, 0);

    public Vector3 RotationMax
    {
        get => RotationMaxValue;
        set => SetProperty(ref RotationMaxValue, value);
    }

    private float RandomScaleMinValue = 1f;

    public float RandomScaleMin
    {
        get => RandomScaleMinValue;
        set => SetProperty(ref RandomScaleMinValue, value);
    }

    private float RandomScaleMaxValue = 1f;

    public float RandomScaleMax
    {
        get => RandomScaleMaxValue;
        set => SetProperty(ref RandomScaleMaxValue, value);
    }

    private float DensityMinScaleValue = 1f;

    public float DensityMinScale
    {
        get => DensityMinScaleValue;
        set => SetProperty(ref DensityMinScaleValue, value);
    }

    private float BlendWeightMinScaleValue = 1f;

    public float BlendWeightMinScale
    {
        get => BlendWeightMinScaleValue;
        set => SetProperty(ref BlendWeightMinScaleValue, value);
    }

    private float BlendWeightMinValue = 0.25f;

    public float BlendWeightMin
    {
        get => BlendWeightMinValue;
        set => SetProperty(ref BlendWeightMinValue, value);
    }

    private float BlendWeightMaxValue = 1f;

    public float BlendWeightMax
    {
        get => BlendWeightMaxValue;
        set => SetProperty(ref BlendWeightMaxValue, value);
    }

    private float BlendWeightFullDensityValue = 0.75f;

    public float BlendWeightFullDensity
    {
        get => BlendWeightFullDensityValue;
        set => SetProperty(ref BlendWeightFullDensityValue, value);
    }

    private bool CastStaticShadowsValue;

    public bool CastStaticShadows
    {
        get => CastStaticShadowsValue;
        set => SetProperty(ref CastStaticShadowsValue, value);
    }

    public string DisplayName => string.IsNullOrWhiteSpace(ModelName) ? "<no model>" : Path.GetFileName(ModelName);
}
