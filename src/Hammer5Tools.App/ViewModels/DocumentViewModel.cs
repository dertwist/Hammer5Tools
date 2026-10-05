namespace Hammer5Tools.App.ViewModels;

using CommunityToolkit.Mvvm.Input;

public abstract class DocumentViewModel : ViewModelBase
{
    private string TitleValue = "Untitled";
    private bool IsDirtyValue;

    public string Title
    {
        get => TitleValue;
        set
        {
            if (SetProperty(ref TitleValue, value))
            {
                OnPropertyChanged(nameof(DisplayTitle));
            }
        }
    }

    public bool IsDirty
    {
        get => IsDirtyValue;
        set
        {
            if (SetProperty(ref IsDirtyValue, value))
            {
                OnPropertyChanged(nameof(DisplayTitle));
            }
        }
    }

    public string DisplayTitle => IsDirty ? $"{Title}*" : Title;

    public event EventHandler? RequestClose;

    public IRelayCommand CloseCommand { get; }

    protected DocumentViewModel()
    {
        CloseCommand = new RelayCommand(OnRequestClose);
    }

    public virtual void Save()
    {
        IsDirty = false;
    }

    protected void MarkDirty()
    {
        IsDirty = true;
    }

    protected void OnRequestClose()
    {
        RequestClose?.Invoke(this, EventArgs.Empty);
    }
}
