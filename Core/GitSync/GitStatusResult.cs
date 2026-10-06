namespace Hammer5Tools.Core.GitSync;

public class GitStatusResult
{
    public bool IsGitRepository { get; set; }

    public string Branch { get; set; } = "main";

    public int AheadCount { get; set; }

    public int BehindCount { get; set; }

    public List<string> ModifiedFiles { get; } = [];

    public List<string> UntrackedFiles { get; } = [];

    public bool HasUncommittedChanges => ModifiedFiles.Count > 0 || UntrackedFiles.Count > 0;
}
