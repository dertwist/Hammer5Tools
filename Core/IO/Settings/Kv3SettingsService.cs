namespace Hammer5Tools.Core.IO.Settings;

using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Json;
using Hammer5Tools.Core.MapBuilder;
using Hammer5Tools.Core.Settings;
using Microsoft.Extensions.Logging;
using ValveKeyValue;

/// <summary>
/// KV3-based settings service implementing atomic file persistence and thread-safe access.
/// Persists settings as KeyValues3 (settings.kv3) and transparently migrates legacy settings.json and settings.ini.
/// </summary>
public class Kv3SettingsService : ISettingsService
{
    private static readonly KVSerializer Kv3Serializer = KVSerializer.Create(KVSerializationFormat.KeyValues3Text);

    private readonly string SettingsFilePath;
    private readonly string LegacyJsonPath;
    private readonly string LegacyIniPath;
    private readonly ILogger<Kv3SettingsService>? Logger;
    private readonly Lock SyncLock = new();

    private AppSettings CurrentSettings;

    public AppSettings Settings
    {
        get
        {
            lock (SyncLock)
            {
                return CurrentSettings;
            }
        }
    }

    public event EventHandler<AppSettings>? SettingsChanged;

    public Kv3SettingsService(string? customSettingsPath = null, ILogger<Kv3SettingsService>? logger = null)
    {
        Logger = logger;
        CurrentSettings = new AppSettings();

        if (!string.IsNullOrWhiteSpace(customSettingsPath))
        {
            SettingsFilePath = customSettingsPath;
            var directory = Path.GetDirectoryName(customSettingsPath) ?? string.Empty;
            LegacyJsonPath = Path.Combine(directory, "settings.json");
            LegacyIniPath = Path.Combine(directory, "settings.ini");
        }
        else
        {
            var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            var defaultDir = Path.Combine(appData, "Hammer5Tools");
            SettingsFilePath = Path.Combine(defaultDir, "settings.kv3");
            LegacyJsonPath = Path.Combine(defaultDir, "settings.json");
            LegacyIniPath = Path.Combine(defaultDir, "settings.ini");
        }

        Load();
    }

    /// <inheritdoc/>
    public void Load()
    {
        lock (SyncLock)
        {
            if (File.Exists(SettingsFilePath))
            {
                try
                {
                    using var stream = new FileStream(SettingsFilePath, FileMode.Open, FileAccess.Read, FileShare.Read);
                    var kvDoc = Kv3Serializer.Deserialize(stream);
                    if (kvDoc?.Root is not null)
                    {
                        CurrentSettings = DeserializeFromKv(kvDoc.Root);
                        return;
                    }
                }
                catch (Exception ex)
                {
                    Logger?.LogWarning(ex, "Failed to read settings from KV3 file {Path}, falling back to migration/defaults", SettingsFilePath);
                }
            }

            // Fallback 1: migrate from legacy JSON file if present
            if (File.Exists(LegacyJsonPath))
            {
                try
                {
                    using var stream = new FileStream(LegacyJsonPath, FileMode.Open, FileAccess.Read, FileShare.Read);
                    var deserialized = JsonSerializer.Deserialize(stream, SettingsJsonContext.Default.AppSettings);
                    if (deserialized is not null)
                    {
                        stream.Position = 0;
                        using var document = JsonDocument.Parse(stream);
                        if (document.RootElement.TryGetProperty("editor", out var editor))
                        {
                            if (!editor.TryGetProperty("launchOptions", out _))
                            {
                                var launch = Core.Cs2.LaunchOptions.FromLegacy(deserialized.Editor.CustomLaunchArgs);
                                launch.Options.OpenTools = true;
                                launch.Options.Insecure = true;
                                if (string.Equals(launch.CustomArgs, deserialized.Editor.CustomLaunchArgs?.Trim(), StringComparison.Ordinal))
                                {
                                    launch.Options.OpenMap = true;
                                    launch.Options.Steam = true;
                                    launch.Options.Retail = true;
                                    launch.Options.GpuRayTracing = true;
                                }
                                deserialized.Editor.LaunchOptions = launch.Options;
                                deserialized.Editor.CustomLaunchArgs = launch.CustomArgs;
                            }
                            else if (editor.TryGetProperty("launchOptions", out var lo))
                            {
                                if (!lo.TryGetProperty("openMap", out _) && !lo.TryGetProperty("OpenMap", out _))
                                {
                                    deserialized.Editor.LaunchOptions.OpenMap = true;
                                }
                                else if (!deserialized.Editor.LaunchOptions.OpenMap
                                         && !deserialized.Editor.LaunchOptions.Steam
                                         && !deserialized.Editor.LaunchOptions.Retail
                                         && !deserialized.Editor.LaunchOptions.GpuRayTracing
                                         && deserialized.Editor.LaunchOptions.OpenTools
                                         && deserialized.Editor.LaunchOptions.Insecure)
                                {
                                    deserialized.Editor.LaunchOptions.OpenMap = true;
                                    deserialized.Editor.LaunchOptions.Steam = true;
                                    deserialized.Editor.LaunchOptions.Retail = true;
                                    deserialized.Editor.LaunchOptions.GpuRayTracing = true;
                                }
                            }
                        }
                        CurrentSettings = deserialized;
                        SaveInternal();
                        return;
                    }
                }
                catch (Exception ex)
                {
                    Logger?.LogWarning(ex, "Failed to migrate settings from legacy JSON {Path}", LegacyJsonPath);
                }
            }

            // Fallback 2: migrate from legacy INI file if present
            CurrentSettings = new AppSettings();
            var migrator = new LegacySettingsMigrator(Logger);
            if (migrator.TryMigrate(LegacyIniPath, CurrentSettings))
            {
                SaveInternal();
            }
        }
    }

