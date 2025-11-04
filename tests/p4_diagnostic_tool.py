"""
P4 체인지리스트 생성 문제 진단 도구

이 스크립트는 Perforce 체인지리스트 생성 관련 문제를 진단하기 위한 통합 도구입니다.
3ds Max 환경에서 실행 가능하며, 모든 진단 결과를 로그 파일로 저장합니다.

실행 방법:
    from tests.p4_diagnostic_tool import run_diagnostic
    run_diagnostic("workspace_name")

출력:
    %USERPROFILE%\\Documents\\PyJalLib_Diagnostics\\p4_diagnostic_YYYYMMDD_HHMMSS.{json,txt}
"""

import sys
import os
import json
import traceback
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    from P4 import P4, P4Exception
except ImportError as e:
    exact_import_error = str(e)
    exact_traceback = traceback.format_exc()

try:
    # 프로젝트 루트를 sys.path에 추가
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    src_dir = project_root / "src"
    
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    
    from pyjallib.perforceCore.adapter import P4Adapter
    from pyjallib.perforceCore.service import PerforceService
    from pyjallib.perforce import Perforce
    from pyjallib.exceptions import PerforceError
except ImportError as e:
    exact_import_error = str(e)
    exact_traceback = traceback.format_exc()


def get_documents_path() -> Path:
    """사용자의 Documents 폴더 경로를 반환합니다."""
    try:
        # Windows
        documents = Path.home() / "Documents"
    except Exception:
        # 폴백: 현재 디렉토리
        documents = Path.cwd()
    
    # 진단 로그 폴더
    diagnostic_dir = documents / "PyJalLib_Diagnostics"
    diagnostic_dir.mkdir(parents=True, exist_ok=True)
    
    return diagnostic_dir


def safe_get_value(func, default=None):
    """함수를 안전하게 실행하고 예외가 발생하면 기본값 반환."""
    try:
        return func()
    except Exception as e:
        return default if default is not None else str(e)


def collect_environment_info() -> Dict[str, Any]:
    """환경 정보를 수집합니다."""
    info = {}
    
    # Python 정보
    info["python_version"] = safe_get_value(lambda: sys.version)
    info["python_version_info"] = safe_get_value(lambda: sys.version_info)
    info["python_executable"] = safe_get_value(lambda: sys.executable)
    info["platform"] = safe_get_value(lambda: platform.platform())
    info["system"] = safe_get_value(lambda: platform.system())
    info["machine"] = safe_get_value(lambda: platform.machine())
    info["default_encoding"] = safe_get_value(lambda: sys.getdefaultencoding())
    
    # P4 Python 정보
    try:
        p4 = P4()
        info["p4_python_version"] = safe_get_value(lambda: P4.__version__)
        try:
            info["p4_api_info"] = safe_get_value(lambda: P4.P4API.identify())
        except:
            info["p4_api_info"] = None
        info["p4_class_location"] = safe_get_value(lambda: P4.__module__)
    except Exception as e:
        info["p4_python_version"] = f"가져오기 실패: {e}"
        info["p4_python_available"] = False
    else:
        info["p4_python_available"] = True
    
    # 환경 변수
    p4_env_vars = ["P4PORT", "P4USER", "P4CLIENT", "P4PASSWD", "P4CONFIG", "P4CHARSET", "P4TRUST"]
    info["environment_variables"] = {}
    for var in p4_env_vars:
        info["environment_variables"][var] = safe_get_value(lambda v=var: os.environ.get(v), None)
    
    # 3ds Max 감지 시도
    info["max_detected"] = False
    for module_name in sys.modules:
        if "MaxPlus" in module_name or "pymxs" in module_name:
            info["max_detected"] = True
            info["max_modules"] = [m for m in sys.modules if "Max" in m or "mxs" in m]
            break
    
    # 타임스탬프
    info["timestamp"] = datetime.now().isoformat()
    info["machine_name"] = safe_get_value(lambda: platform.node())
    
    return info


def test_p4_connection(workspace_name: str) -> Dict[str, Any]:
    """P4 연결 및 서버 정보를 수집합니다."""
    result = {"connected": False, "error": None}
    
    try:
        p4 = P4()
        p4.client = workspace_name
        p4.connect()
        
        result["connected"] = True
        
        # 서버 정보
        try:
            info = p4.run_info()
            result["server_info"] = info[0] if info else {}
        except Exception as e:
            result["server_info_error"] = str(e)
        
        # 워크스페이스 정보
        try:
            client_info = p4.run_client("-o", workspace_name)
            result["client_info"] = client_info[0] if client_info else {}
        except Exception as e:
            result["client_info_error"] = str(e)
        
        # 사용자 정보
        result["user"] = p4.user
        result["client"] = p4.client
        result["port"] = p4.port
        
        # 연결 해제
        p4.disconnect()
        
    except Exception as e:
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
    
    return result


