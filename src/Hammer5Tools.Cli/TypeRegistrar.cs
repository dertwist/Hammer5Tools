namespace Hammer5Tools.Cli;

using Microsoft.Extensions.DependencyInjection;
using Spectre.Console.Cli;

public class TypeRegistrar : ITypeRegistrar
{
    private readonly IServiceCollection Services;

    public TypeRegistrar(IServiceCollection services)
    {
        Services = services;
    }

    public ITypeResolver Build() => new TypeResolver(Services.BuildServiceProvider());

    public void Register(Type service, Type implementation) => Services.AddSingleton(service, implementation);

    public void RegisterInstance(Type service, object implementation) => Services.AddSingleton(service, implementation);

    public void RegisterLazy(Type service, Func<object> factory) => Services.AddSingleton(service, _ => factory());
}

public class TypeResolver : ITypeResolver, IDisposable
{
    private readonly IServiceProvider Provider;

    public TypeResolver(IServiceProvider provider)
    {
        Provider = provider;
    }

    public object? Resolve(Type? type) => type is null ? null : Provider.GetService(type);

    public void Dispose()
    {
        if (Provider is IDisposable disposable)
        {
            disposable.Dispose();
        }

        GC.SuppressFinalize(this);
    }
}
