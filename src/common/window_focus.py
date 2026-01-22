"""
Window focus and activation utilities for Windows platform.
Handles bringing windows to foreground reliably across different scenarios.
"""
import ctypes
from ctypes import wintypes
import time
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer


class WindowActivator:
    """Handles window activation with various fallback strategies."""
    
    # Windows API constants
    SW_RESTORE = 9
    SW_SHOW = 5
    SW_SHOWMAXIMIZED = 3
    SW_SHOWMINIMIZED = 2
    SW_SHOWNORMAL = 1
    
    HWND_TOP = 0
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_SHOWWINDOW = 0x0040
    
    def __init__(self):
        self.user32 = ctypes.windll.user32
    
    def activate_window(self, widget: QWidget, strategy='aggressive'):
        """
        Activate window using specified strategy.
        
        Args:
            widget: QWidget (typically QMainWindow)
            strategy: 'gentle', 'normal', 'aggressive', 'flash'
        """
        hwnd = int(widget.winId())
        
        if strategy == 'gentle':
            self._gentle_activate(hwnd, widget)
        elif strategy == 'normal':
            self._normal_activate(hwnd, widget)
        elif strategy == 'aggressive':
            self._aggressive_activate(hwnd, widget)
        elif strategy == 'flash':
            self._flash_and_activate(hwnd, widget)
    
    def _gentle_activate(self, hwnd, widget):
        """
        Gentle activation - respects user focus.
        Only brings to front if minimized.
        """
        # Check if minimized
        if self.user32.IsIconic(hwnd):
            self.user32.ShowWindow(hwnd, self.SW_RESTORE)
        
        # Qt-level activation
        widget.show()
        widget.raise_()
        widget.activateWindow()
    
    def _normal_activate(self, hwnd, widget):
        """
        Normal activation - standard window activation.
        """
        # Restore if minimized
        if self.user32.IsIconic(hwnd):
            self.user32.ShowWindow(hwnd, self.SW_RESTORE)
        else:
            self.user32.ShowWindow(hwnd, self.SW_SHOW)
        
        # Set foreground
        self.user32.SetForegroundWindow(hwnd)
        
        # Qt-level activation
        widget.showNormal()
        widget.raise_()
        widget.activateWindow()
    
    def _aggressive_activate(self, hwnd, widget):
        """
        Aggressive activation - forces window to front.
        Used when opening files from Explorer.
        """
        # Step 1: Restore window state
        if self.user32.IsIconic(hwnd):
            self.user32.ShowWindow(hwnd, self.SW_RESTORE)
        
        time.sleep(0.05)  # Small delay for state change
        
        # Step 2: Update window to ensure it's drawn
        self.user32.UpdateWindow(hwnd)
        
        # Step 3: Bring to top (temporarily topmost)
        self.user32.SetWindowPos(
            hwnd,
            self.HWND_TOPMOST,
            0, 0, 0, 0,
            self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_SHOWWINDOW
        )
        
        time.sleep(0.05)
        
        # Step 4: Remove topmost flag but keep at top
        self.user32.SetWindowPos(
            hwnd,
            self.HWND_NOTOPMOST,
            0, 0, 0, 0,
            self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_SHOWWINDOW
        )
        
        # Step 5: Set foreground (may fail if user is typing elsewhere)
        self._try_set_foreground_window(hwnd)
        
        # Step 6: Bring to top of Z-order
        self.user32.BringWindowToTop(hwnd)
        
        # Step 7: Qt-level activation
        widget.showNormal()
        widget.raise_()
        widget.activateWindow()
        
        # Step 8: Force repaint
        widget.repaint()
    
    def _flash_and_activate(self, hwnd, widget):
        """
        Flash taskbar and activate window.
        Gets user's attention without being too intrusive.
        """
        # Flash window
        self._flash_window(hwnd, count=3, interval=100)
        
        # Then activate normally
        QTimer.singleShot(350, lambda: self._normal_activate(hwnd, widget))
    
    def _flash_window(self, hwnd, count=3, interval=100):
        """
        Flash window in taskbar to get user's attention.
        """
        FLASHW_ALL = 0x00000003
        FLASHW_TIMERNOFG = 0x0000000C
        
        class FLASHWINFO(ctypes.Structure):
            _fields_ = [
                ('cbSize', wintypes.UINT),
                ('hwnd', wintypes.HWND),
                ('dwFlags', wintypes.DWORD),
                ('uCount', wintypes.UINT),
                ('dwTimeout', wintypes.DWORD)
            ]
        
        flash_info = FLASHWINFO()
        flash_info.cbSize = ctypes.sizeof(FLASHWINFO)
        flash_info.hwnd = hwnd
        flash_info.dwFlags = FLASHW_ALL | FLASHW_TIMERNOFG
        flash_info.uCount = count
        flash_info.dwTimeout = interval
        
        self.user32.FlashWindowEx(ctypes.byref(flash_info))
    
    def _try_set_foreground_window(self, hwnd):
        """
        Try to set foreground window with various workarounds.
        Windows has restrictions on when SetForegroundWindow works.
        """
        # Method 1: Direct call
        if self.user32.SetForegroundWindow(hwnd):
            return True
        
        # Method 2: Attach to foreground thread and try again
        try:
            current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
            foreground_hwnd = self.user32.GetForegroundWindow()
            foreground_thread = self.user32.GetWindowThreadProcessId(foreground_hwnd, None)
            
            if foreground_thread != current_thread:
                self.user32.AttachThreadInput(foreground_thread, current_thread, True)
                self.user32.SetForegroundWindow(hwnd)
                self.user32.AttachThreadInput(foreground_thread, current_thread, False)
                return True
        except:
            pass
        
        # Method 3: SwitchToThisWindow (undocumented but works)
        try:
            self.user32.SwitchToThisWindow(hwnd, True)
            return True
        except:
            pass
        
        return False
    
    def is_window_minimized(self, widget: QWidget) -> bool:
        """Check if window is minimized."""
        hwnd = int(widget.winId())
        return bool(self.user32.IsIconic(hwnd))
    
    def is_window_visible(self, widget: QWidget) -> bool:
        """Check if window is visible."""
        hwnd = int(widget.winId())
        return bool(self.user32.IsWindowVisible(hwnd))


# Global instance
_window_activator = WindowActivator()


def activate_window(widget: QWidget, strategy='aggressive'):
    """Convenience function to activate window."""
    _window_activator.activate_window(widget, strategy)


def flash_window(widget: QWidget, count=3):
    """Convenience function to flash window."""
    hwnd = int(widget.winId())
    _window_activator._flash_window(hwnd, count=count)
