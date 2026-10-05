namespace Hammer5Tools.App.Services.Lifecycle;

/// <summary>
/// Mutex-based single-instance application guard.
/// </summary>
public class SingleInstanceGuard : IDisposable
{
    private const string MutexName = "Local\\Hammer5Tools_SingleInstance_Mutex";

    private readonly Mutex? InstanceMutex;
    private readonly bool HasHandle;

    public bool IsFirstInstance => HasHandle;

    public SingleInstanceGuard()
    {
        try
        {
            InstanceMutex = new Mutex(initiallyOwned: true, MutexName, out var createdNew);
            HasHandle = createdNew;
        }
        catch
        {
            HasHandle = true; // Fallback to allowing startup if mutex creation fails
        }
    }

    public void Dispose()
    {
        if (HasHandle)
        {
            try
            {
                InstanceMutex?.ReleaseMutex();
            }
            catch
            {
                // Ignore release errors
            }
        }

        InstanceMutex?.Dispose();
        GC.SuppressFinalize(this);
    }
}
