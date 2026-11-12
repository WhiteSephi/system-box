"""Windows-specific graceful fallbacks (PDH GPU counters & optional HWiNFO shared memory)."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import mmap
import re
import struct
import sys

from src.sensors.base import GpuProvider
from src.sensors.models import GpuInfo, GpuSample


def read_hwinfo_cpu_temp() -> tuple[float | None, str | None]:
    """Optionally read CPU temperature from HWiNFO64 shared memory if running (no admin)."""
    if sys.platform != "win32":
        return None, None
    try:
        # HWiNFO64 Sensor Shared Memory header is 44 bytes:
        # sig(4s), ver(I), rev(I), poll_time(q), offset_sensor(I), size_sensor(I),
        # num_sensor(I), offset_reading(I), size_reading(I), num_reading(I)
        shm = mmap.mmap(-1, 44, tagname="Global\\HWiNFO_SENS_SM2", access=mmap.ACCESS_READ)
    except OSError:
        return None, None

    try:
        header = shm.read(44)
        if len(header) < 44 or header[:4] != b"HWiS":
            return None, None
        _, _, _, _, _, _, _, off_read, sz_read, num_read = struct.unpack("<4sIIqIIIIII", header)
        shm.close()
        total_size = off_read + sz_read * num_read
        if total_size <= 44 or sz_read < 280:
            return None, None
        shm_full = mmap.mmap(-1, total_size, tagname="Global\\HWiNFO_SENS_SM2", access=mmap.ACCESS_READ)
        try:
            for i in range(min(num_read, 512)):
                pos = off_read + i * sz_read
                shm_full.seek(pos)
                rec = shm_full.read(sz_read)
                if len(rec) < 280:
                    continue
                reading_type = struct.unpack("<I", rec[0:4])[0]
                if reading_type != 1:  # 1 = SENSOR_TYPE_TEMP
                    continue
                label_raw = rec[12:140].split(b"\x00", 1)[0]
                label = label_raw.decode("utf-8", errors="ignore").lower()
                if any(k in label for k in ("cpu (tctl", "cpu package", "tctl/tdie", "cpu die", "core average")):
                    val = struct.unpack("<d", rec[268:276])[0]
                    if 5.0 < val < 125.0:
                        return round(float(val), 1), "HWiNFO"
        finally:
            shm_full.close()
    except Exception:
        try:
            shm.close()
        except Exception:
            pass
    return None, None


class _PDH_FMT_COUNTERVALUE_DOUBLE(ctypes.Structure):
    _fields_ = [("CStatus", wintypes.DWORD), ("doubleValue", ctypes.c_double)]


class WindowsPdhGpuProvider(GpuProvider):
    """Fallback GPU utilization & VRAM provider on Windows using PDH counters (no admin)."""

    def __init__(self, skip_nvidia: bool = True) -> None:
        self._available = False
        self._gpus: list[GpuInfo] = []
        self._query = wintypes.HANDLE()
        self._util_counter = wintypes.HANDLE()
        self._mem_counter = wintypes.HANDLE()
        self._pdh = None
        if sys.platform == "win32":
            self._init_pdh(skip_nvidia=skip_nvidia)

    def _init_pdh(self, skip_nvidia: bool) -> None:
        try:
            pdh = ctypes.WinDLL("pdh.dll")
            self._pdh = pdh
            if pdh.PdhOpenQueryW(None, 0, ctypes.byref(self._query)) != 0:
                return
            rc1 = pdh.PdhAddEnglishCounterW(
                self._query,
                "\\GPU Engine(*)\\Utilization Percentage",
                0,
                ctypes.byref(self._util_counter),
            )
            rc2 = pdh.PdhAddEnglishCounterW(
                self._query,
                "\\GPU Adapter Memory(*)\\Dedicated Usage",
                0,
                ctypes.byref(self._mem_counter),
            )
            if rc1 != 0 and rc2 != 0:
                self.close()
                return
            pdh.PdhCollectQueryData(self._query)
            self._gpus.append(
                GpuInfo(
                    index=0,
                    name="Windows GPU (PDH)",
                    vendor="unknown" if not skip_nvidia else "integrated",
                    backend="pdh",
                )
            )
            self._available = True
        except Exception:
            self._available = False
            self._gpus = []

    def is_available(self) -> bool:
        return self._available and len(self._gpus) > 0

    def list_gpus(self) -> list[GpuInfo]:
        return list(self._gpus)

    def _read_formatted_sum(self, counter: wintypes.HANDLE) -> float | None:
        if not self._pdh or not counter:
            return None
        val = _PDH_FMT_COUNTERVALUE_DOUBLE()
        rc = self._pdh.PdhGetFormattedCounterValue(counter, 0x00000200, None, ctypes.byref(val))
        if rc == 0 and val.CStatus == 0:
            return float(val.doubleValue)
        return None

    def read_gpu(self, local_index: int) -> GpuSample | None:
        if not self.is_available() or local_index != 0 or self._pdh is None:
            return None
        try:
            self._pdh.PdhCollectQueryData(self._query)
            util = self._read_formatted_sum(self._util_counter)
            mem_bytes = self._read_formatted_sum(self._mem_counter)
            vram_used_mb = round(mem_bytes / (1024.0 * 1024.0), 0) if mem_bytes is not None else None
            return GpuSample(
                index=0,
                name=self._gpus[0].name,
                vendor=self._gpus[0].vendor,
                available=True,
                util_percent=round(min(100.0, max(0.0, util)), 1) if util is not None else None,
                vram_used_mb=vram_used_mb,
            )
        except Exception:
            return None

    def close(self) -> None:
        if self._pdh is not None and self._query:
            try:
                self._pdh.PdhCloseQuery(self._query)
            except Exception:
                pass
            self._query = wintypes.HANDLE()
            self._available = False
