"""
Madstamp Automation - 포토샵 BMP 변환 및 출력 모듈

최종 도장 파일을 BMP 형식으로 변환하여 레이저 프린터 출력용으로 준비합니다.

주요 기능:
- AI/EPS/PNG → BMP 변환
- 흑백 1비트 BMP (레이저 프린터 최적화)
- 해상도 조정 (300/600/1200 DPI)
- 프린터 설정 최적화
"""

import asyncio
import logging
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

logger = logging.getLogger(__name__)


class BMPColorDepth(str, Enum):
    """BMP 색상 깊이"""
    MONO_1BIT = "1"         # 1비트 흑백 (레이저 프린터용)
    GRAYSCALE_8BIT = "L"    # 8비트 그레이스케일
    RGB_24BIT = "RGB"       # 24비트 컬러


class PrinterDPI(int, Enum):
    """프린터 DPI 설정"""
    DPI_300 = 300       # 일반 품질
    DPI_600 = 600       # 고품질
    DPI_1200 = 1200     # 최고 품질


@dataclass
class BMPSettings:
    """BMP 변환 설정"""
    color_depth: BMPColorDepth = BMPColorDepth.MONO_1BIT
    dpi: PrinterDPI = PrinterDPI.DPI_600
    target_width_mm: float = 50.0       # 출력 너비 (mm)
    target_height_mm: float = 50.0      # 출력 높이 (mm)
    invert_for_stamp: bool = False      # 도장용 반전 (검정 배경, 흰색 디자인)
    add_margin_mm: float = 2.0          # 여백 (mm)
    maintain_aspect_ratio: bool = True  # 원본 비율 유지


@dataclass
class BMPConversionResult:
    """BMP 변환 결과"""
    success: bool
    input_path: str
    output_path: Optional[str] = None
    original_size: Tuple[int, int] = None
    output_size: Tuple[int, int] = None
    output_size_mm: Tuple[float, float] = None
    dpi: int = 0
    file_size_kb: float = 0.0
    issues: list[str] = field(default_factory=list)
    conversion_log: list[str] = field(default_factory=list)


class PhotoshopScriptGenerator:
    """
    Adobe Photoshop ExtendScript (JSX) 생성기
    
    포토샵 자동화 스크립트를 생성합니다.
    """

    @staticmethod
    def generate_bmp_export_script(
        input_path: str,
        output_path: str,
        settings: BMPSettings,
    ) -> str:
        """BMP 내보내기 스크립트 생성"""
        # 픽셀 크기 계산
        width_px = int(settings.target_width_mm * settings.dpi.value / 25.4)
        height_px = int(settings.target_height_mm * settings.dpi.value / 25.4)
        
        script = f'''
// Madstamp Photoshop BMP Export Script
// Generated automatically

// 파일 열기
var inputFile = new File("{input_path}");
var doc = app.open(inputFile);

// 이미지 크기 조정
doc.resizeImage(
    new UnitValue({width_px}, "px"),
    new UnitValue({height_px}, "px"),
    {settings.dpi.value},
    ResampleMethod.BICUBIC
);

// 모드 변환
'''
        if settings.color_depth == BMPColorDepth.MONO_1BIT:
            script += '''
// 그레이스케일로 변환
doc.changeMode(ChangeMode.GRAYSCALE);

// 비트맵 (1비트)으로 변환
var bitmapOptions = new BitmapConversionOptions();
bitmapOptions.method = BitmapConversionType.HALFTHRESHOLD;
bitmapOptions.resolution = doc.resolution;
doc.changeMode(ChangeMode.BITMAP, bitmapOptions);
'''
        elif settings.color_depth == BMPColorDepth.GRAYSCALE_8BIT:
            script += '''
// 그레이스케일로 변환
doc.changeMode(ChangeMode.GRAYSCALE);
'''
        
        if settings.invert_for_stamp:
            script += '''
// 색상 반전 (도장용)
doc.activeLayer.invert();
'''
        
        script += f'''
// BMP로 저장
var outputFile = new File("{output_path}");
var bmpOptions = new BMPSaveOptions();
bmpOptions.depth = BMPDepthType.BMP_X1;  // 1비트
bmpOptions.osType = OperatingSystem.WINDOWS;
bmpOptions.rleCompression = false;

doc.saveAs(outputFile, bmpOptions, true);

// 문서 닫기
doc.close(SaveOptions.DONOTSAVECHANGES);
'''
        return script

    @staticmethod
    def generate_layer_check_script() -> str:
        """레이어 검토 스크립트"""
        script = '''
// 레이어 구조 검토
function checkLayers() {
    var doc = app.activeDocument;
    var report = "=== 레이어 검토 보고서 ===\\n\\n";
    
    report += "문서 정보:\\n";
    report += "  - 크기: " + doc.width + " x " + doc.height + "\\n";
    report += "  - 해상도: " + doc.resolution + " DPI\\n";
    report += "  - 색상 모드: " + doc.mode + "\\n";
    report += "  - 레이어 수: " + doc.layers.length + "\\n\\n";
    
    report += "레이어 목록:\\n";
    for (var i = 0; i < doc.layers.length; i++) {
        var layer = doc.layers[i];
        report += "  " + (i + 1) + ". " + layer.name;
        report += " [" + (layer.visible ? "표시" : "숨김") + "]";
        report += " [" + (layer.allLocked ? "잠금" : "편집가능") + "]\\n";
    }
    
    return report;
}

alert(checkLayers());
'''
        return script


