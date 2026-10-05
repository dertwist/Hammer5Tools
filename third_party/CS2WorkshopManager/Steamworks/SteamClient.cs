using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;
using Microsoft.Win32;

namespace Steamworks;

/// <summary>
/// Steam can not be talked to: it is not running, still starting up, or nobody is logged in. The message says which and what to do.
/// </summary>
public sealed class SteamUnavailableException : InvalidOperationException
{
    public SteamUnavailableException() { }
    public SteamUnavailableException(string message) : base(message) { }
    public SteamUnavailableException(string message, Exception innerException) : base(message, innerException) { }
}

/// <summary>
/// A pipe to the running Steam client. This is the part of steam_api that is needed to make Steam calls:
/// it loads the client's own steamclient library, connects to it as the given app and delivers the results of asynchronous calls.
/// </summary>
public sealed class SteamClient : IDisposable
{
    /// <summary>ISteamClient version whose layout is used below, the client keeps serving old versions.</summary>
    private const string ClientInterfaceVersion = "SteamClient021";

    /// <summary>Sent by the client when an asynchronous call has finished, SteamAPICallCompleted_t.</summary>
    private const int ApiCallCompletedCallback = 703;

    /// <summary>Callback structs are packed to 8 bytes on Windows and to 4 bytes elsewhere, see steam_api_common.h.</summary>
    public static readonly int StructPack = OperatingSystem.IsWindows() ? 8 : 4;

    private static readonly TimeSpan CallbackPollInterval = TimeSpan.FromMilliseconds(50);

    // ISteamClient vtable slots
    private const int CreateSteamPipeSlot = 0;
    private const int ReleaseSteamPipeSlot = 1;
    private const int ConnectToGlobalUserSlot = 2;
    private const int ReleaseUserSlot = 4;
    private const int GetISteamGenericInterfaceSlot = 12;
    private const int ShutdownIfAllPipesClosedSlot = 22;

    private readonly nint library;
    private readonly unsafe delegate* unmanaged<int, CallbackMessage*, int*, byte> getCallback;
    private readonly unsafe delegate* unmanaged<int, byte> freeLastCallback;
    private readonly unsafe delegate* unmanaged<int, ulong, void*, int, int, byte*, byte> getApiCallResult;

    private readonly nint client;
    private readonly int pipe;
    private readonly int user;
    private bool disposed;

    public SteamUser User { get; }

    public SteamUGC UGC { get; }

    /// <summary>
    /// Connects to the running Steam client as <paramref name="appId"/>.
    /// </summary>
    public unsafe SteamClient(uint appId)
    {
        // the client identifies the connecting process by these, same as steam_api
        Environment.SetEnvironmentVariable("SteamAppId", appId.ToString(CultureInfo.InvariantCulture));
        Environment.SetEnvironmentVariable("SteamGameId", appId.ToString(CultureInfo.InvariantCulture));

        try
        {
            var path = GetSteamClientPath();

            try
            {
                library = NativeLibrary.Load(path);
            }
            catch (Exception exception) when (exception is DllNotFoundException or BadImageFormatException)
            {
                throw new InvalidOperationException($"Steam's client library could not be loaded from \"{path}\". Reinstalling Steam replaces it.", exception);
            }

            var createInterface = (delegate* unmanaged<byte*, int*, void*>)NativeLibrary.GetExport(library, "CreateInterface");
            getCallback = (delegate* unmanaged<int, CallbackMessage*, int*, byte>)NativeLibrary.GetExport(library, "Steam_BGetCallback");
            freeLastCallback = (delegate* unmanaged<int, byte>)NativeLibrary.GetExport(library, "Steam_FreeLastCallback");
            getApiCallResult = (delegate* unmanaged<int, ulong, void*, int, int, byte*, byte>)NativeLibrary.GetExport(library, "Steam_GetAPICallResult");

            fixed (byte* version = NullTerminated(ClientInterfaceVersion))
            {
                client = (nint)createInterface(version, null);
            }

            if (client == 0)
            {
                throw new InvalidOperationException($"Steam client does not provide {ClientInterfaceVersion}.");
            }

            pipe = ((delegate* unmanaged<void*, int>)VTable(client)[CreateSteamPipeSlot])((void*)client);

            // the library is left behind when Steam exits, so it is the pipe that tells whether Steam is up
            if (pipe == 0)
            {
                throw new SteamUnavailableException(IsSteamProcessRunning()
                    ? "Steam is running but did not accept a connection, it may still be starting up. Try again in a moment."
                    : NotRunningMessage);
            }

            user = ((delegate* unmanaged<void*, int, int>)VTable(client)[ConnectToGlobalUserSlot])((void*)client, pipe);

            if (user == 0)
            {
                throw new SteamUnavailableException("No account logged into Steam. Log in, then try again.");
            }

            User = new SteamUser(GetInterface(SteamUser.InterfaceVersion));
            UGC = new SteamUGC(GetInterface(SteamUGC.InterfaceVersion));
        }
        catch
        {
            Dispose();
            throw;
        }
    }

