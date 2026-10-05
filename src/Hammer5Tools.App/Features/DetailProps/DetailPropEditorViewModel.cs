namespace Hammer5Tools.App.Features.DetailProps;

using System.Collections.ObjectModel;
using System.IO;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.DetailProps;

public class DetailPropEditorViewModel : DocumentViewModel
{
    public override string IconUri => "avares://Hammer5Tools.App/Assets/Icons/detailprop_editor.png";

    private readonly IAddonService AddonService;
    private readonly string? FilePath;
    private DetailPropDocument Document;

    private DetailPropType? SelectedTypeValue;
    private DetailPropModel? SelectedModelValue;

    public ObservableCollection<DetailPropType> Types { get; } = [];

    public ObservableCollection<DetailPropModel> Models { get; } = [];

    public DetailPropType? SelectedType
    {
        get => SelectedTypeValue;
        set
        {
            if (SetProperty(ref SelectedTypeValue, value))
            {
                RefreshModels();
            }
        }
    }

    public DetailPropModel? SelectedModel
    {
        get => SelectedModelValue;
        set => SetProperty(ref SelectedModelValue, value);
    }

    public IRelayCommand AddTypeCommand { get; }

    public IRelayCommand DeleteTypeCommand { get; }

    public IRelayCommand AddModelCommand { get; }

    public IRelayCommand DeleteModelCommand { get; }

    public DetailPropEditorViewModel(IAddonService addonService, string? filePath = null)
    {
        AddonService = addonService;
        FilePath = filePath;
        Title = string.IsNullOrWhiteSpace(filePath) ? "DetailProp Editor" : Path.GetFileName(filePath);

        if (!string.IsNullOrWhiteSpace(filePath) && File.Exists(filePath))
        {
            Document = DetailPropDocument.Load(filePath);
        }
        else
        {
            Document = new DetailPropDocument();
            var defaultType = new DetailPropType("grass_clump") { Density = 1.0f };
            defaultType.Models.Add(new DetailPropModel
            {
                ModelName = "models/props/grass.vmdl",
                MinScale = 0.8f,
                MaxScale = 1.2f,
                RandomYaw = true,
                Upright = true,
            });
            Document.Types.Add(defaultType);
        }

        AddTypeCommand = new RelayCommand(OnAddType);
        DeleteTypeCommand = new RelayCommand(OnDeleteType);
        AddModelCommand = new RelayCommand(OnAddModel);
        DeleteModelCommand = new RelayCommand(OnDeleteModel);

        RefreshTypes();
    }

    private void RefreshTypes()
    {
        Types.Clear();
        foreach (var t in Document.Types)
        {
            Types.Add(t);
        }

        SelectedType = Types.FirstOrDefault();
    }

    private void RefreshModels()
    {
        Models.Clear();
        if (SelectedType is not null)
        {
            foreach (var m in SelectedType.Models)
            {
                Models.Add(m);
            }
        }

        SelectedModel = Models.FirstOrDefault();
    }

    private void OnAddType()
    {
        var name = $"prop_type_{Types.Count + 1}";
        var newType = new DetailPropType(name);
        Document.Types.Add(newType);
        Types.Add(newType);
        SelectedType = newType;
        MarkDirty();
    }

    private void OnDeleteType()
    {
        if (SelectedType is null)
        {
            return;
        }

        Document.Types.Remove(SelectedType);
        Types.Remove(SelectedType);
        SelectedType = Types.FirstOrDefault();
        MarkDirty();
    }

    private void OnAddModel()
    {
        if (SelectedType is null)
        {
            return;
        }

        var newModel = new DetailPropModel { ModelName = "models/new_prop.vmdl" };
        SelectedType.Models.Add(newModel);
        Models.Add(newModel);
        SelectedModel = newModel;
        MarkDirty();
    }

    private void OnDeleteModel()
    {
        if (SelectedType is null || SelectedModel is null)
        {
            return;
        }

        SelectedType.Models.Remove(SelectedModel);
        Models.Remove(SelectedModel);
        SelectedModel = Models.FirstOrDefault();
        MarkDirty();
    }

    public override void Save()
    {
        var savePath = FilePath;
        if (string.IsNullOrWhiteSpace(savePath) && AddonService.ActiveAddon is { } addon)
        {
            var scriptsDir = Path.Combine(addon.ContentPath, "scripts");
            savePath = Path.Combine(scriptsDir, "detail_prop_types.vdata");
        }

        if (!string.IsNullOrWhiteSpace(savePath))
        {
            Document.Save(savePath);
        }

        base.Save();
    }
}