class BMPConverter:
    """
    BMP 변환기
    
    다양한 형식의 이미지를 레이저 프린터용 BMP로 변환합니다.
    """

    def __init__(
        self,
        output_dir: str = "/home/ubuntu/madstamp_output/bmp",
    ):
        self.output_dir = output_dir
        self.script_generator = PhotoshopScriptGenerator()
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    async def convert_to_bmp(
        self,
        input_path: str,
        settings: BMPSettings = None,
        output_filename: str = None,
    ) -> BMPConversionResult:
        """
        이미지를 BMP로 변환
        
        Args:
            input_path: 입력 파일 경로
            settings: BMP 설정
            output_filename: 출력 파일명
            
        Returns:
            BMPConversionResult: 변환 결과
        """
        if settings is None:
            settings = BMPSettings()
        
        result = BMPConversionResult(
            success=False,
            input_path=input_path,
        )
        
        try:
            # 입력 파일 확인
            if not os.path.exists(input_path):
                result.issues.append(f"입력 파일이 존재하지 않습니다: {input_path}")
                return result
            
            result.conversion_log.append(f"입력 파일: {input_path}")
            
            # 출력 파일명 생성
            if output_filename is None:
                base_name = Path(input_path).stem
                output_filename = f"{base_name}_final.bmp"
            
            output_path = os.path.join(self.output_dir, output_filename)
            
            # 파일 형식에 따른 처리
            ext = Path(input_path).suffix.lower()
            
            if ext in [".ai", ".eps", ".pdf"]:
                # 벡터 파일 → PIL에서 직접 처리 불가, 변환 필요
                result.conversion_log.append("벡터 파일 감지 - Inkscape로 PNG 변환 후 처리")
                png_path = await self._convert_vector_to_png(input_path)
                if png_path:
                    input_path = png_path
                else:
                    result.issues.append("벡터 파일 변환 실패")
                    return result
            
            # PIL로 BMP 변환
            result = await self._convert_with_pil(
                input_path=input_path,
                output_path=output_path,
                settings=settings,
                result=result,
            )
            
        except Exception as e:
            result.issues.append(f"변환 오류: {str(e)}")
            logger.error(f"BMP conversion error: {e}")
        
        return result

    async def _convert_vector_to_png(self, vector_path: str) -> Optional[str]:
        """벡터 파일을 PNG로 변환 (Inkscape 사용)"""
        try:
            png_path = vector_path.rsplit(".", 1)[0] + "_temp.png"
            
            process = await asyncio.create_subprocess_exec(
                "inkscape",
                vector_path,
                "--export-type=png",
                "--export-filename=" + png_path,
                "--export-dpi=600",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            await process.communicate()
            
            if process.returncode == 0 and os.path.exists(png_path):
                return png_path
            
            return None
            
        except Exception as e:
            logger.error(f"Vector to PNG conversion error: {e}")
            return None

    async def _convert_with_pil(
        self,
        input_path: str,
        output_path: str,
        settings: BMPSettings,
        result: BMPConversionResult,
    ) -> BMPConversionResult:
        """PIL을 사용한 BMP 변환"""
        try:
            # 이미지 로드
            img = Image.open(input_path)
            result.original_size = img.size
            result.conversion_log.append(f"원본 크기: {img.size}, 모드: {img.mode}")
            
            # 픽셀 크기 계산 (mm → px)
            target_width_px = int(settings.target_width_mm * settings.dpi.value / 25.4)
            target_height_px = int(settings.target_height_mm * settings.dpi.value / 25.4)
            
            # 여백 추가
            margin_px = int(settings.add_margin_mm * settings.dpi.value / 25.4)
            target_width_px += margin_px * 2
            target_height_px += margin_px * 2
            
            # 크기 조정 (비율 유지)
            if settings.maintain_aspect_ratio:
                img.thumbnail(
                    (target_width_px, target_height_px),
                    Image.Resampling.LANCZOS,
                )
                
                # 캔버스 생성 (여백 포함)
                canvas = Image.new("RGB", (target_width_px, target_height_px), (255, 255, 255))
                
                # 중앙 배치
                x = (target_width_px - img.size[0]) // 2
                y = (target_height_px - img.size[1]) // 2
                
                if img.mode == "RGBA":
                    canvas.paste(img, (x, y), img.split()[-1])
                else:
                    canvas.paste(img, (x, y))
                
                img = canvas
            else:
                img = img.resize(
                    (target_width_px, target_height_px),
                    Image.Resampling.LANCZOS,
                )
            
            result.conversion_log.append(f"크기 조정: {img.size}")
            
            # 색상 모드 변환
            if settings.color_depth == BMPColorDepth.MONO_1BIT:
                # 그레이스케일 변환
                if img.mode != "L":
                    img = img.convert("L")
                
                # 이진화 (1비트)
                threshold = 128
                img = img.point(lambda x: 255 if x > threshold else 0, "1")
                result.conversion_log.append("1비트 흑백 변환 완료")
                
            elif settings.color_depth == BMPColorDepth.GRAYSCALE_8BIT:
                if img.mode != "L":
                    img = img.convert("L")
                result.conversion_log.append("8비트 그레이스케일 변환 완료")
            
            # 도장용 반전
            if settings.invert_for_stamp:
                from PIL import ImageOps
                img = ImageOps.invert(img.convert("L"))
                if settings.color_depth == BMPColorDepth.MONO_1BIT:
                    img = img.convert("1")
                result.conversion_log.append("색상 반전 완료")
            
            # BMP 저장
            img.save(output_path, "BMP", dpi=(settings.dpi.value, settings.dpi.value))
            
            # 결과 정보
            result.output_path = output_path
            result.output_size = img.size
            result.output_size_mm = (
                img.size[0] * 25.4 / settings.dpi.value,
                img.size[1] * 25.4 / settings.dpi.value,
            )
            result.dpi = settings.dpi.value
            result.file_size_kb = os.path.getsize(output_path) / 1024
            result.success = True
            result.conversion_log.append(f"저장 완료: {output_path}")
            result.conversion_log.append(f"파일 크기: {result.file_size_kb:.1f} KB")
            
        except Exception as e:
            result.issues.append(f"PIL 변환 오류: {str(e)}")
            logger.error(f"PIL conversion error: {e}")
        
        return result

    def generate_photoshop_script(
        self,
        input_path: str,
        output_path: str,
        settings: BMPSettings = None,
    ) -> str:
        """포토샵 자동화 스크립트 생성"""
        if settings is None:
            settings = BMPSettings()
        
        return self.script_generator.generate_bmp_export_script(
            input_path=input_path,
            output_path=output_path,
            settings=settings,
        )

    def save_photoshop_script(
        self,
        script: str,
        script_name: str,
    ) -> str:
        """포토샵 스크립트 저장"""
        scripts_dir = os.path.join(os.path.dirname(self.output_dir), "scripts", "jsx")
        Path(scripts_dir).mkdir(parents=True, exist_ok=True)
        
        script_path = os.path.join(scripts_dir, script_name)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)
        
        return script_path