def test_fetch_change_spec(workspace_name: str) -> Dict[str, Any]:
    """체인지 스펙 생성 테스트"""
    result = {"success": False}
    
    try:
        p4 = P4()
        p4.client = workspace_name
        p4.connect()
        
        # fetch_change() 호출
        try:
            spec = p4.fetch_change()
            
            result["success"] = True
            result["spec_keys"] = list(spec.keys())
            result["spec_type"] = type(spec).__name__
            
            # 각 필드 정보
            result["spec_fields"] = {}
            for key, value in spec.items():
                result["spec_fields"][key] = {
                    "type": type(value).__name__,
                    "value": str(value)[:200] if value else None  # 200자로 제한
                }
            
            # Description 필드 특별 확인
            if "Description" in spec:
                desc = spec["Description"]
                result["description_info"] = {
                    "exists": True,
                    "type": type(desc).__name__,
                    "length": len(str(desc)) if desc else 0,
                    "encoding_sample": repr(str(desc)[:50]) if desc else None
                }
            
        except Exception as e:
            result["fetch_error"] = str(e)
            result["fetch_traceback"] = traceback.format_exc()
        
        p4.disconnect()
        
    except Exception as e:
        result["connection_error"] = str(e)
        result["traceback"] = traceback.format_exc()
    
    return result


def test_save_methods(workspace_name: str, description: str = "Test Changelist") -> Dict[str, Any]:
    """다양한 저장 방식 테스트"""
    result = {}
    
    # 방법 A: p4.save_change(spec)
    result["method_a"] = test_method_a(workspace_name, description)
    
    # 방법 B: p4.input = spec; p4.run_change("-i")
    result["method_b"] = test_method_b(workspace_name, description)
    
    # 방법 C: p4.run("change", "-i", input=spec)
    result["method_c"] = test_method_c(workspace_name, description)
    
    return result


def test_method_a(workspace_name: str, description: str) -> Dict[str, Any]:
    """방법 A: p4.save_change(spec)"""
    result = {"method_name": "p4.save_change(spec)", "success": False}
    
    try:
        p4 = P4()
        p4.client = workspace_name
        p4.connect()
        
        spec = p4.fetch_change()
        spec["Description"] = description
        
        # 에러 초기화 (시도하지만 실패해도 계속 진행)
        try:
            p4.errors = []
            p4.warnings = []
        except AttributeError:
            pass  # P4 버전에 따라 read-only일 수 있음
        
        try:
            saved = p4.save_change(spec)
            result["success"] = True
            result["return_value"] = str(saved)[:500] if saved else None
            result["return_type"] = type(saved).__name__ if saved else None
        except Exception as e:
            result["error"] = str(e)
            result["error_type"] = type(e).__name__
            result["traceback"] = traceback.format_exc()
        
        # 에러 및 경고 수집
        try:
            result["p4_errors"] = [str(e) for e in p4.errors] if p4.errors else []
            result["p4_warnings"] = [str(w) for w in p4.warnings] if p4.warnings else []
        except AttributeError:
            result["p4_errors"] = []
            result["p4_warnings"] = []
        
        p4.disconnect()
        
    except Exception as e:
        result["outer_error"] = str(e)
        result["outer_traceback"] = traceback.format_exc()
    
    return result


def test_method_b(workspace_name: str, description: str) -> Dict[str, Any]:
    """방법 B: p4.input = spec; p4.run_change("-i")"""
    result = {"method_name": "p4.input = spec; p4.run_change('-i')", "success": False}
    
    try:
        p4 = P4()
        p4.client = workspace_name
        p4.connect()
        
        spec = p4.fetch_change()
        spec["Description"] = description
        
        # 에러 초기화 (시도하지만 실패해도 계속 진행)
        try:
            p4.errors = []
            p4.warnings = []
        except AttributeError:
            pass  # P4 버전에 따라 read-only일 수 있음
        
        try:
            p4.input = spec
            saved = p4.run_change("-i")
            result["success"] = True
            result["return_value"] = str(saved)[:500] if saved else None
            result["return_type"] = type(saved).__name__ if saved else None
        except Exception as e:
            result["error"] = str(e)
            result["error_type"] = type(e).__name__
            result["traceback"] = traceback.format_exc()
        
        # 에러 및 경고 수집
        try:
            result["p4_errors"] = [str(e) for e in p4.errors] if p4.errors else []
            result["p4_warnings"] = [str(w) for w in p4.warnings] if p4.warnings else []
        except AttributeError:
            result["p4_errors"] = []
            result["p4_warnings"] = []
        
        p4.disconnect()
        
    except Exception as e:
        result["outer_error"] = str(e)
        result["outer_traceback"] = traceback.format_exc()
    
    return result


