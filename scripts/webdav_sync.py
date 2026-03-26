#!/usr/bin/env python3
"""Main entry point for WebDAV sync plugin."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from webdav_sync.cli import main

if __name__ == "__main__":
    main()
