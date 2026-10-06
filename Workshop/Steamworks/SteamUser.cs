namespace Steamworks;

/// <summary>
/// The logged in account, on ISteamUser.
/// </summary>
public sealed class SteamUser
{
    /// <summary>ISteamUser version whose layout is used below, the client keeps serving old versions.</summary>
    public const string InterfaceVersion = "SteamUser023";

    private const int GetSteamIDSlot = 2;

    private readonly nint instance;

    internal SteamUser(nint instance)
    {
        this.instance = instance;
    }

    private unsafe void** VTable => SteamClient.VTable(instance);

    /// <summary>
    /// The 64 bit id of the logged in account.
    /// </summary>
    public unsafe ulong GetSteamId()
    {
        if (OperatingSystem.IsWindows())
        {
            // CSteamID has constructors, so MSVC returns it through a hidden pointer instead of in a register
            ulong steamId;
            ((delegate* unmanaged<void*, ulong*, ulong*>)VTable[GetSteamIDSlot])((void*)instance, &steamId);
            return steamId;
        }

        return ((delegate* unmanaged<void*, ulong>)VTable[GetSteamIDSlot])((void*)instance);
    }

    /// <summary>
    /// The account id, which is the low 32 bits of the steam id.
    /// </summary>
    public uint GetAccountId()
    {
        return (uint)GetSteamId();
    }
}