def test_method_c(workspace_name: str, description: str) -> Dict[str, Any]:
    """방법 C: p4.run("change", "-i", input=spec)"""
    result = {"method_name": "p4.run('change', '-i', input=spec)", "success": False}
    
    try:
        p4 = P4()
        p4.client = workspace_name
        p4.connect()
        
        spec = p4.fetch_change()
        spec["Description"] = description
        
        # 에러 초기화 (시도하지만 실패해도 계속 진행)
        try:
            p4.errors = []
            p4.warnings = []
        except AttributeError:
            pass  # P4 버전에 따라 read-only일 수 있음
        
        try:
            saved = p4.run("change", "-i", input=spec)
            result["success"] = True
            result["return_value"] = str(saved)[:500] if saved else None
            result["return_type"] = type(saved).__name__ if saved else None
        except Exception as e:
            result["error"] = str(e)
            result["error_type"] = type(e).__name__
            result["traceback"] = traceback.format_exc()
        
        # 에러 및 경고 수집
        try:
            result["p4_errors"] = [str(e) for e in p4.errors] if p4.errors else []
            result["p4_warnings"] = [str(w) for w in p4.warnings] if p4.warnings else []
        except AttributeError:
            result["p4_errors"] = []
            result["p4_warnings"] = []
        
        p4.disconnect()
        
    except Exception as e:
        result["outer_error"] = str(e)
        result["outer_traceback"] = traceback.format_exc()
    
    return result


def test_pyjallib_library(workspace_name: str, description: str = "Test Changelist") -> Dict[str, Any]:
    """pyjallib 라이브러리 테스트"""
    result = {"success": False, "steps": {}}
    
    try:
        # 1. 초기화
        result["steps"]["init"] = {"success": False}
        try:
            from pyjallib.perforce import Perforce
            p4_instance = Perforce()
            result["steps"]["init"]["success"] = True
        except Exception as e:
            result["steps"]["init"]["error"] = str(e)
            result["steps"]["init"]["traceback"] = traceback.format_exc()
            return result
        
        # 2. 연결
        result["steps"]["connect"] = {"success": False}
        try:
            p4_instance.connect(workspace_name)
            result["steps"]["connect"]["success"] = True
            result["steps"]["connect"]["connected"] = p4_instance.connected
            result["steps"]["connect"]["workspace_root"] = p4_instance.workspaceRoot
        except Exception as e:
            result["steps"]["connect"]["error"] = str(e)
            result["steps"]["connect"]["traceback"] = traceback.format_exc()
            return result
        
        # 3. 체인지리스트 생성
        result["steps"]["create_changelist"] = {"success": False}
        try:
            changelist = p4_instance.create_change_list(description)
            result["steps"]["create_changelist"]["success"] = True
            result["steps"]["create_changelist"]["result"] = changelist
        except Exception as e:
            result["steps"]["create_changelist"]["error"] = str(e)
            result["steps"]["create_changelist"]["error_type"] = type(e).__name__
            result["steps"]["create_changelist"]["traceback"] = traceback.format_exc()
        
        # 4. 내부 상태 확인
        result["steps"]["internal_state"] = {}
        try:
            result["steps"]["internal_state"]["adapter_connected"] = safe_get_value(lambda: p4_instance._adapter.connected, "N/A")
            result["steps"]["internal_state"]["adapter_workspace_root"] = safe_get_value(lambda: p4_instance._adapter.workspaceRoot, "N/A")
            result["steps"]["internal_state"]["service_connected"] = safe_get_value(lambda: p4_instance._service.is_connected, "N/A")
        except Exception as e:
            result["steps"]["internal_state"]["error"] = str(e)
        
        # 5. 정리
        try:
            p4_instance.disconnect()
        except:
            pass
        
        result["success"] = True
        
    except Exception as e:
        result["outer_error"] = str(e)
        result["outer_traceback"] = traceback.format_exc()
    
    return result


