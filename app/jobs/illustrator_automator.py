"""
Madstamp Automation - Adobe Illustrator 자동화 모듈

일러스트레이터 작업 자동화:
- 대지에 이미지 배치
- 폰트 타이핑 및 배열
- 레이어 관리
- 펜툴 선 처리 (도장 적합화)
- 색상 비우기 (흑백 변환)

Note: 실제 일러스트레이터 자동화는 다음 방법 중 하나를 사용합니다:
1. Adobe ExtendScript (JSX) - 일러스트레이터 내장 스크립팅
2. AppleScript (macOS) - 시스템 레벨 자동화
3. Python + subprocess - JSX 스크립트 실행
"""

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class StampShape(str, Enum):
    """도장 형태"""
    CIRCLE = "circle"           # 원형
    SQUARE = "square"           # 사각형
    RECTANGLE = "rectangle"     # 직사각형
    OVAL = "oval"               # 타원형
    CUSTOM = "custom"           # 사용자 정의


class LayerType(str, Enum):
    """레이어 타입"""
    BACKGROUND = "배경"
    BORDER = "테두리"
    MAIN_IMAGE = "메인이미지"
    TEXT_PRIMARY = "주텍스트"
    TEXT_SECONDARY = "부텍스트"
    DECORATION = "장식"
    FINAL_OUTPUT = "최종출력"


@dataclass
class ArtboardSettings:
    """대지 설정"""
    width_mm: float = 50.0      # 대지 너비 (mm)
    height_mm: float = 50.0     # 대지 높이 (mm)
    bleed_mm: float = 3.0       # 도련 (mm)
    color_mode: str = "CMYK"    # 색상 모드


@dataclass
class TextElement:
    """텍스트 요소"""
    content: str
    font_name: str = "NotoSansKR-Regular"
    font_size: float = 12.0     # pt
    position_x: float = 0.0     # mm (대지 중심 기준)
    position_y: float = 0.0     # mm
    color: str = "#000000"      # 흑백이므로 검정
    tracking: int = 0           # 자간
    leading: float = None       # 행간 (None이면 자동)
    alignment: str = "center"   # left, center, right


@dataclass
class ImageElement:
    """이미지 요소"""
    file_path: str
    position_x: float = 0.0     # mm
    position_y: float = 0.0     # mm
    width: float = None         # mm (None이면 원본 비율 유지)
    height: float = None        # mm
    fit_to_artboard: bool = True
    maintain_aspect_ratio: bool = True  # 원본 비율 유지 필수


@dataclass
class StampDesign:
    """도장 디자인 설정"""
    shape: StampShape = StampShape.CIRCLE
    artboard: ArtboardSettings = field(default_factory=ArtboardSettings)
    border_width: float = 2.0   # 테두리 두께 (pt)
    images: list[ImageElement] = field(default_factory=list)
    texts: list[TextElement] = field(default_factory=list)
    layers: list[LayerType] = field(default_factory=lambda: [
        LayerType.BACKGROUND,
        LayerType.BORDER,
        LayerType.MAIN_IMAGE,
        LayerType.TEXT_PRIMARY,
        LayerType.TEXT_SECONDARY,
        LayerType.DECORATION,
        LayerType.FINAL_OUTPUT,
    ])