    /// <summary>
    /// Fetches a versioned interface for the connected user, ISteamClient::GetISteamGenericInterface.
    /// </summary>
    public unsafe nint GetInterface(string version)
    {
        nint result;

        fixed (byte* name = NullTerminated(version))
        {
            result = (nint)((delegate* unmanaged<void*, int, int, byte*, void*>)VTable(client)[GetISteamGenericInterfaceSlot])((void*)client, user, pipe, name);
        }

        return result != 0 ? result : throw new InvalidOperationException($"Steam client does not provide {version}.");
    }

    /// <summary>
    /// Pumps the pipe's callbacks until <paramref name="call"/> has finished and returns its result, <paramref name="onPoll"/> runs on every pass.
    /// </summary>
    public async Task<T> WaitForCallResultAsync<T>(ulong call, Action? onPoll = null) where T : ICallResult<T>
    {
        while (true)
        {
            var result = PumpCallbacks(call);

            if (result != null)
            {
                return T.Read(result);
            }

            onPoll?.Invoke();

            await Task.Delay(CallbackPollInterval).ConfigureAwait(false);
        }
    }

    /// <summary>
    /// Frees every pending callback, returning the result of <paramref name="call"/> if its SteamAPICallCompleted_t was among them.
    /// </summary>
    private unsafe byte[]? PumpCallbacks(ulong call)
    {
        byte[]? result = null;
        var failed = false;

        CallbackMessage message;
        int steamCall;

        while (getCallback(pipe, &message, &steamCall) != 0)
        {
            if (result == null && message.Callback == ApiCallCompletedCallback)
            {
                var completed = (ApiCallCompleted*)message.Param;

                if (completed->AsyncCall == call)
                {
                    result = new byte[completed->ParamSize];
                    byte ioFailure;

                    fixed (byte* buffer = result)
                    {
                        failed = getApiCallResult(pipe, call, buffer, result.Length, completed->Callback, &ioFailure) == 0 || ioFailure != 0;
                    }
                }
            }

            freeLastCallback(pipe);
        }

        return failed ? throw new IOException($"Steam call {call} failed.") : result;
    }

    public unsafe void Dispose()
    {
        if (disposed)
        {
            return;
        }

        disposed = true;

        if (user != 0)
        {
            ((delegate* unmanaged<void*, int, int, void>)VTable(client)[ReleaseUserSlot])((void*)client, pipe, user);
        }

        if (pipe != 0)
        {
            ((delegate* unmanaged<void*, int, byte>)VTable(client)[ReleaseSteamPipeSlot])((void*)client, pipe);
        }

        if (client != 0)
        {
            ((delegate* unmanaged<void*, byte>)VTable(client)[ShutdownIfAllPipesClosedSlot])((void*)client);
        }

        if (library != 0)
        {
            NativeLibrary.Free(library);
        }
    }

    private const string NotRunningMessage = "Steam is not running. Start Steam and log in, then try again.";

    /// <summary>Whether a Steam client process exists, which does not yet mean it is ready to talk.</summary>
    private static bool IsSteamProcessRunning()
    {
        var processes = Process.GetProcessesByName("steam");

        foreach (var process in processes)
        {
            process.Dispose();
        }

        return processes.Length > 0;
    }

    /// <summary>
    /// Where steam_api loads the client library from on each platform.
    /// </summary>
    private static string GetSteamClientPath()
    {
        string? path = null;

        if (OperatingSystem.IsWindows())
        {
            // written by the client while it is running
            path = Registry.GetValue(@"HKEY_CURRENT_USER\Software\Valve\Steam\ActiveProcess", "SteamClientDll64", null) as string;
        }
        else if (OperatingSystem.IsLinux())
        {
            path = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".steam", "sdk64", "steamclient.so");
        }

        // the path is only written once Steam has run, so without it Steam is either not installed or has never been started
        return path != null && File.Exists(path) ? path : throw new SteamUnavailableException(NotRunningMessage);
    }

    internal static unsafe void** VTable(nint instance)
    {
        return *(void***)instance;
    }

    internal static byte[] NullTerminated(string value)
    {
        return Encoding.UTF8.GetBytes(value + '\0');
    }

    /// <summary>CallbackMsg_t</summary>
    [StructLayout(LayoutKind.Sequential)]
    private unsafe struct CallbackMessage
    {
        public int User;
        public int Callback;
        public byte* Param;
        public int ParamSize;
    }

    /// <summary>SteamAPICallCompleted_t</summary>
    [StructLayout(LayoutKind.Sequential)]
    private struct ApiCallCompleted
    {
        public ulong AsyncCall;
        public int Callback;
        public uint ParamSize;
    }
}

/// <summary>
/// A call result struct, read from the bytes the client returns for a finished asynchronous call.
/// </summary>
public interface ICallResult<TSelf> where TSelf : ICallResult<TSelf>
{
    static abstract TSelf Read(ReadOnlySpan<byte> data);
}
