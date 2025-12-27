"""
Madstamp Automation - 파일 관리 및 Google Drive 연동 모듈

고객 요청 파일의 분류 체계 관리 및 Google Drive 동기화
"""

import asyncio
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FileCategory(str, Enum):
    """파일 카테고리"""
    ORIGINAL = "01_원본"           # 고객이 보낸 원본 파일
    REFERENCE = "02_참고자료"       # 참고 이미지/자료
    WORKING = "03_작업중"          # 일러스트 작업 파일
    REVIEW = "04_검토대기"         # 고객 검토 대기
    APPROVED = "05_승인완료"       # 고객 승인 완료
    FINAL = "06_최종파일"          # 최종 제작 파일 (BMP)
    ARCHIVE = "07_보관"            # 완료 후 보관


class FileType(str, Enum):
    """파일 타입"""
    IMAGE_ORIGINAL = "img_original"     # 원본 이미지
    IMAGE_PROCESSED = "img_processed"   # 처리된 이미지
    ILLUSTRATOR = "ai"                  # 일러스트레이터 파일
    PHOTOSHOP = "psd"                   # 포토샵 파일
    VECTOR_SVG = "svg"                  # SVG 벡터
    VECTOR_EPS = "eps"                  # EPS 벡터
    FINAL_BMP = "bmp"                   # 최종 BMP (흑백)
    FONT = "font"                       # 폰트 파일


@dataclass
class FileMetadata:
    """파일 메타데이터"""
    filename: str
    category: FileCategory
    file_type: FileType
    order_id: str
    customer_name: str
    version: int = 1
    is_final: bool = False
    created_at: datetime = None
    modified_at: datetime = None
    local_path: Optional[str] = None
    gdrive_path: Optional[str] = None
    gdrive_link: Optional[str] = None
    notes: str = ""

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.modified_at is None:
            self.modified_at = datetime.now()


@dataclass
class OrderFolder:
    """주문 폴더 구조"""
    order_id: str
    customer_name: str
    order_date: datetime
    base_path: str
    gdrive_base: str = "manus_google_drive:Madstamp/주문"
    files: list[FileMetadata] = field(default_factory=list)

    @property
    def folder_name(self) -> str:
        """폴더명 생성: YYYYMMDD_주문번호_고객명"""
        date_str = self.order_date.strftime("%Y%m%d")
        # 파일명에 사용 불가능한 문자 제거
        safe_customer = re.sub(r'[<>:"/\\|?*]', '', self.customer_name)
        return f"{date_str}_{self.order_id}_{safe_customer}"

    @property
    def local_folder(self) -> str:
        """로컬 폴더 경로"""
        return os.path.join(self.base_path, self.folder_name)

    @property
    def gdrive_folder(self) -> str:
        """Google Drive 폴더 경로"""
        return f"{self.gdrive_base}/{self.folder_name}"


class FileNamingConvention:
    """
    파일 네이밍 규칙
    
    형식: {주문번호}_{고객명}_{카테고리}_{버전}_{타입}.{확장자}
    예시: ORD001_홍길동_03_작업중_v2_ai.ai
    """

    @staticmethod
    def generate_filename(
        order_id: str,
        customer_name: str,
        category: FileCategory,
        file_type: FileType,
        version: int = 1,
        extension: str = None,
    ) -> str:
        """파일명 생성"""
        safe_customer = re.sub(r'[<>:"/\\|?*]', '', customer_name)
        safe_customer = safe_customer[:10]  # 최대 10자
        
        # 확장자 결정
        if extension is None:
            ext_map = {
                FileType.IMAGE_ORIGINAL: "png",
                FileType.IMAGE_PROCESSED: "png",
                FileType.ILLUSTRATOR: "ai",
                FileType.PHOTOSHOP: "psd",
                FileType.VECTOR_SVG: "svg",
                FileType.VECTOR_EPS: "eps",
                FileType.FINAL_BMP: "bmp",
                FileType.FONT: "ttf",
            }
            extension = ext_map.get(file_type, "bin")
        
        # 카테고리 번호 추출
        category_num = category.value.split("_")[0]
        
        return f"{order_id}_{safe_customer}_{category_num}_v{version}_{file_type.value}.{extension}"

    @staticmethod
    def parse_filename(filename: str) -> Optional[dict]:
        """파일명 파싱"""
        pattern = r'^([A-Z]+\d+)_(.+?)_(\d+)_v(\d+)_(.+?)\.(.+)$'
        match = re.match(pattern, filename)
        
        if match:
            return {
                "order_id": match.group(1),
                "customer_name": match.group(2),
                "category_num": match.group(3),
                "version": int(match.group(4)),
                "file_type": match.group(5),
                "extension": match.group(6),
            }
        return None


