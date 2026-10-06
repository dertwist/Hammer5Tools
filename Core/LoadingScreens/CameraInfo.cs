namespace Hammer5Tools.Core.LoadingScreens;

using System.Numerics;

public class CameraInfo
{
    public string Name { get; set; } = "Camera";

    public Vector3 Position { get; set; }

    public Vector3 Angles { get; set; }

    public float Fov { get; set; } = 90f;

    public CameraInfo()
    {
    }

    public CameraInfo(string name, Vector3 position, Vector3 angles, float fov = 90f)
    {
        Name = name;
        Position = position;
        Angles = angles;
        Fov = fov;
    }
}
