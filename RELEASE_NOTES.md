**## General**

Cs2 dropped -netconport in a recent update, which silently broke certain features, so now Hammer5Tools uses concommandpipe.

If you are running Cs2 workshop tools via Steam, add these lines to enable support for Hammer5Tools.

`-insecure -concommandpipe .\pipe\hammer5tools\_cmd,.\pipe\hammer5tools\_out -con\_logfile hammer5tools\_console.log`

**## Utilities**

* Added Video to Texture utility which converts a video into an animated texture with vmat file.