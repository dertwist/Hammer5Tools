"""Pieces of the main window that are not the main window.

app_core.MainWindow is the application shell: tabs, menus, dialogs and the Qt
event overrides. Everything here is a collaborator it owns rather than another
fifty lines of it -- a tray icon, geometry persistence, the addon combo box,
the shell-integration entry points, and the _vrad3 cache utility.
"""
