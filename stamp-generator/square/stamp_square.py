#!/usr/bin/env python3
"""
Madstamp 정사각형 도장 생성기
=============================

지원 글자 수: 4~20글자
- 4글자: 2x2 격자
- 5글자: 2+3 또는 3+2
- 6글자: 3+3 또는 2+2+2
- ...
- 20글자: 5+5+5+5

배치 규칙:
- 글자 수에 따라 행/열 자동 결정
- 각 행은 중심선 기준 좌우 대칭
- 글자 간격: 거의 붙을 듯
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math


class SquareStampGenerator:
    
    def __init__(self, size=1024):
        self.size = size
        self.cx = size // 2
        self.cy = size // 2
        
        self.fonts = {
            'noto_serif': '/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc',
            'noto_sans': '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
        }
        
        self.stamp_color = (200, 30, 30)
        self.bg_color = (255, 255, 255, 0)
        
        self.output_dir = './output'
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_font(self, font_name, font_size):
        font_path = self.fonts.get(font_name)
        if font_path and os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, font_size)
            except:
                pass
        return ImageFont.load_default()
    
    def get_layout(self, char_count):
        """
        글자 수에 따른 행/열 배치 결정
        반환: [(row1_count), (row2_count), ...]
        """
        layouts = {
            4: [2, 2],           # 2+2
            5: [2, 3],           # 2+3
            6: [3, 3],           # 3+3
            7: [3, 4],           # 3+4
            8: [4, 4],           # 4+4
            9: [3, 3, 3],        # 3+3+3
            10: [3, 4, 3],       # 3+4+3
            11: [3, 4, 4],       # 3+4+4
            12: [4, 4, 4],       # 4+4+4
            13: [4, 5, 4],       # 4+5+4
            14: [4, 5, 5],       # 4+5+5
            15: [5, 5, 5],       # 5+5+5
            16: [4, 4, 4, 4],    # 4+4+4+4
            17: [4, 4, 5, 4],    # 4+4+5+4
            18: [4, 5, 5, 4],    # 4+5+5+4
            19: [4, 5, 5, 5],    # 4+5+5+5
            20: [5, 5, 5, 5],    # 5+5+5+5
        }
        return layouts.get(char_count, self._auto_layout(char_count))
    
    def _auto_layout(self, char_count):
        """자동 레이아웃 계산"""
        cols = math.ceil(math.sqrt(char_count))
        rows = math.ceil(char_count / cols)
        
        layout = []
        remaining = char_count
        for r in range(rows):
            if r == rows - 1:
                layout.append(remaining)
            else:
                row_count = min(cols, remaining)
                layout.append(row_count)
                remaining -= row_count
        return layout
    
    def create_stamp(self, text, font_name='noto_serif'):
        img = Image.new('RGBA', (self.size, self.size), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        # 정사각형 테두리
        margin = int(self.size * 0.03)
        border_width = int(self.size * 0.035)
        
        draw.rectangle(
            [margin, margin, self.size - margin, self.size - margin],
            outline=self.stamp_color, width=border_width
        )
        
        # 내부 영역
        inner_margin = margin + border_width + int(self.size * 0.02)
        inner_size = self.size - 2 * inner_margin
        
        chars = list(text)
        char_count = len(chars)
        
        if char_count < 1:
            return img
        
        layout = self.get_layout(char_count)
        self._draw_chars(draw, chars, layout, inner_margin, inner_size, font_name)
        
        return img
    
    def _draw_chars(self, draw, chars, layout, inner_margin, inner_size, font_name):
        """
        글자 배치 - 펜툴 방식
        각 행은 중심선 기준 좌우 대칭
        """
        num_rows = len(layout)
        max_cols = max(layout)
        
        # 글자 크기 계산
        gap_ratio = 0.02  # 글자 간격 (거의 붙을 듯)
        
        # 가로/세로 중 더 제한적인 방향 기준
        char_size_by_cols = inner_size / (max_cols + (max_cols - 1) * gap_ratio)
        char_size_by_rows = inner_size / (num_rows + (num_rows - 1) * gap_ratio)
        char_size = int(min(char_size_by_cols, char_size_by_rows))
        gap = int(char_size * gap_ratio)
        
        font_size = int(char_size * 0.92)
        font = self.get_font(font_name, font_size)
        
        # 전체 높이 계산
        total_height = num_rows * char_size + (num_rows - 1) * gap
        start_y = self.cy - total_height / 2 + char_size / 2
        
        char_idx = 0
        for row_idx, row_count in enumerate(layout):
            # 행의 y 좌표
            row_y = start_y + row_idx * (char_size + gap)
            
            # 행의 글자들을 중심선 기준 좌우 대칭 배치
            row_width = row_count * char_size + (row_count - 1) * gap
            start_x = self.cx - row_width / 2 + char_size / 2
            
            for col_idx in range(row_count):
                if char_idx >= len(chars):
                    break
                
                char = chars[char_idx]
                target_x = start_x + col_idx * (char_size + gap)
                target_y = row_y
                
                # bbox 중심을 target에 맞춤
                bbox = draw.textbbox((0, 0), char, font=font)
                bbox_cx = (bbox[0] + bbox[2]) / 2
                bbox_cy = (bbox[1] + bbox[3]) / 2
                
                draw_x = target_x - bbox_cx
                draw_y = target_y - bbox_cy
                
                draw.text((draw_x, draw_y), char, font=font, fill=self.stamp_color)
                char_idx += 1
    
    def save(self, img, filename):
        path = os.path.join(self.output_dir, filename)
        img.save(path, 'PNG')
        print(f"저장됨: {path}")
        return path


def main():
    generator = SquareStampGenerator(size=1024)
    generator.output_dir = '/home/ubuntu/madstamp-automation/test_output'
    os.makedirs(generator.output_dir, exist_ok=True)
    
    # 테스트 케이스
    test_cases = [
        ("합격인", 4, "4글자: 2+2"),
        ("대한민국만", 5, "5글자: 2+3"),
        ("매드스탬프야", 6, "6글자: 3+3"),
        ("대한민국만세요", 7, "7글자: 3+4"),
        ("사랑해요우리가족", 8, "8글자: 4+4"),
        ("주식회사매드스탬프", 9, "9글자: 3+3+3"),
        ("대한민국서울시강남구", 10, "10글자: 3+4+3"),
        ("대한민국서울특별시강남", 11, "11글자: 3+4+4"),
        ("대한민국서울특별시강남구", 12, "12글자: 4+4+4"),
        ("일이삼사오육칠팔구십일이삼사오육", 16, "16글자: 4+4+4+4"),
        ("일이삼사오육칠팔구십일이삼사오육칠팔구십", 20, "20글자: 5+5+5+5"),
    ]
    
    for text, expected_count, desc in test_cases:
        actual_count = len(text)
        layout = generator.get_layout(actual_count)
        print(f"\n=== {desc} ===")
        print(f"텍스트: {text} ({actual_count}글자)")
        print(f"배치: {'+'.join(map(str, layout))}")
        img = generator.create_stamp(text, 'noto_serif')
        generator.save(img, f"stamp_square_{actual_count}char.png")
    
    print("\n완료!")


if __name__ == '__main__':
    main()
