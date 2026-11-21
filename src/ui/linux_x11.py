"""Linux X11/EWMH helpers for hiding desktop widgets from taskbar and pager."""

from __future__ import annotations

import ctypes
import logging

logger = logging.getLogger(__name__)


def set_x11_skip_taskbar_libx11(wid: int) -> bool:
    """Set _NET_WM_STATE_SKIP_TASKBAR and _NET_WM_STATE_SKIP_PAGER directly via libX11."""
    try:
        x11 = ctypes.CDLL("libX11.so.6")
    except OSError:
        return False

    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    x11.XCloseDisplay.restype = ctypes.c_int
    x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x11.XDefaultRootWindow.restype = ctypes.c_ulong
    x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    x11.XInternAtom.restype = ctypes.c_ulong
    x11.XChangeProperty.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_ulong),
        ctypes.c_int,
    ]
    x11.XChangeProperty.restype = ctypes.c_int
    x11.XFlush.argtypes = [ctypes.c_void_p]
    x11.XFlush.restype = ctypes.c_int

    class _XClientMessageEvent(ctypes.Structure):
        _fields_ = [
            ("type", ctypes.c_int),
            ("serial", ctypes.c_ulong),
            ("send_event", ctypes.c_int),
            ("display", ctypes.c_void_p),
            ("window", ctypes.c_ulong),
            ("message_type", ctypes.c_ulong),
            ("format", ctypes.c_int),
            ("data", ctypes.c_long * 5),
        ]

    x11.XSendEvent.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_int,
        ctypes.c_long,
        ctypes.POINTER(_XClientMessageEvent),
    ]
    x11.XSendEvent.restype = ctypes.c_int

    display = x11.XOpenDisplay(None)
    if not display:
        return False
    try:
        atom_state = x11.XInternAtom(display, b"_NET_WM_STATE", 0)
        atom_skip_taskbar = x11.XInternAtom(display, b"_NET_WM_STATE_SKIP_TASKBAR", 0)
        atom_skip_pager = x11.XInternAtom(display, b"_NET_WM_STATE_SKIP_PAGER", 0)
        if not atom_state or not atom_skip_taskbar or not atom_skip_pager:
            return False

        xa_atom = 4
        prop_mode_append = 2  # Preserve existing _NET_WM_STATE atoms such as _NET_WM_STATE_ABOVE
        atoms = (ctypes.c_ulong * 2)(atom_skip_taskbar, atom_skip_pager)
        x11.XChangeProperty(
            display,
            ctypes.c_ulong(wid),
            atom_state,
            xa_atom,
            32,
            prop_mode_append,
            atoms,
            2,
        )

        # Also notify the window manager via _NET_WM_STATE_ADD (1) for already-mapped windows.
        root = x11.XDefaultRootWindow(display)
        event = _XClientMessageEvent()
        event.type = 33  # ClientMessage
        event.send_event = 1
        event.display = display
        event.window = ctypes.c_ulong(wid)
        event.message_type = atom_state
        event.format = 32
        event.data[0] = 1  # _NET_WM_STATE_ADD
        event.data[1] = int(atom_skip_taskbar)
        event.data[2] = int(atom_skip_pager)
        event.data[3] = 1  # normal application source indication
        event.data[4] = 0
        substructure_redirect_notify = (1 << 20) | (1 << 19)
        x11.XSendEvent(display, root, 0, substructure_redirect_notify, ctypes.byref(event))
        x11.XFlush(display)
        return True
    except Exception as exc:
        logger.warning("Failed to apply _NET_WM_STATE_SKIP_TASKBAR via libX11: %s", exc)
        return False
    finally:
        x11.XCloseDisplay(display)
