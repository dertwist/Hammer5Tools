namespace Hammer5Tools.Core.IO.Commands;

using System.Buffers.Binary;
using System.IO;
using System.Net.Sockets;
using System.Text;
using Hammer5Tools.Core.Commands;

/// <summary>Reads live Source 2 console output and convar definitions from VConsole.</summary>
public sealed class VConsoleClient : IDisposable
{
    private readonly int Port;
    private readonly Lock SyncLock = new();
    private readonly SemaphoreSlim SendLock = new(1);
    private readonly Dictionary<string, ConsoleVariable> Variables = new(StringComparer.OrdinalIgnoreCase);
    private CancellationTokenSource? Cts;
    private Task? ListenTask;
    private NetworkStream? Stream;
    private bool Connected;
    private string StatusValue = "VConsole disconnected";
    private int RevisionValue;

    /// <summary>Raised for each console output line.</summary>
    public event EventHandler<string>? OutputReceived;

    /// <summary>Gets whether the game has sent a VConsole greeting.</summary>
    public bool IsConnected
    {
        get
        {
            lock (SyncLock)
            {
                return Connected;
            }
        }
    }
    /// <summary>Gets the current connection status.</summary>
    public string Status
    {
        get
        {
            lock (SyncLock)
            {
                return StatusValue;
            }
        }
    }
    /// <summary>Gets the convar catalog revision.</summary>
    public int Revision
    {
        get
        {
            lock (SyncLock)
            {
                return RevisionValue;
            }
        }
    }
    /// <summary>Returns an alphabetically sorted snapshot of live convars.</summary>
    public IReadOnlyList<ConsoleVariable> Convars
    {
        get
        {
            lock (SyncLock)
            {
                return Variables.Values.OrderBy(variable => variable.Name, StringComparer.OrdinalIgnoreCase).ToArray();
            }
        }
    }

    /// <summary>Creates a client for the local game, optionally overriding the port.</summary>
    public VConsoleClient(int port = 29000) => Port = port;

    /// <summary>Starts listening and reconnects when the game restarts.</summary>
    public void Start()
    {
        if (ListenTask is not null)
        {
            return;
        }

        Cts = new CancellationTokenSource();
        var token = Cts.Token;
        ListenTask = Task.Run(() => ListenAsync(token));
    }

    /// <summary>Disconnects and releases the VConsole client slot.</summary>
    public void Stop()
    {
        Cts?.Cancel();
        try
        {
            ListenTask?.GetAwaiter().GetResult();
        }
        catch (OperationCanceledException)
        {
            // Cancellation ends pending socket reads and reconnect delays.
        }
        ListenTask = null;
        Cts?.Dispose();
        Cts = null;
    }

    /// <summary>Sends a UTF-8 command over the active VConsole connection.</summary>
    public async Task<bool> SendCommandAsync(string command, CancellationToken ct = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(command);
        var payload = Encoding.UTF8.GetBytes(command);
        if (payload.Length > ushort.MaxValue - 13 || command.Contains('\0'))
        {
            return false;
        }

        var packet = new byte[13 + payload.Length];
        "CMND"u8.CopyTo(packet);
        BinaryPrimitives.WriteUInt32BigEndian(packet.AsSpan(4), 0x00D40000);
        BinaryPrimitives.WriteUInt16BigEndian(packet.AsSpan(8), (ushort)packet.Length);
        payload.CopyTo(packet, 12);
        await SendLock.WaitAsync(ct);
        try
        {
            NetworkStream? stream;
            lock (SyncLock)
            {
                stream = Connected ? Stream : null;
            }
            if (stream is null)
            {
                return false;
            }
            await stream.WriteAsync(packet, ct);
            return true;
        }
        catch (Exception ex) when (ex is IOException or SocketException or ObjectDisposedException)
        {
            return false;
        }
        finally
        {
            SendLock.Release();
        }
    }

    private async Task ListenAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            try
            {
                using var client = new TcpClient();
                using var greetingTimeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
                greetingTimeout.CancelAfter(TimeSpan.FromSeconds(3));
                lock (SyncLock)
                {
                    StatusValue = "Connecting to VConsole…";
                }
                await client.ConnectAsync("127.0.0.1", Port, greetingTimeout.Token);
                using var stream = client.GetStream();
                lock (SyncLock)
                {
                    Stream = stream;
                }
                var header = new byte[12];
                while (!ct.IsCancellationRequested)
                {
                    var token = IsConnected ? ct : greetingTimeout.Token;
                    await stream.ReadExactlyAsync(header, token);
                    var length = BinaryPrimitives.ReadUInt16BigEndian(header.AsSpan(8));
                    if (length < 12)
                    {
                        throw new InvalidDataException("Invalid VConsole packet length.");
                    }
                    var body = new byte[length - 12];
                    await stream.ReadExactlyAsync(body, token);
                    var tag = Encoding.ASCII.GetString(header, 0, 4);
                    lock (SyncLock)
                    {
                        if (!Connected)
                        {
                            Variables.Clear();
                            RevisionValue++;
                            Connected = true;
                            StatusValue = "VConsole connected";
                        }
                    }
                    ProcessPacket(tag, body);
                }
            }
            catch (Exception ex) when (ex is IOException or InvalidDataException or SocketException or OperationCanceledException)
            {
                // The game serves one VConsole client; a silent socket can mean another client owns it.
            }
            finally
            {
                lock (SyncLock)
                {
                    Stream = null;
                    Connected = false;
                    Variables.Clear();
                    RevisionValue++;
                    StatusValue = ct.IsCancellationRequested ? "VConsole disconnected" : "VConsole unavailable — start CS2 in tools mode or close vconsole2";
                }
            }
            await Task.Delay(TimeSpan.FromSeconds(2), ct);
        }
    }

    private void ProcessPacket(string tag, byte[] body)
    {
        if (tag == "PRNT" && body.Length >= 28)
        {
            foreach (var line in ReadString(body.AsSpan(28)).Replace("\r", "").Split('\n', StringSplitOptions.RemoveEmptyEntries))
            {
                OutputReceived?.Invoke(this, line);
            }
        }
        else if (tag == "CVAR" && body.Length >= 81)
        {
            var name = ReadString(body.AsSpan(0, 64));
            if (string.IsNullOrWhiteSpace(name))
            {
                return;
            }
            lock (SyncLock)
            {
                Variables.TryGetValue(name, out var previous);
                Variables[name] = new ConsoleVariable(name,
                    BinaryPrimitives.ReadUInt32BigEndian(body.AsSpan(68)),
                    BinaryPrimitives.ReadSingleBigEndian(body.AsSpan(72)),
                    BinaryPrimitives.ReadSingleBigEndian(body.AsSpan(76)), previous?.Value);
                RevisionValue++;
            }
        }
        else if (tag == "CFGV" && body.Length >= 129)
        {
            var name = ReadString(body.AsSpan(0, 64));
            lock (SyncLock)
            {
                if (Variables.TryGetValue(name, out var variable))
                {
                    Variables[name] = variable with { Value = ReadString(body.AsSpan(64, 65)) };
                    RevisionValue++;
                }
            }
        }
    }

    private static string ReadString(ReadOnlySpan<byte> bytes)
    {
        var terminator = bytes.IndexOf((byte)0);
        return Encoding.UTF8.GetString(terminator < 0 ? bytes : bytes[..terminator]);
    }

    /// <inheritdoc/>
    public void Dispose()
    {
        Stop();
        SendLock.Dispose();
    }
}
