"""
Madstamp Automation - Lovart AI 브라우저 자동화 모듈

Playwright를 사용하여 Lovart AI 웹사이트에서 도장 이미지를 자동 생성합니다.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class GenerationStatus(str, Enum):
    """이미지 생성 상태"""
    PENDING = "pending"
    NAVIGATING = "navigating"
    CREATING_PROJECT = "creating_project"
    ENTERING_PROMPT = "entering_prompt"
    GENERATING = "generating"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LovartGenerationResult:
    """Lovart AI 이미지 생성 결과"""
    status: GenerationStatus
    prompt: str
    project_url: Optional[str] = None
    image_path: Optional[str] = None
    generation_time_seconds: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class LovartAutomator:
    """
    Lovart AI 브라우저 자동화
    
    Playwright를 사용하여 Lovart AI에서 도장 이미지를 자동 생성합니다.
    """

    def __init__(
        self,
        headless: bool = True,
        download_dir: str = "/tmp/lovart_downloads",
        timeout_ms: int = 120000,  # 2분
    ):
        self.headless = headless
        self.download_dir = download_dir
        self.timeout_ms = timeout_ms
        self.browser = None
        self.context = None
        self.page = None

        # 다운로드 디렉토리 생성
        Path(download_dir).mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """브라우저 초기화"""
        try:
            from playwright.async_api import async_playwright
            
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
            )
            self.context = await self.browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
            )
            self.page = await self.context.new_page()
            
            logger.info("Lovart Automator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise

    async def close(self):
        """브라우저 종료"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        
        logger.info("Lovart Automator closed")

    async def check_login_status(self) -> bool:
        """로그인 상태 확인"""
        try:
            await self.page.goto("https://www.lovart.ai/ko/home", timeout=30000)
            await self.page.wait_for_load_state("networkidle")
            
            # 로그인 버튼이 있으면 로그인 안됨
            login_button = await self.page.query_selector('text="로그인"')
            if login_button:
                logger.warning("Not logged in to Lovart AI")
                return False
            
            # 프로필 아이콘이나 새 프로젝트 버튼이 있으면 로그인됨
            new_project = await self.page.query_selector('text="새 프로젝트"')
            if new_project:
                logger.info("Logged in to Lovart AI")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check login status: {e}")
            return False

    async def generate_image(
        self,
        prompt: str,
        reference_image_path: Optional[str] = None,
        resolution: str = "4K",
    ) -> LovartGenerationResult:
        """
        Lovart AI에서 이미지를 생성합니다.
        
        Args:
            prompt: 이미지 생성 프롬프트
            reference_image_path: 참조 이미지 경로 (선택)
            resolution: 해상도 (4K, HD, SD)
            
        Returns:
            LovartGenerationResult: 생성 결과
        """
        start_time = datetime.now()
        
        try:
            # 1. Lovart AI 홈으로 이동
            logger.info("Navigating to Lovart AI...")
            await self.page.goto("https://www.lovart.ai/ko/home", timeout=30000)
            await self.page.wait_for_load_state("networkidle")

            # 2. 새 프로젝트 생성
            logger.info("Creating new project...")
            new_project_btn = await self.page.wait_for_selector(
                'text="새 프로젝트"',
                timeout=10000,
            )
            await new_project_btn.click()
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)  # 캔버스 로딩 대기

            # 3. 프롬프트 입력
            logger.info(f"Entering prompt: {prompt[:50]}...")
            
            # 텍스트 입력 영역 찾기 (여러 셀렉터 시도)
            input_selectors = [
                'textarea[placeholder*="idea"]',
                'textarea[placeholder*="아이디어"]',
                'input[type="text"]',
                '[contenteditable="true"]',
                '.chat-input',
                'textarea',
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    input_element = await self.page.wait_for_selector(
                        selector,
                        timeout=5000,
                    )
                    if input_element:
                        break
                except:
                    continue

            if not input_element:
                return LovartGenerationResult(
                    status=GenerationStatus.FAILED,
                    prompt=prompt,
                    error_message="프롬프트 입력 영역을 찾을 수 없습니다.",
                )

            # 프롬프트 입력
            await input_element.click()
            await input_element.fill(prompt)
            await asyncio.sleep(0.5)

            # 4. 참조 이미지 업로드 (선택)
            if reference_image_path and Path(reference_image_path).exists():
                logger.info("Uploading reference image...")
                # 이미지 업로드 버튼 찾기
                upload_btn = await self.page.query_selector('input[type="file"]')
                if upload_btn:
                    await upload_btn.set_input_files(reference_image_path)
                    await asyncio.sleep(2)

            # 5. 생성 시작 (Enter 키 또는 전송 버튼)
            logger.info("Starting generation...")
            await self.page.keyboard.press("Enter")
            
            # 6. 생성 완료 대기
            logger.info("Waiting for generation to complete...")
            await asyncio.sleep(5)  # 초기 대기
            
            # 생성 완료 감지 (이미지가 나타날 때까지 대기)
            max_wait = 120  # 최대 2분 대기
            for _ in range(max_wait // 5):
                # 생성된 이미지 확인
                images = await self.page.query_selector_all('img[src*="lovart"]')
                if len(images) > 1:  # 새 이미지가 생성됨
                    logger.info("Image generation detected")
                    break
                await asyncio.sleep(5)

            # 7. 현재 URL 저장
            project_url = self.page.url

            # 8. 이미지 다운로드
            logger.info("Downloading generated image...")
            image_path = await self._download_image(prompt)

            # 생성 시간 계산
            generation_time = int((datetime.now() - start_time).total_seconds())

            return LovartGenerationResult(
                status=GenerationStatus.COMPLETED,
                prompt=prompt,
                project_url=project_url,
                image_path=image_path,
                generation_time_seconds=generation_time,
            )

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return LovartGenerationResult(
                status=GenerationStatus.FAILED,
                prompt=prompt,
                error_message=str(e),
            )

    async def _download_image(self, prompt: str) -> Optional[str]:
        """생성된 이미지 다운로드"""
        try:
            # 다운로드 버튼 찾기
            download_selectors = [
                'button[aria-label*="download"]',
                'button[aria-label*="다운로드"]',
                '[data-testid="download"]',
                'text="다운로드"',
                'text="Download"',
            ]

            for selector in download_selectors:
                try:
                    download_btn = await self.page.wait_for_selector(
                        selector,
                        timeout=3000,
                    )
                    if download_btn:
                        # 다운로드 이벤트 대기
                        async with self.page.expect_download() as download_info:
                            await download_btn.click()
                        
                        download = await download_info.value
                        
                        # 파일 저장
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        safe_prompt = "".join(c for c in prompt[:30] if c.isalnum() or c in " _-")
                        filename = f"lovart_{timestamp}_{safe_prompt}.png"
                        save_path = os.path.join(self.download_dir, filename)
                        
                        await download.save_as(save_path)
                        logger.info(f"Image saved to: {save_path}")
                        return save_path
                        
                except:
                    continue

            # 다운로드 버튼을 찾지 못한 경우, 스크린샷으로 대체
            logger.warning("Download button not found, taking screenshot instead")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(self.download_dir, f"lovart_{timestamp}_screenshot.png")
            await self.page.screenshot(path=screenshot_path, full_page=False)
            return screenshot_path

        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            return None


async def generate_stamp_image(
    prompt: str,
    reference_image_path: Optional[str] = None,
    headless: bool = True,
) -> LovartGenerationResult:
    """
    도장 이미지 생성 헬퍼 함수
    
    Args:
        prompt: 이미지 생성 프롬프트
        reference_image_path: 참조 이미지 경로
        headless: 헤드리스 모드 여부
        
    Returns:
        LovartGenerationResult: 생성 결과
    """
    automator = LovartAutomator(headless=headless)
    
    try:
        await automator.initialize()
        
        # 로그인 상태 확인
        is_logged_in = await automator.check_login_status()
        if not is_logged_in:
            return LovartGenerationResult(
                status=GenerationStatus.FAILED,
                prompt=prompt,
                error_message="Lovart AI에 로그인되어 있지 않습니다. 먼저 로그인해주세요.",
            )
        
        # 이미지 생성
        return await automator.generate_image(
            prompt=prompt,
            reference_image_path=reference_image_path,
        )
        
    finally:
        await automator.close()


# 프롬프트 템플릿
STAMP_PROMPT_TEMPLATES = {
    "traditional_korean": """한국 전통 도장 디자인을 만들어주세요.
- 스타일: 전통적인 한국 인장 (낙관)
- 형태: {shape}
- 텍스트: {text}
- 색상: 빨간색 인주 스타일
- 배경: 투명 또는 흰색
- 해상도: 4K 고해상도
- 용도: 상업용 도장 제작""",

    "modern_logo": """현대적인 로고 스타일 도장을 만들어주세요.
- 스타일: 미니멀하고 현대적인 디자인
- 형태: {shape}
- 텍스트: {text}
- 색상: 단색 (검정 또는 지정 색상)
- 배경: 투명
- 해상도: 4K 고해상도
- 용도: 회사 로고 도장""",

    "handwriting_style": """손글씨 스타일 도장을 만들어주세요.
- 스타일: 자연스러운 손글씨 느낌
- 형태: {shape}
- 텍스트: {text}
- 색상: 검정 또는 빨간색
- 배경: 투명
- 해상도: 4K 고해상도
- 용도: 개인 서명 도장""",

    "company_seal": """회사 직인 스타일 도장을 만들어주세요.
- 스타일: 공식적인 회사 직인
- 형태: 원형 또는 사각형
- 텍스트: {text}
- 테두리: 이중 테두리
- 색상: 빨간색
- 배경: 투명
- 해상도: 4K 고해상도
- 용도: 공식 문서용 직인""",
}


def build_stamp_prompt(
    template_name: str,
    text: str,
    shape: str = "원형",
    additional_instructions: Optional[str] = None,
) -> str:
    """
    도장 프롬프트 생성
    
    Args:
        template_name: 템플릿 이름
        text: 도장에 들어갈 텍스트
        shape: 도장 형태
        additional_instructions: 추가 지시사항
        
    Returns:
        str: 완성된 프롬프트
    """
    template = STAMP_PROMPT_TEMPLATES.get(template_name, STAMP_PROMPT_TEMPLATES["modern_logo"])
    prompt = template.format(text=text, shape=shape)
    
    if additional_instructions:
        prompt += f"\n\n추가 요청사항:\n{additional_instructions}"
    
    return prompt
