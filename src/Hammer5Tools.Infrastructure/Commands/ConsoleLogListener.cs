namespace Hammer5Tools.Infrastructure.Commands;

using System.IO;
using System.Text;
using Microsoft.Extensions.Logging;

/// <summary>
/// Asynchronously tails the CS2 console log file and notifies listeners on every line.
/// </summary>
public class ConsoleLogListener : IDisposable
{
    private readonly string LogFilePath;
    private readonly ILogger? Logger;
    private readonly CancellationTokenSource Cts = new();
    private Task? TailTask;

    public event EventHandler<string>? LineReceived;

    public ConsoleLogListener(string logFilePath, ILogger? logger = null)
    {
        LogFilePath = logFilePath;
        Logger = logger;
    }

    public void Start()
    {
        if (TailTask is not null)
        {
            return;
        }

        TailTask = Task.Run(() => TailLoopAsync(Cts.Token));
    }

    public void Stop()
    {
        Cts.Cancel();
        try
        {
            TailTask?.Wait(TimeSpan.FromSeconds(1));
        }
        catch
        {
            // Ignore cancellation/timeout
        }
    }

    private async Task TailLoopAsync(CancellationToken ct)
    {
        long lastPosition = 0;

        while (!ct.IsCancellationRequested)
        {
            try
            {
                if (!File.Exists(LogFilePath))
                {
                    lastPosition = 0;
                    await Task.Delay(200, ct);
                    continue;
                }

                using var stream = new FileStream(LogFilePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
                var length = stream.Length;

                if (length < lastPosition)
                {
                    // File was truncated or recreated
                    lastPosition = 0;
                }

                if (length > lastPosition)
                {
                    stream.Seek(lastPosition, SeekOrigin.Begin);
                    using var reader = new StreamReader(stream, Encoding.UTF8, detectEncodingFromByteOrderMarks: true, bufferSize: 4096, leaveOpen: true);

                    while (await reader.ReadLineAsync(ct) is { } line)
                    {
                        LineReceived?.Invoke(this, line);
                    }

                    lastPosition = stream.Position;
                }
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                Logger?.LogDebug(ex, "Error reading log file {Path}", LogFilePath);
            }

            await Task.Delay(100, ct);
        }
    }

    public void Dispose()
    {
        Stop();
        Cts.Dispose();
        GC.SuppressFinalize(this);
    }
}