class GoogleDriveManager:
    """
    Google Drive 관리자
    
    rclone을 통해 Google Drive와 동기화합니다.
    """

    def __init__(
        self,
        config_path: str = "/home/ubuntu/.gdrive-rclone.ini",
        remote_name: str = "manus_google_drive",
    ):
        self.config_path = config_path
        self.remote_name = remote_name

    async def _run_rclone(self, *args) -> tuple[bool, str]:
        """rclone 명령 실행"""
        cmd = ["rclone"] + list(args) + ["--config", self.config_path]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return True, stdout.decode()
            else:
                return False, stderr.decode()
                
        except Exception as e:
            return False, str(e)

    async def create_folder(self, remote_path: str) -> bool:
        """폴더 생성"""
        success, _ = await self._run_rclone("mkdir", f"{self.remote_name}:{remote_path}")
        return success

    async def upload_file(
        self,
        local_path: str,
        remote_path: str,
    ) -> bool:
        """파일 업로드"""
        success, _ = await self._run_rclone(
            "copy",
            local_path,
            f"{self.remote_name}:{remote_path}",
        )
        return success

    async def download_file(
        self,
        remote_path: str,
        local_path: str,
    ) -> bool:
        """파일 다운로드"""
        success, _ = await self._run_rclone(
            "copy",
            f"{self.remote_name}:{remote_path}",
            local_path,
        )
        return success

    async def sync_folder(
        self,
        local_path: str,
        remote_path: str,
        direction: str = "upload",  # upload or download
    ) -> bool:
        """폴더 동기화"""
        if direction == "upload":
            source = local_path
            dest = f"{self.remote_name}:{remote_path}"
        else:
            source = f"{self.remote_name}:{remote_path}"
            dest = local_path
        
        success, _ = await self._run_rclone("sync", source, dest)
        return success

    async def get_share_link(self, remote_path: str) -> Optional[str]:
        """공유 링크 생성"""
        success, output = await self._run_rclone(
            "link",
            f"{self.remote_name}:{remote_path}",
        )
        
        if success:
            return output.strip()
        return None

    async def list_files(self, remote_path: str) -> list[dict]:
        """파일 목록 조회"""
        success, output = await self._run_rclone(
            "lsjson",
            f"{self.remote_name}:{remote_path}",
        )
        
        if success:
            import json
            try:
                return json.loads(output)
            except:
                return []
        return []