class PrinterManager:
    """
    프린터 관리자
    
    레이저 프린터 출력을 관리합니다.
    """

    def __init__(self):
        self.default_printer = None

    async def list_printers(self) -> list[str]:
        """사용 가능한 프린터 목록"""
        try:
            # Linux: lpstat 사용
            process = await asyncio.create_subprocess_exec(
                "lpstat", "-p",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            
            printers = []
            for line in stdout.decode().split("\n"):
                if line.startswith("printer"):
                    parts = line.split()
                    if len(parts) >= 2:
                        printers.append(parts[1])
            
            return printers
            
        except Exception as e:
            logger.error(f"Failed to list printers: {e}")
            return []

    async def print_bmp(
        self,
        bmp_path: str,
        printer_name: str = None,
        copies: int = 1,
    ) -> bool:
        """
        BMP 파일 출력
        
        Args:
            bmp_path: BMP 파일 경로
            printer_name: 프린터 이름 (None이면 기본 프린터)
            copies: 출력 매수
            
        Returns:
            bool: 출력 성공 여부
        """
        try:
            cmd = ["lp"]
            
            if printer_name:
                cmd.extend(["-d", printer_name])
            
            cmd.extend(["-n", str(copies)])
            cmd.append(bmp_path)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"Print job submitted: {bmp_path}")
                return True
            else:
                logger.error(f"Print failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Print error: {e}")
            return False