class IllustratorScriptGenerator:
    """
    Adobe Illustrator JSX 스크립트 생성기
    
    ExtendScript (JSX)를 생성하여 일러스트레이터 자동화를 수행합니다.
    """

    @staticmethod
    def generate_setup_script(design: StampDesign) -> str:
        """초기 설정 스크립트 생성"""
        width_pt = design.artboard.width_mm * 2.834645669  # mm to pt
        height_pt = design.artboard.height_mm * 2.834645669
        
        script = f'''
// Madstamp Illustrator Automation Script
// Generated automatically - DO NOT EDIT MANUALLY

// 새 문서 생성
var docPreset = new DocumentPreset();
docPreset.width = {width_pt};
docPreset.height = {height_pt};
docPreset.colorMode = DocumentColorSpace.CMYK;
docPreset.units = RulerUnits.Millimeters;

var doc = app.documents.addDocument("Print", docPreset);

// 레이어 생성
var layerNames = {json.dumps([layer.value for layer in design.layers], ensure_ascii=False)};
for (var i = layerNames.length - 1; i >= 0; i--) {{
    var layer = doc.layers.add();
    layer.name = layerNames[i];
}}

// 기본 레이어 삭제
if (doc.layers.length > layerNames.length) {{
    doc.layers[doc.layers.length - 1].remove();
}}
'''
        return script

    @staticmethod
    def generate_border_script(design: StampDesign) -> str:
        """테두리 생성 스크립트"""
        width_pt = design.artboard.width_mm * 2.834645669
        height_pt = design.artboard.height_mm * 2.834645669
        center_x = width_pt / 2
        center_y = height_pt / 2
        
        if design.shape == StampShape.CIRCLE:
            radius = min(width_pt, height_pt) / 2 - design.border_width
            script = f'''
// 원형 테두리 생성
var borderLayer = doc.layers.getByName("테두리");
var ellipse = borderLayer.pathItems.ellipse(
    {center_y + radius}, // top
    {center_x - radius}, // left
    {radius * 2}, // width
    {radius * 2}  // height
);
ellipse.filled = false;
ellipse.stroked = true;
ellipse.strokeWidth = {design.border_width};
ellipse.strokeColor = new CMYKColor();
ellipse.strokeColor.cyan = 0;
ellipse.strokeColor.magenta = 0;
ellipse.strokeColor.yellow = 0;
ellipse.strokeColor.black = 100;
'''
        elif design.shape == StampShape.SQUARE:
            size = min(width_pt, height_pt) - design.border_width * 2
            script = f'''
// 사각형 테두리 생성
var borderLayer = doc.layers.getByName("테두리");
var rect = borderLayer.pathItems.rectangle(
    {center_y + size/2}, // top
    {center_x - size/2}, // left
    {size}, // width
    {size}  // height
);
rect.filled = false;
rect.stroked = true;
rect.strokeWidth = {design.border_width};
rect.strokeColor = new CMYKColor();
rect.strokeColor.cyan = 0;
rect.strokeColor.magenta = 0;
rect.strokeColor.yellow = 0;
rect.strokeColor.black = 100;
'''
        else:
            script = "// Custom shape - manual creation required\n"
        
        return script

    @staticmethod
    def generate_image_placement_script(image: ImageElement, layer_name: str = "메인이미지") -> str:
        """이미지 배치 스크립트"""
        script = f'''
// 이미지 배치
var imageLayer = doc.layers.getByName("{layer_name}");
var imageFile = new File("{image.file_path}");

if (imageFile.exists) {{
    var placedItem = imageLayer.placedItems.add();
    placedItem.file = imageFile;
    
    // 원본 비율 유지하며 배치
    var originalWidth = placedItem.width;
    var originalHeight = placedItem.height;
    var aspectRatio = originalWidth / originalHeight;
    
'''
        if image.fit_to_artboard:
            script += f'''
    // 대지에 맞춤 (비율 유지)
    var artboardWidth = doc.artboards[0].artboardRect[2] - doc.artboards[0].artboardRect[0];
    var artboardHeight = doc.artboards[0].artboardRect[1] - doc.artboards[0].artboardRect[3];
    
    var targetWidth, targetHeight;
    if (artboardWidth / artboardHeight > aspectRatio) {{
        targetHeight = artboardHeight * 0.8;
        targetWidth = targetHeight * aspectRatio;
    }} else {{
        targetWidth = artboardWidth * 0.8;
        targetHeight = targetWidth / aspectRatio;
    }}
    
    placedItem.width = targetWidth;
    placedItem.height = targetHeight;
    
    // 중앙 정렬
    placedItem.position = [
        (artboardWidth - targetWidth) / 2,
        -(artboardHeight - targetHeight) / 2 + artboardHeight
    ];
'''
        else:
            script += f'''
    // 지정된 위치에 배치
    placedItem.position = [{image.position_x * 2.834645669}, {image.position_y * 2.834645669}];
'''
        
        script += '''
    // 임베드 (링크 해제)
    placedItem.embed();
} else {
    alert("이미지 파일을 찾을 수 없습니다: " + imageFile.fsName);
}
'''
        return script

    @staticmethod
    def generate_text_script(text: TextElement, layer_name: str = "주텍스트") -> str:
        """텍스트 생성 스크립트"""
        script = f'''
// 텍스트 생성
var textLayer = doc.layers.getByName("{layer_name}");
var textFrame = textLayer.textFrames.add();
textFrame.contents = "{text.content}";

// 텍스트 속성 설정
var textRange = textFrame.textRange;
textRange.characterAttributes.size = {text.font_size};
textRange.characterAttributes.tracking = {text.tracking};

// 폰트 설정
try {{
    textRange.characterAttributes.textFont = app.textFonts.getByName("{text.font_name}");
}} catch (e) {{
    // 폰트가 없으면 기본 폰트 사용
    alert("폰트를 찾을 수 없습니다: {text.font_name}. 기본 폰트를 사용합니다.");
}}

// 색상 설정 (흑백)
var blackColor = new CMYKColor();
blackColor.cyan = 0;
blackColor.magenta = 0;
blackColor.yellow = 0;
blackColor.black = 100;
textRange.characterAttributes.fillColor = blackColor;

// 위치 설정
var artboardWidth = doc.artboards[0].artboardRect[2] - doc.artboards[0].artboardRect[0];
var artboardHeight = doc.artboards[0].artboardRect[1] - doc.artboards[0].artboardRect[3];
textFrame.position = [
    (artboardWidth - textFrame.width) / 2 + {text.position_x * 2.834645669},
    artboardHeight / 2 + {text.position_y * 2.834645669}
];
'''
        return script

    @staticmethod
    def generate_trace_to_vector_script() -> str:
        """이미지를 벡터로 트레이스하는 스크립트"""
        script = '''
// 이미지 트레이스 (벡터화)
function traceImageToVector(placedItem) {
    // 이미지 트레이스 설정
    var traceOptions = new ImageTraceOptions();
    traceOptions.preset = "Black and White Logo";  // 흑백 로고 프리셋
    traceOptions.threshold = 128;
    traceOptions.cornerAngle = 20;
    traceOptions.pathFitting = 2;
    traceOptions.ignoreWhite = true;
    
    // 트레이스 실행
    var traceObject = placedItem.trace();
    traceObject.tracing.tracingOptions = traceOptions;
    
    // 확장 (벡터 패스로 변환)
    traceObject.tracing.expandTracing();
    
    return traceObject;
}

// 선택된 이미지 트레이스
if (doc.selection.length > 0) {
    for (var i = 0; i < doc.selection.length; i++) {
        if (doc.selection[i].typename == "PlacedItem") {
            traceImageToVector(doc.selection[i]);
        }
    }
}
'''
        return script

    @staticmethod
    def generate_convert_to_bw_script() -> str:
        """흑백 변환 스크립트"""
        script = '''
// 모든 요소를 흑백으로 변환
function convertToBW() {
    var blackColor = new CMYKColor();
    blackColor.cyan = 0;
    blackColor.magenta = 0;
    blackColor.yellow = 0;
    blackColor.black = 100;
    
    var whiteColor = new CMYKColor();
    whiteColor.cyan = 0;
    whiteColor.magenta = 0;
    whiteColor.yellow = 0;
    whiteColor.black = 0;
    
    // 모든 패스 아이템 처리
    for (var i = 0; i < doc.pathItems.length; i++) {
        var item = doc.pathItems[i];
        
        // 채우기 색상 변환
        if (item.filled) {
            var fillBrightness = getColorBrightness(item.fillColor);
            if (fillBrightness < 128) {
                item.fillColor = blackColor;
            } else {
                item.fillColor = whiteColor;
            }
        }
        
        // 선 색상 변환
        if (item.stroked) {
            item.strokeColor = blackColor;
        }
    }
    
    // 모든 텍스트 프레임 처리
    for (var i = 0; i < doc.textFrames.length; i++) {
        var textFrame = doc.textFrames[i];
        var textRange = textFrame.textRange;
        textRange.characterAttributes.fillColor = blackColor;
    }
}

// 색상 밝기 계산
function getColorBrightness(color) {
    if (color.typename == "CMYKColor") {
        return 255 - (color.black * 2.55);
    } else if (color.typename == "RGBColor") {
        return (color.red + color.green + color.blue) / 3;
    }
    return 128;
}

convertToBW();
'''
        return script

    @staticmethod
    def generate_export_script(output_path: str, format: str = "ai") -> str:
        """파일 내보내기 스크립트"""
        if format.lower() == "ai":
            script = f'''
// AI 파일로 저장
var saveFile = new File("{output_path}");
var saveOptions = new IllustratorSaveOptions();
saveOptions.compatibility = Compatibility.ILLUSTRATOR24;  // CC 2020
saveOptions.embedICCProfile = true;
saveOptions.embedLinkedFiles = true;

doc.saveAs(saveFile, saveOptions);
'''
        elif format.lower() == "eps":
            script = f'''
// EPS 파일로 저장
var saveFile = new File("{output_path}");
var saveOptions = new EPSSaveOptions();
saveOptions.compatibility = Compatibility.ILLUSTRATOR24;
saveOptions.embedAllFonts = true;
saveOptions.includeDocumentThumbnails = true;

doc.saveAs(saveFile, saveOptions);
'''
        elif format.lower() == "pdf":
            script = f'''
// PDF 파일로 저장
var saveFile = new File("{output_path}");
var saveOptions = new PDFSaveOptions();
saveOptions.compatibility = PDFCompatibility.ACROBAT7;
saveOptions.preserveEditability = true;

doc.saveAs(saveFile, saveOptions);
'''
        else:
            script = f'// Unsupported format: {format}\n'
        
        return script

    @staticmethod
    def generate_layer_check_script() -> str:
        """레이어 검토 스크립트"""
        script = '''
// 레이어 구조 검토
function checkLayers() {
    var report = "=== 레이어 검토 보고서 ===\\n\\n";
    
    for (var i = 0; i < doc.layers.length; i++) {
        var layer = doc.layers[i];
        report += "레이어: " + layer.name + "\\n";
        report += "  - 가시성: " + (layer.visible ? "표시" : "숨김") + "\\n";
        report += "  - 잠금: " + (layer.locked ? "잠금" : "해제") + "\\n";
        report += "  - 패스 아이템: " + layer.pathItems.length + "개\\n";
        report += "  - 텍스트 프레임: " + layer.textFrames.length + "개\\n";
        report += "  - 배치된 이미지: " + layer.placedItems.length + "개\\n";
        report += "\\n";
    }
    
    return report;
}

var layerReport = checkLayers();
alert(layerReport);
'''
        return script


