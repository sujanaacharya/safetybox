"""Compatibility facade; runners must import :mod:`capture_raw` directly.

Import isolation applies to ``capture_raw.py``. This facade exists only for local
callers migrating from the initial infrastructure draft.
"""

try:
    from .capture_raw import CaptureFailure, capture_raw
    from .score_sealed import score_sealed
except ImportError:  # Direct execution from the audit directory.
    from capture_raw import CaptureFailure, capture_raw
    from score_sealed import score_sealed

__all__ = ["CaptureFailure", "capture_raw", "score_sealed"]