class FileManager:
    """
    파일 관리자
    
    주문별 파일 분류 및 Google Drive 동기화를 관리합니다.
    """

    def __init__(
        self,
        base_path: str = "/home/ubuntu/madstamp_orders",
        gdrive_base: str = "Madstamp/주문",
    ):
        self.base_path = base_path
        self.gdrive_base = gdrive_base
        self.gdrive = GoogleDriveManager()
        self.naming = FileNamingConvention()
        
        # 기본 디렉토리 생성
        Path(base_path).mkdir(parents=True, exist_ok=True)

    async def create_order_folder(
        self,
        order_id: str,
        customer_name: str,
        order_date: datetime = None,
    ) -> OrderFolder:
        """주문 폴더 생성"""
        if order_date is None:
            order_date = datetime.now()
        
        order = OrderFolder(
            order_id=order_id,
            customer_name=customer_name,
            order_date=order_date,
            base_path=self.base_path,
            gdrive_base=f"manus_google_drive:{self.gdrive_base}",
        )
        
        # 로컬 폴더 구조 생성
        for category in FileCategory:
            category_path = os.path.join(order.local_folder, category.value)
            Path(category_path).mkdir(parents=True, exist_ok=True)
        
        # Google Drive 폴더 생성
        for category in FileCategory:
            gdrive_path = f"{self.gdrive_base}/{order.folder_name}/{category.value}"
            await self.gdrive.create_folder(gdrive_path)
        
        logger.info(f"Created order folder: {order.folder_name}")
        return order

    async def save_file(
        self,
        order: OrderFolder,
        file_path: str,
        category: FileCategory,
        file_type: FileType,
        version: int = 1,
        sync_to_gdrive: bool = True,
    ) -> FileMetadata:
        """파일 저장 및 분류"""
        # 파일명 생성
        extension = Path(file_path).suffix.lstrip(".")
        new_filename = self.naming.generate_filename(
            order_id=order.order_id,
            customer_name=order.customer_name,
            category=category,
            file_type=file_type,
            version=version,
            extension=extension,
        )
        
        # 로컬 저장 경로
        local_category_path = os.path.join(order.local_folder, category.value)
        local_file_path = os.path.join(local_category_path, new_filename)
        
        # 파일 복사
        import shutil
        shutil.copy2(file_path, local_file_path)
        
        # 메타데이터 생성
        metadata = FileMetadata(
            filename=new_filename,
            category=category,
            file_type=file_type,
            order_id=order.order_id,
            customer_name=order.customer_name,
            version=version,
            local_path=local_file_path,
        )
        
        # Google Drive 동기화
        if sync_to_gdrive:
            gdrive_path = f"{self.gdrive_base}/{order.folder_name}/{category.value}"
            success = await self.gdrive.upload_file(local_file_path, gdrive_path)
            
            if success:
                metadata.gdrive_path = f"{gdrive_path}/{new_filename}"
                metadata.gdrive_link = await self.gdrive.get_share_link(metadata.gdrive_path)
        
        order.files.append(metadata)
        logger.info(f"Saved file: {new_filename}")
        
        return metadata

    async def get_latest_version(
        self,
        order: OrderFolder,
        category: FileCategory,
        file_type: FileType,
    ) -> int:
        """최신 버전 번호 조회"""
        max_version = 0
        
        category_path = os.path.join(order.local_folder, category.value)
        if not os.path.exists(category_path):
            return 0
        
        for filename in os.listdir(category_path):
            parsed = self.naming.parse_filename(filename)
            if parsed and parsed["file_type"] == file_type.value:
                max_version = max(max_version, parsed["version"])
        
        return max_version

    async def promote_file(
        self,
        order: OrderFolder,
        file_metadata: FileMetadata,
        new_category: FileCategory,
    ) -> FileMetadata:
        """파일을 다음 단계로 이동"""
        # 새 버전으로 저장
        new_version = await self.get_latest_version(
            order, new_category, file_metadata.file_type
        ) + 1
        
        return await self.save_file(
            order=order,
            file_path=file_metadata.local_path,
            category=new_category,
            file_type=file_metadata.file_type,
            version=new_version,
        )

    async def sync_order_to_gdrive(self, order: OrderFolder) -> bool:
        """주문 폴더 전체를 Google Drive에 동기화"""
        gdrive_path = f"{self.gdrive_base}/{order.folder_name}"
        return await self.gdrive.sync_folder(
            local_path=order.local_folder,
            remote_path=gdrive_path,
            direction="upload",
        )

    async def sync_order_from_gdrive(self, order: OrderFolder) -> bool:
        """Google Drive에서 주문 폴더 동기화"""
        gdrive_path = f"{self.gdrive_base}/{order.folder_name}"
        return await self.gdrive.sync_folder(
            local_path=order.local_folder,
            remote_path=gdrive_path,
            direction="download",
        )


# 주문 ID 생성기
class OrderIDGenerator:
    """주문 ID 생성기"""
    
    @staticmethod
    def generate(prefix: str = "ORD") -> str:
        """새 주문 ID 생성"""
        timestamp = datetime.now().strftime("%y%m%d%H%M")
        import random
        suffix = f"{random.randint(0, 99):02d}"
        return f"{prefix}{timestamp}{suffix}"


async def create_new_order(
    customer_name: str,
    base_path: str = "/home/ubuntu/madstamp_orders",
) -> OrderFolder:
    """
    새 주문 생성 헬퍼 함수
    
    Args:
        customer_name: 고객명
        base_path: 기본 저장 경로
        
    Returns:
        OrderFolder: 생성된 주문 폴더
    """
    manager = FileManager(base_path=base_path)
    order_id = OrderIDGenerator.generate()
    
    return await manager.create_order_folder(
        order_id=order_id,
        customer_name=customer_name,
    )
