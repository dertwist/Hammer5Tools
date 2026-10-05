"""A no-op theme selection must not trigger an application repolish."""
import sys
sys.path.insert(0, "Hammer5ToolsGUI")


def test_reselecting_active_level_does_not_repolish(monkeypatch):
    from gui.styles import theme
    from gui.settings.main import PreferencesDialog

    theme.set_level(2)
    calls = []
    monkeypatch.setattr("gui.styles.manager.reapply", lambda t: calls.append(t))

    class Combo:
        data = 2
        def currentData(self): return self.data

    dialog = PreferencesDialog.__new__(PreferencesDialog)
    dialog.appearance_combo_theme = Combo()

    dialog.apply_theme_level()
    assert calls == [], "re-selecting the active level repolished the app"

    Combo.data = 3
    dialog.apply_theme_level()
    assert len(calls) == 1 and calls[0].level == 3
    theme.set_level(2)
