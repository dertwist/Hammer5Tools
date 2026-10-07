namespace Hammer5Tools.App.Services.Updates;

using System.Net.Http;
using System.Text.Json;

/// <summary>A published GitHub release and its authored notes.</summary>
public sealed record ReleaseNotes(string Version, string Body, Uri Url);

internal static class GithubReleaseNotes
{
    private static readonly HttpClient Http = new() { Timeout = TimeSpan.FromSeconds(20) };

    public static async Task<IReadOnlyList<ReleaseNotes>> LoadAsync(string channel, CancellationToken ct)
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, "https://api.github.com/repos/dertwist/Hammer5Tools/releases?per_page=20");
        request.Headers.UserAgent.ParseAdd("Hammer5Tools/1.0");
        using var response = await Http.SendAsync(request, ct);
        response.EnsureSuccessStatusCode();
        using var json = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync(ct), cancellationToken: ct);
        return json.RootElement.EnumerateArray()
            .Where(release => !release.GetProperty("draft").GetBoolean()
                && (channel == "dev" || !release.GetProperty("prerelease").GetBoolean()))
            .Select(release => new ReleaseNotes(release.GetProperty("tag_name").GetString()!.TrimStart('v'),
                release.GetProperty("body").GetString() ?? "", new Uri(release.GetProperty("html_url").GetString()!)))
            .ToArray();
    }
}
