from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Any


@dataclass
class ChangeListInfo:
    """체인지 리스트 정보를 표현하는 DTO."""

    id: Union[str, int]
    description: str
    status: str
    user: str
    client: str
    files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """사전(dict) 형태로 변환합니다."""
        return {
            "Change": self.id,
            "Description": self.description,
            "Status": self.status,
            "User": self.user,
            "Client": self.client,
            "Files": list(self.files),
        }


@dataclass
class FileInfo:
    """파일 상태/동기화 정보를 표현하는 DTO."""

    path: str
    inPerforce: bool
    isCheckedOut: bool
    changeList: Optional[int] = None
    action: Optional[str] = None
    user: Optional[str] = None
    client: Optional[str] = None
    isCurrentUser: bool = False
    isOthers: bool = False
    syncNeeded: Optional[bool] = None
    syncPerformed: Optional[bool] = None
    skippedReason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """사전(dict) 형태로 변환합니다."""
        return {
            "path": self.path,
            "inPerforce": self.inPerforce,
            "isCheckedOut": self.isCheckedOut,
            "changeList": self.changeList,
            "action": self.action,
            "user": self.user,
            "client": self.client,
            "isCurrentUser": self.isCurrentUser,
            "isOthers": self.isOthers,
            "syncNeeded": self.syncNeeded,
            "syncPerformed": self.syncPerformed,
            "skippedReason": self.skippedReason,
            "warnings": list(self.warnings),
        }


