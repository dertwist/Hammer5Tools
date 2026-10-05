namespace Hammer5Tools.Infrastructure.MapBuilder;

using System.Runtime.InteropServices;
using Hammer5Tools.Core.MapBuilder;

/// <summary>Reads Windows system counters and optional NVIDIA driver telemetry.</summary>
public sealed class SystemUsageService : ISystemUsageService, IDisposable
{
    private readonly Lock Sync = new();
    private ulong? PreviousTotal;
    private ulong PreviousIdle;
    private bool NvidiaAttempted;
    private bool NvidiaInitialized;
    private IntPtr NvidiaDevice;

    public SystemUsage Read()
    {
        if (!OperatingSystem.IsWindows()) return new(null, null, null);
        lock (Sync)
        {
            double? cpu = null;
            if (Environment.ProcessorCount <= 64 && GetSystemTimes(out var idle, out var kernel, out var user))
            {
                var total = kernel + user;
                if (PreviousTotal is { } previous && total > previous && idle >= PreviousIdle)
                {
                    cpu = Math.Clamp(100.0 * (1.0 - (idle - PreviousIdle) / (double)(total - previous)), 0, 100);
                }
                PreviousTotal = total;
                PreviousIdle = idle;
            }
            var memory = new MemoryStatus { Length = (uint)Marshal.SizeOf<MemoryStatus>() };
            double? memoryLoad = GlobalMemoryStatusEx(ref memory) ? memory.Load : null;
            return new(cpu, memoryLoad, ReadGpu());
        }
    }

    private double? ReadGpu()
    {
        try
        {
            if (!NvidiaAttempted)
            {
                NvidiaAttempted = true;
                NvidiaInitialized = nvmlInit_v2() == 0;
                if (NvidiaInitialized && nvmlDeviceGetHandleByIndex_v2(0, out NvidiaDevice) != 0)
                {
                    NvidiaDevice = IntPtr.Zero;
                }
            }
            if (NvidiaDevice != IntPtr.Zero && nvmlDeviceGetUtilizationRates(NvidiaDevice, out var rates) == 0)
            {
                return rates.Gpu;
            }
        }
        catch (DllNotFoundException) { }
        catch (EntryPointNotFoundException) { }
        return null;
    }

    public void Dispose()
    {
        lock (Sync)
        {
            if (NvidiaInitialized)
            {
                NvidiaInitialized = nvmlShutdown() != 0;
                NvidiaDevice = IntPtr.Zero;
            }
        }
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct MemoryStatus
    {
        public uint Length;
        public uint Load;
        public ulong TotalPhysical;
        public ulong AvailablePhysical;
        public ulong TotalPageFile;
        public ulong AvailablePageFile;
        public ulong TotalVirtual;
        public ulong AvailableVirtual;
        public ulong AvailableExtendedVirtual;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct GpuUtilization
    {
        public uint Gpu;
        public uint Memory;
    }

    [DllImport("kernel32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetSystemTimes(out ulong idle, out ulong kernel, out ulong user);

    [DllImport("kernel32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GlobalMemoryStatusEx(ref MemoryStatus status);

    [DllImport("nvml.dll", CallingConvention = CallingConvention.Cdecl)]
    private static extern int nvmlInit_v2();

    [DllImport("nvml.dll", CallingConvention = CallingConvention.Cdecl)]
    private static extern int nvmlDeviceGetHandleByIndex_v2(uint index, out IntPtr device);

    [DllImport("nvml.dll", CallingConvention = CallingConvention.Cdecl)]
    private static extern int nvmlDeviceGetUtilizationRates(IntPtr device, out GpuUtilization utilization);

    [DllImport("nvml.dll", CallingConvention = CallingConvention.Cdecl)]
    private static extern int nvmlShutdown();
}
