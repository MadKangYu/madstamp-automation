"""
Madstamp Automation - 메인 파이프라인

전체 도장 이미지 자동화 워크플로우를 통합하여 실행합니다.

워크플로우:
1. 이메일 모니터링 (Gmail MCP)
2. 이미지 분석 및 제작 가능 여부 판단 (OpenRouter Grok 4.1 Fast)
3. 고객에게 분석 결과 발송
4. 제작 가능한 경우 Lovart AI로 이미지 생성
5. 벡터 변환 (PNG → EPS/AI)
6. 완성된 파일 고객에게 발송
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.jobs.email_handler import CustomerEmail, EmailHandler, EmailStatus
from app.jobs.lovart_automator import LovartAutomator, build_stamp_prompt
from app.jobs.vector_converter import VectorConverter
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
    ANALYZING_IMAGE = "analyzing_image"
    SENDING_ANALYSIS = "sending_analysis"
    GENERATING_IMAGE = "generating_image"
    CONVERTING_VECTOR = "converting_vector"
    SENDING_RESULT = "sending_result"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineResult:
    """파이프라인 실행 결과"""
    status: PipelineStatus
    customer_email: Optional[CustomerEmail] = None
    analysis_result: Optional[ComprehensiveAnalysisResult] = None
    generated_image_path: Optional[str] = None
    vector_files: list[str] = None
    error_message: Optional[str] = None
    started_at: datetime = None
    completed_at: datetime = None

    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now()
        if self.vector_files is None:
            self.vector_files = []


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
        output_dir: str = "/tmp/madstamp_output",
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
        self.image_analyzer = ImageAnalyzerService(
            openrouter_api_key=self.openrouter_api_key,
            ocr_api_key=self.ocr_api_key,
        )
        self.vector_converter = VectorConverter(output_dir=output_dir)

    async def close(self):
        """리소스 정리"""
        await self.image_analyzer.close()

    async def run_once(self) -> list[PipelineResult]:
        """
        파이프라인 1회 실행
        
        새 이메일을 확인하고 각 이메일에 대해 전체 워크플로우를 실행합니다.
        
        Returns:
            list[PipelineResult]: 각 이메일에 대한 처리 결과
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
        """단일 이메일 처리"""
        result = PipelineResult(
            status=PipelineStatus.CHECKING_EMAILS,
            customer_email=email,
        )

        try:
            # 첨부파일 다운로드
            image_paths = await self._download_attachments(email)
            
            if not image_paths:
                # 첨부파일이 없으면 본문에서 이미지 URL 추출 시도
                logger.warning(f"No image attachments found in email: {email.subject}")
                result.status = PipelineStatus.FAILED
                result.error_message = "이미지 첨부파일이 없습니다."
                return result

            # 첫 번째 이미지 분석
            result.status = PipelineStatus.ANALYZING_IMAGE
            logger.info(f"Analyzing image: {image_paths[0]}")
            
            analysis = await self.image_analyzer.analyze(
                image_path=image_paths[0],
                customer_request=email.body,
            )
            result.analysis_result = analysis

            # 분석 결과 이메일 발송
            result.status = PipelineStatus.SENDING_ANALYSIS
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

            # 제작 가능한 경우 이미지 생성
            if analysis.producibility_status == ProducibilityStatus.PRODUCIBLE:
                result = await self._generate_and_deliver(email, analysis, result)
            else:
                result.status = PipelineStatus.COMPLETED
                result.completed_at = datetime.now()

            return result

        except Exception as e:
            logger.error(f"Error processing email: {e}")
            result.status = PipelineStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()
            return result

    async def _download_attachments(self, email: CustomerEmail) -> list[str]:
        """이메일 첨부파일 다운로드"""
        image_paths = []
        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

        for attachment in email.attachments:
            ext = Path(attachment.filename).suffix.lower()
            if ext in image_extensions:
                local_path = await self.email_handler.gmail_client.download_attachment(
                    message_id=email.message_id,
                    attachment_id="",  # 실제 구현에서는 attachment_id 필요
                    filename=attachment.filename,
                )
                if local_path:
                    image_paths.append(local_path)
                    attachment.local_path = local_path

        return image_paths

    async def _generate_and_deliver(
        self,
        email: CustomerEmail,
        analysis: ComprehensiveAnalysisResult,
        result: PipelineResult,
    ) -> PipelineResult:
        """이미지 생성 및 전달"""
        try:
            # Lovart AI로 이미지 생성
            result.status = PipelineStatus.GENERATING_IMAGE
            logger.info("Generating image with Lovart AI...")

            # 프롬프트 생성
            prompt = analysis.recommended_prompt or build_stamp_prompt(
                template_name="modern_logo",
                text=analysis.detected_text or "STAMP",
                shape="원형",
                additional_instructions=email.body[:200] if email.body else None,
            )

            # Lovart AI 자동화
            lovart = LovartAutomator(
                headless=self.headless,
                download_dir=self.output_dir,
            )
            
            try:
                await lovart.initialize()
                generation_result = await lovart.generate_image(
                    prompt=prompt,
                    reference_image_path=analysis.image_path,
                )
                
                if generation_result.image_path:
                    result.generated_image_path = generation_result.image_path
                else:
                    raise Exception("이미지 생성 실패")
                    
            finally:
                await lovart.close()

            # 벡터 변환
            result.status = PipelineStatus.CONVERTING_VECTOR
            logger.info("Converting to vector format...")
            
            vector_result = await self.vector_converter.convert(
                input_path=result.generated_image_path,
                output_formats=["svg", "eps"],
            )
            
            if vector_result.svg_path:
                result.vector_files.append(vector_result.svg_path)
            if vector_result.eps_path:
                result.vector_files.append(vector_result.eps_path)

            # 결과 발송
            result.status = PipelineStatus.SENDING_RESULT
            logger.info("Sending completed result to customer...")
            
            await self.email_handler.send_completed_result(
                customer_email=email,
                generated_image_path=result.generated_image_path,
                vector_files=result.vector_files,
            )

            result.status = PipelineStatus.COMPLETED
            result.completed_at = datetime.now()
            
            logger.info(f"Pipeline completed for email: {email.subject}")

        except Exception as e:
            logger.error(f"Generation/delivery error: {e}")
            result.status = PipelineStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()

        return result

    async def run_continuous(self, interval_seconds: int = 60):
        """
        연속 실행 모드
        
        지정된 간격으로 이메일을 확인하고 처리합니다.
        
        Args:
            interval_seconds: 확인 간격 (초)
        """
        logger.info(f"Starting continuous monitoring (interval: {interval_seconds}s)")
        
        while True:
            try:
                results = await self.run_once()
                
                for result in results:
                    if result.status == PipelineStatus.COMPLETED:
                        logger.info(f"Successfully processed: {result.customer_email.subject if result.customer_email else 'Unknown'}")
                    elif result.status == PipelineStatus.FAILED:
                        logger.error(f"Failed to process: {result.error_message}")
                
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
                print(f"Status: {result.status.value}")
                if result.customer_email:
                    print(f"Email: {result.customer_email.subject}")
                if result.error_message:
                    print(f"Error: {result.error_message}")
        else:
            await pipeline.run_continuous(interval_seconds=args.interval)
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
