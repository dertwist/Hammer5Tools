# CS2 Workshop Manager

Source: https://github.com/Angel-foxxo/CS2-Workshop-Manager
Revision: `1db8b283e178fbd58831955c33025ff444280759` (version 1.4.0).
License: MIT; see LICENSE and THIRD_PARTY_NOTICES.txt.

The GUI, library, Steamworks, assets and build settings are based on this revision. The library and Steamworks projects live in `Core/CS2WorkshopManager/` and `Core/Steamworks/`; the adapted GUI lives in `GUI/CS2WorkshopManager/` and is hosted in-process, including standalone Workshop startup. Steam publishing requires Windows or Linux and a running, logged-in Steam client.

Update these directories together from one upstream revision and retain all notices and Hammer5Tools hosting adaptations. Do not reformat or apply Hammer5Tools control styles to vendored source. Run `dotnet format --exclude Core/Steamworks Core/CS2WorkshopManager GUI/CS2WorkshopManager` for owned code; CI preserves the upstream formatting. Each project imports the shared build files retained here and carries the upstream `.editorconfig`. `Directory.Packages.props` keeps upstream package versions independent of the repository's central package versions. Parent projects exclude the nested upstream sources.
