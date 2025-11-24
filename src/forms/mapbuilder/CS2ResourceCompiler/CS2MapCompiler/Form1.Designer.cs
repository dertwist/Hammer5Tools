
namespace CS2MapCompiler
{
    partial class Form1
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.components = new System.ComponentModel.Container();
            this.timer1 = new System.Windows.Forms.Timer(this.components);
            this.button1 = new System.Windows.Forms.Button();
            this.button2 = new System.Windows.Forms.Button();
            this.label1 = new System.Windows.Forms.Label();
            this.cs2status = new System.Windows.Forms.Label();
            this.label2 = new System.Windows.Forms.Label();
            this.wststatus = new System.Windows.Forms.Label();
            this.button3 = new System.Windows.Forms.Button();
            this.buildworld = new System.Windows.Forms.CheckBox();
            this.settlephys = new System.Windows.Forms.CheckBox();
            this.genLightmaps = new System.Windows.Forms.CheckBox();
            this.label3 = new System.Windows.Forms.Label();
            this.lightmapres = new System.Windows.Forms.ComboBox();
            this.label4 = new System.Windows.Forms.Label();
            this.lightmapquality = new System.Windows.Forms.ComboBox();
            this.compression = new System.Windows.Forms.CheckBox();
            this.noiseremoval = new System.Windows.Forms.CheckBox();
            this.buildPhys = new System.Windows.Forms.CheckBox();
            this.buildVis = new System.Windows.Forms.CheckBox();
            this.buildNav = new System.Windows.Forms.CheckBox();
            this.cpu = new System.Windows.Forms.CheckBox();
            this.cpuLabel = new System.Windows.Forms.Label();
            this.button4 = new System.Windows.Forms.Button();
            this.label6 = new System.Windows.Forms.Label();
            this.outputdir = new System.Windows.Forms.Label();
            this.button5 = new System.Windows.Forms.Button();
            this.label7 = new System.Windows.Forms.Label();
            this.threadcount = new System.Windows.Forms.ComboBox();
            this.CategoryWorld = new System.Windows.Forms.Label();
            this.entsOnly = new System.Windows.Forms.CheckBox();
            this.debugVisGeo = new System.Windows.Forms.CheckBox();
            this.noLightCalc = new System.Windows.Forms.CheckBox();
            this.useDeterCharts = new System.Windows.Forms.CheckBox();
            this.writeDebugPT = new System.Windows.Forms.CheckBox();
            this.CategoryLight = new System.Windows.Forms.Label();
            this.CategoryPhys = new System.Windows.Forms.Label();
            this.CategoryVis = new System.Windows.Forms.Label();
            this.CategoryNav = new System.Windows.Forms.Label();
            this.navDbg = new System.Windows.Forms.CheckBox();
            this.CategoryAudio = new System.Windows.Forms.Label();
            this.AudioThreadsBox = new System.Windows.Forms.ComboBox();
            this.AudioThreadsLabel = new System.Windows.Forms.Label();
            this.saReverb = new System.Windows.Forms.CheckBox();
            this.baPaths = new System.Windows.Forms.CheckBox();
            this.CategoryExtra = new System.Windows.Forms.Label();
            this.vconPrint = new System.Windows.Forms.CheckBox();
            this.vprofPrint = new System.Windows.Forms.CheckBox();
            this.logPrint = new System.Windows.Forms.CheckBox();
            this.label8 = new System.Windows.Forms.Label();
            this.gamedir = new System.Windows.Forms.Label();
            this.bakeCustom = new System.Windows.Forms.CheckBox();
            this.gridNav = new System.Windows.Forms.CheckBox();
            this.nolightmaps = new System.Windows.Forms.CheckBox();
            this.onlyBaseTileMesh = new System.Windows.Forms.CheckBox();
            this.legacyCompileColMesh = new System.Windows.Forms.CheckBox();
            this.label5 = new System.Windows.Forms.Label();
            this.cmdLine = new System.Windows.Forms.Label();
            this.PresetFullBuild = new System.Windows.Forms.Button();
            this.PresetFastBuild = new System.Windows.Forms.Button();
            this.PresetFinalBuild = new System.Windows.Forms.Button();
            this.PresetOnlyEntities = new System.Windows.Forms.Button();
            this.label9 = new System.Windows.Forms.Label();
            this.helpLabel = new System.Windows.Forms.Label();
            this.PresetCustom = new System.Windows.Forms.Button();
            this.vrad3LargeSize = new System.Windows.Forms.CheckBox();
            this.builddynamicsurfaceeffects = new System.Windows.Forms.CheckBox();
            this.SuspendLayout();
            // 
            // timer1
            // 
            this.timer1.Interval = 500;
            this.timer1.Tick += new System.EventHandler(this.timer1_Tick);
            // 
            // button1
            // 
            this.button1.Location = new System.Drawing.Point(12, 12);
            this.button1.Name = "button1";
            this.button1.Size = new System.Drawing.Size(75, 23);
            this.button1.TabIndex = 1;
            this.button1.Tag = "labelCompile";
            this.button1.Text = "Compile";
            this.button1.UseVisualStyleBackColor = true;
            this.button1.Click += new System.EventHandler(this.button1_Click);
            // 
            // button2
            // 
            this.button2.Location = new System.Drawing.Point(385, 12);
            this.button2.Name = "button2";
            this.button2.Size = new System.Drawing.Size(75, 23);
            this.button2.TabIndex = 2;
            this.button2.Tag = "labelCancel";
            this.button2.Text = "Cancel";
            this.button2.UseVisualStyleBackColor = true;
            this.button2.Click += new System.EventHandler(this.button2_Click);
            // 
            // label1
            // 
            this.label1.AutoSize = true;
            this.label1.Location = new System.Drawing.Point(109, 17);
            this.label1.Name = "label1";
            this.label1.Size = new System.Drawing.Size(35, 13);
            this.label1.TabIndex = 3;
            this.label1.Text = "Game";
            // 
            // cs2status
            // 
            this.cs2status.AutoSize = true;
            this.cs2status.ForeColor = System.Drawing.Color.DarkRed;
            this.cs2status.Location = new System.Drawing.Point(142, 17);
            this.cs2status.Name = "cs2status";
            this.cs2status.Size = new System.Drawing.Size(57, 13);
            this.cs2status.TabIndex = 4;
            this.cs2status.Tag = "labelgamestatus";
            this.cs2status.Text = "Not Found";
            // 
            // label2
            // 
            this.label2.AutoSize = true;
            this.label2.Location = new System.Drawing.Point(282, 17);
            this.label2.Name = "label2";
            this.label2.Size = new System.Drawing.Size(33, 13);
            this.label2.TabIndex = 5;
            this.label2.Text = "Tools";
            // 
            // wststatus
            // 
            this.wststatus.AutoSize = true;
            this.wststatus.ForeColor = System.Drawing.Color.DarkRed;
            this.wststatus.Location = new System.Drawing.Point(317, 17);
            this.wststatus.Name = "wststatus";
            this.wststatus.Size = new System.Drawing.Size(57, 13);
            this.wststatus.TabIndex = 6;
            this.wststatus.Tag = "labeltoolstatus";
            this.wststatus.Text = "Not Found";
            // 
            // button3
            // 
            this.button3.Location = new System.Drawing.Point(385, 41);
            this.button3.Name = "button3";
            this.button3.Size = new System.Drawing.Size(75, 22);
            this.button3.TabIndex = 7;
            this.button3.Tag = "labelCustomPath";
            this.button3.Text = "Custom Path";
            this.button3.UseVisualStyleBackColor = true;
            this.button3.Click += new System.EventHandler(this.button3_Click);
            // 
            // buildworld
            // 
            this.buildworld.AutoSize = true;
            this.buildworld.Checked = true;
            this.buildworld.CheckState = System.Windows.Forms.CheckState.Checked;
            this.buildworld.Location = new System.Drawing.Point(12, 57);
            this.buildworld.Name = "buildworld";
            this.buildworld.Size = new System.Drawing.Size(80, 17);
            this.buildworld.TabIndex = 8;
            this.buildworld.Tag = "labelBuildWorld";
            this.buildworld.Text = "Build World";
            this.buildworld.UseVisualStyleBackColor = true;
            // 
            // settlephys
            // 
            this.settlephys.AutoSize = true;
            this.settlephys.Checked = true;
            this.settlephys.CheckState = System.Windows.Forms.CheckState.Checked;
            this.settlephys.Location = new System.Drawing.Point(12, 105);
            this.settlephys.Name = "settlephys";
            this.settlephys.Size = new System.Drawing.Size(147, 17);
            this.settlephys.TabIndex = 9;
            this.settlephys.Tag = "labelSettlePhys";
            this.settlephys.Text = "Pre-Settle physics objects";
            this.settlephys.UseVisualStyleBackColor = true;
            // 
            // genLightmaps
            // 
            this.genLightmaps.AutoSize = true;
            this.genLightmaps.Checked = true;
            this.genLightmaps.CheckState = System.Windows.Forms.CheckState.Checked;
            this.genLightmaps.Location = new System.Drawing.Point(6, 181);
            this.genLightmaps.Name = "genLightmaps";
            this.genLightmaps.Size = new System.Drawing.Size(121, 17);
            this.genLightmaps.TabIndex = 10;
            this.genLightmaps.Tag = "labelgenLightmaps";
            this.genLightmaps.Text = "Generate Lightmaps";
            this.genLightmaps.UseVisualStyleBackColor = true;
            this.genLightmaps.CheckedChanged += new System.EventHandler(this.genLightmaps_CheckedChanged);
            // 
            // label3
            // 
            this.label3.AutoSize = true;
            this.label3.Location = new System.Drawing.Point(3, 213);
            this.label3.Name = "label3";
            this.label3.Size = new System.Drawing.Size(60, 13);
            this.label3.TabIndex = 11;
            this.label3.Text = "Resolution:";
            // 
            // lightmapres
            // 
            this.lightmapres.FormattingEnabled = true;
            this.lightmapres.Items.AddRange(new object[] {
            "8192",
            "4096",
            "2048",
            "1024",
            "512"});
            this.lightmapres.Location = new System.Drawing.Point(72, 210);
            this.lightmapres.Name = "lightmapres";
            this.lightmapres.Size = new System.Drawing.Size(55, 21);
            this.lightmapres.TabIndex = 12;
            this.lightmapres.Tag = "labellightmapres";
            // 
            // label4
            // 
            this.label4.AutoSize = true;
            this.label4.Location = new System.Drawing.Point(136, 213);
            this.label4.Name = "label4";
            this.label4.Size = new System.Drawing.Size(42, 13);
            this.label4.TabIndex = 13;
            this.label4.Text = "Quality:";
            // 
            // lightmapquality
            // 
            this.lightmapquality.FormattingEnabled = true;
            this.lightmapquality.Items.AddRange(new object[] {
            "Fast",
            "Standard",
            "Final"});
            this.lightmapquality.Location = new System.Drawing.Point(184, 210);
            this.lightmapquality.Name = "lightmapquality";
            this.lightmapquality.Size = new System.Drawing.Size(82, 21);
            this.lightmapquality.TabIndex = 14;
            this.lightmapquality.Tag = "labellightmapquality";
            // 
            // compression
            // 
            this.compression.AutoSize = true;
            this.compression.Checked = true;
            this.compression.CheckState = System.Windows.Forms.CheckState.Checked;
            this.compression.Location = new System.Drawing.Point(282, 212);
            this.compression.Name = "compression";
            this.compression.Size = new System.Drawing.Size(86, 17);
            this.compression.TabIndex = 15;
            this.compression.Tag = "labelCompression";
            this.compression.Text = "Compression";
            this.compression.UseVisualStyleBackColor = true;
            // 
            // noiseremoval
            // 
            this.noiseremoval.AutoSize = true;
            this.noiseremoval.Checked = true;
            this.noiseremoval.CheckState = System.Windows.Forms.CheckState.Checked;
            this.noiseremoval.Location = new System.Drawing.Point(8, 237);
            this.noiseremoval.Name = "noiseremoval";
            this.noiseremoval.Size = new System.Drawing.Size(98, 17);
            this.noiseremoval.TabIndex = 16;
            this.noiseremoval.Tag = "labelnoiseremoval";
            this.noiseremoval.Text = "Noise Removal";
            this.noiseremoval.UseVisualStyleBackColor = true;
            // 
            // buildPhys
            // 
            this.buildPhys.AutoSize = true;
            this.buildPhys.Checked = true;
            this.buildPhys.CheckState = System.Windows.Forms.CheckState.Checked;
            this.buildPhys.Location = new System.Drawing.Point(5, 318);
            this.buildPhys.Name = "buildPhys";
            this.buildPhys.Size = new System.Drawing.Size(87, 17);
            this.buildPhys.TabIndex = 17;
            this.buildPhys.Tag = "labelbuildPhys";
            this.buildPhys.Text = "Build physics";
            this.buildPhys.UseVisualStyleBackColor = true;
            // 
            // buildVis
            // 
            this.buildVis.AutoSize = true;
            this.buildVis.Checked = true;
            this.buildVis.CheckState = System.Windows.Forms.CheckState.Checked;
            this.buildVis.Location = new System.Drawing.Point(114, 318);
            this.buildVis.Name = "buildVis";
            this.buildVis.Size = new System.Drawing.Size(65, 17);
            this.buildVis.TabIndex = 18;
            this.buildVis.Tag = "labelbuildVis";
            this.buildVis.Text = "Build vis";
            this.buildVis.UseVisualStyleBackColor = true;
            // 
            // buildNav
            // 
            this.buildNav.AutoSize = true;
            this.buildNav.Checked = true;
            this.buildNav.CheckState = System.Windows.Forms.CheckState.Checked;
            this.buildNav.Location = new System.Drawing.Point(184, 318);
            this.buildNav.Name = "buildNav";
            this.buildNav.Size = new System.Drawing.Size(72, 17);
            this.buildNav.TabIndex = 19;
            this.buildNav.Tag = "labelbuildNav";
            this.buildNav.Text = "Build Nav";
            this.buildNav.UseVisualStyleBackColor = true;
            // 
            // cpu
            // 
            this.cpu.AutoSize = true;
            this.cpu.Location = new System.Drawing.Point(133, 181);
            this.cpu.Name = "cpu";
            this.cpu.Size = new System.Drawing.Size(70, 17);
            this.cpu.TabIndex = 20;
            this.cpu.Tag = "labelCPUcompile";
            this.cpu.Text = "Use CPU";
            this.cpu.UseVisualStyleBackColor = true;
            // 
            // cpuLabel
            // 
            this.cpuLabel.AutoSize = true;
            this.cpuLabel.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F);
            this.cpuLabel.ForeColor = System.Drawing.Color.DimGray;
            this.cpuLabel.Location = new System.Drawing.Point(130, 159);
            this.cpuLabel.Name = "cpuLabel";
            this.cpuLabel.Size = new System.Drawing.Size(268, 13);
            this.cpuLabel.TabIndex = 21;
            this.cpuLabel.Text = "Use if you don\'t have a RT-capable GPU. Now broken!";
            // 
            // button4
            // 
            this.button4.Location = new System.Drawing.Point(356, 454);
            this.button4.Name = "button4";
            this.button4.Size = new System.Drawing.Size(75, 21);
            this.button4.TabIndex = 22;
            this.button4.Tag = "labelopenvmap";
            this.button4.Text = "Open .vmap";
            this.button4.UseVisualStyleBackColor = true;
            this.button4.Click += new System.EventHandler(this.button4_Click);
            // 
            // label6
            // 
            this.label6.AutoSize = true;
            this.label6.Location = new System.Drawing.Point(5, 507);
            this.label6.Name = "label6";
            this.label6.Size = new System.Drawing.Size(42, 13);
            this.label6.TabIndex = 23;
            this.label6.Text = "Output:";
            this.label6.Click += new System.EventHandler(this.label6_Click);
            // 
            // outputdir
            // 
            this.outputdir.AutoSize = true;
            this.outputdir.Location = new System.Drawing.Point(50, 507);
            this.outputdir.MaximumSize = new System.Drawing.Size(450, 0);
            this.outputdir.Name = "outputdir";
            this.outputdir.Size = new System.Drawing.Size(27, 13);
            this.outputdir.TabIndex = 24;
            this.outputdir.Text = "N/A";
            this.outputdir.Click += new System.EventHandler(this.outputdir_Click);
            // 
            // button5
            // 
            this.button5.Enabled = false;
            this.button5.Location = new System.Drawing.Point(259, 454);
            this.button5.Name = "button5";
            this.button5.Size = new System.Drawing.Size(91, 21);
            this.button5.TabIndex = 25;
            this.button5.Tag = "labeloverrideoutput";
            this.button5.Text = "Change Output";
            this.button5.UseVisualStyleBackColor = true;
            this.button5.Click += new System.EventHandler(this.button5_Click);
            // 
            // label7
            // 
            this.label7.AutoSize = true;
            this.label7.Location = new System.Drawing.Point(279, 44);
            this.label7.Name = "label7";
            this.label7.Size = new System.Drawing.Size(49, 13);
            this.label7.TabIndex = 27;
            this.label7.Text = "Threads:";
            // 
            // threadcount
            // 
            this.threadcount.FormattingEnabled = true;
            this.threadcount.Location = new System.Drawing.Point(333, 41);
            this.threadcount.Name = "threadcount";
            this.threadcount.Size = new System.Drawing.Size(41, 21);
            this.threadcount.TabIndex = 28;
            this.threadcount.Tag = "labelThreads";
            // 
            // CategoryWorld
            // 
            this.CategoryWorld.AutoSize = true;
            this.CategoryWorld.BackColor = System.Drawing.SystemColors.ActiveCaptionText;
            this.CategoryWorld.ForeColor = System.Drawing.Color.Snow;
            this.CategoryWorld.Location = new System.Drawing.Point(78, 38);
            this.CategoryWorld.Name = "CategoryWorld";
            this.CategoryWorld.Size = new System.Drawing.Size(35, 13);
            this.CategoryWorld.TabIndex = 29;
            this.CategoryWorld.Text = "World";
            // 
            // entsOnly
            // 
            this.entsOnly.AutoSize = true;
            this.entsOnly.Location = new System.Drawing.Point(12, 82);
            this.entsOnly.Name = "entsOnly";
            this.entsOnly.Size = new System.Drawing.Size(84, 17);
            this.entsOnly.TabIndex = 30;
            this.entsOnly.Tag = "labelEntsOnly";
            this.entsOnly.Text = "Entities Only";
            this.entsOnly.UseVisualStyleBackColor = true;
            this.entsOnly.CheckedChanged += new System.EventHandler(this.entsOnly_CheckedChanged);
            // 
            // debugVisGeo
            // 
            this.debugVisGeo.AutoSize = true;
            this.debugVisGeo.Location = new System.Drawing.Point(100, 57);
            this.debugVisGeo.Name = "debugVisGeo";
            this.debugVisGeo.Size = new System.Drawing.Size(123, 17);
            this.debugVisGeo.TabIndex = 31;
            this.debugVisGeo.Tag = "labelDebugVisGeo";
            this.debugVisGeo.Text = "Debug Vis Geometry";
            this.debugVisGeo.UseVisualStyleBackColor = true;
            // 
            // noLightCalc
            // 
            this.noLightCalc.AutoSize = true;
            this.noLightCalc.Location = new System.Drawing.Point(112, 237);
            this.noLightCalc.Name = "noLightCalc";
            this.noLightCalc.Size = new System.Drawing.Size(156, 17);
            this.noLightCalc.TabIndex = 32;
            this.noLightCalc.Tag = "labelnoLightCalc";
            this.noLightCalc.Text = "Disable lighting calculations";
            this.noLightCalc.UseVisualStyleBackColor = true;
            // 
            // useDeterCharts
            // 
            this.useDeterCharts.AutoSize = true;
            this.useDeterCharts.Location = new System.Drawing.Point(6, 260);
            this.useDeterCharts.Name = "useDeterCharts";
            this.useDeterCharts.Size = new System.Drawing.Size(193, 17);
            this.useDeterCharts.TabIndex = 33;
            this.useDeterCharts.Tag = "labeluseDeterCharts";
            this.useDeterCharts.Text = "Deterministic charting computations";
            this.useDeterCharts.UseVisualStyleBackColor = true;
            // 
            // writeDebugPT
            // 
            this.writeDebugPT.AutoSize = true;
            this.writeDebugPT.Location = new System.Drawing.Point(198, 260);
            this.writeDebugPT.Name = "writeDebugPT";
            this.writeDebugPT.Size = new System.Drawing.Size(163, 17);
            this.writeDebugPT.TabIndex = 34;
            this.writeDebugPT.Tag = "labelwriteDebugPT";
            this.writeDebugPT.Text = "Write Debug Path Trace Info";
            this.writeDebugPT.UseVisualStyleBackColor = true;
            // 
            // CategoryLight
            // 
            this.CategoryLight.AutoSize = true;
            this.CategoryLight.BackColor = System.Drawing.SystemColors.ActiveCaptionText;
            this.CategoryLight.ForeColor = System.Drawing.Color.Snow;
            this.CategoryLight.Location = new System.Drawing.Point(181, 135);
            this.CategoryLight.Name = "CategoryLight";
            this.CategoryLight.Size = new System.Drawing.Size(78, 13);
            this.CategoryLight.TabIndex = 35;
            this.CategoryLight.Text = "Baked Lighting";
            // 
            // CategoryPhys
            // 
            this.CategoryPhys.AutoSize = true;
            this.CategoryPhys.BackColor = System.Drawing.SystemColors.ActiveCaptionText;
            this.CategoryPhys.ForeColor = System.Drawing.Color.Snow;
            this.CategoryPhys.Location = new System.Drawing.Point(7, 293);
            this.CategoryPhys.Name = "CategoryPhys";
            this.CategoryPhys.Size = new System.Drawing.Size(43, 13);
            this.CategoryPhys.TabIndex = 36;
            this.CategoryPhys.Text = "Physics";
            // 
            // CategoryVis
            // 
            this.CategoryVis.AutoSize = true;
            this.CategoryVis.BackColor = System.Drawing.SystemColors.ActiveCaptionText;
            this.CategoryVis.ForeColor = System.Drawing.Color.Snow;
            this.CategoryVis.Location = new System.Drawing.Point(116, 293);
            this.CategoryVis.Name = "CategoryVis";
            this.CategoryVis.Size = new System.Drawing.Size(43, 13);
            this.CategoryVis.TabIndex = 37;
            this.CategoryVis.Text = "Visibility";
            // 
            // CategoryNav
            // 
            this.CategoryNav.AutoSize = true;
            this.CategoryNav.BackColor = System.Drawing.SystemColors.ActiveCaptionText;
            this.CategoryNav.ForeColor = System.Drawing.Color.Snow;
            this.CategoryNav.Location = new System.Drawing.Point(181, 293);
            this.CategoryNav.Name = "CategoryNav";
            this.CategoryNav.Size = new System.Drawing.Size(27, 13);
            this.CategoryNav.TabIndex = 38;
            this.CategoryNav.Text = "Nav";
            // 
            // navDbg
            // 
            this.navDbg.AutoSize = true;
            this.navDbg.Location = new System.Drawing.Point(184, 341);
            this.navDbg.Name = "navDbg";
            this.navDbg.Size = new System.Drawing.Size(146, 17);
            this.navDbg.TabIndex = 39;
            this.navDbg.Tag = "labelnavDbg";
            this.navDbg.Text = "Save debug stages to file";
            this.navDbg.UseVisualStyleBackColor = true;
            // 
            // CategoryAudio
            // 
            this.CategoryAudio.AutoSize = true;
            this.CategoryAudio.BackColor = System.Drawing.SystemColors.ActiveCaptionText;
            this.CategoryAudio.ForeColor = System.Drawing.Color.Snow;
            this.CategoryAudio.Location = new System.Drawing.Point(9, 375);
            this.CategoryAudio.Name = "CategoryAudio";
            this.CategoryAudio.Size = new System.Drawing.Size(67, 13);
            this.CategoryAudio.TabIndex = 40;
            this.CategoryAudio.Text = "Steam Audio";
            // 
            // AudioThreadsBox
            // 
            this.AudioThreadsBox.FormattingEnabled = true;
            this.AudioThreadsBox.Location = new System.Drawing.Point(385, 398);
            this.AudioThreadsBox.Name = "AudioThreadsBox";
            this.AudioThreadsBox.Size = new System.Drawing.Size(41, 21);
            this.AudioThreadsBox.TabIndex = 42;
            this.AudioThreadsBox.Tag = "labelsaThreads";
            // 
            // AudioThreadsLabel
            // 
            this.AudioThreadsLabel.AutoSize = true;
            this.AudioThreadsLabel.Location = new System.Drawing.Point(300, 401);
            this.AudioThreadsLabel.Name = "AudioThreadsLabel";
            this.AudioThreadsLabel.Size = new System.Drawing.Size(79, 13);
            this.AudioThreadsLabel.TabIndex = 41;
            this.AudioThreadsLabel.Tag = "labelsaThreads";
            this.AudioThreadsLabel.Text = "Audio Threads:";
            // 
            // saReverb
            // 
            this.saReverb.AutoSize = true;
            this.saReverb.Checked = true;
            this.saReverb.CheckState = System.Windows.Forms.CheckState.Checked;
            this.saReverb.Location = new System.Drawing.Point(6, 400);
            this.saReverb.Name = "saReverb";
            this.saReverb.Size = new System.Drawing.Size(84, 17);
            this.saReverb.TabIndex = 43;
            this.saReverb.Tag = "labelsaReverb";
            this.saReverb.Text = "Bake reverb";
            this.saReverb.UseVisualStyleBackColor = true;
            // 
            // baPaths
            // 
            this.baPaths.AutoSize = true;
            this.baPaths.Checked = true;
            this.baPaths.CheckState = System.Windows.Forms.CheckState.Checked;
            this.baPaths.Location = new System.Drawing.Point(96, 400);
            this.baPaths.Name = "baPaths";
            this.baPaths.Size = new System.Drawing.Size(80, 17);
            this.baPaths.TabIndex = 44;
            this.baPaths.Tag = "labelsaPaths";
            this.baPaths.Text = "Bake paths";
            this.baPaths.UseVisualStyleBackColor = true;
            // 
            // CategoryExtra
            // 
            this.CategoryExtra.AutoSize = true;
            this.CategoryExtra.BackColor = System.Drawing.SystemColors.ActiveCaptionText;
            this.CategoryExtra.ForeColor = System.Drawing.Color.Snow;
            this.CategoryExtra.Location = new System.Drawing.Point(9, 429);
            this.CategoryExtra.Name = "CategoryExtra";
            this.CategoryExtra.Size = new System.Drawing.Size(31, 13);
            this.CategoryExtra.TabIndex = 45;
            this.CategoryExtra.Text = "Extra";
            // 
            // vconPrint
            // 
            this.vconPrint.AutoSize = true;
            this.vconPrint.Location = new System.Drawing.Point(6, 454);
            this.vconPrint.Name = "vconPrint";
            this.vconPrint.Size = new System.Drawing.Size(107, 17);
            this.vconPrint.TabIndex = 46;
            this.vconPrint.Tag = "labelvconPrint";
            this.vconPrint.Text = "Print to VConsole";
            this.vconPrint.UseVisualStyleBackColor = true;
            // 
            // vprofPrint
            // 
            this.vprofPrint.AutoSize = true;
            this.vprofPrint.Location = new System.Drawing.Point(111, 454);
            this.vprofPrint.Name = "vprofPrint";
            this.vprofPrint.Size = new System.Drawing.Size(111, 17);
            this.vprofPrint.TabIndex = 47;
            this.vprofPrint.Tag = "labelvprofPrint";
            this.vprofPrint.Text = "Print compile stats";
            this.vprofPrint.UseVisualStyleBackColor = true;
            // 
            // logPrint
            // 
            this.logPrint.AutoSize = true;
            this.logPrint.Location = new System.Drawing.Point(6, 477);
            this.logPrint.Name = "logPrint";
            this.logPrint.Size = new System.Drawing.Size(64, 17);
            this.logPrint.TabIndex = 48;
            this.logPrint.Tag = "labellogPrint";
            this.logPrint.Text = "Print log";
            this.logPrint.UseVisualStyleBackColor = true;
            // 
            // label8
            // 
            this.label8.AutoSize = true;
            this.label8.Location = new System.Drawing.Point(7, 537);
            this.label8.Name = "label8";
            this.label8.Size = new System.Drawing.Size(52, 13);
            this.label8.TabIndex = 49;
            this.label8.Text = "Game dir:";
            // 
            // gamedir
            // 
            this.gamedir.AutoSize = true;
            this.gamedir.Location = new System.Drawing.Point(58, 537);
            this.gamedir.MaximumSize = new System.Drawing.Size(450, 0);
            this.gamedir.Name = "gamedir";
            this.gamedir.Size = new System.Drawing.Size(27, 13);
            this.gamedir.TabIndex = 50;
            this.gamedir.Text = "N/A";
            // 
            // bakeCustom
            // 
            this.bakeCustom.AutoSize = true;
            this.bakeCustom.Location = new System.Drawing.Point(182, 400);
            this.bakeCustom.Name = "bakeCustom";
            this.bakeCustom.Size = new System.Drawing.Size(115, 17);
            this.bakeCustom.TabIndex = 51;
            this.bakeCustom.Tag = "labelbakeCustom";
            this.bakeCustom.Text = "Bake Custom Data";
            this.bakeCustom.TextAlign = System.Drawing.ContentAlignment.TopLeft;
            this.bakeCustom.UseVisualStyleBackColor = true;
            // 
            // gridNav
            // 
            this.gridNav.AutoSize = true;
            this.gridNav.Location = new System.Drawing.Point(256, 318);
            this.gridNav.Name = "gridNav";
            this.gridNav.Size = new System.Drawing.Size(94, 17);
            this.gridNav.TabIndex = 52;
            this.gridNav.Tag = "labelgridNav";
            this.gridNav.Text = "Build Grid Nav";
            this.gridNav.UseVisualStyleBackColor = true;
            // 
            // nolightmaps
            // 
            this.nolightmaps.AutoSize = true;
            this.nolightmaps.Enabled = false;
            this.nolightmaps.Location = new System.Drawing.Point(207, 181);
            this.nolightmaps.Name = "nolightmaps";
            this.nolightmaps.Size = new System.Drawing.Size(91, 17);
            this.nolightmaps.TabIndex = 53;
            this.nolightmaps.Text = "No Lightmaps";
            this.nolightmaps.UseVisualStyleBackColor = true;
            this.nolightmaps.Visible = false;
            // 
            // onlyBaseTileMesh
            // 
            this.onlyBaseTileMesh.AutoSize = true;
            this.onlyBaseTileMesh.Location = new System.Drawing.Point(100, 82);
            this.onlyBaseTileMesh.Name = "onlyBaseTileMesh";
            this.onlyBaseTileMesh.Size = new System.Drawing.Size(163, 17);
            this.onlyBaseTileMesh.TabIndex = 54;
            this.onlyBaseTileMesh.Tag = "labelOnlyBaseTileMesh";
            this.onlyBaseTileMesh.Text = "Only base tile mesh geometry";
            this.onlyBaseTileMesh.UseVisualStyleBackColor = true;
            // 
            // legacyCompileColMesh
            // 
            this.legacyCompileColMesh.AutoSize = true;
            this.legacyCompileColMesh.Enabled = false;
            this.legacyCompileColMesh.Location = new System.Drawing.Point(5, 341);
            this.legacyCompileColMesh.Name = "legacyCompileColMesh";
            this.legacyCompileColMesh.Size = new System.Drawing.Size(171, 17);
            this.legacyCompileColMesh.TabIndex = 55;
            this.legacyCompileColMesh.Tag = "labellegacyCompileColMesh";
            this.legacyCompileColMesh.Text = "Legacy Compile Collision Mesh";
            this.legacyCompileColMesh.UseVisualStyleBackColor = true;
            this.legacyCompileColMesh.Visible = false;
            // 
            // label5
            // 
            this.label5.AutoSize = true;
            this.label5.Location = new System.Drawing.Point(7, 565);
            this.label5.Name = "label5";
            this.label5.Size = new System.Drawing.Size(76, 13);
            this.label5.TabIndex = 56;
            this.label5.Text = "Command line:";
            // 
            // cmdLine
            // 
            this.cmdLine.AutoSize = true;
            this.cmdLine.Location = new System.Drawing.Point(84, 565);
            this.cmdLine.MaximumSize = new System.Drawing.Size(450, 0);
            this.cmdLine.Name = "cmdLine";
            this.cmdLine.Size = new System.Drawing.Size(27, 13);
            this.cmdLine.TabIndex = 57;
            this.cmdLine.Text = "N/A";
            // 
            // PresetFullBuild
            // 
            this.PresetFullBuild.Location = new System.Drawing.Point(464, 71);
            this.PresetFullBuild.Name = "PresetFullBuild";
            this.PresetFullBuild.Size = new System.Drawing.Size(63, 61);
            this.PresetFullBuild.TabIndex = 58;
            this.PresetFullBuild.Tag = "labelfullbuild";
            this.PresetFullBuild.Text = "Full Compile";
            this.PresetFullBuild.UseVisualStyleBackColor = true;
            this.PresetFullBuild.Click += new System.EventHandler(this.PresetFullBuild_Click);
            // 
            // PresetFastBuild
            // 
            this.PresetFastBuild.Location = new System.Drawing.Point(464, 138);
            this.PresetFastBuild.Name = "PresetFastBuild";
            this.PresetFastBuild.Size = new System.Drawing.Size(63, 61);
            this.PresetFastBuild.TabIndex = 59;
            this.PresetFastBuild.Tag = "labelfastbuild";
            this.PresetFastBuild.Text = "Fast Compile";
            this.PresetFastBuild.UseVisualStyleBackColor = true;
            this.PresetFastBuild.Click += new System.EventHandler(this.PresetFastBuild_Click);
            // 
            // PresetFinalBuild
            // 
            this.PresetFinalBuild.Location = new System.Drawing.Point(464, 205);
            this.PresetFinalBuild.Name = "PresetFinalBuild";
            this.PresetFinalBuild.Size = new System.Drawing.Size(63, 61);
            this.PresetFinalBuild.TabIndex = 60;
            this.PresetFinalBuild.Tag = "labelfinalbuild";
            this.PresetFinalBuild.Text = "Final Compile";
            this.PresetFinalBuild.UseVisualStyleBackColor = true;
            this.PresetFinalBuild.Click += new System.EventHandler(this.PresetFinalBuild_Click);
            // 
            // PresetOnlyEntities
            // 
            this.PresetOnlyEntities.Location = new System.Drawing.Point(464, 272);
            this.PresetOnlyEntities.Name = "PresetOnlyEntities";
            this.PresetOnlyEntities.Size = new System.Drawing.Size(63, 61);
            this.PresetOnlyEntities.TabIndex = 61;
            this.PresetOnlyEntities.Tag = "labelentsonly";
            this.PresetOnlyEntities.Text = "Only Entities";
            this.PresetOnlyEntities.UseVisualStyleBackColor = true;
            this.PresetOnlyEntities.Click += new System.EventHandler(this.PresetOnlyEntities_Click);
            // 
            // label9
            // 
            this.label9.AutoSize = true;
            this.label9.Location = new System.Drawing.Point(5, 667);
            this.label9.Name = "label9";
            this.label9.Size = new System.Drawing.Size(32, 13);
            this.label9.TabIndex = 62;
            this.label9.Text = "Help:";
            // 
            // helpLabel
            // 
            this.helpLabel.AutoSize = true;
            this.helpLabel.Location = new System.Drawing.Point(34, 667);
            this.helpLabel.MaximumSize = new System.Drawing.Size(450, 0);
            this.helpLabel.Name = "helpLabel";
            this.helpLabel.Size = new System.Drawing.Size(27, 13);
            this.helpLabel.TabIndex = 63;
            this.helpLabel.Text = "N/A";
            // 
            // PresetCustom
            // 
            this.PresetCustom.Location = new System.Drawing.Point(464, 339);
            this.PresetCustom.Name = "PresetCustom";
            this.PresetCustom.Size = new System.Drawing.Size(63, 61);
            this.PresetCustom.TabIndex = 64;
            this.PresetCustom.Tag = "labelcustom";
            this.PresetCustom.Text = "Custom";
            this.PresetCustom.UseVisualStyleBackColor = true;
            this.PresetCustom.Click += new System.EventHandler(this.PresetCustom_Click);
            // 
            // vrad3LargeSize
            // 
            this.vrad3LargeSize.AutoSize = true;
            this.vrad3LargeSize.Checked = true;
            this.vrad3LargeSize.CheckState = System.Windows.Forms.CheckState.Checked;
            this.vrad3LargeSize.Location = new System.Drawing.Point(263, 237);
            this.vrad3LargeSize.Name = "vrad3LargeSize";
            this.vrad3LargeSize.Size = new System.Drawing.Size(142, 17);
            this.vrad3LargeSize.TabIndex = 65;
            this.vrad3LargeSize.Tag = "labellargesize";
            this.vrad3LargeSize.Text = "VRAD3 Large block size";
            this.vrad3LargeSize.UseVisualStyleBackColor = true;
            // 
            // builddynamicsurfaceeffects
            // 
            this.builddynamicsurfaceeffects.AutoSize = true;
            this.builddynamicsurfaceeffects.Checked = true;
            this.builddynamicsurfaceeffects.CheckState = System.Windows.Forms.CheckState.Checked;
            this.builddynamicsurfaceeffects.Location = new System.Drawing.Point(165, 105);
            this.builddynamicsurfaceeffects.Name = "builddynamicsurfaceeffects";
            this.builddynamicsurfaceeffects.Size = new System.Drawing.Size(200, 17);
            this.builddynamicsurfaceeffects.TabIndex = 66;
            this.builddynamicsurfaceeffects.Tag = "labelDynamicSurfaceEffects";
            this.builddynamicsurfaceeffects.Text = "Build World Dynamic Surface Effects";
            this.builddynamicsurfaceeffects.UseVisualStyleBackColor = true;
            // 
            // Form1
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(539, 689);
            this.Controls.Add(this.builddynamicsurfaceeffects);
            this.Controls.Add(this.vrad3LargeSize);
            this.Controls.Add(this.PresetCustom);
            this.Controls.Add(this.helpLabel);
            this.Controls.Add(this.label9);
            this.Controls.Add(this.PresetOnlyEntities);
            this.Controls.Add(this.PresetFinalBuild);
            this.Controls.Add(this.PresetFastBuild);
            this.Controls.Add(this.PresetFullBuild);
            this.Controls.Add(this.cmdLine);
            this.Controls.Add(this.label5);
            this.Controls.Add(this.legacyCompileColMesh);
            this.Controls.Add(this.onlyBaseTileMesh);
            this.Controls.Add(this.nolightmaps);
            this.Controls.Add(this.gridNav);
            this.Controls.Add(this.bakeCustom);
            this.Controls.Add(this.gamedir);
            this.Controls.Add(this.label8);
            this.Controls.Add(this.logPrint);
            this.Controls.Add(this.vprofPrint);
            this.Controls.Add(this.vconPrint);
            this.Controls.Add(this.CategoryExtra);
            this.Controls.Add(this.baPaths);
            this.Controls.Add(this.saReverb);
            this.Controls.Add(this.AudioThreadsBox);
            this.Controls.Add(this.AudioThreadsLabel);
            this.Controls.Add(this.CategoryAudio);
            this.Controls.Add(this.navDbg);
            this.Controls.Add(this.CategoryNav);
            this.Controls.Add(this.CategoryVis);
            this.Controls.Add(this.CategoryPhys);
            this.Controls.Add(this.CategoryLight);
            this.Controls.Add(this.writeDebugPT);
            this.Controls.Add(this.useDeterCharts);
            this.Controls.Add(this.noLightCalc);
            this.Controls.Add(this.debugVisGeo);
            this.Controls.Add(this.entsOnly);
            this.Controls.Add(this.CategoryWorld);
            this.Controls.Add(this.threadcount);
            this.Controls.Add(this.label7);
            this.Controls.Add(this.button5);
            this.Controls.Add(this.outputdir);
            this.Controls.Add(this.label6);
            this.Controls.Add(this.button4);
            this.Controls.Add(this.cpuLabel);
            this.Controls.Add(this.cpu);
            this.Controls.Add(this.buildNav);
            this.Controls.Add(this.buildVis);
            this.Controls.Add(this.buildPhys);
            this.Controls.Add(this.noiseremoval);
            this.Controls.Add(this.compression);
            this.Controls.Add(this.lightmapquality);
            this.Controls.Add(this.label4);
            this.Controls.Add(this.lightmapres);
            this.Controls.Add(this.label3);
            this.Controls.Add(this.genLightmaps);
            this.Controls.Add(this.settlephys);
            this.Controls.Add(this.buildworld);
            this.Controls.Add(this.button3);
            this.Controls.Add(this.wststatus);
            this.Controls.Add(this.label2);
            this.Controls.Add(this.cs2status);
            this.Controls.Add(this.label1);
            this.Controls.Add(this.button2);
            this.Controls.Add(this.button1);
            this.Name = "Form1";
            this.Text = "CS2 Map Compiler";
            this.Load += new System.EventHandler(this.Form1_Load);
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion
        private System.Windows.Forms.Timer timer1;
        private System.Windows.Forms.Button button1;
        private System.Windows.Forms.Button button2;
        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.Label cs2status;
        private System.Windows.Forms.Label label2;
        private System.Windows.Forms.Label wststatus;
        private System.Windows.Forms.Button button3;
        private System.Windows.Forms.CheckBox buildworld;
        private System.Windows.Forms.CheckBox settlephys;
        private System.Windows.Forms.CheckBox genLightmaps;
        private System.Windows.Forms.Label label3;
        private System.Windows.Forms.ComboBox lightmapres;
        private System.Windows.Forms.Label label4;
        private System.Windows.Forms.ComboBox lightmapquality;
        private System.Windows.Forms.CheckBox compression;
        private System.Windows.Forms.CheckBox noiseremoval;
        private System.Windows.Forms.CheckBox buildPhys;
        private System.Windows.Forms.CheckBox buildVis;
        private System.Windows.Forms.CheckBox buildNav;
        private System.Windows.Forms.CheckBox cpu;
        private System.Windows.Forms.Label cpuLabel;
        private System.Windows.Forms.Button button4;
        private System.Windows.Forms.Label label6;
        private System.Windows.Forms.Label outputdir;
        private System.Windows.Forms.Button button5;
        private System.Windows.Forms.Label label7;
        private System.Windows.Forms.ComboBox threadcount;
        private System.Windows.Forms.Label CategoryWorld;
        private System.Windows.Forms.CheckBox entsOnly;
        private System.Windows.Forms.CheckBox debugVisGeo;
        private System.Windows.Forms.CheckBox noLightCalc;
        private System.Windows.Forms.CheckBox useDeterCharts;
        private System.Windows.Forms.CheckBox writeDebugPT;
        private System.Windows.Forms.Label CategoryLight;
        private System.Windows.Forms.Label CategoryPhys;
        private System.Windows.Forms.Label CategoryVis;
        private System.Windows.Forms.Label CategoryNav;
        private System.Windows.Forms.CheckBox navDbg;
        private System.Windows.Forms.Label CategoryAudio;
        private System.Windows.Forms.ComboBox AudioThreadsBox;
        private System.Windows.Forms.Label AudioThreadsLabel;
        private System.Windows.Forms.CheckBox saReverb;
        private System.Windows.Forms.CheckBox baPaths;
        private System.Windows.Forms.Label CategoryExtra;
        private System.Windows.Forms.CheckBox vconPrint;
        private System.Windows.Forms.CheckBox vprofPrint;
        private System.Windows.Forms.CheckBox logPrint;
        private System.Windows.Forms.Label label8;
        private System.Windows.Forms.Label gamedir;
        private System.Windows.Forms.CheckBox bakeCustom;
        private System.Windows.Forms.CheckBox gridNav;
        private System.Windows.Forms.CheckBox nolightmaps;
        private System.Windows.Forms.CheckBox onlyBaseTileMesh;
        private System.Windows.Forms.CheckBox legacyCompileColMesh;
        private System.Windows.Forms.Label label5;
        private System.Windows.Forms.Label cmdLine;
        private System.Windows.Forms.Button PresetFullBuild;
        private System.Windows.Forms.Button PresetFastBuild;
        private System.Windows.Forms.Button PresetFinalBuild;
        private System.Windows.Forms.Button PresetOnlyEntities;
        private System.Windows.Forms.Label label9;
        private System.Windows.Forms.Label helpLabel;
        private System.Windows.Forms.Button PresetCustom;
        private System.Windows.Forms.CheckBox vrad3LargeSize;
        private System.Windows.Forms.CheckBox builddynamicsurfaceeffects;
    }
}

