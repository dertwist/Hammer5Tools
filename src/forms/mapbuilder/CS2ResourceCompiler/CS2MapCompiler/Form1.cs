using Microsoft.Win32;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Diagnostics;
using System.Diagnostics.Eventing.Reader;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace CS2MapCompiler
{
    public partial class Form1 : Form
    {
        public Form1()
        {
            InitializeComponent();
        }
        string cs2dir;
        string resourcecompiler;
        string addonname;
        string mapname;
        string mappath;
        string outputpath;
        string arg;
        bool oldsource2pre2020 = false; // this parameter enables parameters for S2 games pre 2021 and disables the post 2021 parameters.
        static string output;
        Process process;
        private string GetCS2Dir()
        {
            string steamPath = (string)Registry.GetValue("HKEY_CURRENT_USER\\Software\\Valve\\Steam", "SteamPath", "");
            string pathsFile = Path.Combine(steamPath, "steamapps", "libraryfolders.vdf");

            if (!File.Exists(pathsFile))
                return null;

            List<string> libraries = new List<string>();
            libraries.Add(Path.Combine(steamPath));

            var pathVDF = File.ReadAllLines(pathsFile);
            // Okay, this is not a full vdf-parser, but it seems to work pretty much, since the 
            // vdf-grammar is pretty easy. Hopefully it never breaks. I'm too lazy to write a full vdf-parser though. 
            Regex pathRegex = new Regex(@"\""(([^\""]*):\\([^\""]*))\""");
            foreach (var line in pathVDF)
            {
                if (pathRegex.IsMatch(line))
                {
                    string match = pathRegex.Matches(line)[0].Groups[1].Value;

                    // De-Escape vdf. 
                    libraries.Add(match.Replace("\\\\", "\\"));
                }
            }

            foreach (var library in libraries)
            {
                string cs2Path = Path.Combine(library, "steamapps\\common\\Counter-Strike Global Offensive\\game\\bin\\win64");
                if (Directory.Exists(cs2Path))
                {
                    return cs2Path;
                }
            }

            return null;
        }
        private void Form1_Load(object sender, EventArgs e)
        {
            lightmapres.SelectedIndex = 2;
            lightmapquality.SelectedIndex = 1;
            cs2dir = GetCS2Dir();
            CS2Validator();
            gamedir.Text = cs2dir;
            Checkers();
            HelpSystemEventReg();


            int cpuCount = Environment.ProcessorCount;
            for (int i = 1; i <= cpuCount; i++)
            {
                threadcount.Items.Add(i);
                AudioThreadsBox.Items.Add(i);
            }
            AudioThreadsBox.SelectedIndex = cpuCount - 1;
            threadcount.SelectedIndex = cpuCount - 1;
        }
        void CS2Validator()
        {
            string[] requiredExecutables = { "cs2.exe", "hlvr.exe", "project8.exe", "deadlock.exe", "primelock.exe", "hlx.exe", "hl3.exe", "steamtours.exe", "dota2.exe", "deskjob.exe", "vr.exe" };
            bool anyExecutableFound = false;

            foreach (string exe in requiredExecutables)
            {
                if (File.Exists(Path.Combine(cs2dir, exe)))
                {
                    anyExecutableFound = true;
                    cs2status.Text = $"Found {exe}";
                    cs2status.ForeColor = Color.Green;
                    button1.Enabled = true;
                    if (exe != "cs2.exe" && exe != "project8.exe" && exe != "deadlock.exe" && exe != "hl3.exe" && exe != "hlx.exe" && exe != "dota2.exe" && exe != "primelock.exe")
                    { //the future stares back - todo add resourcecompiler parameters for future s2 versions/games
                        oldsource2pre2020 = true;
                    }

                    if (oldsource2pre2020 == true) //if its not a S2 game post 2021, then assume we are a s2 game pre 2021 and disable post 2021 features like GPU VRAD3.
                                                   //todo add support for envmaps and nolight/old light from 2015-2016
                    {
                        cpu.Enabled = false;
                        cpu.Visible = false;
                        legacyCompileColMesh.Enabled = false;
                        legacyCompileColMesh.Visible = false;
                        bakeCustom.Enabled = false;
                        bakeCustom.Visible = false;
                        AudioThreadsBox.Visible = false;
                        AudioThreadsBox.Enabled = false;
                        AudioThreadsLabel.Visible = false;
                        AudioThreadsLabel.Enabled = false;
                        vrad3LargeSize.Visible = false;
                        vrad3LargeSize.Enabled = false;
                        cpuLabel.Text = "Only CPU lightmap is supported.";
                    }

                    if (exe == "deskjob.exe") //if deskjob - disable the lighting options by default as there is no vrad3
                    {
                        genLightmaps.Checked = false;
                        noiseremoval.Checked = false;
                        cpuLabel.Text = "No light is possible.";
                    }

                    if (exe != "dota2.exe")
                    {
                        gridNav.Enabled = false;
                        gridNav.Visible = false;
                        nolightmaps.Enabled = false;
                        nolightmaps.Visible = false;
                    }
                    else
                    if (exe == "dota2.exe") //if dota 2 - show grid nav button and uncheck others.
                    {
                        gridNav.Enabled = true;
                        gridNav.Visible = true;
                        genLightmaps.Checked = false;
                        noiseremoval.Checked = false;
                        buildNav.Checked = false;
                        saReverb.Checked = false;
                        baPaths.Checked = false;
                        bakeCustom.Checked = false;
                    }

                    if (File.Exists(Path.Combine(cs2dir, "resourcecompiler.exe")))
                    {
                        wststatus.Text = "Found";
                        wststatus.ForeColor = Color.Green;
                        resourcecompiler = Path.Combine(cs2dir, "resourcecompiler.exe");
                        button1.Enabled = true;
                    }
                    else
                    {
                        wststatus.Text = "Not Found";
                        wststatus.ForeColor = Color.DarkRed;
                        MessageBox.Show("Please Install Workshop Tools!", "CS2 Map Compiler", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                        button1.Enabled = false;
                    }

                    break; // Exit the loop once any executable is found
                }
            }

            if (!anyExecutableFound)
            {
                cs2status.Text = "Not Found";
                cs2status.ForeColor = Color.DarkRed;
                wststatus.Text = "Not Found";
                wststatus.ForeColor = Color.DarkRed;
                MessageBox.Show("CS2 Installation Not Found! Please install the game or set the path manually in the options!", "CS2 Map Compiler", MessageBoxButtons.OK, MessageBoxIcon.Error);
                button1.Enabled = false;
            }
        }

        private void timer1_Tick(object sender, EventArgs e)
        {

        }

        private void webBrowser1_DocumentCompleted(object sender, WebBrowserDocumentCompletedEventArgs e)
        {

        }

        private bool IsTextFile(string path)
        {
            return Path.GetExtension(path)?.Equals(".txt", StringComparison.OrdinalIgnoreCase) == true;
        }

        string ArgumentBuilder()
        {
            List<string> args = new List<string>();
            string inputFlag = IsTextFile(mappath) ? "-filelist" : "-i";
            string argument = $"-threads {threadcount.SelectedItem} -fshallow -maxtextureres 256 -dxlevel 110 -quiet -unbufferedio {inputFlag} " + string.Format("\"{0}\"", mappath) + " -noassert ";

            if (buildworld.Checked)
            {
                args.Add("-world");
                args.Remove("-entities");
            }
            if (!builddynamicsurfaceeffects.Checked)
            {
                args.Add("-skipauxfiles");
            }
            if (entsOnly.Checked)
            {
                args.Add("-entities");
                args.Remove("-world");
                args.Remove($"-sareverb_threads {AudioThreadsBox.SelectedItem}");
                args.Remove($"-sareverb_threads {AudioThreadsBox.SelectedItem}");
                args.Remove($"-sacustomdata_threads {AudioThreadsBox.SelectedItem}");
            }
            if (!settlephys.Checked)
            {
                args.Add("-nosettle");
            }
            if (debugVisGeo.Checked)
            {
                args.Add("-debugvisgeo");
            }
            if (onlyBaseTileMesh.Checked)
            {
                args.Add("-tileMeshBaseGeometry");
            }
            if (genLightmaps.Checked)
            {
                args.Add("-bakelighting");
                if (oldsource2pre2020 == true)
                {
                    args.Add("-vrad3");
                    if (compression.Checked)
                    {
                        args.Add("-lightmapCompressionDisabled 0");
                    }
                }
                if (cpu.Checked)
                {
                    args.Add("-lightmapcpu");
                }
                args.Add("-lightmapMaxResolution " + lightmapres.Text);
                args.Add("-lightmapDoWeld");
                args.Add("-lightmapVRadQuality " + lightmapquality.SelectedIndex.ToString());
                if (!noiseremoval.Checked)
                {
                    args.Add("-lightmapDisableFiltering");
                }
                if (!compression.Checked)
                {
                    args.Add("-lightmapCompressionDisabled");
                    if (oldsource2pre2020 == true)
                    {
                        args.Remove("-lightmapCompressionDisabled 0");
                        args.Add("-lightmapCompressionDisabled 1");
                    }
                }
                if (noLightCalc.Checked)
                {
                    args.Add("-disableLightingCalculations");
                }
                if (useDeterCharts.Checked)
                {
                    args.Add("-lightmapDeterministicCharts");
                }
                if (writeDebugPT.Checked)
                {
                    args.Add("-write_debug_path_trace_scene_info");
                }
                if (vrad3LargeSize.Checked)
                {
                    args.Add("-vrad3LargeBlockSize");
                }
                args.Add("-lightmapLocalCompile");
            }
            else if (!genLightmaps.Checked)
            {
                args.Add("-nolightmaps");
            }
            /*if (nolightmaps.Checked)
            {
                args.Add("-nolightmaps");
            }
            if (!nolightmaps.Checked)
            {
                args.Remove("-nolightmaps");
            }*/
            if (buildPhys.Checked)
            {
                args.Add("-phys");
            }
            if (legacyCompileColMesh.Checked)
            {
                args.Add("-legacycompilecollisionmesh");
            }
            if (buildVis.Checked)
            {
                args.Add("-vis");
            }
            if (buildNav.Checked)
            {
                args.Add("-nav");
            }
            if (navDbg.Checked)
            {
                args.Add("-navdbg");
            }
            if (gridNav.Checked)
            {
                args.Add("-gridnav");
            }
            if (saReverb.Checked)
            {
                args.Add("-sareverb");
                args.Add($"-sareverb_threads {AudioThreadsBox.SelectedItem}");
                if (oldsource2pre2020 == true)
                {
                    args.Remove($"-sareverb_threads {AudioThreadsBox.SelectedItem}");
                }
            }
            if (baPaths.Checked)
            {
                args.Add("-sapaths");
                args.Add($"-sareverb_threads {AudioThreadsBox.SelectedItem}");
                if (oldsource2pre2020 == true)
                {
                    args.Remove($"-sareverb_threads {AudioThreadsBox.SelectedItem}");
                }
            }
            if (bakeCustom.Checked)
            {
                args.Add("-sacustomdata");
                args.Add($"-sacustomdata_threads {AudioThreadsBox.SelectedItem}");
            }
            if (vconPrint.Checked)
            {
                args.Add("-vconsole");
                args.Add("-vconport 29000");
            }
            if (vprofPrint.Checked)
            {
                args.Add("-resourcecompiler_log_compile_stats");
            }
            if (logPrint.Checked)
            {
                args.Add("-condebug");
                args.Add("-consolelog");
            }
            args.Add("-retail -breakpad -nop4 -outroot ");
            if (oldsource2pre2020 == true)
            {
                args.Add("-retail -breakpad -nompi -nop4 -outroot ");
                args.Remove("-retail -breakpad -nop4 -outroot ");
            }
            return argument + string.Join(" ", args.ToArray());

        }

        void UpdateArgLabel()
        {
            string myarg = ArgumentBuilder();
            cmdLine.Text = myarg;
        }

        private void button1_Click(object sender, EventArgs e)
        {
            if (string.IsNullOrEmpty(outputpath))
            {
                MessageBox.Show("No .vmap is specified.", "CS2 Map Compiler",
                       MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }
            process = new Process();
            var task = new Task(() => ProcessThread());
            if (File.Exists(Path.Combine(outputpath, Path.GetFileNameWithoutExtension(mapname) + ".vpk")))
            {
                var response = MessageBox.Show("Do you want to overwrite the existing map file?", "CS2 Map Compiler", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
                if (response == DialogResult.Yes)
                {
                    arg = ArgumentBuilder() + string.Format("\"{0}\"", outputpath);
                    task.Start();
                }
                else
                {
                    MessageBox.Show("Compile Cancelled!", "CS2 Map Compiler", MessageBoxButtons.OK, MessageBoxIcon.Information);
                }
            }
            else
            {
                arg = ArgumentBuilder() + string.Format("\"{0}\"", outputpath);             
                task.Start();
            }
        }

        private void ProcessThread()
        {

            process.StartInfo.FileName = resourcecompiler;
            process.StartInfo.Arguments = arg;
            process.StartInfo.UseShellExecute = false;
            process.StartInfo.RedirectStandardError = true;

            //* Set ONLY ONE handler here.

            //* Start process

            process.Start();
            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine("(CS2MapCompiler) Compile started with parameters:\n " + resourcecompiler + " " + arg + "\nTime: " + DateTime.Now + "\n");
            Console.ForegroundColor = ConsoleColor.White;
            //* Read one element asynchronously
            //* Read the other one synchronously

            output = process.StandardError.ReadToEnd();
            Console.WriteLine(output);

            process.WaitForExit();

        }

        private void button2_Click(object sender, EventArgs e)
        {
            if (!process.HasExited)
            {
                process.Kill();
                process.WaitForExit();
                process.Dispose();
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("(CS2MapCompiler) Compile cancelled! - " + DateTime.Now + "\n");
                Console.ForegroundColor = ConsoleColor.White;
            }
            else
            {
                Console.ForegroundColor = ConsoleColor.Blue;
                Console.WriteLine("(CS2MapCompiler) Compile already exited! - " + DateTime.Now + "\n");
                Console.ForegroundColor = ConsoleColor.White;
            }
        }

        private void button3_Click(object sender, EventArgs e)
        {
            OpenFileDialog file = new OpenFileDialog();
            file.Filter = "Executable Files (*.exe)|cs2.exe;hlvr.exe;project8.exe;deadlock.exe;primelock.exe;steamtours.exe;deskjob.exe;dota2.exe";
            if (file.ShowDialog() == DialogResult.OK)
            {
                cs2dir = Path.GetDirectoryName(file.FileName);
                CS2Validator();
                gamedir.Text = cs2dir;
            }
        }

        private void genLightmaps_CheckedChanged(object sender, EventArgs e)
        {
            if (genLightmaps.Checked == false)
            {

                cpu.Enabled = false;
                lightmapres.Enabled = false;
                lightmapquality.Enabled = false;
                compression.Enabled = false;
                noiseremoval.Enabled = false;
                noLightCalc.Enabled = false;
                useDeterCharts.Enabled = false;
                writeDebugPT.Enabled = false;
                /*nolightmaps.Enabled = true;
                nolightmaps.Visible = false;*/
                vrad3LargeSize.Enabled = false;
            }
            else
            {
                /*nolightmaps.Enabled = false;
                nolightmaps.Visible = false;*/
                cpu.Enabled = true;
                lightmapres.Enabled = true;
                lightmapquality.Enabled = true;
                compression.Enabled = true;
                noiseremoval.Enabled = true;
                noLightCalc.Enabled = true;
                useDeterCharts.Enabled = true;
                writeDebugPT.Enabled = true;
                vrad3LargeSize.Enabled = true;
            }
        }
        void Checkers()
        {
            //World
            buildworld.CheckedChanged += OnSettingChanged;
            entsOnly.CheckedChanged += OnSettingChanged;
            settlephys.CheckedChanged += OnSettingChanged;
            debugVisGeo.CheckedChanged += OnSettingChanged;
            onlyBaseTileMesh.CheckedChanged += OnSettingChanged;
            threadcount.SelectedIndexChanged += OnSettingChanged;
            button3.Click += OnSettingChanged;
            builddynamicsurfaceeffects.CheckedChanged += OnSettingChanged;
            //Baked Lighting
            genLightmaps.CheckedChanged += OnSettingChanged;
            cpu.CheckedChanged += OnSettingChanged;
            nolightmaps.CheckedChanged += OnSettingChanged;
            lightmapres.SelectedIndexChanged += OnSettingChanged;
            lightmapquality.SelectedIndexChanged += OnSettingChanged;
            compression.CheckedChanged += OnSettingChanged;
            noiseremoval.CheckedChanged += OnSettingChanged;
            noLightCalc.CheckedChanged += OnSettingChanged;
            useDeterCharts.CheckedChanged += OnSettingChanged;
            writeDebugPT.CheckedChanged += OnSettingChanged;
            vrad3LargeSize.CheckedChanged += OnSettingChanged;
            //Phys
            buildPhys.CheckedChanged += OnSettingChanged;
            legacyCompileColMesh.CheckedChanged += OnSettingChanged;
            //Vis
            buildVis.CheckedChanged += OnSettingChanged;
            //Nav
            buildNav.CheckedChanged += OnSettingChanged;
            gridNav.CheckedChanged += OnSettingChanged;
            navDbg.CheckedChanged += OnSettingChanged;
            //Steam Audio
            saReverb.CheckedChanged += OnSettingChanged;
            baPaths.CheckedChanged += OnSettingChanged;
            bakeCustom.CheckedChanged += OnSettingChanged;
            AudioThreadsBox.SelectedIndexChanged += OnSettingChanged;
            //Extra
            vconPrint.CheckedChanged += OnSettingChanged;
            vprofPrint.CheckedChanged += OnSettingChanged;
            logPrint.CheckedChanged += OnSettingChanged;
        }
        private void OnSettingChanged(object sender, EventArgs e)
        {
            UpdateArgLabel();
        }
        private void button4_Click(object sender, EventArgs e)
        {
            OpenFileDialog file = new OpenFileDialog();

            string[] addonDirectories = {
        "csgo_addons",
        "hlvr_addons",
        "citadel_addons",
        "dota_addons",
        "testbed_addons",
        "steamtours_addons"
        };

            foreach (string addonDir in addonDirectories)
            {
                string path = Path.Combine(Directory.GetParent(cs2dir).Parent.Parent.FullName, "content", addonDir);
                if (Directory.Exists(path))
                {
                    file.InitialDirectory = path;
                    break;
                }
            }

            file.Filter = "Hammer Map File(*.vmap)|*.vmap;|Map List(*.txt)|*.txt;";

            if (file.ShowDialog() == DialogResult.OK)
            {
                mappath = file.FileName;
                mapname = Path.GetFileName(file.FileName);
                addonname = Directory.GetParent(file.FileName).Parent.Name;
                outputpath = Directory.GetParent(cs2dir).Parent.FullName;
                outputdir.Text = outputpath;
                button5.Enabled = true;
                UpdateArgLabel();
            }
        }

        private void button5_Click(object sender, EventArgs e)
        {
            string dummyFileName = "Select Here";
            SaveFileDialog file = new SaveFileDialog();

            string[] addonDirectories = {
        "csgo_addons",
        "hlvr_addons",
        "citadel_addons",
        "dota_addons",
        "testbed_addons",
        "steamtours_addons"
        };

            foreach (string addonDir in addonDirectories)
            {
                string path = Path.Combine(Directory.GetParent(cs2dir).Parent.FullName, addonDir, addonname, "maps");
                if (Directory.Exists(path))
                {
                    file.InitialDirectory = path;
                    break;
                }
            }

            file.FileName = dummyFileName;
            file.Filter = "Directory | directory";

            if (file.ShowDialog() == DialogResult.OK)
            {
                outputpath = Path.GetDirectoryName(file.FileName);
                outputdir.Text = outputpath;
            }
        }

        private void button6_Click(object sender, EventArgs e)
        {
            Console.Clear();
            Console.WriteLine(ArgumentBuilder() + string.Format("\"{0}\"", outputpath));
        }

        private void label6_Click(object sender, EventArgs e)
        {

        }

        private void outputdir_Click(object sender, EventArgs e)
        {

        }

        private void entsOnly_CheckedChanged(object sender, EventArgs e)
        {
            if (entsOnly.Checked == false)
            {
                genLightmaps.Enabled = true;
                cpu.Enabled = true;
                lightmapres.Enabled = true;
                lightmapquality.Enabled = true;
                noiseremoval.Enabled = true;
                compression.Enabled = true;
                useDeterCharts.Enabled = true;
                noLightCalc.Enabled = true;
                writeDebugPT.Enabled = true;
                buildPhys.Enabled = true;
                buildVis.Enabled = true;
                buildNav.Enabled = true;
                navDbg.Enabled = true;
                saReverb.Enabled = true;
                baPaths.Enabled = true;
                bakeCustom.Enabled = true;
            }
            else
            {
            }
        }

        private void PresetFullBuild_Click(object sender, EventArgs e)
        {
            //World
            buildworld.Checked = true;
            entsOnly.Checked = false;
            settlephys.Checked = true;
            debugVisGeo.Checked = false;
            onlyBaseTileMesh.Checked = false;
            builddynamicsurfaceeffects.Checked = true;
            //Baked Lighting
            genLightmaps.Enabled = true;
            genLightmaps.Checked = true;
            cpu.Checked = false;
            nolightmaps.Checked = false;
            lightmapres.SelectedIndex = 3;
            lightmapquality.SelectedIndex = 1;
            vrad3LargeSize.Checked = true;
            compression.Checked = true;
            noiseremoval.Checked = true;
            noLightCalc.Checked = false;
            useDeterCharts.Checked = false;
            writeDebugPT.Checked = false;
            //Phys
            buildPhys.Checked = true;
            legacyCompileColMesh.Checked = false;
            //Vis
            buildVis.Checked = true;
            //Nav
            buildNav.Checked = true;
            if (gridNav.Enabled)
            {
                gridNav.Checked = true;
            }
            navDbg.Checked = false;
            //Steam Audio
            saReverb.Checked = true;
            baPaths.Checked = true;
            bakeCustom.Checked = false; //yet
            //Extra
            vconPrint.Checked = false;
            vprofPrint.Checked = false;
            logPrint.Checked = false;         
        }

        private void PresetFastBuild_Click(object sender, EventArgs e)
        {
            //World
            buildworld.Checked = true;
            entsOnly.Checked = false;
            settlephys.Checked = true;
            debugVisGeo.Checked = false;
            onlyBaseTileMesh.Checked = false;
            builddynamicsurfaceeffects.Checked = true;
            //Baked Lighting
            genLightmaps.Checked = false;
            genLightmaps.Enabled = false;
            //Phys
            buildPhys.Checked = true;
            legacyCompileColMesh.Checked = false;
            //Vis
            buildVis.Checked = false;
            //Nav
            buildNav.Checked = true;
            if (gridNav.Enabled)
            {
                gridNav.Checked = true;
            }
            navDbg.Checked = false;
            //Steam Audio
            saReverb.Checked = false;
            baPaths.Checked = false;
            bakeCustom.Checked = false; //yet
            //Extra
            vconPrint.Checked = false;
            vprofPrint.Checked = false;
            logPrint.Checked = false;         
        }

        private void PresetFinalBuild_Click(object sender, EventArgs e)
        {
            //World
            buildworld.Checked = true;
            entsOnly.Checked = false;
            settlephys.Checked = true;
            debugVisGeo.Checked = false;
            onlyBaseTileMesh.Checked = false;
            builddynamicsurfaceeffects.Checked = true;
            //Baked Lighting
            genLightmaps.Enabled = true;
            genLightmaps.Checked = true;
            cpu.Checked = false;
            nolightmaps.Checked = false;
            lightmapres.SelectedIndex = 2;
            lightmapquality.SelectedIndex = 2;
            vrad3LargeSize.Checked = true;
            compression.Checked = true;
            noiseremoval.Checked = true;
            noLightCalc.Checked = false;
            useDeterCharts.Checked = false;
            writeDebugPT.Checked = false;
            //Phys
            buildPhys.Checked = true;
            legacyCompileColMesh.Checked = false;
            //Vis
            buildVis.Checked = true;
            //Nav
            buildNav.Checked = true;
            if (gridNav.Enabled)
            {
                gridNav.Checked = true;
            }
            navDbg.Checked = false;
            //Steam Audio
            saReverb.Checked = true;
            baPaths.Checked = true;
            bakeCustom.Checked = false; //yet
            //Extra
            vconPrint.Checked = false;
            vprofPrint.Checked = false;
            logPrint.Checked = false;            
        }

        private void PresetOnlyEntities_Click(object sender, EventArgs e)
        {
            //World
            buildworld.Checked = true;
            entsOnly.Checked = true;
            settlephys.Checked = true;
            debugVisGeo.Checked = false;
            onlyBaseTileMesh.Checked = false;
            builddynamicsurfaceeffects.Checked = true;
            //Baked Lighting
            genLightmaps.Checked = false;
            genLightmaps.Enabled = false;
            //Phys
            buildPhys.Checked = false;
            legacyCompileColMesh.Checked = false;
            //Vis
            buildVis.Checked = false;
            //Nav
            buildNav.Checked = false;
            if (gridNav.Enabled)
            {
                gridNav.Checked = false;
            }
            navDbg.Checked = false;
            //Steam Audio
            saReverb.Checked = false;
            baPaths.Checked = false;
            bakeCustom.Checked = false; //yet
            //Extra
            vconPrint.Checked = false;
            vprofPrint.Checked = false;
            logPrint.Checked = false;            
        }

        private void PresetCustom_Click(object sender, EventArgs e)
        {
            //World
            buildworld.Checked = true;
            entsOnly.Checked = false;
            settlephys.Checked = true;
            debugVisGeo.Checked = false;
            onlyBaseTileMesh.Checked = false;
            builddynamicsurfaceeffects.Checked = true;
            //Baked Lighting
            genLightmaps.Enabled = true;
            genLightmaps.Checked = true;
            cpu.Checked = false;
            nolightmaps.Checked = false;
            lightmapres.SelectedIndex = 3;
            lightmapquality.SelectedIndex = 1;
            vrad3LargeSize.Checked = true;
            compression.Checked = true;
            noiseremoval.Checked = true;
            noLightCalc.Checked = false;
            useDeterCharts.Checked = false;
            writeDebugPT.Checked = false;
            //Phys
            buildPhys.Checked = true;
            legacyCompileColMesh.Checked = false;
            //Vis
            buildVis.Checked = true;
            //Nav
            buildNav.Checked = true;
            if (gridNav.Enabled)
            {
                gridNav.Checked = true;
            }
            navDbg.Checked = false;
            //Steam Audio
            saReverb.Checked = true;
            baPaths.Checked = true;
            bakeCustom.Checked = false; //yet
            //Extra
            vconPrint.Checked = true;
            vprofPrint.Checked = true;
            logPrint.Checked = true;          
        }

        private Dictionary<string, string> _helpText = new Dictionary<string, string>
        {
            {"labelThreads", "Amount of CPU threads used by the compiler."},
            {"labelCancel", "Cancel build."},
            {"labelCustomPath", "Override game path."},
            {"labelgamestatus", "Current game status. Game executable must be present."},
            {"labeltoolstatus", "Current tools status. resourcecompiler.exe must be present."},
            {"labeloverrideoutput", "Override map vpk output path."},
            {"labelopenvmap", "Open .vmap file."},
            {"labelCompile", "Begin map compilation."},
            {"labelBuildWorld", "Build world."},
            {"labelEntsOnly", "Compile only entities. Useful for testing small changes."},
            {"labelSettlePhys", "Pre-Settle physics objects."},
            {"labelDebugVisGeo", "Debug VIS Geometry."},
            {"labelOnlyBaseTileMesh", "Only base Tile Mesh geometry."},
            {"labelDynamicSurfaceEffects", "Build world dynamic surface effects. Unknown."},
            {"labelgenLightmaps", "Bake lightmaps. GPU with RT support required."},
            {"labellightmapres", "Lightmap resolution. 1024 - Standard, 2048 - Final, 8192 - Shipping / Final."},
            {"labellightmapquality", "Lightmap quality."},
            {"labelgenLightmapsAlyx", "Bake lightmaps. Uses CPU for compilation."},
            {"labelCPUcompile", "Use CPU for lightmap compilation. Removed in CS2 after Oct 3, 2024."},
            {"labelCompression", "Enable/Disable lightmap compression."},
            {"labelnoiseremoval", "Enable/Disable lightmap denoising."},
            {"labelnoLightCalc", "Disable lighting calculations (useful for debugging texel density/chart allocation)."},
            {"labeluseDeterCharts", "Use Deterministic lightmap charts during bake."},
            {"labellargesize", "Make larger VRAD3 blocks at the cost of higher VRAM usage."},
            {"labelwriteDebugPT", "Write debug Path Trace scene info into a file."},
            {"labelbuildPhys", "Build collision physics mesh."},
            {"labellegacyCompileColMesh", "Build legacy collision physics mesh."},
            {"labelbuildVis", "Build visibility for optimization. Must be set to On in shipping maps."},
            {"labelbuildNav", "Build navigation mesh for NPCs / CS Bots."},
            {"labelgridNav", "Build grid navigation mesh for Dota NPCs."},
            {"labelnavDbg", "Save nav debug stages to file."},
            {"labelsaReverb", "Build Steam Audio reverb data."},
            {"labelsaPaths", "Build Steam Audio pathing data."},
            {"labelsaThreads", "CPU threads used for Steam Audio build."},
            {"labelbakeCustom", "Build Steam Audio custom data (occlusions and materials)."},
            {"labelvconPrint", "Print resourcecompiler data to VConsole (Default port 29000)"},
            {"labelvprofPrint", "Print VProf stats at the end of compilation."},
            {"labellogPrint", "Save resourcecompiler log to console.log in game/mod."},
            {"labelfullbuild", "Standard compile of all map components"},
            {"labelfastbuild", "Build world, phys or nav but no vis or lighting"},
            {"labelfinalbuild", "Build everything, including final quality lighting"},
            {"labelentsonly", "Build Entities. Nothing else!"},
            {"labelcustom", "Custom"},
        };

        void HelpSystemEventReg()
        {
            //General
            threadcount.MouseHover += Control_MouseEnter;
            button1.MouseHover += Control_MouseEnter;
            button2.MouseHover += Control_MouseEnter;
            button3.MouseHover += Control_MouseEnter;
            button4.MouseHover += Control_MouseEnter;
            button5.MouseHover += Control_MouseEnter;
            cs2status.MouseHover += Control_MouseEnter;
            wststatus.MouseHover += Control_MouseEnter;
            PresetFullBuild.MouseHover += Control_MouseEnter;
            PresetFastBuild.MouseHover += Control_MouseEnter;
            PresetFinalBuild.MouseHover += Control_MouseEnter;
            PresetOnlyEntities.MouseHover += Control_MouseEnter;
            PresetCustom.MouseHover += Control_MouseEnter;
            //World
            buildworld.MouseHover += Control_MouseEnter;
            entsOnly.MouseHover += Control_MouseEnter;
            settlephys.MouseHover += Control_MouseEnter;
            debugVisGeo.MouseHover += Control_MouseEnter;
            onlyBaseTileMesh.MouseHover += Control_MouseEnter;
            builddynamicsurfaceeffects.MouseHover += Control_MouseEnter;
            //Baked Lighting
            genLightmaps.MouseHover += Control_MouseEnter;         
            cpu.MouseHover += Control_MouseEnter;
            lightmapquality.MouseHover += Control_MouseEnter;
            lightmapres.MouseHover += Control_MouseEnter;
            nolightmaps.MouseHover += Control_MouseEnter;
            compression.MouseHover += Control_MouseEnter;
            noiseremoval.MouseHover += Control_MouseEnter;
            noLightCalc.MouseHover += Control_MouseEnter;
            useDeterCharts.MouseHover += Control_MouseEnter;
            writeDebugPT.MouseHover += Control_MouseEnter;
            vrad3LargeSize.MouseHover += Control_MouseEnter;
            //Phys
            buildPhys.MouseHover += Control_MouseEnter;
            legacyCompileColMesh.MouseHover += Control_MouseEnter;
            //Vis
            buildVis.MouseHover += Control_MouseEnter;
            //Nav
            buildNav.MouseHover += Control_MouseEnter;
            gridNav.MouseHover += Control_MouseEnter;
            navDbg.MouseHover += Control_MouseEnter;
            //Steam Audio
            saReverb.MouseHover += Control_MouseEnter;
            baPaths.MouseHover += Control_MouseEnter;
            bakeCustom.MouseHover += Control_MouseEnter;
            AudioThreadsLabel.MouseHover += Control_MouseEnter;
            AudioThreadsBox.MouseHover += Control_MouseEnter;
            //Extra
            vconPrint.MouseHover += Control_MouseEnter;
            vprofPrint.MouseHover += Control_MouseEnter;
            logPrint.MouseHover += Control_MouseEnter;
        }

        private void Control_MouseEnter(object sender, EventArgs e)
        {
            Control hoveredControl = (Control)sender;
            if (hoveredControl.Tag != null &&
                _helpText.TryGetValue(hoveredControl.Tag.ToString(), out string helpText))
            {
                helpLabel.Text = helpText;
            }
        }   
    }
}