    /// <inheritdoc/>
    public void Save()
    {
        lock (SyncLock)
        {
            SaveInternal();
        }

        SettingsChanged?.Invoke(this, Settings);
    }

    /// <inheritdoc/>
    public void Update(Action<AppSettings> updateAction)
    {
        ArgumentNullException.ThrowIfNull(updateAction);

        lock (SyncLock)
        {
            updateAction(CurrentSettings);
            SaveInternal();
        }

        SettingsChanged?.Invoke(this, Settings);
    }

    private void SaveInternal()
    {
        var targetDirectory = Path.GetDirectoryName(SettingsFilePath);
        if (!string.IsNullOrEmpty(targetDirectory) && !Directory.Exists(targetDirectory))
        {
            Directory.CreateDirectory(targetDirectory);
        }

        var tempPath = $"{SettingsFilePath}.tmp.{Guid.NewGuid():N}";

        try
        {
            var root = SerializeToKv(CurrentSettings);
            var header = new KVHeader();
            var document = new KVDocument(header, "AppSettings", root);

            using (var stream = new FileStream(tempPath, FileMode.Create, FileAccess.Write, FileShare.None))
            {
                Kv3Serializer.Serialize(stream, document);
                stream.Flush(true);
            }

            File.Move(tempPath, SettingsFilePath, overwrite: true);
        }
        catch (Exception ex)
        {
            Logger?.LogError(ex, "Failed to atomically write settings to {Path}", SettingsFilePath);
            if (File.Exists(tempPath))
            {
                try
                {
                    File.Delete(tempPath);
                }
                catch
                {
                    // Ignore temp file cleanup errors
                }
            }

            throw;
        }
    }

