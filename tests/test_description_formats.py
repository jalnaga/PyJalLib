"""
Description 형식 테스트

다양한 Description 형식으로 체인지리스트 생성을 테스트합니다.
"""

import sys
import traceback
from pathlib import Path

# PyJalLib 경로 추가
current_dir = Path(__file__).parent
project_root = current_dir.parent
src_dir = project_root / "src"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from pyjallib.perforce import Perforce

# orvlib에서 워크스페이스 가져오기
try:
    from orvlib.p4Sync import P4Sync
    orvP4 = P4Sync()
    workspace_name = None
    
    if hasattr(orvP4, 'devStorageP4') and orvP4.devStorageP4:
        workspace_name = orvP4.devStorageP4.p4.client
    elif hasattr(orvP4, 'omniP4') and orvP4.omniP4:
        workspace_name = orvP4.omniP4.p4.client
    
    if not workspace_name:
        print("워크스페이스를 찾을 수 없습니다")
        sys.exit(1)
        
    print(f"워크스페이스: {workspace_name}")
    print("=" * 80)
except:
    print("orvlib 로드 실패")
    sys.exit(1)

# Perforce 연결
p4 = Perforce()
p4.connect(workspace_name)

# 다양한 Description 형식 테스트
test_cases = [
    ("단순 텍스트", "Simple description"),
    ("개행 포함 (끝에 개행 없음)", "Line 1\n- Item 1"),
    ("개행 포함 (끝에 개행 있음)", "Line 1\n- Item 1\n"),
    ("실제 툴 형식", "ORV Save Anim File\n- test_file"),
    ("실제 툴 형식 (끝 개행)", "ORV Save Anim File\n- test_file\n"),
    ("다중 개행", "Line 1\n\nLine 2"),
    ("탭 포함", "Line 1\n\t- Item 1"),
]

print("\n테스트 시작:")
print("=" * 80)

for name, description in test_cases:
    print(f"\n[{name}]")
    print(f"Description: {repr(description)}")
    
    try:
        result = p4.create_change_list(description)
        change_num = result.get("Change", "???")
        print(f"✓ 성공! Change #{change_num}")
        
        # 생성된 체인지리스트 삭제
        try:
            p4.delete_empty_change_list(int(change_num))
            print(f"  (삭제 완료)")
        except:
            print(f"  (삭제 실패 - 수동으로 삭제 필요)")
            
    except Exception as e:
        print(f"✗ 실패!")
        print(f"  에러: {e}")
        print(f"  타입: {type(e).__name__}")

p4.disconnect()

print("\n" + "=" * 80)
print("테스트 완료")


