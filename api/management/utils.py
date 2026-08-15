import os
import shutil
from pathlib import Path
from typing import List

from django.core.management.base import CommandError


def resolve_executable_path(path: str) -> str:
    return str(Path(path).expanduser().resolve())


def find_executable(
    name: str,
    common_paths: List[str],
    not_found_message: str,
) -> str:
    path = shutil.which(name)
    if not path:
        for candidate in common_paths:
            expanded = os.path.expanduser(candidate)
            if os.path.exists(expanded) and os.access(expanded, os.X_OK):
                path = expanded
                break
    if not path:
        raise CommandError(not_found_message)
    return path
