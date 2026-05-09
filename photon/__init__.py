"""Photon — desktop application for astrophotography science analysis."""

import sys

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# PySide6 compatibility shims
#
# Several classes moved between QtWidgets and QtGui across PySide6 6.x
# releases.  Patching them onto the wrong module here means every import
# in the codebase works regardless of the installed PySide6 version.
# ---------------------------------------------------------------------------

def _apply_pyside6_shims() -> None:
    # Only shim when PySide6 is actually installed (headless CI skips this).
    try:
        import PySide6.QtWidgets  # noqa: F401
        import PySide6.QtGui      # noqa: F401
    except ImportError:
        return

    import PySide6.QtWidgets as _W
    import PySide6.QtGui     as _G

    # QShortcut: lives in QtGui since PySide6 6.0; older builds had it in QtWidgets.
    if not hasattr(_W, "QShortcut"):
        try:
            from PySide6.QtGui import QShortcut
            _W.QShortcut = QShortcut  # type: ignore[attr-defined]
        except ImportError:
            pass

    # QAction: moved to QtGui in PySide6 6.0.
    if not hasattr(_W, "QAction"):
        try:
            from PySide6.QtGui import QAction
            _W.QAction = QAction  # type: ignore[attr-defined]
        except ImportError:
            pass

    if not hasattr(_G, "QAction"):
        try:
            from PySide6.QtWidgets import QAction  # type: ignore[attr-defined]
            _G.QAction = QAction  # type: ignore[attr-defined]
        except ImportError:
            pass

    # QUndoCommand: moved to QtGui in PySide6 6.0.
    if not hasattr(_W, "QUndoCommand"):
        try:
            from PySide6.QtGui import QUndoCommand
            _W.QUndoCommand = QUndoCommand  # type: ignore[attr-defined]
        except ImportError:
            pass

    if not hasattr(_G, "QUndoCommand"):
        try:
            from PySide6.QtWidgets import QUndoCommand  # type: ignore[attr-defined]
            _G.QUndoCommand = QUndoCommand  # type: ignore[attr-defined]
        except ImportError:
            pass


_apply_pyside6_shims()
