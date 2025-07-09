"""
템플릿 처리를 위한 유틸리티 모듈
UE5 익스포트 시 파이썬 스크립트 템플릿을 실제 코드로 변환하는 기능을 제공합니다.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from .logger import ue5_logger
from .templates import (
    get_template_path, 
    get_all_template_paths, 
    get_available_templates,
    ANIM_IMPORT_TEMPLATE,
    SKELETON_IMPORT_TEMPLATE,
    SKELETAL_MESH_IMPORT_TEMPLATE,
    BATCH_ANIM_IMPORT_TEMPLATE
)


class TemplateProcessor:
    """템플릿 처리를 위한 확장된 클래스"""
    
    def __init__(self):
        """TemplateProcessor 초기화"""
        ue5_logger.debug("TemplateProcessor 초기화")
        self._default_output_dir = Path.cwd() / "temp_scripts"
    
    def process_template(self, inTemplatePath: str, inTemplateOutPath: str, inTemplateData: Dict[str, Any]) -> str:
        """
        템플릿을 처리하여 실제 코드로 변환 (기존 메서드 유지)
        
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
        
        ue5_logger.info(f"템플릿 처리 완료: {inTemplatePath} -> {inTemplateOutPath}")
        return processedContent

    # === 새로운 템플릿 경로 관리 메서드 ===
    def get_template_path(self, template_name: str) -> str:
        """
        템플릿 파일 경로를 간단하게 가져오기
        
        Args:
            template_name (str): 'animImport', 'skeletonImport', 'skeletalMeshImport' 중 하나
            
        Returns:
            str: 템플릿 파일의 절대 경로
        """
        return get_template_path(template_name)
        
    def get_all_template_paths(self) -> Dict[str, str]:
        """모든 템플릿 경로를 딕셔너리로 반환"""
        return get_all_template_paths()
    
    def get_available_templates(self) -> list:
        """사용 가능한 템플릿 목록 반환"""
        return get_available_templates()

    # === 타입별 특화 처리 메서드 ===
    def process_animation_import_template(self, 
                                        inTemplateData: Dict[str, Any], 
                                        inOutputPath: Optional[str] = None) -> str:
        """
        애니메이션 임포트 전용 템플릿 처리
        
        Args:
            inTemplateData (Dict[str, Any]): 템플릿 데이터
                필수 키:
                - inExtPackagePath: 외부 패키지 경로
                - inAnimFbxPath: 애니메이션 FBX 경로
                - inSkeletonFbxPath: 스켈레톤 FBX 경로  
                - inContentRootPrefix: Content 루트 경로
                - inFbxRootPrefix: FBX 루트 경로
            inOutputPath (Optional[str]): 출력 파일 경로. None인 경우 기본 경로 사용
            
        Returns:
            str: 처리된 템플릿 내용
        """
        # 필수 키 검증
        required_keys = ['inExtPackagePath', 'inAnimFbxPath', 'inSkeletonFbxPath', 
                        'inContentRootPrefix', 'inFbxRootPrefix']
        if not self.validate_template_data(ANIM_IMPORT_TEMPLATE, inTemplateData, required_keys):
            raise ValueError(f"애니메이션 템플릿에 필요한 키가 누락되었습니다: {required_keys}")
        
        template_path = get_template_path(ANIM_IMPORT_TEMPLATE)
        
        if inOutputPath is None:
            inOutputPath = self.get_default_output_path(ANIM_IMPORT_TEMPLATE, "animImportScript")
        
        return self.process_template(template_path, inOutputPath, inTemplateData)
        
    def process_skeleton_import_template(self, 
                                       inTemplateData: Dict[str, Any], 
                                       inOutputPath: Optional[str] = None) -> str:
        """
        스켈레톤 임포트 전용 템플릿 처리
        
        Args:
            inTemplateData (Dict[str, Any]): 템플릿 데이터
                필수 키:
                - inExtPackagePath: 외부 패키지 경로
                - inSkeletonFbxPath: 스켈레톤 FBX 경로
                - inContentRootPrefix: Content 루트 경로
                - inFbxRootPrefix: FBX 루트 경로
            inOutputPath (Optional[str]): 출력 파일 경로. None인 경우 기본 경로 사용
            
        Returns:
            str: 처리된 템플릿 내용
        """
        # 필수 키 검증
        required_keys = ['inExtPackagePath', 'inSkeletonFbxPath', 
                        'inContentRootPrefix', 'inFbxRootPrefix']
        if not self.validate_template_data(SKELETON_IMPORT_TEMPLATE, inTemplateData, required_keys):
            raise ValueError(f"스켈레톤 템플릿에 필요한 키가 누락되었습니다: {required_keys}")
        
        template_path = get_template_path(SKELETON_IMPORT_TEMPLATE)
        
        if inOutputPath is None:
            inOutputPath = self.get_default_output_path(SKELETON_IMPORT_TEMPLATE, "skeletonImportScript")
        
        return self.process_template(template_path, inOutputPath, inTemplateData)
        
    def process_skeletal_mesh_import_template(self, 
                                            inTemplateData: Dict[str, Any], 
                                            inOutputPath: Optional[str] = None) -> str:
        """
        스켈레탈 메시 임포트 전용 템플릿 처리
        
        Args:
            inTemplateData (Dict[str, Any]): 템플릿 데이터
                필수 키:
                - inExtPackagePath: 외부 패키지 경로
                - inSkeletalMeshFbxPath: 스켈레탈 메시 FBX 경로
                - inSkeletonFbxPath: 스켈레톤 FBX 경로
                - inContentRootPrefix: Content 루트 경로
                - inFbxRootPrefix: FBX 루트 경로
            inOutputPath (Optional[str]): 출력 파일 경로. None인 경우 기본 경로 사용
            
        Returns:
            str: 처리된 템플릿 내용
        """
        # 필수 키 검증
        required_keys = ['inExtPackagePath', 'inSkeletalMeshFbxPath', 'inSkeletonFbxPath', 
                        'inContentRootPrefix', 'inFbxRootPrefix']
        if not self.validate_template_data(SKELETAL_MESH_IMPORT_TEMPLATE, inTemplateData, required_keys):
            raise ValueError(f"스켈레탈 메시 템플릿에 필요한 키가 누락되었습니다: {required_keys}")
        
        template_path = get_template_path(SKELETAL_MESH_IMPORT_TEMPLATE)
        
        if inOutputPath is None:
            inOutputPath = self.get_default_output_path(SKELETAL_MESH_IMPORT_TEMPLATE, "skeletalMeshImportScript")
        
        return self.process_template(template_path, inOutputPath, inTemplateData)
    
    def process_batch_anim_import_template(self, 
                                        inTemplateData: Dict[str, Any], 
                                        inOutputPath: Optional[str] = None) -> str:
        """
        배치 애니메이션 임포트 전용 템플릿 처리
        
        Args:
            inTemplateData (Dict[str, Any]): 템플릿 데이터
                필수 키:
                - inExtPackagePath: 외부 패키지 경로
                - inAnimFbxPaths: 애니메이션 FBX 경로들 (리스트)
                - inSkeletonFbxPaths: 스켈레톤 FBX 경로들 (리스트)
                - inContentRootPrefix: Content 루트 경로
                - inFbxRootPrefix: FBX 루트 경로
            inOutputPath (Optional[str]): 출력 파일 경로. None인 경우 기본 경로 사용
            
        Returns:
            str: 처리된 템플릿 내용
        """
        # 필수 키 검증
        required_keys = ['inExtPackagePath', 'inAnimFbxPaths', 'inSkeletonFbxPaths', 
                        'inContentRootPrefix', 'inFbxRootPrefix']
        if not self.validate_template_data(BATCH_ANIM_IMPORT_TEMPLATE, inTemplateData, required_keys):
            raise ValueError(f"배치 애니메이션 템플릿에 필요한 키가 누락되었습니다: {required_keys}")
        
        template_path = get_template_path(BATCH_ANIM_IMPORT_TEMPLATE)
        
        if inOutputPath is None:
            inOutputPath = self.get_default_output_path(BATCH_ANIM_IMPORT_TEMPLATE, "batchAnimImportScript")
        
        return self.process_template(template_path, inOutputPath, inTemplateData)
    
    # === 유틸리티 메서드 ===
    def validate_template_data(self, template_type: str, template_data: Dict[str, Any], required_keys: list = None) -> bool:
        """
        템플릿 데이터 유효성 검사
        
        Args:
            template_type (str): 템플릿 타입
            template_data (Dict[str, Any]): 검사할 템플릿 데이터
            required_keys (list, optional): 필수 키 목록. None인 경우 기본 검사만 수행
            
        Returns:
            bool: 유효한 데이터면 True, 그렇지 않으면 False
        """
        if not isinstance(template_data, dict):
            ue5_logger.error(f"템플릿 데이터가 딕셔너리가 아닙니다: {type(template_data)}")
            return False
        
        if required_keys:
            missing_keys = [key for key in required_keys if key not in template_data]
            if missing_keys:
                ue5_logger.error(f"템플릿 데이터에 필수 키가 누락되었습니다: {missing_keys}")
                return False
        
        return True
        
    def get_default_output_path(self, template_type: str, base_name: str = None) -> str:
        """
        기본 출력 경로 생성
        
        Args:
            template_type (str): 템플릿 타입
            base_name (str, optional): 기본 파일명. None인 경우 템플릿 타입으로 생성
            
        Returns:
            str: 기본 출력 파일 경로
        """
        if base_name is None:
            base_name = f"{template_type}Script"
        
        # 기본 출력 디렉토리 생성
        self._default_output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = self._default_output_dir / f"{base_name}.py"
        return str(output_path)
    
    def set_default_output_directory(self, directory_path: str):
        """
        기본 출력 디렉토리 설정
        
        Args:
            directory_path (str): 새로운 기본 출력 디렉토리 경로
        """
        self._default_output_dir = Path(directory_path)
        ue5_logger.info(f"기본 출력 디렉토리가 변경되었습니다: {directory_path}")