"""
템플릿 처리를 위한 유틸리티 모듈
UE5 익스포트 시 파이썬 스크립트 템플릿을 실제 코드로 변환하는 기능을 제공합니다.

Interchange Framework 기반 템플릿만 지원합니다.
외부 의존성: 파이썬 표준 라이브러리 + pyjallib.logger
"""

import os
import warnings
from pathlib import Path
from typing import Dict, Any, Optional, List
from pyjallib.logger import Logger
from .templates import (
    get_template_path,
    get_all_template_paths,
    get_available_templates,
    # Interchange 템플릿
    INTERCHANGE_ANIM_IMPORT_TEMPLATE,
    INTERCHANGE_SKELETON_IMPORT_TEMPLATE,
    INTERCHANGE_SKELETAL_MESH_IMPORT_TEMPLATE,
    INTERCHANGE_BATCH_ANIM_IMPORT_TEMPLATE,
    # Legacy 템플릿
    LEGACY_SKELETON_IMPORT_TEMPLATE,
    LEGACY_SKELETAL_MESH_IMPORT_TEMPLATE,
    LEGACY_ANIM_IMPORT_TEMPLATE,
    LEGACY_BATCH_ANIM_IMPORT_TEMPLATE,
)


class TemplateProcessor:
    """
    Interchange Framework 기반 템플릿 처리 클래스
    
    새 인터페이스를 사용하여 UE5 임포트 스크립트를 생성합니다.
    - inFbxPath: FBX 파일 절대 경로
    - inDestinationPath: /Game/... 형식의 Content 목적지 경로
    - inSkeletonPath: /Game/... 형식의 스켈레톤 Content 경로 (해당 시)
    - inAssetName: 에셋 이름 (선택적)
    """
    
    def __init__(self):
        """TemplateProcessor 초기화"""
        self._logger = Logger(inLogFileName="ue5_template")
        self._logger.debug("TemplateProcessor 초기화")
        self._default_output_dir = Path.cwd() / "temp_scripts"
    
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
            self._logger.error(f"템플릿 파일을 찾을 수 없습니다: {inTemplatePath}")
            raise FileNotFoundError(f"템플릿 파일을 찾을 수 없습니다: {inTemplatePath}")
        
        # 템플릿 파일 읽기 권한 확인
        if not os.access(templatePath, os.R_OK):
            self._logger.error(f"템플릿 파일 읽기 권한이 없습니다: {inTemplatePath}")
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
            self._logger.error(f"출력 파일 쓰기 권한이 없습니다: {inTemplateOutPath}")
            raise PermissionError(f"출력 파일 쓰기 권한이 없습니다: {inTemplateOutPath}")
        
        # 처리된 내용을 파일로 출력
        with open(outputPath, 'w', encoding='utf-8') as file:
            file.write(processedContent)
        
        self._logger.info(f"템플릿 처리 완료: {inTemplatePath} -> {inTemplateOutPath}")
        return processedContent

    # === 템플릿 경로 관리 메서드 ===
    def get_template_path(self, template_name: str) -> str:
        """
        템플릿 파일 경로를 간단하게 가져오기
        
        Args:
            template_name (str): 템플릿 이름 상수
            
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

    # === Interchange 템플릿 처리 메서드 (Deprecated) ===
    def process_interchange_skeleton_import_template(
        self,
        inTemplateData: Dict[str, Any],
        inOutputPath: Optional[str] = None
    ) -> str:
        """
        Interchange 스켈레톤 임포트 전용 템플릿 처리

        .. deprecated::
            이 메서드는 deprecated되었습니다. process_import_template('skeleton', 'interchange', ...)를 사용하세요.

        Args:
            inTemplateData (Dict[str, Any]): 템플릿 데이터
                필수 키:
                - inExtPackagePath: 외부 패키지 경로
                - inFbxPath: FBX 파일 절대 경로
                - inDestinationPath: /Game/... 형식의 Content 목적지 경로
                선택 키:
                - inAssetName: 에셋 이름 (빈 문자열이면 자동 생성)
            inOutputPath (Optional[str]): 출력 파일 경로. None인 경우 기본 경로 사용

        Returns:
            str: 처리된 템플릿 내용
        """
        warnings.warn(
            "process_interchange_skeleton_import_template is deprecated. "
            "Use process_import_template('skeleton', 'interchange', ...) instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.process_import_template('skeleton', 'interchange', inTemplateData, inOutputPath)
    
    def process_interchange_skeletal_mesh_import_template(
        self, 
        inTemplateData: Dict[str, Any], 
        inOutputPath: Optional[str] = None
    ) -> str:
        """
        Interchange 스켈레탈 메시 임포트 전용 템플릿 처리
        
        Args:
            inTemplateData (Dict[str, Any]): 템플릿 데이터
                필수 키:
                - inExtPackagePath: 외부 패키지 경로
                - inFbxPath: FBX 파일 절대 경로
                - inDestinationPath: /Game/... 형식의 Content 목적지 경로
                - inSkeletonPath: /Game/... 형식의 스켈레톤 Content 경로
                선택 키:
                - inAssetName: 에셋 이름 (빈 문자열이면 자동 생성)
            inOutputPath (Optional[str]): 출력 파일 경로. None인 경우 기본 경로 사용
            
        Returns:
            str: 처리된 템플릿 내용
        """
        required_keys = ['inExtPackagePath', 'inFbxPath', 'inDestinationPath', 'inSkeletonPath']
        if not self.validate_template_data(INTERCHANGE_SKELETAL_MESH_IMPORT_TEMPLATE, inTemplateData, required_keys):
            raise ValueError(f"Interchange 스켈레탈 메시 템플릿에 필요한 키가 누락되었습니다: {required_keys}")
        
        # 선택적 키에 기본값 설정
        if 'inAssetName' not in inTemplateData:
            inTemplateData['inAssetName'] = ''
        
        template_path = get_template_path(INTERCHANGE_SKELETAL_MESH_IMPORT_TEMPLATE)
        
        if inOutputPath is None:
            inOutputPath = self.get_default_output_path(INTERCHANGE_SKELETAL_MESH_IMPORT_TEMPLATE, "interchangeSkeletalMeshImportScript")
        
        return self.process_template(template_path, inOutputPath, inTemplateData)
    
    def process_interchange_animation_import_template(
        self, 
        inTemplateData: Dict[str, Any], 
        inOutputPath: Optional[str] = None
    ) -> str:
        """
        Interchange 애니메이션 임포트 전용 템플릿 처리
        
        Args:
            inTemplateData (Dict[str, Any]): 템플릿 데이터
                필수 키:
                - inExtPackagePath: 외부 패키지 경로
                - inFbxPath: FBX 파일 절대 경로
                - inDestinationPath: /Game/... 형식의 Content 목적지 경로
                - inSkeletonPath: /Game/... 형식의 스켈레톤 Content 경로
                선택 키:
                - inAssetName: 에셋 이름 (빈 문자열이면 자동 생성)
            inOutputPath (Optional[str]): 출력 파일 경로. None인 경우 기본 경로 사용
            
        Returns:
            str: 처리된 템플릿 내용
        """
        required_keys = ['inExtPackagePath', 'inFbxPath', 'inDestinationPath', 'inSkeletonPath']
        if not self.validate_template_data(INTERCHANGE_ANIM_IMPORT_TEMPLATE, inTemplateData, required_keys):
            raise ValueError(f"Interchange 애니메이션 템플릿에 필요한 키가 누락되었습니다: {required_keys}")
        
        # 선택적 키에 기본값 설정
        if 'inAssetName' not in inTemplateData:
            inTemplateData['inAssetName'] = ''
        
        template_path = get_template_path(INTERCHANGE_ANIM_IMPORT_TEMPLATE)
        
        if inOutputPath is None:
            inOutputPath = self.get_default_output_path(INTERCHANGE_ANIM_IMPORT_TEMPLATE, "interchangeAnimImportScript")
        
        return self.process_template(template_path, inOutputPath, inTemplateData)
    
    def process_interchange_batch_anim_import_template(
        self, 
        inTemplateData: Dict[str, Any], 
        inOutputPath: Optional[str] = None
    ) -> str:
        """
        Interchange 배치 애니메이션 임포트 전용 템플릿 처리
        
        Args:
            inTemplateData (Dict[str, Any]): 템플릿 데이터
                필수 키:
                - inExtPackagePath: 외부 패키지 경로
                - inFbxPaths: FBX 파일 절대 경로 리스트 (Python 리스트 문자열)
                - inDestinationPaths: /Game/... 형식 Content 목적지 경로 리스트
                - inSkeletonPaths: /Game/... 형식 스켈레톤 Content 경로 리스트
                선택 키:
                - inAssetNames: 에셋 이름 리스트 (빈 리스트면 자동 생성)
            inOutputPath (Optional[str]): 출력 파일 경로. None인 경우 기본 경로 사용
            
        Returns:
            str: 처리된 템플릿 내용
        """
        required_keys = ['inExtPackagePath', 'inFbxPaths', 'inDestinationPaths', 'inSkeletonPaths']
        if not self.validate_template_data(INTERCHANGE_BATCH_ANIM_IMPORT_TEMPLATE, inTemplateData, required_keys):
            raise ValueError(f"Interchange 배치 애니메이션 템플릿에 필요한 키가 누락되었습니다: {required_keys}")
        
        # 선택적 키에 기본값 설정
        if 'inAssetNames' not in inTemplateData:
            inTemplateData['inAssetNames'] = '[]'
        
        template_path = get_template_path(INTERCHANGE_BATCH_ANIM_IMPORT_TEMPLATE)
        
        if inOutputPath is None:
            inOutputPath = self.get_default_output_path(INTERCHANGE_BATCH_ANIM_IMPORT_TEMPLATE, "interchangeBatchAnimImportScript")
        
        return self.process_template(template_path, inOutputPath, inTemplateData)

    # === Legacy 템플릿 처리 메서드 ===
    def process_legacy_skeleton_import_template(
        self,
        inTemplateData: Dict[str, Any],
        inOutputPath: Optional[str] = None
    ) -> str:
        """
        Legacy 스켈레톤 임포트 전용 템플릿 처리 (Interchange 방식 변수 사용)

        Args:
            inTemplateData (Dict[str, Any]): 템플릿 데이터
                필수 키:
                - inExtPackagePath: 외부 패키지 경로
                - inFbxPath: FBX 파일 절대 경로
                - inDestinationPath: /Game/... 형식의 목적지 경로
                선택 키:
                - inAssetName: 에셋 이름 (빈 문자열이면 자동 생성)
            inOutputPath (Optional[str]): 출력 파일 경로. None인 경우 기본 경로 사용

        Returns:
            str: 처리된 템플릿 내용
        """
        required_keys = ['inExtPackagePath', 'inFbxPath', 'inDestinationPath']
        if not self.validate_template_data(LEGACY_SKELETON_IMPORT_TEMPLATE, inTemplateData, required_keys):
            raise ValueError(f"Legacy 스켈레톤 템플릿에 필요한 키가 누락되었습니다: {required_keys}")

        # 선택적 키에 기본값 설정
        if 'inAssetName' not in inTemplateData:
            inTemplateData['inAssetName'] = ''

        template_path = get_template_path(LEGACY_SKELETON_IMPORT_TEMPLATE)

        if inOutputPath is None:
            inOutputPath = self.get_default_output_path(LEGACY_SKELETON_IMPORT_TEMPLATE, "legacySkeletonImportScript")

        return self.process_template(template_path, inOutputPath, inTemplateData)

    def process_legacy_skeletal_mesh_import_template(
        self,
        inTemplateData: Dict[str, Any],
        inOutputPath: Optional[str] = None
    ) -> str:
        """
        Legacy 스켈레탈 메시 임포트 전용 템플릿 처리 (Interchange 방식 변수 사용)

        Args:
            inTemplateData (Dict[str, Any]): 템플릿 데이터
                필수 키:
                - inExtPackagePath: 외부 패키지 경로
                - inFbxPath: FBX 파일 절대 경로
                - inDestinationPath: /Game/... 형식의 목적지 경로
                - inSkeletonPath: /Game/... 형식의 스켈레톤 경로
                선택 키:
                - inAssetName: 에셋 이름 (빈 문자열이면 자동 생성)
            inOutputPath (Optional[str]): 출력 파일 경로. None인 경우 기본 경로 사용

        Returns:
            str: 처리된 템플릿 내용
        """
        required_keys = ['inExtPackagePath', 'inFbxPath', 'inDestinationPath', 'inSkeletonPath']
        if not self.validate_template_data(LEGACY_SKELETAL_MESH_IMPORT_TEMPLATE, inTemplateData, required_keys):
            raise ValueError(f"Legacy 스켈레탈 메시 템플릿에 필요한 키가 누락되었습니다: {required_keys}")

        # 선택적 키에 기본값 설정
        if 'inAssetName' not in inTemplateData:
            inTemplateData['inAssetName'] = ''

        template_path = get_template_path(LEGACY_SKELETAL_MESH_IMPORT_TEMPLATE)

        if inOutputPath is None:
            inOutputPath = self.get_default_output_path(LEGACY_SKELETAL_MESH_IMPORT_TEMPLATE, "legacySkeletalMeshImportScript")

        return self.process_template(template_path, inOutputPath, inTemplateData)

    def process_legacy_animation_import_template(
        self,
        inTemplateData: Dict[str, Any],
        inOutputPath: Optional[str] = None
    ) -> str:
        """
        Legacy 애니메이션 임포트 전용 템플릿 처리 (Interchange 방식 변수 사용)

        Args:
            inTemplateData (Dict[str, Any]): 템플릿 데이터
                필수 키:
                - inExtPackagePath: 외부 패키지 경로
                - inFbxPath: FBX 파일 절대 경로
                - inDestinationPath: /Game/... 형식의 목적지 경로
                - inSkeletonPath: /Game/... 형식의 스켈레톤 경로
                선택 키:
                - inAssetName: 에셋 이름 (빈 문자열이면 자동 생성)
            inOutputPath (Optional[str]): 출력 파일 경로. None인 경우 기본 경로 사용

        Returns:
            str: 처리된 템플릿 내용
        """
        required_keys = ['inExtPackagePath', 'inFbxPath', 'inDestinationPath', 'inSkeletonPath']
        if not self.validate_template_data(LEGACY_ANIM_IMPORT_TEMPLATE, inTemplateData, required_keys):
            raise ValueError(f"Legacy 애니메이션 템플릿에 필요한 키가 누락되었습니다: {required_keys}")

        # 선택적 키에 기본값 설정
        if 'inAssetName' not in inTemplateData:
            inTemplateData['inAssetName'] = ''

        template_path = get_template_path(LEGACY_ANIM_IMPORT_TEMPLATE)

        if inOutputPath is None:
            inOutputPath = self.get_default_output_path(LEGACY_ANIM_IMPORT_TEMPLATE, "legacyAnimImportScript")

        return self.process_template(template_path, inOutputPath, inTemplateData)

    def process_legacy_batch_anim_import_template(
        self,
        inTemplateData: Dict[str, Any],
        inOutputPath: Optional[str] = None
    ) -> str:
        """
        Legacy 배치 애니메이션 임포트 전용 템플릿 처리 (Interchange 방식 변수 사용)

        Args:
            inTemplateData (Dict[str, Any]): 템플릿 데이터
                필수 키:
                - inExtPackagePath: 외부 패키지 경로
                - inFbxPaths: FBX 파일 절대 경로 리스트 (Python 리스트 문자열)
                - inDestinationPath: /Game/... 형식의 목적지 경로
                - inSkeletonPath: /Game/... 형식의 스켈레톤 경로
            inOutputPath (Optional[str]): 출력 파일 경로. None인 경우 기본 경로 사용

        Returns:
            str: 처리된 템플릿 내용
        """
        required_keys = ['inExtPackagePath', 'inFbxPaths', 'inDestinationPath', 'inSkeletonPath']
        if not self.validate_template_data(LEGACY_BATCH_ANIM_IMPORT_TEMPLATE, inTemplateData, required_keys):
            raise ValueError(f"Legacy 배치 애니메이션 템플릿에 필요한 키가 누락되었습니다: {required_keys}")

        template_path = get_template_path(LEGACY_BATCH_ANIM_IMPORT_TEMPLATE)

        if inOutputPath is None:
            inOutputPath = self.get_default_output_path(LEGACY_BATCH_ANIM_IMPORT_TEMPLATE, "legacyBatchAnimImportScript")

        return self.process_template(template_path, inOutputPath, inTemplateData)

    # === 통합 템플릿 처리 메서드 ===
    def process_import_template(
        self,
        asset_type: str,
        template_type: str,
        template_data: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> str:
        """
        통합 템플릿 처리 메서드 - asset_type과 template_type으로 템플릿 선택

        Args:
            asset_type (str): 'skeleton', 'skeletal_mesh', 'animation', 'batch_animation'
            template_type (str): 'legacy', 'interchange'
            template_data (Dict[str, Any]): 템플릿 데이터
                공통 필수 키:
                - inExtPackagePath: 외부 패키지 경로
                - inFbxPath: FBX 파일 절대 경로 (batch_animation은 inFbxPaths)
                - inDestinationPath: /Game/... 형식의 목적지 경로 (Interchange 방식)
                선택 키:
                - inAssetName: 에셋 이름 (빈 문자열이면 자동 생성)
                - inSkeletonPath: /Game/... 형식의 스켈레톤 경로 (skeletal_mesh, animation 필요)
            output_path (Optional[str]): 출력 파일 경로. None인 경우 자동 생성

        Returns:
            str: 처리된 템플릿 내용

        Raises:
            ValueError: 잘못된 asset_type이나 template_type, 또는 필수 키 누락 시
        """
        # 템플릿 이름 매핑
        template_name = self._get_template_name(asset_type, template_type)

        # 필수 키 검증
        required_keys = self._get_required_keys(asset_type)
        if not self.validate_template_data(template_name, template_data, required_keys):
            raise ValueError(f"템플릿 데이터에 필요한 키가 누락되었습니다: {required_keys}")

        # 선택적 키에 기본값 설정
        if 'inAssetName' not in template_data:
            template_data['inAssetName'] = ''

        # 템플릿 경로 가져오기
        template_path = get_template_path(template_name)

        # 출력 경로 생성 (파일명 자동 생성)
        if output_path is None:
            output_filename = self._generate_output_filename(asset_type, template_type)
            output_path = self.get_default_output_path(template_name, output_filename)

        return self.process_template(template_path, output_path, template_data)

    def _get_template_name(self, asset_type: str, template_type: str) -> str:
        """
        asset_type과 template_type으로 템플릿 이름 상수 반환

        Args:
            asset_type (str): 'skeleton', 'skeletal_mesh', 'animation', 'batch_animation'
            template_type (str): 'legacy', 'interchange'

        Returns:
            str: 템플릿 이름 상수

        Raises:
            ValueError: 잘못된 asset_type이나 template_type
        """
        template_map = {
            ('skeleton', 'legacy'): LEGACY_SKELETON_IMPORT_TEMPLATE,
            ('skeleton', 'interchange'): INTERCHANGE_SKELETON_IMPORT_TEMPLATE,
            ('skeletal_mesh', 'legacy'): LEGACY_SKELETAL_MESH_IMPORT_TEMPLATE,
            ('skeletal_mesh', 'interchange'): INTERCHANGE_SKELETAL_MESH_IMPORT_TEMPLATE,
            ('animation', 'legacy'): LEGACY_ANIM_IMPORT_TEMPLATE,
            ('animation', 'interchange'): INTERCHANGE_ANIM_IMPORT_TEMPLATE,
            ('batch_animation', 'legacy'): LEGACY_BATCH_ANIM_IMPORT_TEMPLATE,
            ('batch_animation', 'interchange'): INTERCHANGE_BATCH_ANIM_IMPORT_TEMPLATE,
        }

        key = (asset_type, template_type)
        if key not in template_map:
            raise ValueError(f"잘못된 asset_type 또는 template_type: {asset_type}, {template_type}")

        return template_map[key]

    def _get_required_keys(self, asset_type: str) -> list:
        """
        asset_type에 따른 필수 키 목록 반환

        Args:
            asset_type (str): 'skeleton', 'skeletal_mesh', 'animation', 'batch_animation'

        Returns:
            list: 필수 키 목록
        """
        # 통일된 Interchange 방식의 키
        if asset_type == 'skeleton':
            return ['inExtPackagePath', 'inFbxPath', 'inDestinationPath']
        elif asset_type == 'skeletal_mesh':
            return ['inExtPackagePath', 'inFbxPath', 'inDestinationPath', 'inSkeletonPath']
        elif asset_type == 'animation':
            return ['inExtPackagePath', 'inFbxPath', 'inDestinationPath', 'inSkeletonPath']
        elif asset_type == 'batch_animation':
            return ['inExtPackagePath', 'inFbxPaths', 'inDestinationPath', 'inSkeletonPath']
        else:
            raise ValueError(f"잘못된 asset_type: {asset_type}")

    def _generate_output_filename(self, asset_type: str, template_type: str) -> str:
        """
        출력 파일명 자동 생성: {template_type}_{asset_type}Import 형식

        Args:
            asset_type (str): 'skeleton', 'skeletal_mesh', 'animation', 'batch_animation'
            template_type (str): 'legacy', 'interchange'

        Returns:
            str: 생성된 파일명 (확장자 제외)

        Examples:
            >>> _generate_output_filename('skeleton', 'legacy')
            'legacy_skeletonImport'
            >>> _generate_output_filename('batch_animation', 'interchange')
            'interchange_batch_animationImport'
        """
        return f"{template_type}_{asset_type}Import"

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
            self._logger.error(f"템플릿 데이터가 딕셔너리가 아닙니다: {type(template_data)}")
            return False
        
        if required_keys:
            missing_keys = [key for key in required_keys if key not in template_data]
            if missing_keys:
                self._logger.error(f"템플릿 데이터에 필수 키가 누락되었습니다: {missing_keys}")
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
        self._logger.info(f"기본 출력 디렉토리가 변경되었습니다: {directory_path}")
    
    # === 편의 메서드 (리스트 변환) ===
    @staticmethod
    def format_list_for_template(items: List[str]) -> str:
        """
        Python 리스트를 템플릿용 문자열로 변환
        
        Args:
            items: 문자열 리스트
            
        Returns:
            str: Python 리스트 형태의 문자열 (예: ['item1', 'item2'])
        """
        formatted_items = [f"r'{item}'" for item in items]
        return f"[{', '.join(formatted_items)}]"