    private static KVObject SerializeToKv(AppSettings s)
    {
        var root = KVObject.Collection();

        if (s.SelectedAddon is not null) root["selectedAddon"] = new KVObject(s.SelectedAddon);
        if (s.Cs2PathOverride is not null) root["cs2PathOverride"] = new KVObject(s.Cs2PathOverride);
        root["theme"] = new KVObject(s.Theme);
        root["updateChannel"] = new KVObject(s.UpdateChannel);
        root["archivePath"] = new KVObject(s.ArchivePath);
        if (s.SelectedAddonPreset is not null) root["selectedAddonPreset"] = new KVObject(s.SelectedAddonPreset);

        // Window state
        var ws = KVObject.Collection();
        if (s.WindowState.X.HasValue) ws["x"] = new KVObject(s.WindowState.X.Value);
        if (s.WindowState.Y.HasValue) ws["y"] = new KVObject(s.WindowState.Y.Value);
        ws["width"] = new KVObject(s.WindowState.Width);
        ws["height"] = new KVObject(s.WindowState.Height);
        ws["isMaximized"] = new KVObject(s.WindowState.IsMaximized);
        root["windowState"] = ws;

        // Editor preferences
        var ed = KVObject.Collection();
        ed["generateGitCommitMessages"] = new KVObject(s.Editor.GenerateGitCommitMessages);
        ed["loadingUseSavedCameras"] = new KVObject(s.Editor.LoadingUseSavedCameras);
        ed["smartPropDisplayIds"] = new KVObject(s.Editor.SmartPropDisplayIds);
        ed["smartPropHideExperimental"] = new KVObject(s.Editor.SmartPropHideExperimental);
        ed["smartPropRoundVmapValues"] = new KVObject(s.Editor.SmartPropRoundVmapValues);
        ed["smartPropRoundDecimals"] = new KVObject(s.Editor.SmartPropRoundDecimals);
        ed["smartPropMsaa"] = new KVObject(s.Editor.SmartPropMsaa);
        ed["assetGroupMonitorPaths"] = new KVObject(s.Editor.AssetGroupMonitorPaths);
        ed["assetGroupAutoRefresh"] = new KVObject(s.Editor.AssetGroupAutoRefresh);
        ed["soundEventPlayOnClick"] = new KVObject(s.Editor.SoundEventPlayOnClick);
        ed["launchNcmMode"] = new KVObject(s.Editor.LaunchNcmMode);
        ed["minimizeToTray"] = new KVObject(s.Editor.MinimizeToTray);
        ed["customLaunchArgs"] = new KVObject(s.Editor.CustomLaunchArgs);

        var lo = KVObject.Collection();
        lo["openTools"] = new KVObject(s.Editor.LaunchOptions.OpenTools);
        lo["openMap"] = new KVObject(s.Editor.LaunchOptions.OpenMap);
        lo["steam"] = new KVObject(s.Editor.LaunchOptions.Steam);
        lo["retail"] = new KVObject(s.Editor.LaunchOptions.Retail);
        lo["gpuRayTracing"] = new KVObject(s.Editor.LaunchOptions.GpuRayTracing);
        lo["insecure"] = new KVObject(s.Editor.LaunchOptions.Insecure);
        lo["noCustomerMachine"] = new KVObject(s.Editor.LaunchOptions.NoCustomerMachine);
        ed["launchOptions"] = lo;

        root["editor"] = ed;

        // Workspace layouts
        if (s.WorkspaceLayouts.Count > 0)
        {
            var layouts = KVObject.Collection();
            foreach (var (k, v) in s.WorkspaceLayouts)
            {
                layouts[k] = new KVObject(v);
            }
            root["workspaceLayouts"] = layouts;
        }

        // Map build presets
        if (s.MapBuildPresets.Count > 0)
        {
            var presetsList = new List<KVObject>();
            foreach (var preset in s.MapBuildPresets)
            {
                var p = KVObject.Collection();
                p["name"] = new KVObject(preset.Name);

                var opt = KVObject.Collection();
                opt["threads"] = new KVObject(preset.Options.Threads);
                opt["saveMapPath"] = new KVObject(preset.Options.SaveMapPath);
                opt["saveBuildLogs"] = new KVObject(preset.Options.SaveBuildLogs);
                opt["clearVradCache"] = new KVObject(preset.Options.ClearVradCache);
                opt["quiet"] = new KVObject(preset.Options.Quiet);
                opt["buildWorld"] = new KVObject(preset.Options.BuildWorld);
                opt["entitiesOnly"] = new KVObject(preset.Options.EntitiesOnly);
                opt["noSettle"] = new KVObject(preset.Options.NoSettle);
                opt["bakeLighting"] = new KVObject(preset.Options.BakeLighting);
                opt["lightmapResolution"] = new KVObject(preset.Options.LightmapResolution);
                opt["lightmapQuality"] = new KVObject(preset.Options.LightmapQuality);
                opt["lightmapCompression"] = new KVObject(preset.Options.LightmapCompression);
                opt["noiseRemoval"] = new KVObject(preset.Options.NoiseRemoval);
                opt["noLightCalculations"] = new KVObject(preset.Options.NoLightCalculations);
                opt["largeBlockSize"] = new KVObject(preset.Options.LargeBlockSize);
                opt["buildPhysics"] = new KVObject(preset.Options.BuildPhysics);
                opt["legacyCollisionMesh"] = new KVObject(preset.Options.LegacyCollisionMesh);
                opt["buildVisibility"] = new KVObject(preset.Options.BuildVisibility);
                opt["debugVisibility"] = new KVObject(preset.Options.DebugVisibility);
                opt["buildNavigation"] = new KVObject(preset.Options.BuildNavigation);
                opt["debugNavigation"] = new KVObject(preset.Options.DebugNavigation);
                opt["gridNavigation"] = new KVObject(preset.Options.GridNavigation);
                opt["buildReverb"] = new KVObject(preset.Options.BuildReverb);
                opt["buildAudioPaths"] = new KVObject(preset.Options.BuildAudioPaths);
                opt["bakeCustomAudio"] = new KVObject(preset.Options.BakeCustomAudio);
                opt["audioThreads"] = new KVObject(preset.Options.AudioThreads);
                opt["launchAfterBuild"] = new KVObject(preset.Options.LaunchAfterBuild);
                opt["buildCubemaps"] = new KVObject(preset.Options.BuildCubemaps);
                p["options"] = opt;

                var maps = preset.Maps.Select(m => new KVObject(m)).ToArray();
                p["maps"] = KVObject.Array(maps);

                presetsList.Add(p);
            }
            root["mapBuildPresets"] = KVObject.Array(presetsList.ToArray());
        }

        return root;
    }

