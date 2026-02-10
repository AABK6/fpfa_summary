#!/usr/bin/env python3
"""
Deprecated compatibility entrypoint for Foreign Affairs ingestion.

Use `summarize_fa_hardened.py` directly for the canonical implementation.
This wrapper is intentionally minimal and keeps legacy command usage working:

    python summarize_fa.py [N]
"""

from summarize_fa_hardened import main as hardened_main


def main():
    print(
        "[DEPRECATED] `summarize_fa.py` now forwards to "
        "`summarize_fa_hardened.py`."
    )
    hardened_main()


if __name__ == "__main__":
    main()
