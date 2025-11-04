"""
P4 객체 재사용 테스트

동일한 P4/Perforce 객체를 여러 번 재사용하여 체인지리스트를 생성합니다.
"""

import sys
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

# Perforce 객체 생성 (한 번만!)
print("\nPerforce 객체 생성 및 연결...")
p4 = Perforce()
p4.connect(workspace_name)
print("✓ 연결 성공\n")

# 여러 번 체인지리스트 생성 (실제 툴처럼)
print("동일한 객체로 여러 번 체인지리스트 생성:")
print("=" * 80)

for i in range(1, 6):
    description = f"Reuse Test #{i}"
    print(f"\n[시도 {i}] Description: {description}")
    
    try:
        result = p4.create_change_list(description)
        change_num = result.get("Change", "???")
        print(f"  ✓ 성공! Change #{change_num}")
        
        # 삭제
        try:
            p4.delete_empty_change_list(int(change_num))
            print(f"  (삭제 완료)")
        except:
            print(f"  (삭제 실패)")
            
    except Exception as e:
        print(f"  ✗ 실패!")
        print(f"  에러: {e}")
        print(f"  타입: {type(e).__name__}")
        import traceback
        print(traceback.format_exc())
        break

# 연결 해제 후 다시 연결
print("\n" + "=" * 80)
print("연결 해제 후 재연결 테스트:")
print("=" * 80)

p4.disconnect()
print("✓ 연결 해제")

p4.connect(workspace_name)
print("✓ 재연결\n")

for i in range(6, 9):
    description = f"Reconnect Test #{i}"
    print(f"\n[시도 {i}] Description: {description}")
    
    try:
        result = p4.create_change_list(description)
        change_num = result.get("Change", "???")
        print(f"  ✓ 성공! Change #{change_num}")
        
        try:
            p4.delete_empty_change_list(int(change_num))
            print(f"  (삭제 완료)")
        except:
            print(f"  (삭제 실패)")
            
    except Exception as e:
        print(f"  ✗ 실패!")
        print(f"  에러: {e}")
        print(f"  타입: {type(e).__name__}")
        import traceback
        print(traceback.format_exc())
        break

p4.disconnect()

print("\n" + "=" * 80)
print("테스트 완료")
print("=" * 80)


