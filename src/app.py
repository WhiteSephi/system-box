"""Central application controller managing widgets, tray icon, polling, and settings."""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from src.config import AppConfig
from src.sensors import SensorManager
from src.ui.base_widget import BaseDesktopWidget
from src.ui.clock_widget import ClockWidget
from src.ui.cpu_widget import CpuSystemWidget
from src.ui.gpu_widget import GpuWidget
from src.ui.settings_dlg import SettingsDialog
from src.ui.tray import create_systembox_icon


class SystemBoxApp(QObject):
    """Coordinates a single shared event loop, tray icon, sensor polling, and all widgets."""

    def __init__(self, app: QApplication, config: AppConfig) -> None:
        super().__init__()
        self.app = app
        self.config = config
        self.sensor_manager = SensorManager()
        self._settings_dlg: SettingsDialog | None = None

        self.clock_widget = ClockWidget(self.config)
        self.gpu_widget = GpuWidget(self.config)
        self.cpu_widget = CpuSystemWidget(self.config)
        self._widgets: dict[str, BaseDesktopWidget] = {
            "clock": self.clock_widget,
            "gpu": self.gpu_widget,
            "cpu": self.cpu_widget,
        }

        for widget in self._widgets.values():
            widget.settings_requested.connect(self.open_settings)
            widget.quit_requested.connect(self.quit_application)
            widget.config_changed.connect(self._sync_tray_menu)

        self._setup_tray()

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_sensors)
        self._poll_timer.start(self.config.refresh_interval_ms)

        self._apply_widget_visibility()
        self._poll_sensors()

    def _setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(create_systembox_icon(self.config.primary_color), self)
        self.tray.setToolTip("SystemBox – Live Desktop Widgets")
        self.tray.activated.connect(self._on_tray_activated)

        self._tray_menu = QMenu()
        self._tray_widget_actions: dict[str, QAction] = {}
        for key, label in (("clock", "Uhrzeit & Datum"), ("gpu", "GPU-Monitor"), ("cpu", "CPU & System")):
            act = QAction(label, self._tray_menu, checkable=True)
            act.triggered.connect(lambda checked, k=key: self._toggle_widget_enabled(k, checked))
            self._tray_menu.addAction(act)
            self._tray_widget_actions[key] = act

        self._tray_menu.addSeparator()

        self._act_lock_all = QAction("Alle Positionen sperren", self._tray_menu, checkable=True)
        self._act_lock_all.triggered.connect(self._toggle_lock_all)
        self._tray_menu.addAction(self._act_lock_all)

        self._act_top_all = QAction("Alle immer im Vordergrund", self._tray_menu, checkable=True)
        self._act_top_all.triggered.connect(self._toggle_top_all)
        self._tray_menu.addAction(self._act_top_all)

        self._tray_menu.addSeparator()

        act_settings = QAction("Einstellungen...", self._tray_menu)
        act_settings.triggered.connect(self.open_settings)
        self._tray_menu.addAction(act_settings)

        act_quit = QAction("Beenden", self._tray_menu)
        act_quit.triggered.connect(self.quit_application)
        self._tray_menu.addAction(act_quit)

        self.tray.setContextMenu(self._tray_menu)
        self.tray.show()
        self._sync_tray_menu()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.open_settings()

    def _sync_tray_menu(self) -> None:
        for key, act in self._tray_widget_actions.items():
            act.setChecked(self.config.get_widget(key).enabled)
        self._act_lock_all.setChecked(self.config.locked_pos)
        self._act_top_all.setChecked(self.config.always_on_top)

    def _toggle_widget_enabled(self, key: str, enabled: bool) -> None:
        self.config.get_widget(key).enabled = enabled
        self.config.save()
        self._apply_widget_visibility()

    def _toggle_lock_all(self, checked: bool) -> None:
        self.config.locked_pos = checked
        for wc in self.config.widgets.values():
            wc.locked_pos = None
        self.config.save()

    def _toggle_top_all(self, checked: bool) -> None:
        self.config.always_on_top = checked
        for wc in self.config.widgets.values():
            wc.always_on_top = None
        self.config.save()
        self.apply_all_configs()

    def _apply_widget_visibility(self) -> None:
        for key, widget in self._widgets.items():
            if self.config.get_widget(key).enabled:
                widget.show()
            else:
                widget.hide()
        self._sync_tray_menu()

    def apply_all_configs(self) -> None:
        """Propagate updated AppConfig to polling timer, tray icon, and all widgets."""
        self._poll_timer.setInterval(self.config.refresh_interval_ms)
        self.tray.setIcon(create_systembox_icon(self.config.primary_color))
        for widget in self._widgets.values():
            widget.apply_config()
        self._apply_widget_visibility()
        self._poll_sensors()

    def _poll_sensors(self) -> None:
        snapshot = self.sensor_manager.poll(selected_gpu_index=self.config.selected_gpu_index)
        self.clock_widget.update_snapshot(snapshot)
        self.gpu_widget.update_snapshot(snapshot)
        self.cpu_widget.update_snapshot(snapshot)

    def open_settings(self) -> None:
        """Show or raise the central SettingsDialog."""
        if self._settings_dlg is not None and self._settings_dlg.isVisible():
            self._settings_dlg.raise_()
            self._settings_dlg.activateWindow()
            return

        self._settings_dlg = SettingsDialog(
            config=self.config,
            gpus=self.sensor_manager.list_gpus(),
            on_apply=self.apply_all_configs,
        )
        self._settings_dlg.show()
        self._settings_dlg.raise_()
        self._settings_dlg.activateWindow()

    def quit_application(self) -> None:
        """Persist state, release hardware handles, and exit cleanly."""
        self._poll_timer.stop()
        for widget in self._widgets.values():
            widget._persist_geometry()
            widget.close()
        self.sensor_manager.close()
        self.tray.hide()
        self.app.quit()