class IllustratorAutomator:
    """
    Adobe Illustrator 자동화 관리자
    
    JSX 스크립트를 생성하고 실행합니다.
    """

    def __init__(
        self,
        scripts_dir: str = "/home/ubuntu/madstamp-automation/scripts/jsx",
        output_dir: str = "/home/ubuntu/madstamp_output",
    ):
        self.scripts_dir = scripts_dir
        self.output_dir = output_dir
        self.generator = IllustratorScriptGenerator()
        
        # 디렉토리 생성
        Path(scripts_dir).mkdir(parents=True, exist_ok=True)
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    def create_stamp_design(
        self,
        shape: StampShape = StampShape.CIRCLE,
        width_mm: float = 50.0,
        height_mm: float = 50.0,
    ) -> StampDesign:
        """도장 디자인 설정 생성"""
        artboard = ArtboardSettings(
            width_mm=width_mm,
            height_mm=height_mm,
        )
        return StampDesign(shape=shape, artboard=artboard)

    def add_image_to_design(
        self,
        design: StampDesign,
        image_path: str,
        fit_to_artboard: bool = True,
    ) -> StampDesign:
        """디자인에 이미지 추가"""
        image = ImageElement(
            file_path=image_path,
            fit_to_artboard=fit_to_artboard,
            maintain_aspect_ratio=True,  # 항상 원본 비율 유지
        )
        design.images.append(image)
        return design

    def add_text_to_design(
        self,
        design: StampDesign,
        content: str,
        font_name: str = "NotoSansKR-Regular",
        font_size: float = 12.0,
        position_y: float = 0.0,
    ) -> StampDesign:
        """디자인에 텍스트 추가"""
        text = TextElement(
            content=content,
            font_name=font_name,
            font_size=font_size,
            position_y=position_y,
        )
        design.texts.append(text)
        return design

    def generate_full_script(
        self,
        design: StampDesign,
        output_filename: str,
        output_format: str = "ai",
    ) -> str:
        """전체 자동화 스크립트 생성"""
        output_path = os.path.join(self.output_dir, output_filename)
        
        script_parts = [
            "// ========================================",
            "// Madstamp Illustrator Automation Script",
            "// Generated: " + str(asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else "N/A"),
            "// ========================================",
            "",
            self.generator.generate_setup_script(design),
            self.generator.generate_border_script(design),
        ]
        
        # 이미지 배치
        for i, image in enumerate(design.images):
            layer_name = "메인이미지" if i == 0 else f"이미지_{i+1}"
            script_parts.append(self.generator.generate_image_placement_script(image, layer_name))
        
        # 텍스트 배치
        for i, text in enumerate(design.texts):
            layer_name = "주텍스트" if i == 0 else "부텍스트"
            script_parts.append(self.generator.generate_text_script(text, layer_name))
        
        # 흑백 변환
        script_parts.append(self.generator.generate_convert_to_bw_script())
        
        # 레이어 검토
        script_parts.append(self.generator.generate_layer_check_script())
        
        # 저장
        script_parts.append(self.generator.generate_export_script(output_path, output_format))
        
        return "\n".join(script_parts)

    def save_script(self, script: str, script_name: str) -> str:
        """스크립트 파일 저장"""
        script_path = os.path.join(self.scripts_dir, script_name)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)
        logger.info(f"Script saved: {script_path}")
        return script_path

    async def execute_script_macos(self, script_path: str) -> bool:
        """
        macOS에서 AppleScript를 통해 JSX 실행
        
        Note: 이 함수는 macOS에서만 작동합니다.
        """
        applescript = f'''
tell application "Adobe Illustrator"
    activate
    do javascript file "{script_path}"
end tell
'''
        try:
            process = await asyncio.create_subprocess_exec(
                "osascript", "-e", applescript,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info("Script executed successfully")
                return True
            else:
                logger.error(f"Script execution failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to execute script: {e}")
            return False

    def get_manual_instructions(self, script_path: str) -> str:
        """수동 실행 안내"""
        return f"""
=== Adobe Illustrator 스크립트 수동 실행 안내 ===

1. Adobe Illustrator를 실행합니다.
2. 메뉴에서 [파일] > [스크립트] > [기타 스크립트...]를 선택합니다.
3. 다음 파일을 선택합니다:
   {script_path}
4. 스크립트가 자동으로 실행됩니다.

또는 ExtendScript Toolkit에서 직접 실행할 수 있습니다.
"""


# 편의 함수
async def create_stamp_from_image(
    image_path: str,
    customer_name: str,
    text_content: str = None,
    shape: StampShape = StampShape.CIRCLE,
    size_mm: float = 50.0,
    output_format: str = "ai",
) -> dict:
    """
    이미지로부터 도장 디자인 생성
    
    Args:
        image_path: 원본 이미지 경로
        customer_name: 고객명
        text_content: 추가할 텍스트 (선택)
        shape: 도장 형태
        size_mm: 도장 크기 (mm)
        output_format: 출력 형식 (ai, eps, pdf)
        
    Returns:
        dict: 생성 결과 (script_path, output_path, instructions)
    """
    automator = IllustratorAutomator()
    
    # 디자인 생성
    design = automator.create_stamp_design(
        shape=shape,
        width_mm=size_mm,
        height_mm=size_mm,
    )
    
    # 이미지 추가
    design = automator.add_image_to_design(design, image_path)
    
    # 텍스트 추가 (있는 경우)
    if text_content:
        design = automator.add_text_to_design(
            design,
            content=text_content,
            font_name="NotoSansKR-Bold",
            font_size=10.0,
            position_y=-15.0,  # 이미지 아래
        )
    
    # 스크립트 생성
    output_filename = f"{customer_name}_stamp.{output_format}"
    script = automator.generate_full_script(design, output_filename, output_format)
    
    # 스크립트 저장
    script_name = f"{customer_name}_stamp_script.jsx"
    script_path = automator.save_script(script, script_name)
    
    return {
        "script_path": script_path,
        "output_path": os.path.join(automator.output_dir, output_filename),
        "instructions": automator.get_manual_instructions(script_path),
    }