@dataclass
class FinalOutputPackage:
    """최종 출력 패키지"""
    order_id: str
    customer_name: str
    original_file: str
    processed_file: str
    bmp_file: str
    ai_file: Optional[str] = None
    eps_file: Optional[str] = None
    print_ready: bool = False
    quality_approved: bool = False
    notes: str = ""


class FinalOutputManager:
    """
    최종 출력 관리자
    
    도장 제작의 최종 단계를 관리합니다.
    """

    def __init__(
        self,
        output_dir: str = "/home/ubuntu/madstamp_output/final",
    ):
        self.output_dir = output_dir
        self.bmp_converter = BMPConverter()
        self.printer = PrinterManager()
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    async def prepare_final_output(
        self,
        order_id: str,
        customer_name: str,
        processed_image_path: str,
        ai_file_path: str = None,
        stamp_size_mm: float = 50.0,
    ) -> FinalOutputPackage:
        """
        최종 출력 준비
        
        Args:
            order_id: 주문 ID
            customer_name: 고객명
            processed_image_path: 처리된 이미지 경로
            ai_file_path: AI 파일 경로 (선택)
            stamp_size_mm: 도장 크기 (mm)
            
        Returns:
            FinalOutputPackage: 최종 출력 패키지
        """
        package = FinalOutputPackage(
            order_id=order_id,
            customer_name=customer_name,
            original_file="",
            processed_file=processed_image_path,
            bmp_file="",
        )
        
        # BMP 변환 설정
        settings = BMPSettings(
            color_depth=BMPColorDepth.MONO_1BIT,
            dpi=PrinterDPI.DPI_600,
            target_width_mm=stamp_size_mm,
            target_height_mm=stamp_size_mm,
            maintain_aspect_ratio=True,
        )
        
        # BMP 변환
        bmp_filename = f"{order_id}_{customer_name}_final.bmp"
        result = await self.bmp_converter.convert_to_bmp(
            input_path=processed_image_path,
            settings=settings,
            output_filename=bmp_filename,
        )
        
        if result.success:
            package.bmp_file = result.output_path
            package.print_ready = True
            
            # AI 파일 복사 (있는 경우)
            if ai_file_path and os.path.exists(ai_file_path):
                import shutil
                ai_dest = os.path.join(
                    self.output_dir,
                    f"{order_id}_{customer_name}_final.ai"
                )
                shutil.copy2(ai_file_path, ai_dest)
                package.ai_file = ai_dest
        else:
            package.notes = "BMP 변환 실패: " + ", ".join(result.issues)
        
        return package

    async def print_final(
        self,
        package: FinalOutputPackage,
        copies: int = 1,
    ) -> bool:
        """최종 출력"""
        if not package.print_ready:
            logger.error("Package is not ready for printing")
            return False
        
        if not package.quality_approved:
            logger.warning("Quality not approved - proceeding anyway")
        
        return await self.printer.print_bmp(
            bmp_path=package.bmp_file,
            copies=copies,
        )


# 편의 함수
async def convert_to_final_bmp(
    input_path: str,
    stamp_size_mm: float = 50.0,
    dpi: int = 600,
) -> BMPConversionResult:
    """최종 BMP 변환 헬퍼 함수"""
    converter = BMPConverter()
    settings = BMPSettings(
        color_depth=BMPColorDepth.MONO_1BIT,
        dpi=PrinterDPI(dpi) if dpi in [300, 600, 1200] else PrinterDPI.DPI_600,
        target_width_mm=stamp_size_mm,
        target_height_mm=stamp_size_mm,
    )
    return await converter.convert_to_bmp(input_path, settings)
