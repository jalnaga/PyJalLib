"""
P4 진단 로그 분석 도구

수집된 진단 로그 파일들을 비교 분석하여 정상 환경과 문제 환경의 차이점을 파악합니다.

사용법:
    python analyze_diagnostic_logs.py --working log1.json log2.json --failing log3.json log4.json

출력:
    진단_결과_분석_YYYYMMDD_HHMMSS.txt
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Set
from collections import defaultdict


def load_log(log_path: str) -> Dict[str, Any]:
    """JSON 로그 파일을 로드"""
    with open(log_path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_values(name: str, working_values: List[Any], failing_values: List[Any], output: List[str]):
    """값들을 비교하고 차이점이 있으면 출력"""
    working_set = set(str(v) for v in working_values)
    failing_set = set(str(v) for v in failing_values)
    
    common = working_set & failing_set
    only_working = working_set - failing_set
    only_failing = failing_set - working_set
    
    if len(common) == len(working_set) == len(failing_set) == 1:
        # 모두 동일
        return
    
    output.append(f"\n{name}:")
    if common:
        output.append(f"  공통: {', '.join(sorted(common))}")
    if only_working:
        output.append(f"  ✓ 정상 환경에만: {', '.join(sorted(only_working))}")
    if only_failing:
        output.append(f"  ✗ 문제 환경에만: {', '.join(sorted(only_failing))}")


def analyze_logs(working_logs: List[Dict], failing_logs: List[Dict]) -> str:
    """로그들을 비교 분석"""
    output = []
    output.append("=" * 80)
    output.append("P4 진단 로그 비교 분석 결과")
    output.append("=" * 80)
    output.append("")
    output.append(f"분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append("")
    
    # 1. 환경 정보 비교
    output.append("1. 환경 정보 비교")
    output.append("-" * 80)
    
    env_fields = ["python_version", "platform", "system", "default_encoding", "p4_python_version"]
    for field in env_fields:
        working_vals = [log.get("environment", {}).get(field, "N/A") for log in working_logs]
        failing_vals = [log.get("environment", {}).get(field, "N/A") for log in failing_logs]
        compare_values(field, working_vals, failing_vals, output)
    
    # P4 Python 사용 가능 여부
    working_p4_available = [log.get("environment", {}).get("p4_python_available", False) for log in working_logs]
    failing_p4_available = [log.get("environment", {}).get("p4_python_available", False) for log in failing_logs]
    compare_values("p4_python_available", working_p4_available, failing_p4_available, output)
    
    # 환경 변수 비교
    output.append("\n환경 변수:")
    p4_vars = ["P4PORT", "P4USER", "P4CLIENT", "P4CONFIG", "P4CHARSET"]
    for var in p4_vars:
        working_vals = [log.get("environment", {}).get("environment_variables", {}).get(var) for log in working_logs]
        failing_vals = [log.get("environment", {}).get("environment_variables", {}).get(var) for log in failing_logs]
        compare_values(f"  {var}", working_vals, failing_vals, output)
    
    output.append("")
    
    # 2. P4 연결 정보 비교
    output.append("2. P4 연결 정보 비교")
    output.append("-" * 80)
    
    working_connected = [log.get("p4_connection", {}).get("connected", False) for log in working_logs]
    failing_connected = [log.get("p4_connection", {}).get("connected", False) for log in failing_logs]
    
    if all(working_connected) and all(failing_connected):
        output.append("✓ 모든 환경에서 P4 연결 성공")
        
        # 서버 정보 비교
        output.append("\nP4 서버 정보:")
        server_fields = ["serverDate", "serverVersion", "serverUptime", "serverLicenses"]
        for field in server_fields:
            working_vals = [log.get("p4_connection", {}).get("server_info", {}).get(field) for log in working_logs if log.get("p4_connection", {}).get("server_info")]
            failing_vals = [log.get("p4_connection", {}).get("server_info", {}).get(field) for log in failing_logs if log.get("p4_connection", {}).get("server_info")]
            if working_vals or failing_vals:
                compare_values(f"  {field}", working_vals, failing_vals, output)
    elif all(failing_connected) and not any(working_connected):
        output.append("⚠ 경고: 문제 환경만 연결 실패")
        for log in failing_logs:
            error = log.get("p4_connection", {}).get("error", "Unknown")
            output.append(f"  에러: {error}")
    else:
        output.append("⚠ 연결 상태가 일관되지 않음")
    
    output.append("")
    
    # 3. 체인지 스펙 생성 비교
    output.append("3. 체인지 스펙 생성 비교")
    output.append("-" * 80)
    
    working_spec_success = [log.get("change_spec", {}).get("success", False) for log in working_logs]
    failing_spec_success = [log.get("change_spec", {}).get("success", False) for log in failing_logs]
    
    if all(working_spec_success) and all(failing_spec_success):
        output.append("✓ 모든 환경에서 체인지 스펙 생성 성공")
        
        # 필드 비교
        working_keys = set()
        failing_keys = set()
        for log in working_logs:
            keys = log.get("change_spec", {}).get("spec_keys", [])
            working_keys.update(keys)
        for log in failing_logs:
            keys = log.get("change_spec", {}).get("spec_keys", [])
            failing_keys.update(keys)
        
        common_keys = working_keys & failing_keys
        only_working = working_keys - failing_keys
        only_failing = failing_keys - working_keys
        
        if only_working or only_failing:
            output.append(f"\n스펙 필드 차이:")
            if common_keys:
                output.append(f"  공통 필드: {len(common_keys)}개")
            if only_working:
                output.append(f"  ✓ 정상 환경에만: {sorted(only_working)}")
            if only_failing:
                output.append(f"  ✗ 문제 환경에만: {sorted(only_failing)}")
    elif any(failing_spec_success):
        output.append("⚠ 문제 환경에서 체인지 스펙 생성 실패")
    else:
        output.append("⚠ 체인지 스펙 생성 실패 없음")
    
    output.append("")
    
    # 4. 저장 방식 테스트 결과 (가장 중요)
    output.append("4. 저장 방식 테스트 결과 (핵심)")
    output.append("-" * 80)
    
    method_names = {
        "method_a": "방법 A: p4.save_change(spec) (현재 방식)",
        "method_b": "방법 B: p4.input + p4.run_change('-i')",
        "method_c": "방법 C: p4.run('change', '-i', input=spec)"
    }
    
    for method_key, method_desc in method_names.items():
        output.append(f"\n{method_desc}:")
        
        working_success = [log.get("save_methods", {}).get(method_key, {}).get("success", False) for log in working_logs]
        failing_success = [log.get("save_methods", {}).get(method_key, {}).get("success", False) for log in failing_logs]
        
        working_count = sum(working_success)
        failing_count = sum(failing_success)
        
        if all(working_success):
            output.append(f"  ✓ 정상 환경: {working_count}/{len(working_logs)} 성공")
        else:
            output.append(f"  ⚠ 정상 환경: {working_count}/{len(working_logs)} 성공")
        
        if all(failing_success):
            output.append(f"  ✓ 문제 환경: {failing_count}/{len(failing_logs)} 성공 → 이 방법이 문제 해결책일 수 있음!")
        elif any(failing_success):
            output.append(f"  ⚠ 문제 환경: {failing_count}/{len(failing_logs)} 성공")
        else:
            output.append(f"  ✗ 문제 환경: {failing_count}/{len(failing_logs)} 성공")
            
            # 에러 메시지 분석
            for log in failing_logs:
                method = log.get("save_methods", {}).get(method_key, {})
                if not method.get("success"):
                    error = method.get("error", "Unknown error")
                    error_type = method.get("error_type", "Unknown")
                    output.append(f"    에러 타입: {error_type}")
                    output.append(f"    에러 메시지: {error[:200]}")
    
    output.append("")
    
    # 5. pyjallib 라이브러리 테스트 결과
    output.append("5. pyjallib 라이브러리 테스트 결과")
    output.append("-" * 80)
    
    working_lib_success = [log.get("pyjallib_test", {}).get("success", False) for log in working_logs]
    failing_lib_success = [log.get("pyjallib_test", {}).get("success", False) for log in failing_logs]
    
    working_lib_count = sum(working_lib_success)
    failing_lib_count = sum(failing_lib_success)
    
    if all(working_lib_success):
        output.append(f"✓ 정상 환경: {working_lib_count}/{len(working_logs)} 성공")
    else:
        output.append(f"⚠ 정상 환경: {working_lib_count}/{len(working_logs)} 성공")
    
    if all(failing_lib_success):
        output.append(f"✓ 문제 환경: {failing_lib_count}/{len(failing_logs)} 성공")
    else:
        output.append(f"✗ 문제 환경: {failing_lib_count}/{len(failing_logs)} 성공")
        
        # 어떤 단계에서 실패했는지
        for log in failing_logs:
            if not log.get("pyjallib_test", {}).get("success"):
                steps = log.get("pyjallib_test", {}).get("steps", {})
                for step_name, step in steps.items():
                    if not step.get("success", False):
                        output.append(f"  실패 단계: {step_name}")
                        output.append(f"  에러: {step.get('error', 'Unknown')}")
    
    output.append("")
    
    # 6. 권장 사항
    output.append("6. 권장 사항 및 결론")
    output.append("-" * 80)
    
    recommendations = []
    
    # 방법 B가 성공하는지 확인
    method_b_working = all(log.get("save_methods", {}).get("method_b", {}).get("success", False) for log in working_logs)
    method_b_failing = any(log.get("save_methods", {}).get("method_b", {}).get("success", False) for log in failing_logs)
    
    if method_b_failing and not failing_logs[0].get("save_methods", {}).get("method_a", {}).get("success", False):
        recommendations.append("방법 B (p4.input + p4.run_change)가 문제 환경에서 작동합니다.")
        recommendations.append("→ adapter.py의 run_change_save를 방법 B로 수정하는 것을 권장합니다.")
    
    # 방법 C가 성공하는지 확인
    method_c_working = all(log.get("save_methods", {}).get("method_c", {}).get("success", False) for log in working_logs)
    method_c_failing = any(log.get("save_methods", {}).get("method_c", {}).get("success", False) for log in failing_logs)
    
    if method_c_failing and not failing_logs[0].get("save_methods", {}).get("method_a", {}).get("success", False):
        recommendations.append("방법 C (p4.run with input parameter)가 문제 환경에서 작동합니다.")
        recommendations.append("→ adapter.py의 run_change_save를 방법 C로 수정하는 것을 권장합니다.")
    
    if not recommendations:
        recommendations.append("모든 저장 방식에서 일관된 결과가 나오지 않았습니다.")
        recommendations.append("→ 추가 조사가 필요합니다. 환경 설정 차이를 더 자세히 확인해주세요.")
    
    for i, rec in enumerate(recommendations, 1):
        output.append(f"{i}. {rec}")
    
    output.append("")
    output.append("=" * 80)
    
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="P4 진단 로그 비교 분석")
    parser.add_argument("--working", nargs="+", required=True, help="정상 작동하는 환경의 로그 파일들")
    parser.add_argument("--failing", nargs="+", required=True, help="문제가 있는 환경의 로그 파일들")
    parser.add_argument("--output", help="출력 파일 경로 (지정하지 않으면 자동 생성)")
    
    args = parser.parse_args()
    
    # 로그 파일 로드
    print("로그 파일 로드 중...")
    working_logs = [load_log(path) for path in args.working]
    failing_logs = [load_log(path) for path in args.failing]
    print(f"  정상 환경: {len(working_logs)}개")
    print(f"  문제 환경: {len(failing_logs)}개")
    
    # 분석
    print("분석 중...")
    report = analyze_logs(working_logs, failing_logs)
    
    # 출력
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"진단_결과_분석_{timestamp}.txt"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n분석 완료!")
    print(f"출력 파일: {output_path}")
    
    # 콘솔에도 출력
    print("\n" + report)


if __name__ == "__main__":
    main()

