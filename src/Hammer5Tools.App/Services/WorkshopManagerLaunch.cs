namespace Hammer5Tools.App.Services;

using System.Diagnostics;

/// <summary>Starts the bundled upstream application with its own UI and Steam lifecycle.</summary>
public static class WorkshopManagerLaunch
{
    public static ProcessStartInfo CreateStartInfo(string applicationDirectory)
    {
        var directory = Path.Combine(applicationDirectory, "WorkshopManager");
        var executable = Path.Combine(directory, OperatingSystem.IsWindows() ? "CS2WorkshopManager-GUI.exe" : "CS2WorkshopManager-GUI");
        if (File.Exists(executable))
        {
            return new ProcessStartInfo(executable) { WorkingDirectory = directory, UseShellExecute = false };
        }

        var assembly = Path.Combine(directory, "CS2WorkshopManager-GUI.dll");
        if (!File.Exists(assembly))
        {
            throw new FileNotFoundException("The bundled Workshop Manager is missing. Rebuild or reinstall Hammer5Tools.", assembly);
        }

        var start = new ProcessStartInfo("dotnet") { WorkingDirectory = directory, UseShellExecute = false };
        start.ArgumentList.Add(assembly);
        return start;
    }
}