    private static AppSettings DeserializeFromKv(KVObject root)
    {
        var s = new AppSettings();

        if (TryGetString(root, "selectedAddon", out var addon)) s.SelectedAddon = addon;
        if (TryGetString(root, "cs2PathOverride", out var cs2Path)) s.Cs2PathOverride = cs2Path;
        if (TryGetString(root, "theme", out var theme)) s.Theme = theme;
        if (TryGetString(root, "updateChannel", out var uc)) s.UpdateChannel = uc;
        if (TryGetString(root, "archivePath", out var ap)) s.ArchivePath = ap;
        if (TryGetString(root, "selectedAddonPreset", out var sap)) s.SelectedAddonPreset = sap;

        // Window state
        if (root.TryGetValue("windowState", out var ws) && ws is not null)
        {
            if (TryGetDouble(ws, "x", out var x)) s.WindowState.X = x;
            if (TryGetDouble(ws, "y", out var y)) s.WindowState.Y = y;
            if (TryGetDouble(ws, "width", out var w)) s.WindowState.Width = w;
            if (TryGetDouble(ws, "height", out var h)) s.WindowState.Height = h;
            if (TryGetBool(ws, "isMaximized", out var max)) s.WindowState.IsMaximized = max;
        }

        // Editor preferences
        if (root.TryGetValue("editor", out var ed) && ed is not null)
        {
            if (TryGetBool(ed, "generateGitCommitMessages", out var git)) s.Editor.GenerateGitCommitMessages = git;
            if (TryGetBool(ed, "loadingUseSavedCameras", out var cam)) s.Editor.LoadingUseSavedCameras = cam;
            if (TryGetBool(ed, "smartPropDisplayIds", out var spIds)) s.Editor.SmartPropDisplayIds = spIds;
            if (TryGetBool(ed, "smartPropHideExperimental", out var exp)) s.Editor.SmartPropHideExperimental = exp;
            if (TryGetBool(ed, "smartPropRoundVmapValues", out var round)) s.Editor.SmartPropRoundVmapValues = round;
            if (TryGetInt(ed, "smartPropRoundDecimals", out var dec)) s.Editor.SmartPropRoundDecimals = dec;
            if (TryGetInt(ed, "smartPropMsaa", out var msaa)) s.Editor.SmartPropMsaa = msaa;
            if (TryGetString(ed, "assetGroupMonitorPaths", out var agp)) s.Editor.AssetGroupMonitorPaths = agp;
            if (TryGetBool(ed, "assetGroupAutoRefresh", out var agar)) s.Editor.AssetGroupAutoRefresh = agar;
            if (TryGetBool(ed, "soundEventPlayOnClick", out var play)) s.Editor.SoundEventPlayOnClick = play;
            if (TryGetBool(ed, "launchNcmMode", out var ncm)) s.Editor.LaunchNcmMode = ncm;
            if (TryGetBool(ed, "minimizeToTray", out var tray)) s.Editor.MinimizeToTray = tray;
            if (TryGetString(ed, "customLaunchArgs", out var args)) s.Editor.CustomLaunchArgs = args;

            if (ed.TryGetValue("launchOptions", out var lo) && lo is not null)
            {
                if (TryGetBool(lo, "openTools", out var ot)) s.Editor.LaunchOptions.OpenTools = ot;
                if (TryGetBool(lo, "openMap", out var om)) s.Editor.LaunchOptions.OpenMap = om;
                if (TryGetBool(lo, "steam", out var st)) s.Editor.LaunchOptions.Steam = st;
                if (TryGetBool(lo, "retail", out var rt)) s.Editor.LaunchOptions.Retail = rt;
                if (TryGetBool(lo, "gpuRayTracing", out var grt)) s.Editor.LaunchOptions.GpuRayTracing = grt;
                if (TryGetBool(lo, "insecure", out var ins)) s.Editor.LaunchOptions.Insecure = ins;
                if (TryGetBool(lo, "noCustomerMachine", out var nom)) s.Editor.LaunchOptions.NoCustomerMachine = nom;
            }
        }

        // Workspace layouts
        if (root.TryGetValue("workspaceLayouts", out var layouts) && layouts is not null)
        {
            foreach (var (k, v) in layouts.Children)
            {
                s.WorkspaceLayouts[k] = v.ToString() ?? string.Empty;
            }
        }

        // Map build presets
        if (root.TryGetValue("mapBuildPresets", out var presets) && presets is not null)
        {
            s.MapBuildPresets = [];
            foreach (var child in presets.Children)
            {
                var presetObj = child.Value;
                var name = TryGetString(presetObj, "name", out var pName) ? pName : child.Key;
                var opt = new MapBuildOptions();

                if (presetObj.TryGetValue("options", out var optObj) && optObj is not null)
                {
                    if (TryGetInt(optObj, "threads", out var th)) opt.Threads = th;
                    if (TryGetBool(optObj, "saveMapPath", out var smp)) opt.SaveMapPath = smp;
                    if (TryGetBool(optObj, "saveBuildLogs", out var sbl)) opt.SaveBuildLogs = sbl;
                    if (TryGetBool(optObj, "clearVradCache", out var cvc)) opt.ClearVradCache = cvc;
                    if (TryGetBool(optObj, "quiet", out var q)) opt.Quiet = q;
                    if (TryGetBool(optObj, "buildWorld", out var bw)) opt.BuildWorld = bw;
                    if (TryGetBool(optObj, "entitiesOnly", out var eo)) opt.EntitiesOnly = eo;
                    if (TryGetBool(optObj, "noSettle", out var ns)) opt.NoSettle = ns;
                    if (TryGetBool(optObj, "bakeLighting", out var bl)) opt.BakeLighting = bl;
                    if (TryGetInt(optObj, "lightmapResolution", out var lres)) opt.LightmapResolution = lres;
                    if (TryGetInt(optObj, "lightmapQuality", out var lq)) opt.LightmapQuality = lq;
                    if (TryGetBool(optObj, "lightmapCompression", out var lc)) opt.LightmapCompression = lc;
                    if (TryGetBool(optObj, "noiseRemoval", out var nr)) opt.NoiseRemoval = nr;
                    if (TryGetBool(optObj, "noLightCalculations", out var nlc)) opt.NoLightCalculations = nlc;
                    if (TryGetBool(optObj, "largeBlockSize", out var lbs)) opt.LargeBlockSize = lbs;
                    if (TryGetBool(optObj, "buildPhysics", out var bp)) opt.BuildPhysics = bp;
                    if (TryGetBool(optObj, "legacyCollisionMesh", out var lcm)) opt.LegacyCollisionMesh = lcm;
                    if (TryGetBool(optObj, "buildVisibility", out var bv)) opt.BuildVisibility = bv;
                    if (TryGetBool(optObj, "debugVisibility", out var dv)) opt.DebugVisibility = dv;
                    if (TryGetBool(optObj, "buildNavigation", out var bn)) opt.BuildNavigation = bn;
                    if (TryGetBool(optObj, "debugNavigation", out var dn)) opt.DebugNavigation = dn;
                    if (TryGetBool(optObj, "gridNavigation", out var gn)) opt.GridNavigation = gn;
                    if (TryGetBool(optObj, "buildReverb", out var br)) opt.BuildReverb = br;
                    if (TryGetBool(optObj, "buildAudioPaths", out var bap)) opt.BuildAudioPaths = bap;
                    if (TryGetBool(optObj, "bakeCustomAudio", out var bca)) opt.BakeCustomAudio = bca;
                    if (TryGetInt(optObj, "audioThreads", out var ath)) opt.AudioThreads = ath;
                    if (TryGetBool(optObj, "launchAfterBuild", out var lab)) opt.LaunchAfterBuild = lab;
                    if (TryGetBool(optObj, "buildCubemaps", out var bc)) opt.BuildCubemaps = bc;
                }

                var mapsList = new List<string>();
                if (presetObj.TryGetValue("maps", out var mapsObj) && mapsObj is not null)
                {
                    foreach (var m in mapsObj.Children)
                    {
                        var str = m.Value.ToString();
                        if (!string.IsNullOrEmpty(str)) mapsList.Add(str);
                    }
                }

                s.MapBuildPresets.Add(new MapBuildConfiguration(name, opt, mapsList.ToArray()));
            }
        }

        return s;
    }

