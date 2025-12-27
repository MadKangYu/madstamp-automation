"""
Madstamp Automation - 벡터 변환 모듈

생성된 PNG 이미지를 EPS/AI 벡터 형식으로 변환합니다.
Potrace와 Inkscape를 사용합니다.
"""

import asyncio
import logging
import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)


class ConversionStatus(str, Enum):
    """변환 상태"""
    PENDING = "pending"
    PREPROCESSING = "preprocessing"
    TRACING = "tracing"
    CONVERTING = "converting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class VectorConversionResult:
    """벡터 변환 결과"""
    status: ConversionStatus
    input_path: str
    svg_path: Optional[str] = None
    eps_path: Optional[str] = None
    ai_path: Optional[str] = None
    error_message: Optional[str] = None


class VectorConverter:
    """
    벡터 변환기
    
    PNG 이미지를 SVG, EPS, AI 형식으로 변환합니다.
    """

    def __init__(self, output_dir: str = "/tmp/vector_output"):
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    async def convert(
        self,
        input_path: str,
        output_formats: list[str] = ["svg", "eps"],
        threshold: int = 128,
        turdsize: int = 2,
        alphamax: float = 1.0,
    ) -> VectorConversionResult:
        """
        이미지를 벡터 형식으로 변환합니다.
        
        Args:
            input_path: 입력 이미지 경로
            output_formats: 출력 형식 목록 (svg, eps, ai)
            threshold: 이진화 임계값 (0-255)
            turdsize: 노이즈 제거 크기
            alphamax: 코너 임계값
            
        Returns:
            VectorConversionResult: 변환 결과
        """
        if not Path(input_path).exists():
            return VectorConversionResult(
                status=ConversionStatus.FAILED,
                input_path=input_path,
                error_message=f"입력 파일을 찾을 수 없습니다: {input_path}",
            )

        try:
            # 1. 전처리: BMP로 변환 (Potrace 입력용)
            logger.info(f"Preprocessing image: {input_path}")
            bmp_path = await self._preprocess_image(input_path, threshold)

            # 2. Potrace로 SVG 변환
            logger.info("Converting to SVG with Potrace...")
            svg_path = await self._trace_to_svg(
                bmp_path,
                turdsize=turdsize,
                alphamax=alphamax,
            )

            result = VectorConversionResult(
                status=ConversionStatus.COMPLETED,
                input_path=input_path,
                svg_path=svg_path,
            )

            # 3. EPS 변환 (요청된 경우)
            if "eps" in output_formats and svg_path:
                logger.info("Converting to EPS...")
                eps_path = await self._convert_svg_to_eps(svg_path)
                result.eps_path = eps_path

            # 4. AI 변환 (요청된 경우)
            if "ai" in output_formats and svg_path:
                logger.info("Converting to AI...")
                ai_path = await self._convert_svg_to_ai(svg_path)
                result.ai_path = ai_path

            # 임시 BMP 파일 삭제
            if Path(bmp_path).exists():
                os.remove(bmp_path)

            return result

        except Exception as e:
            logger.error(f"Vector conversion failed: {e}")
            return VectorConversionResult(
                status=ConversionStatus.FAILED,
                input_path=input_path,
                error_message=str(e),
            )

    async def _preprocess_image(
        self,
        input_path: str,
        threshold: int = 128,
    ) -> str:
        """이미지 전처리 (BMP 변환)"""
        # PIL로 이미지 로드
        img = Image.open(input_path)

        # RGBA → RGB 변환 (알파 채널 제거)
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # 그레이스케일 변환
        img = img.convert("L")

        # 이진화 (흑백)
        img = img.point(lambda x: 0 if x < threshold else 255, "1")

        # BMP로 저장
        base_name = Path(input_path).stem
        bmp_path = os.path.join(self.output_dir, f"{base_name}.bmp")
        img.save(bmp_path, "BMP")

        return bmp_path

    async def _trace_to_svg(
        self,
        bmp_path: str,
        turdsize: int = 2,
        alphamax: float = 1.0,
    ) -> str:
        """Potrace로 SVG 변환"""
        base_name = Path(bmp_path).stem
        svg_path = os.path.join(self.output_dir, f"{base_name}.svg")

        # Potrace 명령 실행
        cmd = [
            "potrace",
            bmp_path,
            "-s",  # SVG 출력
            "-o", svg_path,
            "-t", str(turdsize),  # 노이즈 제거
            "-a", str(alphamax),  # 코너 임계값
            "--flat",  # 평면화
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            # Potrace가 없으면 대체 방법 시도
            logger.warning(f"Potrace failed: {stderr.decode()}")
            return await self._trace_with_inkscape(bmp_path, svg_path)

        return svg_path

    async def _trace_with_inkscape(
        self,
        input_path: str,
        svg_path: str,
    ) -> str:
        """Inkscape로 벡터 트레이싱 (대체 방법)"""
        # PNG로 변환 (Inkscape 입력용)
        img = Image.open(input_path)
        png_path = input_path.replace(".bmp", ".png")
        img.save(png_path, "PNG")

        cmd = [
            "inkscape",
            png_path,
            "--export-filename=" + svg_path,
            "--export-type=svg",
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()

        # 임시 PNG 삭제
        if Path(png_path).exists():
            os.remove(png_path)

        return svg_path

    async def _convert_svg_to_eps(self, svg_path: str) -> Optional[str]:
        """SVG를 EPS로 변환"""
        base_name = Path(svg_path).stem
        eps_path = os.path.join(self.output_dir, f"{base_name}.eps")

        # Inkscape 사용
        cmd = [
            "inkscape",
            svg_path,
            "--export-filename=" + eps_path,
            "--export-type=eps",
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0 and Path(eps_path).exists():
                return eps_path
            else:
                logger.warning(f"EPS conversion failed: {stderr.decode()}")
                return None

        except FileNotFoundError:
            logger.warning("Inkscape not found, skipping EPS conversion")
            return None

    async def _convert_svg_to_ai(self, svg_path: str) -> Optional[str]:
        """SVG를 AI로 변환 (PDF 기반)"""
        # AI 형식은 Adobe 독점이므로, PDF로 변환 후 .ai 확장자 사용
        # (대부분의 디자인 소프트웨어에서 호환됨)
        base_name = Path(svg_path).stem
        ai_path = os.path.join(self.output_dir, f"{base_name}.ai")

        # Inkscape로 PDF 변환 후 AI로 저장
        cmd = [
            "inkscape",
            svg_path,
            "--export-filename=" + ai_path,
            "--export-type=pdf",
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0 and Path(ai_path).exists():
                return ai_path
            else:
                logger.warning(f"AI conversion failed: {stderr.decode()}")
                return None

        except FileNotFoundError:
            logger.warning("Inkscape not found, skipping AI conversion")
            return None


async def convert_to_vector(
    input_path: str,
    output_formats: list[str] = ["svg", "eps"],
    output_dir: Optional[str] = None,
) -> VectorConversionResult:
    """
    벡터 변환 헬퍼 함수
    
    Args:
        input_path: 입력 이미지 경로
        output_formats: 출력 형식 목록
        output_dir: 출력 디렉토리
        
    Returns:
        VectorConversionResult: 변환 결과
    """
    converter = VectorConverter(
        output_dir=output_dir or "/tmp/vector_output"
    )
    return await converter.convert(
        input_path=input_path,
        output_formats=output_formats,
    )


async def check_dependencies() -> dict[str, bool]:
    """벡터 변환 의존성 확인"""
    dependencies = {
        "potrace": False,
        "inkscape": False,
    }

    for tool in dependencies:
        try:
            process = await asyncio.create_subprocess_exec(
                tool, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            dependencies[tool] = process.returncode == 0
        except FileNotFoundError:
            dependencies[tool] = False

    return dependencies
