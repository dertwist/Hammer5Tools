using System;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Text;
using System.Text.Json;
using System.Collections.Generic;

namespace Hammer5ToolsLauncher
{
    class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            string command = "show";
            string? filePath = null;
            string? editorType = "smartprop";

            if (args.Length > 0)
            {
                if (args[0] == "--create-vmdl" && args.Length > 1)
                {
                    command = "create_vmdl";
                    filePath = args[1];
                }
                else if (args[0] == "--create-vmat" && args.Length > 1)
                {
                    command = "create_vmat";
                    filePath = args[1];
                }
                else if (!args[0].StartsWith("-"))
                {
                    command = "open_file";
                    filePath = Path.GetFullPath(args[0]);
                    string ext = Path.GetExtension(filePath).ToLower();
                    if (ext == ".vsndevts") editorType = "soundevent";
                }
            }

            var messageObj = new Dictionary<string, object?>();
            messageObj["command"] = command;
            if (filePath != null) messageObj["file_path"] = filePath;
            if (editorType != null) messageObj["editor_type"] = editorType;

            string jsonMessage = JsonSerializer.Serialize(messageObj);

            using (var client = new NamedPipeClientStream(".", "Hammer5ToolsIPC", PipeDirection.Out))
            {
                try
                {
                    client.Connect(200);
                    byte[] messageBytes = Encoding.UTF8.GetBytes(jsonMessage);
                    client.Write(messageBytes, 0, messageBytes.Length);
                    client.Flush();
                    return;
                }
                catch (TimeoutException)
                {
                    // No instance running
                }
                catch (Exception)
                {
                    // Other errors
                }
            }

            // Start new process
            string appDir = AppDomain.CurrentDomain.BaseDirectory;
            string exePath = Path.Combine(appDir, "app", "Hammer5Tools.exe");

            if (File.Exists(exePath))
            {
                ProcessStartInfo startInfo = new ProcessStartInfo(exePath);
                foreach (string arg in args)
                {
                    startInfo.ArgumentList.Add(arg);
                }
                Process.Start(startInfo);

                // Phase 3: Launch updater
                string updaterPath = Path.Combine(appDir, "Hammer5ToolsUpdater.exe");
                if (File.Exists(updaterPath))
                {
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = updaterPath,
                        CreateNoWindow = true,
                        UseShellExecute = false
                    });
                }
            }
            else
            {
                // Fallback for direct dist execution without installer layout
                string altExePath = Path.Combine(appDir, "Hammer5Tools", "Hammer5Tools.exe");
                if (File.Exists(altExePath))
                {
                    ProcessStartInfo startInfo = new ProcessStartInfo(altExePath);
                    foreach (string arg in args)
                    {
                        startInfo.ArgumentList.Add(arg);
                    }
                    Process.Start(startInfo);
                }
            }
        }
    }
}
