namespace Hammer5Tools.Core.MapBuilder;

/// <summary>Reads system usage; unavailable counters are represented by null.</summary>
public interface ISystemUsageService
{
    SystemUsage Read();
}

/// <summary>Measured system CPU, physical memory and GPU percentages.</summary>
public sealed record SystemUsage(double? Cpu, double? Memory, double? Gpu);
