"""Cross-platform baseline system provider using psutil (no admin required)."""

from __future__ import annotations

import ctypes
from pathlib import Path
import struct
import sys
import time

import psutil

from src.sensors.base import SystemProvider
from src.sensors.models import CpuSystemSample


class PsutilSystemProvider(SystemProvider):
    """Reads CPU, per-core peak, clock, RAM, Disk I/O, and uptime via psutil."""

    def __init__(self) -> None:
        self._last_disk_device: str = ""
        self._last_disk_io = self._safe_disk_io()
        self._last_disk_ts = time.monotonic()
        self._last_pgfault: int | None = self._read_hard_page_faults()
        self._last_pgfault_ts = self._last_disk_ts
        # Prime psutil cpu_percent so the first real poll returns a meaningful delta
        try:
            psutil.cpu_percent(interval=None, percpu=True)
        except Exception:
            pass

    @staticmethod
    def _read_hard_page_faults() -> int | None:
        """Read cumulative hard page faults (Linux pgmajfault / Windows PageReadIoCount)."""
        if sys.platform.startswith("linux"):
            try:
                for line in Path("/proc/vmstat").read_text(encoding="utf-8").splitlines():
                    if line.startswith("pgmajfault "):
                        return int(line.split()[1])
            except (OSError, ValueError, IndexError):
                return None
        elif sys.platform == "win32":
            try:
                ntdll = ctypes.WinDLL("ntdll.dll")
                nt_query = ntdll.NtQuerySystemInformation
                nt_query.argtypes = [
                    ctypes.c_ulong,
                    ctypes.c_void_p,
                    ctypes.c_ulong,
                    ctypes.POINTER(ctypes.c_ulong),
                ]
                nt_query.restype = ctypes.c_long
                buf = ctypes.create_string_buffer(512)
                ret_len = ctypes.c_ulong()
                # SystemPerformanceInformation = 2; PageReadIoCount is uint32 at offset 84
                if nt_query(2, buf, 512, ctypes.byref(ret_len)) == 0 and ret_len.value >= 88:
                    return int(struct.unpack_from("<I", buf.raw, 84)[0])
            except Exception:
                return None
        return None

    @staticmethod
    def list_disks() -> list[str]:
        """Return sorted list of physical disk devices available in psutil."""
        try:
            counters = psutil.disk_io_counters(perdisk=True) or {}
        except Exception:
            return []
        keys = sorted(counters.keys())
        if sys.platform.startswith("linux"):
            sys_block = Path("/sys/block")
            if sys_block.is_dir():
                physical = [
                    k for k in keys
                    if (sys_block / k).is_dir() and not k.startswith(("loop", "zram", "ram"))
                ]
                if physical:
                    return physical
        return [k for k in keys if not k.startswith(("loop", "zram", "ram"))]

    @staticmethod
    def _get_windows_disk_models() -> dict[int, str]:
        """Read physical disk FriendlyName values from Windows Registry."""
        if sys.platform != "win32":
            return {}
        import winreg

        models: dict[int, str] = {}
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\disk\Enum") as enum_key:
                count, _ = winreg.QueryValueEx(enum_key, "Count")
                for idx in range(int(count)):
                    try:
                        pnp_id, _ = winreg.QueryValueEx(enum_key, str(idx))
                        with winreg.OpenKey(
                            winreg.HKEY_LOCAL_MACHINE, rf"SYSTEM\CurrentControlSet\Enum\{pnp_id}"
                        ) as dev_key:
                            name, _ = winreg.QueryValueEx(dev_key, "FriendlyName")
                            cleaned = str(name).strip()
                            if cleaned:
                                models[idx] = cleaned
                    except OSError:
                        continue
        except OSError:
            pass
        return models

    @staticmethod
    def _get_windows_disk_letters() -> dict[int, list[str]]:
        """Map Windows physical disk index to mounted drive letters via IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS."""
        if sys.platform != "win32":
            return {}
        from ctypes import wintypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        k32.CreateFileW.restype = wintypes.HANDLE
        k32.DeviceIoControl.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.c_void_p,
        ]
        k32.DeviceIoControl.restype = wintypes.BOOL
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        k32.CloseHandle.restype = wintypes.BOOL

        invalid_handle = wintypes.HANDLE(-1).value
        letters: dict[int, list[str]] = {}
        try:
            partitions = psutil.disk_partitions(all=False)
        except Exception:
            return {}

        for part in partitions:
            mp = part.mountpoint or ""
            if len(mp) < 2 or mp[1] != ":":
                continue
            drv = mp[:2]
            handle = k32.CreateFileW(rf"\\.\{drv}", 0, 3, None, 3, 0, None)
            if handle == invalid_handle:
                continue
            try:
                buf = ctypes.create_string_buffer(64)
                ret = wintypes.DWORD()
                if k32.DeviceIoControl(handle, 0x00560000, None, 0, buf, 64, ctypes.byref(ret), None) and ret.value >= 12:
                    disk_num = struct.unpack_from("<I", buf.raw, 8)[0]
                    letters.setdefault(disk_num, []).append(drv)
            finally:
                k32.CloseHandle(handle)
        return letters

    @classmethod
    def list_disk_choices(cls) -> list[tuple[str, str]]:
        """Return (device_key, human_friendly_label) pairs for physical disks."""
        keys = cls.list_disks()
        if sys.platform == "win32":
            models = cls._get_windows_disk_models()
            letters = cls._get_windows_disk_letters()
            choices: list[tuple[str, str]] = []
            for key in keys:
                idx: int | None = None
                if key.lower().startswith("physicaldrive"):
                    try:
                        idx = int(key[len("physicaldrive"):])
                    except ValueError:
                        idx = None
                model = models.get(idx, "") if idx is not None else ""
                drv_list = letters.get(idx, []) if idx is not None else []
                if model and drv_list:
                    label = f"{model} ({', '.join(drv_list)})"
                elif model:
                    label = f"{model} ({key})"
                elif drv_list:
                    label = f"{key} ({', '.join(drv_list)})"
                else:
                    label = key
                choices.append((key, label))
            return choices

        choices = []
        for key in keys:
            model = ""
            model_path = Path("/sys/block") / key / "device" / "model"
            try:
                if model_path.is_file():
                    model = model_path.read_text(encoding="utf-8", errors="ignore").strip()
            except OSError:
                model = ""
            label = f"{model} ({key})" if model else key
            choices.append((key, label))
        return choices

    @staticmethod
    def _safe_disk_io(disk_device: str = ""):
        try:
            if disk_device:
                perdisk = psutil.disk_io_counters(perdisk=True) or {}
                return perdisk.get(disk_device)
            return psutil.disk_io_counters()
        except Exception:
            return None

    @staticmethod
    def _read_linux_psutil_temp() -> tuple[float | None, str | None]:
        sensors_fn = getattr(psutil, "sensors_temperatures", None)
        if sensors_fn is None:
            return None, None
        try:
            temps = sensors_fn(fahrenheit=False)
        except Exception:
            return None, None
        if not temps:
            return None, None

        # Prefer well-known CPU sensor labels
        preferred_chips = ("k10temp", "zenpower", "coretemp", "cpu_thermal", "acpitz")
        for chip in preferred_chips:
            entries = temps.get(chip)
            if not entries:
                continue
            for entry in entries:
                label = (entry.label or "").lower()
                if any(k in label for k in ("tctl", "tdie", "package", "cpu")):
                    if entry.current and entry.current > 0:
                        return float(entry.current), chip
            for entry in entries:
                if entry.current and entry.current > 0:
                    return float(entry.current), chip
        return None, None

    def read_system(self, disk_device: str = "") -> CpuSystemSample:
        """Collect current CPU, RAM, Disk I/O, and uptime metrics."""
        per_core: list[float] = []
        try:
            per_core = psutil.cpu_percent(interval=None, percpu=True)
        except Exception:
            per_core = []

        if per_core:
            cpu_percent = sum(per_core) / len(per_core)
            cpu_max_core = max(per_core)
        else:
            try:
                cpu_percent = float(psutil.cpu_percent(interval=None))
            except Exception:
                cpu_percent = 0.0
            cpu_max_core = cpu_percent

        cpu_freq_mhz: float | None = None
        try:
            freq = psutil.cpu_freq()
            if freq and freq.current > 0:
                cpu_freq_mhz = float(freq.current)
        except Exception:
            cpu_freq_mhz = None

        ram_used_gb = 0.0
        ram_total_gb = 0.0
        ram_percent = 0.0
        try:
            vm = psutil.virtual_memory()
            ram_used_gb = vm.used / (1024.0 ** 3)
            ram_total_gb = vm.total / (1024.0 ** 3)
            ram_percent = float(vm.percent)
        except Exception:
            pass

        swap_used_gb = 0.0
        swap_total_gb = 0.0
        swap_percent = 0.0
        try:
            sw = psutil.swap_memory()
            swap_used_gb = sw.used / (1024.0 ** 3)
            swap_total_gb = sw.total / (1024.0 ** 3)
            swap_percent = float(sw.percent)
        except Exception:
            pass

        now = time.monotonic()
        page_faults_per_sec: float | None = None
        cur_pgfault = self._read_hard_page_faults()
        if cur_pgfault is not None and self._last_pgfault is not None:
            dt_pf = max(0.05, now - self._last_pgfault_ts)
            delta = cur_pgfault - self._last_pgfault
            if delta >= 0:
                page_faults_per_sec = delta / dt_pf
        self._last_pgfault = cur_pgfault
        self._last_pgfault_ts = now

        disk_read_mb_s = 0.0
        disk_write_mb_s = 0.0
        if disk_device != self._last_disk_device:
            self._last_disk_io = None
            self._last_disk_device = disk_device
        cur_io = self._safe_disk_io(disk_device)
        if cur_io is not None and self._last_disk_io is not None:
            dt = max(0.05, now - self._last_disk_ts)
            read_bytes = max(0, cur_io.read_bytes - self._last_disk_io.read_bytes)
            write_bytes = max(0, cur_io.write_bytes - self._last_disk_io.write_bytes)
            disk_read_mb_s = (read_bytes / dt) / (1024.0 * 1024.0)
            disk_write_mb_s = (write_bytes / dt) / (1024.0 * 1024.0)
        self._last_disk_io = cur_io
        self._last_disk_ts = now

        uptime_seconds = 0
        try:
            uptime_seconds = max(0, int(time.time() - psutil.boot_time()))
        except Exception:
            uptime_seconds = 0

        cpu_temp_c, temp_source = self._read_linux_psutil_temp()

        return CpuSystemSample(
            cpu_percent=round(cpu_percent, 1),
            cpu_max_core_percent=round(cpu_max_core, 1),
            cpu_cores=[round(float(v), 1) for v in per_core],
            cpu_freq_mhz=round(cpu_freq_mhz, 0) if cpu_freq_mhz is not None else None,
            cpu_temp_c=round(cpu_temp_c, 1) if cpu_temp_c is not None else None,
            temp_source=temp_source,
            ram_used_gb=round(ram_used_gb, 2),
            ram_total_gb=round(ram_total_gb, 2),
            ram_percent=round(ram_percent, 1),
            swap_used_gb=round(swap_used_gb, 2),
            swap_total_gb=round(swap_total_gb, 2),
            swap_percent=round(swap_percent, 1),
            page_faults_per_sec=round(page_faults_per_sec, 0) if page_faults_per_sec is not None else None,
            disk_read_mb_s=round(disk_read_mb_s, 1),
            disk_write_mb_s=round(disk_write_mb_s, 1),
            uptime_seconds=uptime_seconds,
        )
