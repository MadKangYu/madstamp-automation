"""
Madstamp Automation - 원본/수정본 버전 관리 시스템

도장 제작 과정의 모든 파일 버전을 체계적으로 관리합니다.

주요 기능:
- 원본 파일 보존
- 수정 이력 추적
- 레이어 검토 기록
- 최종 승인 파일 관리
- Google Drive 동기화
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class FileStage(str, Enum):
    """파일 단계"""
    ORIGINAL = "01_original"            # 고객 원본
    ANALYZED = "02_analyzed"            # 분석 완료
    PROCESSED = "03_processed"          # 이미지 처리 완료
    ILLUSTRATOR = "04_illustrator"      # 일러스트 작업 완료
    REVIEW = "05_review"                # 검토 대기
    APPROVED = "06_approved"            # 승인 완료
    FINAL_BMP = "07_final_bmp"          # 최종 BMP
    PRINTED = "08_printed"              # 출력 완료


class FileType(str, Enum):
    """파일 유형"""
    CUSTOMER_IMAGE = "customer_image"   # 고객 제공 이미지
    REFERENCE = "reference"             # 참고 자료
    WORKING = "working"                 # 작업 중 파일
    AI_FILE = "ai_file"                 # 일러스트레이터 파일
    EPS_FILE = "eps_file"               # EPS 파일
    PNG_PREVIEW = "png_preview"         # PNG 미리보기
    BMP_FINAL = "bmp_final"             # 최종 BMP
    METADATA = "metadata"               # 메타데이터


@dataclass
class FileVersion:
    """파일 버전 정보"""
    version_id: str
    file_path: str
    file_type: FileType
    stage: FileStage
    created_at: datetime
    created_by: str = "system"
    file_hash: str = ""
    file_size: int = 0
    description: str = ""
    parent_version_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LayerInfo:
    """레이어 정보"""
    name: str
    visible: bool
    locked: bool
    order: int
    type: str = "normal"  # normal, text, image, shape
    notes: str = ""


@dataclass
class LayerReview:
    """레이어 검토 기록"""
    review_id: str
    file_version_id: str
    reviewed_at: datetime
    reviewer: str
    layers: List[LayerInfo]
    issues_found: List[str]
    approved: bool
    notes: str = ""


@dataclass
class OrderFileSet:
    """주문별 파일 세트"""
    order_id: str
    customer_name: str
    created_at: datetime
    updated_at: datetime
    versions: List[FileVersion] = field(default_factory=list)
    layer_reviews: List[LayerReview] = field(default_factory=list)
    current_stage: FileStage = FileStage.ORIGINAL
    final_approved: bool = False
    google_drive_folder_id: Optional[str] = None


class VersionManager:
    """
    버전 관리자
    
    도장 제작 파일의 모든 버전을 관리합니다.
    """

    def __init__(
        self,
        base_dir: str = "/home/ubuntu/madstamp_output",
        gdrive_remote: str = "manus_google_drive",
        gdrive_base_path: str = "Madstamp/Orders",
    ):
        self.base_dir = base_dir
        self.gdrive_remote = gdrive_remote
        self.gdrive_base_path = gdrive_base_path
        self.orders: Dict[str, OrderFileSet] = {}
        
        # 디렉토리 구조 생성
        self._init_directories()

    def _init_directories(self):
        """디렉토리 구조 초기화"""
        dirs = [
            "orders",
            "archive",
            "temp",
            "scripts",
        ]
        for d in dirs:
            Path(os.path.join(self.base_dir, d)).mkdir(parents=True, exist_ok=True)

    def _generate_version_id(self) -> str:
        """버전 ID 생성"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:6]
        return f"v{timestamp}_{random_suffix}"

    def _calculate_file_hash(self, file_path: str) -> str:
        """파일 해시 계산"""
        if not os.path.exists(file_path):
            return ""
        
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()[:16]

    def create_order(
        self,
        order_id: str,
        customer_name: str,
    ) -> OrderFileSet:
        """새 주문 생성"""
        now = datetime.now()
        
        order = OrderFileSet(
            order_id=order_id,
            customer_name=customer_name,
            created_at=now,
            updated_at=now,
        )
        
        # 주문 디렉토리 생성
        order_dir = os.path.join(self.base_dir, "orders", order_id)
        for stage in FileStage:
            Path(os.path.join(order_dir, stage.value)).mkdir(parents=True, exist_ok=True)
        
        self.orders[order_id] = order
        self._save_order_metadata(order)
        
        logger.info(f"Created order: {order_id} for {customer_name}")
        return order

    def get_order(self, order_id: str) -> Optional[OrderFileSet]:
        """주문 조회"""
        if order_id in self.orders:
            return self.orders[order_id]
        
        # 파일에서 로드 시도
        return self._load_order_metadata(order_id)

    def add_file(
        self,
        order_id: str,
        source_path: str,
        file_type: FileType,
        stage: FileStage,
        description: str = "",
        parent_version_id: str = None,
        metadata: Dict[str, Any] = None,
    ) -> Optional[FileVersion]:
        """파일 추가"""
        order = self.get_order(order_id)
        if not order:
            logger.error(f"Order not found: {order_id}")
            return None
        
        if not os.path.exists(source_path):
            logger.error(f"Source file not found: {source_path}")
            return None
        
        # 버전 정보 생성
        version_id = self._generate_version_id()
        file_ext = Path(source_path).suffix
        
        # 파일명 규칙: {order_id}_{stage}_{version_id}{ext}
        new_filename = f"{order_id}_{stage.value.split('_')[0]}_{version_id}{file_ext}"
        
        # 대상 경로
        dest_dir = os.path.join(self.base_dir, "orders", order_id, stage.value)
        dest_path = os.path.join(dest_dir, new_filename)
        
        # 파일 복사
        shutil.copy2(source_path, dest_path)
        
        # 버전 객체 생성
        version = FileVersion(
            version_id=version_id,
            file_path=dest_path,
            file_type=file_type,
            stage=stage,
            created_at=datetime.now(),
            file_hash=self._calculate_file_hash(dest_path),
            file_size=os.path.getsize(dest_path),
            description=description,
            parent_version_id=parent_version_id,
            metadata=metadata or {},
        )
        
        # 주문에 추가
        order.versions.append(version)
        order.updated_at = datetime.now()
        order.current_stage = stage
        
        self._save_order_metadata(order)
        
        logger.info(f"Added file version: {version_id} to order {order_id}")
        return version

    def get_latest_version(
        self,
        order_id: str,
        stage: FileStage = None,
        file_type: FileType = None,
    ) -> Optional[FileVersion]:
        """최신 버전 조회"""
        order = self.get_order(order_id)
        if not order:
            return None
        
        filtered = order.versions
        
        if stage:
            filtered = [v for v in filtered if v.stage == stage]
        
        if file_type:
            filtered = [v for v in filtered if v.file_type == file_type]
        
        if not filtered:
            return None
        
        return max(filtered, key=lambda v: v.created_at)

    def get_version_history(
        self,
        order_id: str,
        file_type: FileType = None,
    ) -> List[FileVersion]:
        """버전 이력 조회"""
        order = self.get_order(order_id)
        if not order:
            return []
        
        versions = order.versions
        
        if file_type:
            versions = [v for v in versions if v.file_type == file_type]
        
        return sorted(versions, key=lambda v: v.created_at)

    def add_layer_review(
        self,
        order_id: str,
        file_version_id: str,
        layers: List[LayerInfo],
        issues_found: List[str],
        approved: bool,
        reviewer: str = "system",
        notes: str = "",
    ) -> Optional[LayerReview]:
        """레이어 검토 추가"""
        order = self.get_order(order_id)
        if not order:
            return None
        
        review_id = f"lr_{self._generate_version_id()}"
        
        review = LayerReview(
            review_id=review_id,
            file_version_id=file_version_id,
            reviewed_at=datetime.now(),
            reviewer=reviewer,
            layers=layers,
            issues_found=issues_found,
            approved=approved,
            notes=notes,
        )
        
        order.layer_reviews.append(review)
        order.updated_at = datetime.now()
        
        self._save_order_metadata(order)
        
        logger.info(f"Added layer review: {review_id} for order {order_id}")
        return review

    def approve_final(
        self,
        order_id: str,
        approver: str = "customer",
    ) -> bool:
        """최종 승인"""
        order = self.get_order(order_id)
        if not order:
            return False
        
        # 최신 레이어 검토 확인
        if order.layer_reviews:
            latest_review = max(order.layer_reviews, key=lambda r: r.reviewed_at)
            if not latest_review.approved:
                logger.warning(f"Latest layer review not approved for order {order_id}")
                return False
        
        order.final_approved = True
        order.current_stage = FileStage.APPROVED
        order.updated_at = datetime.now()
        
        self._save_order_metadata(order)
        
        logger.info(f"Final approval granted for order {order_id} by {approver}")
        return True

    def _save_order_metadata(self, order: OrderFileSet):
        """주문 메타데이터 저장"""
        order_dir = os.path.join(self.base_dir, "orders", order.order_id)
        metadata_path = os.path.join(order_dir, "metadata.json")
        
        # 직렬화 가능한 형태로 변환
        data = {
            "order_id": order.order_id,
            "customer_name": order.customer_name,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "current_stage": order.current_stage.value,
            "final_approved": order.final_approved,
            "google_drive_folder_id": order.google_drive_folder_id,
            "versions": [
                {
                    "version_id": v.version_id,
                    "file_path": v.file_path,
                    "file_type": v.file_type.value,
                    "stage": v.stage.value,
                    "created_at": v.created_at.isoformat(),
                    "created_by": v.created_by,
                    "file_hash": v.file_hash,
                    "file_size": v.file_size,
                    "description": v.description,
                    "parent_version_id": v.parent_version_id,
                    "metadata": v.metadata,
                }
                for v in order.versions
            ],
            "layer_reviews": [
                {
                    "review_id": r.review_id,
                    "file_version_id": r.file_version_id,
                    "reviewed_at": r.reviewed_at.isoformat(),
                    "reviewer": r.reviewer,
                    "layers": [
                        {
                            "name": l.name,
                            "visible": l.visible,
                            "locked": l.locked,
                            "order": l.order,
                            "type": l.type,
                            "notes": l.notes,
                        }
                        for l in r.layers
                    ],
                    "issues_found": r.issues_found,
                    "approved": r.approved,
                    "notes": r.notes,
                }
                for r in order.layer_reviews
            ],
        }
        
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_order_metadata(self, order_id: str) -> Optional[OrderFileSet]:
        """주문 메타데이터 로드"""
        metadata_path = os.path.join(
            self.base_dir, "orders", order_id, "metadata.json"
        )
        
        if not os.path.exists(metadata_path):
            return None
        
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            order = OrderFileSet(
                order_id=data["order_id"],
                customer_name=data["customer_name"],
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
                current_stage=FileStage(data["current_stage"]),
                final_approved=data["final_approved"],
                google_drive_folder_id=data.get("google_drive_folder_id"),
            )
            
            # 버전 복원
            for v_data in data.get("versions", []):
                version = FileVersion(
                    version_id=v_data["version_id"],
                    file_path=v_data["file_path"],
                    file_type=FileType(v_data["file_type"]),
                    stage=FileStage(v_data["stage"]),
                    created_at=datetime.fromisoformat(v_data["created_at"]),
                    created_by=v_data["created_by"],
                    file_hash=v_data["file_hash"],
                    file_size=v_data["file_size"],
                    description=v_data["description"],
                    parent_version_id=v_data.get("parent_version_id"),
                    metadata=v_data.get("metadata", {}),
                )
                order.versions.append(version)
            
            # 레이어 검토 복원
            for r_data in data.get("layer_reviews", []):
                layers = [
                    LayerInfo(
                        name=l["name"],
                        visible=l["visible"],
                        locked=l["locked"],
                        order=l["order"],
                        type=l.get("type", "normal"),
                        notes=l.get("notes", ""),
                    )
                    for l in r_data.get("layers", [])
                ]
                
                review = LayerReview(
                    review_id=r_data["review_id"],
                    file_version_id=r_data["file_version_id"],
                    reviewed_at=datetime.fromisoformat(r_data["reviewed_at"]),
                    reviewer=r_data["reviewer"],
                    layers=layers,
                    issues_found=r_data["issues_found"],
                    approved=r_data["approved"],
                    notes=r_data.get("notes", ""),
                )
                order.layer_reviews.append(review)
            
            self.orders[order_id] = order
            return order
            
        except Exception as e:
            logger.error(f"Failed to load order metadata: {e}")
            return None

    async def sync_to_google_drive(
        self,
        order_id: str,
        rclone_config: str = "/home/ubuntu/.gdrive-rclone.ini",
    ) -> bool:
        """Google Drive로 동기화"""
        order = self.get_order(order_id)
        if not order:
            return False
        
        try:
            local_dir = os.path.join(self.base_dir, "orders", order_id)
            remote_path = f"{self.gdrive_remote}:{self.gdrive_base_path}/{order_id}"
            
            # rclone sync 실행
            process = await asyncio.create_subprocess_exec(
                "rclone", "sync",
                local_dir, remote_path,
                "--config", rclone_config,
                "-v",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"Synced order {order_id} to Google Drive")
                return True
            else:
                logger.error(f"Sync failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Google Drive sync error: {e}")
            return False

    async def get_google_drive_link(
        self,
        order_id: str,
        rclone_config: str = "/home/ubuntu/.gdrive-rclone.ini",
    ) -> Optional[str]:
        """Google Drive 공유 링크 생성"""
        try:
            remote_path = f"{self.gdrive_remote}:{self.gdrive_base_path}/{order_id}"
            
            process = await asyncio.create_subprocess_exec(
                "rclone", "link",
                remote_path,
                "--config", rclone_config,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                logger.error(f"Failed to get link: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Get link error: {e}")
            return None

    def generate_version_report(self, order_id: str) -> str:
        """버전 보고서 생성"""
        order = self.get_order(order_id)
        if not order:
            return "주문을 찾을 수 없습니다."
        
        report = []
        report.append(f"# 주문 버전 보고서: {order_id}")
        report.append(f"\n## 기본 정보")
        report.append(f"- **고객명**: {order.customer_name}")
        report.append(f"- **생성일**: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
        report.append(f"- **최종 수정**: {order.updated_at.strftime('%Y-%m-%d %H:%M')}")
        report.append(f"- **현재 단계**: {order.current_stage.value}")
        report.append(f"- **최종 승인**: {'✅ 완료' if order.final_approved else '⏳ 대기'}")
        
        report.append(f"\n## 파일 버전 이력 ({len(order.versions)}개)")
        report.append("\n| 버전 ID | 단계 | 파일 유형 | 생성일 | 설명 |")
        report.append("|---------|------|----------|--------|------|")
        
        for v in sorted(order.versions, key=lambda x: x.created_at):
            report.append(
                f"| {v.version_id[:12]}... | {v.stage.value.split('_')[1]} | "
                f"{v.file_type.value} | {v.created_at.strftime('%m-%d %H:%M')} | "
                f"{v.description[:30]}{'...' if len(v.description) > 30 else ''} |"
            )
        
        if order.layer_reviews:
            report.append(f"\n## 레이어 검토 이력 ({len(order.layer_reviews)}개)")
            for r in sorted(order.layer_reviews, key=lambda x: x.reviewed_at):
                status = "✅ 승인" if r.approved else "❌ 반려"
                report.append(f"\n### 검토 {r.review_id[:12]}... ({status})")
                report.append(f"- **검토일**: {r.reviewed_at.strftime('%Y-%m-%d %H:%M')}")
                report.append(f"- **검토자**: {r.reviewer}")
                report.append(f"- **레이어 수**: {len(r.layers)}개")
                
                if r.issues_found:
                    report.append(f"- **발견된 문제**:")
                    for issue in r.issues_found:
                        report.append(f"  - {issue}")
                
                if r.notes:
                    report.append(f"- **비고**: {r.notes}")
        
        return "\n".join(report)


# 편의 함수
def create_order_with_file(
    order_id: str,
    customer_name: str,
    original_file_path: str,
    description: str = "고객 원본 파일",
) -> Optional[OrderFileSet]:
    """주문 생성 및 원본 파일 추가"""
    manager = VersionManager()
    order = manager.create_order(order_id, customer_name)
    
    manager.add_file(
        order_id=order_id,
        source_path=original_file_path,
        file_type=FileType.CUSTOMER_IMAGE,
        stage=FileStage.ORIGINAL,
        description=description,
    )
    
    return order