def generate_report(data: Dict[str, Any]) -> str:
    """진단 결과를 읽기 쉬운 텍스트 리포트로 생성"""
    lines = []
    lines.append("=" * 80)
    lines.append("P4 체인지리스트 생성 문제 진단 리포트")
    lines.append("=" * 80)
    lines.append("")
    
    # 환경 정보
    lines.append("환경 정보:")
    lines.append("-" * 80)
    env = data.get("environment", {})
    lines.append(f"Python 버전: {env.get('python_version', 'N/A')}")
    lines.append(f"플랫폼: {env.get('platform', 'N/A')}")
    lines.append(f"인코딩: {env.get('default_encoding', 'N/A')}")
    lines.append(f"P4 Python 버전: {env.get('p4_python_version', 'N/A')}")
    lines.append(f"3ds Max 감지: {env.get('max_detected', False)}")
    lines.append(f"시간: {env.get('timestamp', 'N/A')}")
    lines.append(f"머신: {env.get('machine_name', 'N/A')}")
    lines.append("")
    
    # P4 연결 정보
    lines.append("P4 연결 정보:")
    lines.append("-" * 80)
    conn = data.get("p4_connection", {})
    if conn.get("connected"):
        lines.append("✓ 연결 성공")
        lines.append(f"사용자: {conn.get('user', 'N/A')}")
        lines.append(f"클라이언트: {conn.get('client', 'dashboard')}")
    else:
        lines.append("✗ 연결 실패")
        lines.append(f"에러: {conn.get('error', 'N/A')}")
    lines.append("")
    
    # 체인지 스펙
    lines.append("체인지 스펙 생성:")
    lines.append("-" * 80)
    spec = data.get("change_spec", {})
    if spec.get("success"):
        lines.append("✓ 성공")
        lines.append(f"필드 수: {len(spec.get('spec_keys', []))}")
        if "description_info" in spec:
            info = spec["description_info"]
            lines.append(f"Description 필드: {info.get('type', 'N/A')}, 길이: {info.get('length', 0)}")
    else:
        lines.append("✗ 실패")
        lines.append(f"에러: {spec.get('fetch_error', 'N/A')}")
    lines.append("")
    
    # 저장 방식 테스트
    lines.append("저장 방식 테스트:")
    lines.append("-" * 80)
    save_methods = data.get("save_methods", {})
    for key in ["method_a", "method_b", "method_c"]:
        method = save_methods.get(key, {})
        method_name = method.get("method_name", "N/A")
        success = method.get("success", False)
        status = "✓ 성공" if success else "✗ 실패"
        lines.append(f"{method_name}: {status}")
        if not success and "error" in method:
            lines.append(f"  에러: {method['error']}")
    lines.append("")
    
    # pyjallib 테스트
    lines.append("pyjallib 라이브러리 테스트:")
    lines.append("-" * 80)
    library = data.get("pyjallib_test", {})
    steps = library.get("steps", {})
    for step_name in ["init", "connect", "create_changelist"]:
        step = steps.get(step_name, {})
        success = step.get("success", False)
        status = "✓ 성공" if success else "✗ 실패"
        lines.append(f"  {step_name}: {status}")
        if not success and "error" in step:
            lines.append(f"    에러: {step['error']}")
    lines.append("")
    
    lines.append("=" * 80)
    
    return "\n".join(lines)


