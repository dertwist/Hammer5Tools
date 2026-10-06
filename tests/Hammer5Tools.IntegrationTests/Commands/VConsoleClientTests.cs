namespace Hammer5Tools.IntegrationTests.Commands;

using System.Buffers.Binary;
using System.Net;
using System.Net.Sockets;
using System.Text;
using Hammer5Tools.Core.IO.Commands;

public class VConsoleClientTests
{
    [Test]
    public async Task ReadsFragmentedUnicodeOutputAndLiveConvarsAndSendsCommands()
    {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        using var server = new TcpListener(IPAddress.Loopback, 0);
        server.Start();
        using var client = new VConsoleClient(((IPEndPoint)server.LocalEndpoint).Port);
        var output = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
        client.OutputReceived += (_, line) => output.TrySetResult(line);
        client.Start();
        using var peer = await server.AcceptTcpClientAsync(timeout.Token);
        using var stream = peer.GetStream();
        var convar = new byte[81];
        Encoding.UTF8.GetBytes("sv_gravity").CopyTo(convar, 0);
        BinaryPrimitives.WriteUInt32BigEndian(convar.AsSpan(68), 0x4000);
        BinaryPrimitives.WriteSingleBigEndian(convar.AsSpan(72), -100);
        BinaryPrimitives.WriteSingleBigEndian(convar.AsSpan(76), 1000);
        var packet = Packet("CVAR", convar);
        foreach (var part in packet.Chunk(3)) { await stream.WriteAsync(part, timeout.Token); }
        var value = new byte[129];
        Encoding.UTF8.GetBytes("sv_gravity").CopyTo(value, 0);
        Encoding.UTF8.GetBytes("800").CopyTo(value, 64);
        await stream.WriteAsync(Packet("CFGV", value), timeout.Token);
        var message = new byte[28].Concat(Encoding.UTF8.GetBytes("Hello æ世界\n\0")).ToArray();
        await stream.WriteAsync(Packet("PRNT", message), timeout.Token);
        await Assert.That(await output.Task.WaitAsync(timeout.Token)).IsEqualTo("Hello æ世界");
        var variable = client.Convars.Single();
        await Assert.That(variable.Name).IsEqualTo("sv_gravity");
        await Assert.That(variable.Flags).IsEqualTo(0x4000u);
        await Assert.That(variable.Minimum).IsEqualTo(-100f);
        await Assert.That(variable.Maximum).IsEqualTo(1000f);
        await Assert.That(variable.Value).IsEqualTo("800");
        await Assert.That(await client.SendCommandAsync("echo æ世界", timeout.Token)).IsTrue();
        var header = new byte[12];
        await stream.ReadExactlyAsync(header, timeout.Token);
        await Assert.That(Encoding.ASCII.GetString(header, 0, 4)).IsEqualTo("CMND");
        await Assert.That(BinaryPrimitives.ReadUInt32BigEndian(header.AsSpan(4))).IsEqualTo(0x00D40000u);
        var body = new byte[BinaryPrimitives.ReadUInt16BigEndian(header.AsSpan(8)) - 12];
        await stream.ReadExactlyAsync(body, timeout.Token);
        await Assert.That(Encoding.UTF8.GetString(body)).IsEqualTo("echo æ世界\0");
        client.Stop();
        await Assert.That(client.IsConnected).IsFalse();
        await Assert.That(client.Convars.Count).IsEqualTo(0);
        await Assert.That(await client.SendCommandAsync("status")).IsFalse();
    }

    [Test]
    public async Task RejectsMalformedLengthsAndReconnectsAfterStop()
    {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        using var server = new TcpListener(IPAddress.Loopback, 0);
        server.Start();
        using var client = new VConsoleClient(((IPEndPoint)server.LocalEndpoint).Port);
        client.Start();
        using (var peer = await server.AcceptTcpClientAsync(timeout.Token))
        {
            var malformed = Packet("PRNT", []);
            BinaryPrimitives.WriteUInt16BigEndian(malformed.AsSpan(8), 1);
            await peer.GetStream().WriteAsync(malformed, timeout.Token);
            var eof = new byte[1];
            await Assert.That(await peer.GetStream().ReadAsync(eof, timeout.Token)).IsEqualTo(0);
        }
        client.Stop();
        client.Start();
        using var reconnected = await server.AcceptTcpClientAsync(timeout.Token);
        var output = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
        client.OutputReceived += (_, line) => output.TrySetResult(line);
        await reconnected.GetStream().WriteAsync(Packet("PRNT", new byte[28].Concat("reconnected\0"u8.ToArray()).ToArray()), timeout.Token);
        await Assert.That(await output.Task.WaitAsync(timeout.Token)).IsEqualTo("reconnected");
    }

    private static byte[] Packet(string tag, byte[] body)
    {
        var packet = new byte[12 + body.Length];
        Encoding.ASCII.GetBytes(tag).CopyTo(packet, 0);
        BinaryPrimitives.WriteUInt16BigEndian(packet.AsSpan(8), (ushort)packet.Length);
        body.CopyTo(packet, 12);
        return packet;
    }
}
