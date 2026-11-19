"""Cross-platform disk capacity discovery and usage reader (Windows & Linux)."""

from __future__ import annotations

import ctypes
from pathlib import Path
import sys

import psutil

from src.sensors.models import DiskSpaceInfo

_IGNORED_FSTYPES = {
    "autofs",
    "bpf",
    "cgroup",
    "cgroup2",
    "configfs",
    "debugfs",
    "devpts",
    "devtmpfs",
    "efivarfs",
    "fusectl",
    "hugetlbfs",
    "mqueue",
    "nsfs",
    "overlay",
    "proc",
    "pstore",
    "ramfs",
    "securityfs",
    "squashfs",
    "sysfs",
    "tmpfs",
    "tracefs",
}

_LINUX_IGNORED_PREFIXES = (
    "/snap/",
    "/run/user/",
    "/run/credentials/",
    "/dev/",
    "/proc/",
    "/sys/",
    "/var/lib/docker/",
    "/var/lib/containers/",
)


def format_storage_size(gb: float) -> str:
    """Format GiB/GB size cleanly as GB or TB."""
    if gb >= 1024.0:
        return f"{gb / 1024.0:.2f} TB"
    if gb >= 100.0:
        return f"{gb:.1f} GB"
    return f"{gb:.1f} GB"


def _get_windows_volume_label(mountpoint: str) -> str:
    """Read Windows volume label via GetVolumeInformationW, returning empty string on error."""
    if sys.platform != "win32":
        return ""
    try:
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_vol_info = kernel32.GetVolumeInformationW
        get_vol_info.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPWSTR,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPWSTR,
            wintypes.DWORD,
        ]
        get_vol_info.restype = wintypes.BOOL

        buf = ctypes.create_unicode_buffer(261)
        ok = get_vol_info(
            mountpoint,
            buf,
            len(buf),
            None,
            None,
            None,
            None,
            0,
        )
        return buf.value.strip() if ok else ""
    except Exception:
        return ""


def _build_linux_label(mountpoint: str) -> str:
    if mountpoint == "/":
        return "System (/)"
    if mountpoint == "/home":
        return "Home (/home)"
    name = Path(mountpoint).name or mountpoint
    return f"{name} ({mountpoint})"


def _build_windows_label(mountpoint: str) -> str:
    drive = mountpoint.rstrip("\\/")
    vol = _get_windows_volume_label(mountpoint)
    return f"{vol} ({drive})" if vol else f"Lokaler Datenträger ({drive})"


def _mount_priority(mountpoint: str) -> tuple[int, int, str]:
    """Rank mountpoints so '/' and '/home' win over deeper bind/subvolume mounts."""
    if mountpoint == "/":
        return (0, 1, mountpoint)
    if mountpoint == "/home":
        return (1, len(mountpoint), mountpoint)
    if mountpoint.startswith(("/mnt/", "/media/", "/run/media/")):
        return (2, len(mountpoint), mountpoint)
    return (3, len(mountpoint), mountpoint)


def read_disk_spaces(
    deduplicate_devices: bool = True,
    show_boot: bool = False,
) -> list[DiskSpaceInfo]:
    """Read capacity and usage for mounted physical drives/partitions."""
    try:
        partitions = psutil.disk_partitions(all=False)
    except Exception:
        return []

    is_linux = sys.platform.startswith("linux")
    is_windows = sys.platform == "win32"

    candidates: list[tuple[psutil._common.sdiskpart, DiskSpaceInfo]] = []
    seen_mounts: set[str] = set()

    for part in partitions:
        mnt = part.mountpoint
        if not mnt or mnt in seen_mounts:
            continue
        fstype = (part.fstype or "").lower()
        opts = (part.opts or "").lower()

        if fstype in _IGNORED_FSTYPES:
            continue
        if is_windows and "cdrom" in opts:
            continue
        if is_linux:
            if any(mnt.startswith(prefix) for prefix in _LINUX_IGNORED_PREFIXES):
                continue
            if not show_boot and mnt in ("/boot", "/boot/efi", "/efi"):
                continue

        try:
            usage = psutil.disk_usage(mnt)
        except Exception:
            continue

        if usage.total <= 0:
            continue

        seen_mounts.add(mnt)
        total_gb = usage.total / (1024.0**3)
        used_gb = usage.used / (1024.0**3)
        free_gb = usage.free / (1024.0**3)
        label = _build_windows_label(mnt) if is_windows else _build_linux_label(mnt)

        info = DiskSpaceInfo(
            device=part.device or mnt,
            mountpoint=mnt,
            label=label,
            fstype=part.fstype or "",
            total_gb=round(total_gb, 2),
            used_gb=round(used_gb, 2),
            free_gb=round(free_gb, 2),
            percent=round(float(usage.percent), 1),
        )
        candidates.append((part, info))

    if deduplicate_devices and is_linux:
        best_by_device: dict[str, DiskSpaceInfo] = {}
        for _, info in candidates:
            existing = best_by_device.get(info.device)
            if existing is None or _mount_priority(info.mountpoint) < _mount_priority(existing.mountpoint):
                best_by_device[info.device] = info
        result = list(best_by_device.values())
    else:
        result = [info for _, info in candidates]

    result.sort(key=lambda d: _mount_priority(d.mountpoint) if is_linux else (0, 0, d.mountpoint))
    return result
