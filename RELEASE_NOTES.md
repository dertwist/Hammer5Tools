## SmartProp Editor
* Added support for editing all variable types inside Choice Options.
* Fixed Choice Option values being reset during reordering, loading, and undo/redo.
* Preserved dropdown selection when choosing variables in Choice Options.
* Excluded category headers from auto-completion and variable selectors.
* Improved category creation and automatic cleanup when deleting variables.

## UnrealPorter
* Added Model Apply Mode option (`FBX` / `Vmdl`) with in-place geometry scaling.
* Added pruning of unimported LODs and collision meshes directly from FBX files.

## Model Browser
* Added multi-word search filtering support.
<img width="945" height="758" alt="Model Browser" src="https://github.com/user-attachments/assets/c49ccc1c-819a-45d1-8eab-5630819b8062" />

## Updater
* Added media and image preview support to the update dialog.
* Improved background process cleanup and shutdown handling during updates.

## General
* Fixed `.vsndevts` files opening in SmartProp Editor instead of SoundEvent Editor.
* Added file icon association for `.vsndevts` files.
* Added Windows Job Object management to ensure child processes terminate cleanly on exit.
* Added SmartProp guide link and contributor credits to About window.