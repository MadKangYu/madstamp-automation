"""
Madstamp Automation - 전체 파이프라인 통합

도장 이미지 자동 제작 시스템의 메인 오케스트레이터입니다.

확장된 워크플로우:
1. 이메일 수신 → 고객 요청 감지
2. 파일 분류 → Google Drive 저장
3. 이미지 분석 → 제작 가능 여부 판단
4. OCR → 텍스트 추출 및 폰트 매칭
5. Lovart AI → 이미지 생성 (필요시)
6. 일러스트레이터 → 대지 배치, 폰트 타이핑, 레이어 관리
7. 이미지 처리 → 컬러→흑백, 펜툴 선 처리, 색 비우기
8. 포토샵 → BMP 변환 (레이저 프린터용)
9. 버전 관리 → 원본/수정본 관리, Google Drive 동기화
10. 고객 컨펌 → 최종 출력
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.core.config import settings
from app.jobs.email_handler import CustomerEmail, EmailHandler, EmailStatus
from app.jobs.file_manager import FileManager, FileClassification
from app.jobs.lovart_automator import LovartAutomator, build_stamp_prompt
from app.jobs.illustrator_automator import IllustratorAutomator
from app.jobs.image_processor import ImageProcessor, StampOptimizer, ProcessingSettings, ProcessingMode
from app.jobs.photoshop_converter import BMPConverter, BMPSettings, BMPColorDepth, PrinterDPI
from app.jobs.vector_converter import VectorConverter
from app.jobs.version_manager import (
    VersionManager, FileStage, FileType, LayerInfo, OrderFileSet
)
from app.services.image_analyzer_service import (
    ComprehensiveAnalysisResult,
    ImageAnalyzerService,
    ProducibilityStatus,
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PipelineStatus(str, Enum):
    """파이프라인 상태"""
    IDLE = "idle"
    CHECKING_EMAILS = "checking_emails"
    CLASSIFYING_FILES = "classifying_files"
    ANALYZING_IMAGE = "analyzing_image"
    SENDING_ANALYSIS = "sending_analysis"
    GENERATING_IMAGE = "generating_image"
    PROCESSING_IMAGE = "processing_image"
    ILLUSTRATOR_WORK = "illustrator_work"
    LAYER_REVIEW = "layer_review"
    CUSTOMER_CONFIRM = "customer_confirm"
    CONVERTING_BMP = "converting_bmp"
    SYNCING_DRIVE = "syncing_drive"
    READY_TO_PRINT = "ready_to_print"
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineResult:
    """파이프라인 실행 결과"""
    status: PipelineStatus
    order_id: str = ""
    customer_email: Optional[CustomerEmail] = None
    analysis_result: Optional[ComprehensiveAnalysisResult] = None
    
    # 파일 경로
    original_image_paths: List[str] = field(default_factory=list)
    generated_image_path: Optional[str] = None
    processed_image_path: Optional[str] = None
    ai_file_path: Optional[str] = None
    eps_file_path: Optional[str] = None
    bmp_file_path: Optional[str] = None
    vector_files: List[str] = field(default_factory=list)
    
    # 메타데이터
    google_drive_link: Optional[str] = None
    error_message: Optional[str] = None
    processing_log: List[str] = field(default_factory=list)
    started_at: datetime = None
    completed_at: datetime = None

    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now()


class MadstampPipeline:
    """
    Madstamp 도장 이미지 자동화 파이프라인
    
    전체 워크플로우를 비동기로 실행합니다.
    """

    def __init__(
        self,
        openrouter_api_key: Optional[str] = None,
        ocr_api_key: str = "helloworld",
        target_email: str = "goopick@goopick.net",
        notification_email: str = "richardowen7212@gmail.com",
        output_dir: str = "/home/ubuntu/madstamp_output",
        headless: bool = True,
    ):
        self.openrouter_api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.ocr_api_key = ocr_api_key
        self.target_email = target_email
        self.notification_email = notification_email
        self.output_dir = output_dir
        self.headless = headless

        # 출력 디렉토리 생성
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # 서비스 초기화
        self.email_handler = EmailHandler(
            target_email=target_email,
            notification_email=notification_email,
        )
        self.file_manager = FileManager(
            base_dir=output_dir,
            gdrive_remote="manus_google_drive",
            gdrive_base_path="Madstamp/Orders",
        )
        self.image_analyzer = ImageAnalyzerService(
            openrouter_api_key=self.openrouter_api_key,
            ocr_api_key=self.ocr_api_key,
        )
        self.image_processor = ImageProcessor(output_dir=f"{output_dir}/processed")
        self.stamp_optimizer = StampOptimizer(self.image_processor)
        self.illustrator = IllustratorAutomator(output_dir=f"{output_dir}/illustrator")
        self.bmp_converter = BMPConverter(output_dir=f"{output_dir}/bmp")
        self.vector_converter = VectorConverter(output_dir=f"{output_dir}/vector")
        self.version_manager = VersionManager(base_dir=output_dir)

    async def close(self):
        """리소스 정리"""
        await self.image_analyzer.close()

    def _generate_order_id(self) -> str:
        """주문 ID 생성"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"MS{timestamp}"

    async def run_once(self) -> List[PipelineResult]:
        """
        파이프라인 1회 실행
        
        새 이메일을 확인하고 각 이메일에 대해 전체 워크플로우를 실행합니다.
        """
        results = []

        try:
            # 1. 새 이메일 확인
            logger.info("Checking for new emails...")
            new_emails = await self.email_handler.check_new_emails()
            logger.info(f"Found {len(new_emails)} new emails")

            # 2. 각 이메일 처리
            for email in new_emails:
                result = await self._process_email(email)
                results.append(result)

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            results.append(PipelineResult(
                status=PipelineStatus.FAILED,
                error_message=str(e),
            ))

        return results

    async def _process_email(self, email: CustomerEmail) -> PipelineResult:
        """단일 이메일 처리 - 전체 워크플로우"""
        order_id = self._generate_order_id()
        
        result = PipelineResult(
            status=PipelineStatus.CHECKING_EMAILS,
            order_id=order_id,
            customer_email=email,
        )

        try:
            # 버전 관리 시작
            customer_name = email.sender.split("@")[0].replace(".", " ").title()
            self.version_manager.create_order(order_id, customer_name)
            result.processing_log.append(f"주문 생성: {order_id}")

            # 1. 파일 분류 및 저장
            result.status = PipelineStatus.CLASSIFYING_FILES
            image_paths = await self._classify_and_save_files(email, order_id, result)
            
            if not image_paths:
                result.status = PipelineStatus.FAILED
                result.error_message = "이미지 첨부파일이 없습니다."
                return result

            result.original_image_paths = image_paths

            # 2. 이미지 분석
            result.status = PipelineStatus.ANALYZING_IMAGE
            analysis = await self._analyze_images(image_paths[0], email.body, order_id, result)
            result.analysis_result = analysis

            # 3. 분석 결과 발송
            result.status = PipelineStatus.SENDING_ANALYSIS
            await self._send_analysis_result(email, analysis, result)

            # 4. 제작 가능한 경우 전체 워크플로우 실행
            if analysis.producibility_status == ProducibilityStatus.PRODUCIBLE:
                result = await self._execute_production_workflow(
                    email, analysis, order_id, result
                )
            else:
                result.processing_log.append(f"제작 불가: {analysis.producibility_reason}")
                result.status = PipelineStatus.COMPLETED
                result.completed_at = datetime.now()

            return result

        except Exception as e:
            logger.error(f"Error processing email: {e}")
            result.status = PipelineStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()
            return result

    async def _classify_and_save_files(
        self,
        email: CustomerEmail,
        order_id: str,
        result: PipelineResult,
    ) -> List[str]:
        """파일 분류 및 저장"""
        image_paths = []
        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"}

        for attachment in email.attachments:
            ext = Path(attachment.filename).suffix.lower()
            if ext in image_extensions:
                # 파일 분류
                classification = await self.file_manager.classify_file(
                    filename=attachment.filename,
                    content_type=attachment.content_type,
                )
                
                # 파일 저장
                saved_path = await self.file_manager.save_file(
                    order_id=order_id,
                    source_data=attachment.content,
                    filename=attachment.filename,
                    classification=classification,
                )
                
                if saved_path:
                    image_paths.append(saved_path)
                    
                    # 버전 관리에 추가
                    self.version_manager.add_file(
                        order_id=order_id,
                        source_path=saved_path,
                        file_type=FileType.CUSTOMER_IMAGE,
                        stage=FileStage.ORIGINAL,
                        description=f"고객 첨부: {attachment.filename}",
                    )
                    
                    result.processing_log.append(f"파일 저장: {attachment.filename}")

        # Google Drive 동기화
        await self.file_manager.sync_to_google_drive(order_id)
        result.processing_log.append("Google Drive 동기화 완료")

        return image_paths

    async def _analyze_images(
        self,
        image_path: str,
        customer_request: str,
        order_id: str,
        result: PipelineResult,
    ) -> ComprehensiveAnalysisResult:
        """이미지 분석"""
        logger.info(f"Analyzing image: {image_path}")
        
        analysis = await self.image_analyzer.analyze(
            image_path=image_path,
            customer_request=customer_request,
        )
        
        # 버전 관리 업데이트
        self.version_manager.add_file(
            order_id=order_id,
            source_path=image_path,
            file_type=FileType.CUSTOMER_IMAGE,
            stage=FileStage.ANALYZED,
            description=f"분석 완료 - {analysis.producibility_status.value}",
            metadata={
                "producibility": analysis.producibility_status.value,
                "quality": analysis.image_quality.value,
                "detected_text": analysis.detected_text,
            },
        )
        
        result.processing_log.append(f"분석 완료: {analysis.producibility_status.value}")
        result.processing_log.append(f"품질: {analysis.image_quality.value}")
        
        if analysis.detected_text:
            result.processing_log.append(f"감지된 텍스트: {analysis.detected_text[:50]}...")
        
        return analysis

    async def _send_analysis_result(
        self,
        email: CustomerEmail,
        analysis: ComprehensiveAnalysisResult,
        result: PipelineResult,
    ):
        """분석 결과 발송"""
        await self.email_handler.send_analysis_result(
            customer_email=email,
            analysis_result={
                "status": analysis.producibility_status.value,
                "reason": analysis.producibility_reason,
                "image_quality": analysis.image_quality.value,
                "detected_elements": analysis.detected_elements,
                "detected_text": analysis.detected_text,
                "recommended_fonts": [
                    {"name": f.name, "style": f.style}
                    for f in analysis.recommended_fonts
                ],
                "suggestions": analysis.suggestions,
            },
        )
        result.processing_log.append("분석 결과 이메일 발송 완료")

    async def _execute_production_workflow(
        self,
        email: CustomerEmail,
        analysis: ComprehensiveAnalysisResult,
        order_id: str,
        result: PipelineResult,
    ) -> PipelineResult:
        """제작 워크플로우 실행"""
        try:
            # 5. Lovart AI 이미지 생성
            result.status = PipelineStatus.GENERATING_IMAGE
            generated_path = await self._generate_image(analysis, order_id, result)
            result.generated_image_path = generated_path

            # 6. 이미지 처리 (흑백 변환, 도장 최적화)
            result.status = PipelineStatus.PROCESSING_IMAGE
            processed_path = await self._process_image(
                generated_path or result.original_image_paths[0],
                order_id,
                result,
            )
            result.processed_image_path = processed_path

            # 7. 일러스트레이터 작업
            result.status = PipelineStatus.ILLUSTRATOR_WORK
            ai_path, eps_path = await self._illustrator_work(
                processed_path,
                analysis,
                order_id,
                result,
            )
            result.ai_file_path = ai_path
            result.eps_file_path = eps_path

            # 8. 레이어 검토
            result.status = PipelineStatus.LAYER_REVIEW
            await self._review_layers(order_id, result)

            # 9. 고객 컨펌 요청
            result.status = PipelineStatus.CUSTOMER_CONFIRM
            await self._request_customer_confirm(email, order_id, result)

            # 실제 구현에서는 여기서 고객 응답을 기다림
            # 데모에서는 자동 승인으로 진행

            # 10. BMP 변환
            result.status = PipelineStatus.CONVERTING_BMP
            bmp_path = await self._convert_to_bmp(processed_path, order_id, result)
            result.bmp_file_path = bmp_path

            # 11. Google Drive 동기화
            result.status = PipelineStatus.SYNCING_DRIVE
            drive_link = await self._sync_final_to_drive(order_id, result)
            result.google_drive_link = drive_link

            # 12. 완료
            result.status = PipelineStatus.READY_TO_PRINT
            await self._send_completion_email(email, order_id, result)

            result.status = PipelineStatus.COMPLETED
            result.completed_at = datetime.now()
            
            # 버전 보고서 생성
            report = self.version_manager.generate_version_report(order_id)
            report_path = os.path.join(
                self.output_dir, "orders", order_id, "VERSION_REPORT.md"
            )
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)
            
            result.processing_log.append("워크플로우 완료")
            logger.info(f"Pipeline completed for order: {order_id}")

        except Exception as e:
            logger.error(f"Production workflow error: {e}")
            result.status = PipelineStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()

        return result

    async def _generate_image(
        self,
        analysis: ComprehensiveAnalysisResult,
        order_id: str,
        result: PipelineResult,
    ) -> Optional[str]:
        """Lovart AI 이미지 생성"""
        logger.info("Generating image with Lovart AI...")
        
        # 프롬프트 생성
        prompt = analysis.recommended_prompt or build_stamp_prompt(
            template_name="modern_logo",
            text=analysis.detected_text or "STAMP",
            shape="원형",
        )
        
        lovart = LovartAutomator(
            headless=self.headless,
            download_dir=f"{self.output_dir}/lovart",
        )
        
        try:
            await lovart.initialize()
            gen_result = await lovart.generate_image(
                prompt=prompt,
                reference_image_path=analysis.image_path,
            )
            
            if gen_result.image_path:
                # 버전 관리
                self.version_manager.add_file(
                    order_id=order_id,
                    source_path=gen_result.image_path,
                    file_type=FileType.WORKING,
                    stage=FileStage.PROCESSED,
                    description="Lovart AI 생성 이미지",
                )
                result.processing_log.append("Lovart AI 이미지 생성 완료")
                return gen_result.image_path
            else:
                result.processing_log.append("Lovart AI 이미지 생성 실패 - 원본 사용")
                return None
                
        finally:
            await lovart.close()

    async def _process_image(
        self,
        image_path: str,
        order_id: str,
        result: PipelineResult,
    ) -> str:
        """이미지 처리 (흑백 변환, 도장 최적화)"""
        logger.info(f"Processing image: {image_path}")
        
        # 도장 최적화 처리
        proc_result = await self.stamp_optimizer.optimize_for_stamp(
            input_path=image_path,
            stamp_type="general",
        )
        
        if proc_result.success:
            # 버전 관리
            self.version_manager.add_file(
                order_id=order_id,
                source_path=proc_result.output_path,
                file_type=FileType.WORKING,
                stage=FileStage.PROCESSED,
                description="흑백 변환 및 도장 최적화",
                metadata={
                    "quality_score": proc_result.quality_score,
                    "processing_log": proc_result.processing_log,
                },
            )
            result.processing_log.append(f"이미지 처리 완료 (품질: {proc_result.quality_score:.1f})")
            return proc_result.output_path
        else:
            result.processing_log.append(f"이미지 처리 실패: {proc_result.issues}")
            return image_path

    async def _illustrator_work(
        self,
        image_path: str,
        analysis: ComprehensiveAnalysisResult,
        order_id: str,
        result: PipelineResult,
    ) -> tuple[Optional[str], Optional[str]]:
        """일러스트레이터 작업"""
        logger.info("Creating Illustrator file...")
        
        # 추천 폰트 선택
        font_name = "NotoSansKR-Regular"
        if analysis.recommended_fonts:
            font_name = analysis.recommended_fonts[0].name
        
        # 일러스트레이터 문서 생성
        ill_result = await self.illustrator.create_stamp_document(
            order_id=order_id,
            image_path=image_path,
            text=analysis.detected_text or "",
            font_name=font_name,
            stamp_size_mm=50.0,
        )
        
        ai_path = None
        eps_path = None
        
        if ill_result.success:
            ai_path = ill_result.ai_path
            eps_path = ill_result.eps_path
            
            # 버전 관리
            if ai_path:
                self.version_manager.add_file(
                    order_id=order_id,
                    source_path=ai_path,
                    file_type=FileType.AI_FILE,
                    stage=FileStage.ILLUSTRATOR,
                    description="일러스트레이터 작업 파일",
                )
            
            if eps_path:
                self.version_manager.add_file(
                    order_id=order_id,
                    source_path=eps_path,
                    file_type=FileType.EPS_FILE,
                    stage=FileStage.ILLUSTRATOR,
                    description="EPS 내보내기",
                )
            
            result.processing_log.append("일러스트레이터 작업 완료")
        else:
            result.processing_log.append("일러스트레이터 작업 실패")
        
        return ai_path, eps_path

    async def _review_layers(
        self,
        order_id: str,
        result: PipelineResult,
    ):
        """레이어 검토"""
        # 레이어 정보 생성 (실제 구현에서는 AI 파일에서 추출)
        layers = [
            LayerInfo(name="Background", visible=True, locked=True, order=0, type="normal"),
            LayerInfo(name="Image", visible=True, locked=False, order=1, type="image"),
            LayerInfo(name="Text", visible=True, locked=False, order=2, type="text"),
            LayerInfo(name="Outline", visible=True, locked=False, order=3, type="shape"),
        ]
        
        # 최신 버전 가져오기
        latest = self.version_manager.get_latest_version(order_id, FileStage.ILLUSTRATOR)
        
        if latest:
            self.version_manager.add_layer_review(
                order_id=order_id,
                file_version_id=latest.version_id,
                layers=layers,
                issues_found=[],
                approved=True,
                reviewer="system",
                notes="자동 레이어 검토 완료",
            )
        
        result.processing_log.append("레이어 검토 완료")

    async def _request_customer_confirm(
        self,
        email: CustomerEmail,
        order_id: str,
        result: PipelineResult,
    ):
        """고객 컨펌 요청"""
        # 실제 구현에서는 미리보기 이미지와 함께 이메일 발송
        result.processing_log.append("고객 컨펌 요청 (자동 승인)")

    async def _convert_to_bmp(
        self,
        image_path: str,
        order_id: str,
        result: PipelineResult,
    ) -> str:
        """BMP 변환"""
        logger.info("Converting to BMP...")
        
        settings = BMPSettings(
            color_depth=BMPColorDepth.MONO_1BIT,
            dpi=PrinterDPI.DPI_600,
            target_width_mm=50.0,
            target_height_mm=50.0,
            maintain_aspect_ratio=True,
        )
        
        bmp_result = await self.bmp_converter.convert_to_bmp(
            input_path=image_path,
            settings=settings,
            output_filename=f"{order_id}_final.bmp",
        )
        
        if bmp_result.success:
            # 버전 관리
            self.version_manager.add_file(
                order_id=order_id,
                source_path=bmp_result.output_path,
                file_type=FileType.BMP_FINAL,
                stage=FileStage.FINAL_BMP,
                description="최종 BMP (레이저 프린터용)",
                metadata={
                    "size_mm": bmp_result.output_size_mm,
                    "dpi": bmp_result.dpi,
                    "file_size_kb": bmp_result.file_size_kb,
                },
            )
            result.processing_log.append(f"BMP 변환 완료 ({bmp_result.output_size_mm}mm, {bmp_result.dpi}DPI)")
            return bmp_result.output_path
        else:
            result.processing_log.append(f"BMP 변환 실패: {bmp_result.issues}")
            return ""

    async def _sync_final_to_drive(
        self,
        order_id: str,
        result: PipelineResult,
    ) -> Optional[str]:
        """최종 파일 Google Drive 동기화"""
        logger.info("Syncing to Google Drive...")
        
        success = await self.version_manager.sync_to_google_drive(order_id)
        
        if success:
            link = await self.version_manager.get_google_drive_link(order_id)
            result.processing_log.append(f"Google Drive 동기화 완료")
            return link
        else:
            result.processing_log.append("Google Drive 동기화 실패")
            return None

    async def _send_completion_email(
        self,
        email: CustomerEmail,
        order_id: str,
        result: PipelineResult,
    ):
        """완료 이메일 발송"""
        await self.email_handler.send_completed_result(
            customer_email=email,
            generated_image_path=result.processed_image_path,
            vector_files=[f for f in [result.ai_file_path, result.eps_file_path, result.bmp_file_path] if f],
        )
        result.processing_log.append("완료 이메일 발송")

    async def run_continuous(self, interval_seconds: int = 60):
        """
        연속 실행 모드
        
        지정된 간격으로 이메일을 확인하고 처리합니다.
        """
        logger.info(f"Starting continuous monitoring (interval: {interval_seconds}s)")
        
        while True:
            try:
                results = await self.run_once()
                
                for result in results:
                    if result.status == PipelineStatus.COMPLETED:
                        logger.info(f"✅ Completed: {result.order_id}")
                    elif result.status == PipelineStatus.FAILED:
                        logger.error(f"❌ Failed: {result.error_message}")
                
                await asyncio.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Stopping continuous monitoring...")
                break
            except Exception as e:
                logger.error(f"Continuous monitoring error: {e}")
                await asyncio.sleep(interval_seconds)


async def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Madstamp 도장 이미지 자동화")
    parser.add_argument("--mode", choices=["once", "continuous"], default="once",
                       help="실행 모드 (once: 1회, continuous: 연속)")
    parser.add_argument("--interval", type=int, default=60,
                       help="연속 모드 확인 간격 (초)")
    parser.add_argument("--headless", action="store_true", default=True,
                       help="브라우저 헤드리스 모드")
    
    args = parser.parse_args()
    
    # 파이프라인 초기화
    pipeline = MadstampPipeline(
        headless=args.headless,
    )
    
    try:
        if args.mode == "once":
            results = await pipeline.run_once()
            for result in results:
                print(f"\n{'='*50}")
                print(f"Order ID: {result.order_id}")
                print(f"Status: {result.status.value}")
                if result.customer_email:
                    print(f"Email: {result.customer_email.subject}")
                print(f"\nProcessing Log:")
                for log in result.processing_log:
                    print(f"  - {log}")
                if result.error_message:
                    print(f"\nError: {result.error_message}")
                if result.google_drive_link:
                    print(f"\nGoogle Drive: {result.google_drive_link}")
        else:
            await pipeline.run_continuous(interval_seconds=args.interval)
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
