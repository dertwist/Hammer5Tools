using System.Diagnostics;
using Hammer5Tools.Core.IO.Toolchain;

namespace Hammer5Tools.Core.Tests;

public sealed class AutomationProcessTests
{
    [Test]
    public async Task CancellationStopsOwnedProcessAndDrainsOutput()
    {
        using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        var processId = 0;
        var runner = new ProcessRunner();
        var emitted = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        runner.OnOutput += _ => emitted.TrySetResult();
        var task = runner.RunAsync("powershell.exe", "", null, null, null, cancellation.Token,
            argumentList: ["-NoProfile", "-NonInteractive", "-Command", "Write-Output 'Fixture 模型'; Start-Sleep -Seconds 30"],
            onStarted: process => processId = process.Id);
        await emitted.Task.WaitAsync(TimeSpan.FromSeconds(5));
        cancellation.Cancel();
        await Assert.That(async () => await task).Throws<OperationCanceledException>();
        var alive = false;
        try
        {
            using var process = Process.GetProcessById(processId);
            alive = !process.HasExited;
        }
        catch (ArgumentException) { }
        await Assert.That(alive).IsFalse();
    }
}