def run_diagnostic(workspace_name: str = None, description: str = None, use_orvlib: bool = True) -> str:
    """
    P4 체인지리스트 생성 문제를 진단합니다.
    
    Args:
        workspace_name: P4 워크스페이스 이름 (orvlib에서 자동으로 가져옴)
        description: 테스트용 체인지리스트 설명 (기본값: "PyJalLib Diagnostic Test")
        use_orvlib: orvlib의 P4Sync를 사용할지 여부 (기본값: True)
    
    Returns:
        생성된 로그 파일 경로
    """
    if description is None:
        description = "PyJalLib Diagnostic Test"
    
    # orvlib에서 워크스페이스 가져오기
    orvlib_error = None
    if use_orvlib:
        try:
            from orvlib.p4Sync import P4Sync
            orvP4 = P4Sync()
            
            # workspace_name이 없으면 자동 감지 시도
            if workspace_name is None:
                # devStorageP4 사용 가능하면 사용
                if hasattr(orvP4, 'devStorageP4') and orvP4.devStorageP4:
                    workspace_name = orvP4.devStorageP4.p4.client if hasattr(orvP4.devStorageP4, 'p4') else None
                
                # 여전히 없으면 omniP4 시도
                if workspace_name is None and hasattr(orvP4, 'omniP4') and orvP4.omniP4:
                    workspace_name = orvP4.omniP4.p4.client if hasattr(orvP4.omniP4, 'p4') else None
                
        except ImportError as e:
            orvlib_error = f"orvlib를 찾을 수 없습니다: {e}"
            workspace_name = None
        except Exception as e:
            orvlib_error = f"orvlib 초기화 실패: {e}"
            workspace_name = None
    
    # 결과 저장용
    results = {}
    results["orvlib_error"] = orvlib_error
    
    print("P4 체인지리스트 진단 시작...")
    
    if orvlib_error:
        print(f"⚠ orvlib 오류: {orvlib_error}")
        print("   진단을 중단합니다.")
        print("")
    elif workspace_name is None:
        print("⚠ 경고: 워크스페이스 이름을 찾을 수 없습니다!")
        print("   진단을 계속하지만 일부 테스트가 건너뛰어질 수 있습니다.")
        print("")
    else:
        print(f"워크스페이스: {workspace_name}")
        print("")
    
    # orvlib 오류가 있으면 여기서 중단
    if orvlib_error:
        results["environment"] = collect_environment_info()
        results["p4_connection"] = {"connected": False, "error": orvlib_error}
        results["change_spec"] = {"success": False, "error": orvlib_error}
        results["save_methods"] = {}
        results["pyjallib_test"] = {"success": False, "error": orvlib_error}
    else:
        # 1. 환경 정보 수집
        print("1. 환경 정보 수집 중...")
        results["environment"] = collect_environment_info()
        print("   ✓ 완료")
        
        # 2. P4 연결 테스트
        if workspace_name:
            print("2. P4 연결 테스트 중...")
            results["p4_connection"] = test_p4_connection(workspace_name)
            if results["p4_connection"]["connected"]:
                print("   ✓ 연결 성공")
            else:
                print(f"   ✗ 실패: {results['p4_connection']['error']}")
        else:
            print("2. P4 연결 테스트 건너뛰기 (워크스페이스 이름 없음)")
            results["p4_connection"] = {"connected": False, "error": "워크스페이스 이름 없음"}
        
        # 3. 체인지 스펙 생성 테스트
        if workspace_name and results["p4_connection"]["connected"]:
            print("3. 체인지 스펙 생성 테스트 중...")
            results["change_spec"] = test_fetch_change_spec(workspace_name)
            if results["change_spec"]["success"]:
                print("   ✓ 성공")
            else:
                print(f"   ✗ 실패: {results['change_spec'].get('fetch_error', 'Unknown')}")
            
            # 4. 다양한 저장 방식 테스트
            print("4. 다양한 저장 방식 테스트 중...")
            results["save_methods"] = test_save_methods(workspace_name, description)
            for key in ["method_a", "method_b", "method_c"]:
                method = results["save_methods"][key]
                status = "✓" if method["success"] else "✗"
                print(f"   {status} {method['method_name']}")
            
            # 5. pyjallib 라이브러리 테스트
            print("5. pyjallib 라이브러리 테스트 중...")
            results["pyjallib_test"] = test_pyjallib_library(workspace_name, description)
            if results["pyjallib_test"]["success"]:
                print("   ✓ 성공")
            else:
                steps = results["pyjallib_test"].get("steps", {})
                for step_name, step in steps.items():
                    if not step.get("success", False):
                        print(f"   ✗ {step_name} 실패: {step.get('error', 'Unknown')}")
        else:
            print("3-5. 추가 테스트 건너뛰기 (P4 연결 없음)")
            results["change_spec"] = {"success": False, "error": "P4 연결 없음"}
            results["save_methods"] = {}
            results["pyjallib_test"] = {"success": False, "error": "P4 연결 없음"}
    
    # 로그 파일 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = get_documents_path()
    
    # JSON 파일
    json_path = output_dir / f"p4_diagnostic_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 텍스트 리포트
    txt_path = output_dir / f"p4_diagnostic_{timestamp}.txt"
    report = generate_report(results)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print("")
    print("=" * 80)
    print("진단 완료!")
    print(f"출력 위치: {output_dir}")
    print(f"  - {json_path.name}")
    print(f"  - {txt_path.name}")
    print("=" * 80)
    
    return str(json_path)


if __name__ == "__main__":
    # 기본적으로 orvlib 사용, workspace는 자동 감지
    run_diagnostic()

