"""
템플릿 처리를 위한 유틸리티 모듈
UE5 익스포트 시 파이썬 스크립트 템플릿을 실제 코드로 변환하는 기능을 제공합니다.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from .logger import ue5_logger


class TemplateProcessor:
    """템플릿 처리를 위한 클래스"""
    
    def __init__(self):
        """TemplateProcessor 초기화"""
        pass
    
    def process_template(self, inTemplatePath: str, inTemplateOutPath: str, inTemplateData: Dict[str, Any]) -> str:
        """
        템플릿을 처리하여 실제 코드로 변환
        
        Args:
            inTemplatePath (str): 템플릿 파일 경로
            inTemplateOutPath (str): 출력 파일 경로
            inTemplateData (Dict[str, Any]): 템플릿에서 치환할 데이터
            
        Returns:
            str: 처리된 템플릿 내용
            
        Raises:
            FileNotFoundError: 템플릿 파일이 존재하지 않는 경우
            PermissionError: 파일 읽기/쓰기 권한이 없는 경우
            OSError: 디렉토리 생성 실패 등 파일 시스템 오류
            UnicodeDecodeError: 파일 인코딩 오류
        """
        # 템플릿 파일 존재 확인
        templatePath = Path(inTemplatePath)
        if not templatePath.exists():
            ue5_logger.error(f"템플릿 파일을 찾을 수 없습니다: {inTemplatePath}")
            raise FileNotFoundError(f"템플릿 파일을 찾을 수 없습니다: {inTemplatePath}")
        
        # 템플릿 파일 읽기 권한 확인
        if not os.access(templatePath, os.R_OK):
            ue5_logger.error(f"템플릿 파일 읽기 권한이 없습니다: {inTemplatePath}")
            raise PermissionError(f"템플릿 파일 읽기 권한이 없습니다: {inTemplatePath}")
        
        # 템플릿 파일 읽기
        with open(templatePath, 'r', encoding='utf-8') as file:
            templateContent = file.read()
        
        # 템플릿 데이터로 플레이스홀더 치환
        processedContent = templateContent
        for key, value in inTemplateData.items():
            placeholder = f'{{{key}}}'
            if placeholder in processedContent:
                processedContent = processedContent.replace(placeholder, str(value))
        
        # 출력 디렉토리 생성 (존재하지 않는 경우)
        outputPath = Path(inTemplateOutPath)
        outputPath.parent.mkdir(parents=True, exist_ok=True)
        
        # 출력 파일 쓰기 권한 확인 (기존 파일이 있는 경우)
        if outputPath.exists() and not os.access(outputPath, os.W_OK):
            ue5_logger.error(f"출력 파일 쓰기 권한이 없습니다: {inTemplateOutPath}")
            raise PermissionError(f"출력 파일 쓰기 권한이 없습니다: {inTemplateOutPath}")
        
        # 처리된 내용을 파일로 출력
        with open(outputPath, 'w', encoding='utf-8') as file:
            file.write(processedContent)
        
        return processedContent