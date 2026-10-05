namespace Hammer5Tools.App.Converters;

using System;
using System.Collections.Concurrent;
using System.Globalization;
using Avalonia.Data.Converters;
using Avalonia.Media.Imaging;
using Avalonia.Platform;

public class UriToBitmapConverter : IValueConverter
{
    private static readonly ConcurrentDictionary<string, Bitmap?> Cache = new();

    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is string uriString && !string.IsNullOrWhiteSpace(uriString))
        {
            return Cache.GetOrAdd(uriString, uri =>
            {
                try
                {
                    return new Bitmap(AssetLoader.Open(new Uri(uri)));
                }
                catch
                {
                    return null;
                }
            });
        }

        return null;
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) =>
        throw new NotSupportedException();
}
