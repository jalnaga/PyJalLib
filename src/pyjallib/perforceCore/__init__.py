"""
Perforce 코어 패키지.

Adapter/Service/DTO를 제공하여 레거시 파사드(`pyjallib.perforce`)가
내부적으로 위임할 수 있도록 합니다.
"""

from .adapter import P4Adapter
from .service import PerforceService
from .dtos import ChangeListInfo, FileInfo

__all__ = [
    "P4Adapter",
    "PerforceService",
    "ChangeListInfo",
    "FileInfo",
]


