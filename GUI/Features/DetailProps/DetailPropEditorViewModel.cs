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
    private readonly Services.IDialogService DialogService;
    private DetailPropDocument Document;

    private object? SelectedNodeValue;

    private DetailPropType? SelectedTypeValue;
    private DetailPropModel? SelectedModelValue;

    public ObservableCollection<DetailPropType> Types { get; } = [];

    public ObservableCollection<DetailPropModel> Models { get; } = [];

    public object? SelectedNode
    {
        get => SelectedNodeValue;
        set
        {
            if (!SetProperty(ref SelectedNodeValue, value))
            {
                return;
            }

            if (value is DetailPropType type)
            {
                SelectedType = type;
                SelectedModel = null;
            }
            else if (value is DetailPropModel model)
            {
                SelectedType = Types.FirstOrDefault(type => type.Models.Contains(model));
                SelectedModel = model;
            }
        }
    }

    public DetailPropType? SelectedType
    {
        get => SelectedTypeValue;
        set
        {
            if (SetProperty(ref SelectedTypeValue, value))
            {
                RefreshModels();
                OnPropertyChanged(nameof(IsTypeSelected));
            }
        }
    }

    public DetailPropModel? SelectedModel
    {
        get => SelectedModelValue;
        set
        {
            if (SetProperty(ref SelectedModelValue, value))
            {
                OnPropertyChanged(nameof(IsTypeSelected));
                OnPropertyChanged(nameof(HasSelectedModel));
                OnPropertyChanged(nameof(RotationMinX));
                OnPropertyChanged(nameof(RotationMinY));
                OnPropertyChanged(nameof(RotationMinZ));
                OnPropertyChanged(nameof(RotationMaxX));
                OnPropertyChanged(nameof(RotationMaxY));
                OnPropertyChanged(nameof(RotationMaxZ));
            }
        }
    }

    public bool IsTypeSelected => SelectedModel is null && SelectedType is not null;

    public bool HasSelectedModel => SelectedModel is not null;

    public float RotationMinX
    {
        get => SelectedModel?.RotationMin.X ?? 0;
        set
        {
            if (SelectedModel is { } model)
            {
                var vector = model.RotationMin;
                model.RotationMin = new Vector3(value, vector.Y, vector.Z);
            }
        }
    }

    public float RotationMinY
    {
        get => SelectedModel?.RotationMin.Y ?? 0;
        set
        {
            if (SelectedModel is { } model)
            {
                var vector = model.RotationMin;
                model.RotationMin = new Vector3(vector.X, value, vector.Z);
            }
        }
    }

    public float RotationMinZ
    {
        get => SelectedModel?.RotationMin.Z ?? 0;
        set
        {
            if (SelectedModel is { } model)
            {
                var vector = model.RotationMin;
                model.RotationMin = new Vector3(vector.X, vector.Y, value);
            }
        }
    }

    public float RotationMaxX
    {
        get => SelectedModel?.RotationMax.X ?? 0;
        set
        {
            if (SelectedModel is { } model)
            {
                var vector = model.RotationMax;
                model.RotationMax = new Vector3(value, vector.Y, vector.Z);
            }
        }
    }

    public float RotationMaxY
    {
        get => SelectedModel?.RotationMax.Y ?? 0;
        set
        {
            if (SelectedModel is { } model)
            {
                var vector = model.RotationMax;
                model.RotationMax = new Vector3(vector.X, value, vector.Z);
            }
        }
    }

    public float RotationMaxZ
    {
        get => SelectedModel?.RotationMax.Z ?? 0;
        set
        {
            if (SelectedModel is { } model)
            {
                var vector = model.RotationMax;
                model.RotationMax = new Vector3(vector.X, vector.Y, value);
            }
        }
    }

    public IRelayCommand AddTypeCommand { get; }

    public IRelayCommand DeleteTypeCommand { get; }

    public IRelayCommand AddModelCommand { get; }

    public IRelayCommand DeleteModelCommand { get; }

    public DetailPropEditorViewModel(IAddonService addonService, Services.IDialogService dialogService, string? filePath = null)
    {
        AddonService = addonService;
        DialogService = dialogService;
        ReportSaveFailure = dialogService.ShowErrorAsync;
        filePath ??= addonService.ActiveAddon is { } active ? Path.Combine(active.ContentPath, "scripts", "detail_prop_types.vdata") : null;
        DocumentPath = filePath;
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
        InitializeHistory(() => Document.Serialize(), text =>
        {
            Document = DetailPropDocument.Parse(text);
            RefreshTypes();
            ObserveDocument();
        });
        ObserveDocument();
    }

    private void ObserveDocument()
    {
        ObserveModels(Document.Types.Cast<System.ComponentModel.INotifyPropertyChanged>()
            .Concat(Document.Types.SelectMany(type => type.Models)));
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
        ObserveDocument();
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
        ObserveDocument();
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
        ObserveDocument();
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
        ObserveDocument();
        MarkDirty();
    }

    protected override async Task<bool> SaveCoreAsync()
    {
        DocumentPath ??= AddonService.ActiveAddon is { } addon
            ? Path.Combine(addon.ContentPath, "scripts", "detail_prop_types.vdata")
            : await DialogService.SaveFileAsync("Save detail props", "detail_prop_types.vdata");
        if (DocumentPath is null)
        {
            return false;
        }

        Document.Save(DocumentPath);
        return true;
    }
}
