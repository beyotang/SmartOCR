"""
Dynamic Hotkey Manager for SmartOCR
Allows hotkeys to be updated at runtime without restart.
"""
import keyboard
from PySide6.QtCore import QObject, Signal


class HotkeyManager(QObject):
    """Manages global hotkeys with dynamic update support."""
    
    # Signals for hotkey triggers
    screenshot_triggered = Signal()
    translate_triggered = Signal()
    show_main_triggered = Signal()  # New signal for showing main window
    
    def __init__(self):
        super().__init__()
        self._current_screenshot_hotkey = None
        self._current_translate_hotkey = None
        self._current_show_main_hotkey = None
    
    def register_screenshot_hotkey(self, hotkey: str):
        """Register or update screenshot hotkey."""
        if not hotkey:
            return False
            
        # Unregister old hotkey if exists
        if self._current_screenshot_hotkey:
            try:
                keyboard.remove_hotkey(self._current_screenshot_hotkey)
            except:
                pass
        
        # Register new hotkey
        try:
            self._current_screenshot_hotkey = keyboard.add_hotkey(
                hotkey, 
                lambda: self.screenshot_triggered.emit()
            )
            print(f"Screenshot hotkey registered: {hotkey}")
            return True
        except Exception as e:
            print(f"Failed to register screenshot hotkey '{hotkey}': {e}")
            self._current_screenshot_hotkey = None
            return False
    
    def register_translate_hotkey(self, hotkey: str):
        """Register or update translate hotkey."""
        if not hotkey:
            return False
            
        # Unregister old hotkey if exists
        if self._current_translate_hotkey:
            try:
                keyboard.remove_hotkey(self._current_translate_hotkey)
            except:
                pass
        
        # Register new hotkey
        try:
            self._current_translate_hotkey = keyboard.add_hotkey(
                hotkey, 
                lambda: self.translate_triggered.emit()
            )
            print(f"Translate hotkey registered: {hotkey}")
            return True
        except Exception as e:
            print(f"Failed to register translate hotkey '{hotkey}': {e}")
            self._current_translate_hotkey = None
            return False
    
    def register_show_main_hotkey(self, hotkey: str):
        """Register or update show main window hotkey."""
        if not hotkey:
            return False
            
        # Unregister old hotkey if exists
        if self._current_show_main_hotkey:
            try:
                keyboard.remove_hotkey(self._current_show_main_hotkey)
            except:
                pass
        
        # Register new hotkey
        try:
            self._current_show_main_hotkey = keyboard.add_hotkey(
                hotkey, 
                lambda: self.show_main_triggered.emit()
            )
            print(f"Show main window hotkey registered: {hotkey}")
            return True
        except Exception as e:
            print(f"Failed to register show main hotkey '{hotkey}': {e}")
            self._current_show_main_hotkey = None
            return False
    
    def unregister_all(self):
        """Unregister all hotkeys."""
        if self._current_screenshot_hotkey:
            try:
                keyboard.remove_hotkey(self._current_screenshot_hotkey)
            except:
                pass
            self._current_screenshot_hotkey = None
            
        if self._current_translate_hotkey:
            try:
                keyboard.remove_hotkey(self._current_translate_hotkey)
            except:
                pass
            self._current_translate_hotkey = None
        
        if self._current_show_main_hotkey:
            try:
                keyboard.remove_hotkey(self._current_show_main_hotkey)
            except:
                pass
            self._current_show_main_hotkey = None


# Global singleton instance
hotkey_manager = HotkeyManager()