    private static bool TryGetString(KVObject parent, string key, out string value)
    {
        if (parent.TryGetValue(key, out var obj) && obj is not null)
        {
            value = obj.ToString() ?? string.Empty;
            return true;
        }
        value = string.Empty;
        return false;
    }

    private static bool TryGetBool(KVObject parent, string key, out bool value)
    {
        if (parent.TryGetValue(key, out var obj) && obj is not null)
        {
            var str = obj.ToString();
            if (bool.TryParse(str, out value)) return true;
            if (int.TryParse(str, NumberStyles.Integer, CultureInfo.InvariantCulture, out var i))
            {
                value = i != 0;
                return true;
            }
        }
        value = false;
        return false;
    }

    private static bool TryGetInt(KVObject parent, string key, out int value)
    {
        if (parent.TryGetValue(key, out var obj) && obj is not null)
        {
            var str = obj.ToString();
            if (int.TryParse(str, NumberStyles.Integer, CultureInfo.InvariantCulture, out value)) return true;
        }
        value = 0;
        return false;
    }

    private static bool TryGetDouble(KVObject parent, string key, out double value)
    {
        if (parent.TryGetValue(key, out var obj) && obj is not null)
        {
            var str = obj.ToString();
            if (double.TryParse(str, NumberStyles.Float, CultureInfo.InvariantCulture, out value)) return true;
        }
        value = 0.0;
        return false;
    }
}
