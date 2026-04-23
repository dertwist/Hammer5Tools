using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Linq;

namespace Hammer5ToolsUpdater
{
    public partial class UpdaterForm : Form
    {
        private ProgressBar progressBar;
        private Label statusLabel;
        private Button installButton;
        private Button skipButton;
        private string? latestVersion;
        private string? downloadUrl;

        public UpdaterForm()
        {
            InitializeComponent();
            CheckForUpdates();
        }

        private void InitializeComponent()
        {
            this.progressBar = new ProgressBar { Left = 20, Top = 50, Width = 260 };
            this.statusLabel = new Label { Left = 20, Top = 20, Width = 260, Text = "Checking for updates..." };
            this.installButton = new Button { Left = 50, Top = 90, Text = "Install", Visible = false };
            this.skipButton = new Button { Left = 150, Top = 90, Text = "Skip", Visible = false };

            this.Controls.Add(progressBar);
            this.Controls.Add(statusLabel);
            this.Controls.Add(installButton);
            this.Controls.Add(skipButton);

            this.Width = 320;
            this.Height = 170;
            this.Text = "Hammer5Tools Updater";
            this.StartPosition = FormStartPosition.CenterScreen;
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;

            this.installButton.Click += (s, e) => StartUpdate();
            this.skipButton.Click += (s, e) => Application.Exit();
        }

        private async void CheckForUpdates()
        {
            try
            {
                using var client = new HttpClient();
                client.DefaultRequestHeaders.Add("User-Agent", "Hammer5ToolsUpdater");
                var response = await client.GetStringAsync("https://api.github.com/repos/dertwist/Hammer5Tools/releases/tags/dev");
                using var doc = JsonDocument.Parse(response);
                var root = doc.RootElement;

                string tagName = root.GetProperty("name").GetString() ?? ""; 
                var match = System.Text.RegularExpressions.Regex.Match(tagName, @"v(\d+\.\d+\.\d+)");
                if (match.Success) 
                    latestVersion = match.Groups[1].Value;
                else
                    latestVersion = tagName;

                var assets = root.GetProperty("assets");
                foreach (var asset in assets.EnumerateArray())
                {
                    if (asset.GetProperty("name").GetString() == "hammer5tools.zip")
                    {
                        downloadUrl = asset.GetProperty("browser_download_url").GetString();
                        break;
                    }
                }

                if (downloadUrl == null)
                {
                    Application.Exit();
                    return;
                }

                string localVersion = "0.0.0";
                // version.txt is in app/ relative to updater
                string versionFile = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "app", "version.txt");
                if (File.Exists(versionFile)) localVersion = File.ReadAllText(versionFile).Trim();

                if (latestVersion != localVersion)
                {
                    statusLabel.Text = $"New version available: {latestVersion}";
                    installButton.Visible = true;
                    skipButton.Visible = true;
                }
                else
                {
                    Application.Exit();
                }
            }
            catch (Exception)
            {
                Application.Exit();
            }
        }

        private async void StartUpdate()
        {
            if (downloadUrl == null) return;
            
            installButton.Enabled = false;
            skipButton.Enabled = false;
            statusLabel.Text = "Downloading update...";

            try
            {
                string zipPath = Path.Combine(Path.GetTempPath(), "hammer5tools_update.zip");
                using (var client = new HttpClient())
                {
                    var response = await client.GetAsync(downloadUrl);
                    using (var fs = new FileStream(zipPath, FileMode.Create))
                    {
                        await response.Content.CopyToAsync(fs);
                    }
                }

                statusLabel.Text = "Waiting for Hammer5Tools to exit...";
                while (Process.GetProcessesByName("Hammer5Tools").Any())
                {
                    await Task.Delay(1000);
                }

                statusLabel.Text = "Extracting update...";
                string appDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "app");
                
                if (!Directory.Exists(appDir)) Directory.CreateDirectory(appDir);

                await Task.Run(() => {
                    using (ZipArchive archive = ZipFile.OpenRead(zipPath))
                    {
                        foreach (ZipArchiveEntry entry in archive.Entries)
                        {
                            string destinationPath = Path.GetFullPath(Path.Combine(appDir, entry.FullName));
                            
                            if (entry.FullName.EndsWith("/") || entry.FullName.EndsWith("\\")) 
                            {
                                Directory.CreateDirectory(destinationPath);
                                continue;
                            }
                            
                            Directory.CreateDirectory(Path.GetDirectoryName(destinationPath)!);
                            entry.ExtractToFile(destinationPath, true);
                        }
                    }
                });

                if (latestVersion != null)
                {
                    File.WriteAllText(Path.Combine(appDir, "version.txt"), latestVersion);
                }

                statusLabel.Text = "Update complete! Restarting...";
                await Task.Delay(1500);

                string launcherPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Hammer5ToolsLauncher.exe");
                if (File.Exists(launcherPath))
                {
                    Process.Start(launcherPath);
                }
                Application.Exit();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Update failed: {ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                Application.Exit();
            }
        }
    }
}
