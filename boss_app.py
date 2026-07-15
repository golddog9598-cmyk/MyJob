"""Compatibility import for older local launch commands.

The active backend is defined in :mod:`myjob_server` and intentionally has no
recruitment-platform automation or platform-data endpoints.
"""

from myjob_server import app, main


if __name__ == "__main__":
    main()
