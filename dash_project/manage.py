#!/usr/bin/env python
import os
import sys
from pathlib import Path

if __name__ == '__main__':
    # Ensure repository root is on sys.path so top-level imports like `backend` work
    BASE_DIR = Path(__file__).resolve().parent
    REPO_ROOT = BASE_DIR.parent
    sys.path.insert(0, str(REPO_ROOT))

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dash_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django. Is it installed?") from exc
    execute_from_command_line(sys.argv)
