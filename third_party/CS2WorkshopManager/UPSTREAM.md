# CS2 Workshop Manager

Source: https://github.com/Angel-foxxo/CS2-Workshop-Manager
Revision: `1db8b283e178fbd58831955c33025ff444280759` (version 1.4.0).
License: MIT; see LICENSE and THIRD_PARTY_NOTICES.txt.

The GUI, library, Steamworks, assets and build settings are copied from this revision without source changes. Hammer5Tools builds and bundles the original GUI under `WorkshopManager/`, then opens its executable from Tools > Workshop Manager. The upstream application owns its Steam session, settings, dialogs and UI. It can finish an upload independently of the Hammer5Tools window. Steam publishing requires Windows or Linux and a running, logged-in Steam client.

Update these directories together from one upstream revision and retain all notices. Do not reformat or apply Hammer5Tools control styles to vendored source. Run `dotnet format --exclude third_party` for owned code; CI preserves the upstream formatting. Hammer5Tools uses the matching CS2WorkshopManager NuGet package for its CLI packaging service.
