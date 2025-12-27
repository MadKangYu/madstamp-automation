#!/usr/bin/env python3
"""
256자 손글씨 템플릿 PDF 생성기
한글 폰트 생성을 위한 샘플 글자 템플릿을 생성합니다.
"""

from fpdf import FPDF
import os

# 256자 샘플 글자 세트
CHARS_256 = """가 각 간 갈 감 갑 강 개 객 갱 거 건 걸 검 게 겨
격 견 결 경 계 고 곡 곤 골 공 과 관 광 괴 구 국
군 굴 궁 권 귀 규 균 그 극 근 글 금 급 긍 기 긴
길 김 깊 까 깨 꺼 께 꼬 꽃 꾸 꿈 끄 끌 끝 나 낙
난 날 남 납 낭 내 냉 너 널 네 녀 년 념 녕 노 녹
논 놀 농 뇌 누 눈 눌 느 늘 능 니 닉 닌 닐 님 다
단 달 담 답 당 대 댁 더 덕 던 덜 덤 덩 데 도 독
돈 돌 동 두 둔 둘 둥 드 득 든 들 등 디 따 땅 때
떠 또 뚜 뜨 뜻 라 락 란 랄 람 랍 랑 래 랭 러 럭
런 럴 렁 레 려 력 련 렬 렴 령 례 로 록 론 롤 롱
뢰 료 루 룩 룬 룰 룸 류 륙 륜 률 륭 르 륵 른 를
름 릉 리 릭 린 릴 림 립 마 막 만 말 망 매 맥 맹
머 먹 멀 멍 메 며 면 멸 명 모 목 몰 몽 묘 무 묵
문 물 뭇 므 미 민 밀 밍 바 박 반 발 밤 밥 방 배
백 번 벌 범 법 벽 변 별 병 보 복 본 볼 봉 부 북
분 불 붕 비 빈 빌 빙 빠 빼 뻐 뽀 뿌 쁘 사 삭 산
살 삼 삽 상 새 색 생 서 석 선 설 섬 섭 성 세 소
속 손 솔 송 쇄 쇠 수 숙 순 술 숭 쉬 스 슬 습 승
시 식 신 실 심 십 싱 싸 쌍 써 쏘 쑤 쓰 씨 아 악
안 알 암 압 앙 애 액 앵 야 약 양 어 억 언 얼 엄
업 엉 에 여 역 연 열 염 엽 영 예 오 옥 온 올 옹
와 완 왕 왜 외 요 욕 용 우 욱 운 울 웅 원 월 위
유 육 윤 율 융 으 은 을 음 읍 응 의 이 익 인 일
임 입 잉 자 작 잔 잘 잠 잡 장 재 쟁 저 적 전 절
점 접 정 제 조 족 존 졸 종 좌 죄 주 죽 준 줄 중
즉 즐 즘 증 지 직 진 질 짐 집 징 차 착 찬 찰 참
창 채 책 처 척 천 철 첨 첩 청 체 초 촉 촌 총 최
추 축 춘 출 충 취 측 층 치 칙 친 칠 침 칭 쾌 타
탁 탄 탈 탐 탑 탕 태 택 터 털 토 톤 통 퇴 투 퉁
트 특 틈 티 파 판 팔 패 팽 퍼 펴 편 평 폐 포 폭
표 푸 품 풍 프 피 픽 필 핍 하 학 한 할 함 합 항
해 핵 행 향 허 헌 험 혁 현 혈 협 형 혜 호 혹 혼
홀 홍 화 확 환 활 황 회 획 횡 효 후 훈 훌 훙 휘
휴 흉 흐 흑 흔 흘 흥 희 히 힘"""

# 8자 세트
CHARS_8 = "가 나 다 라 마 바 사 아"

# 28자 세트
CHARS_28 = """갈 같 강 개 걔 거 겨 계
고 과 괴 구 궈 귀 그 긔
기 깨 꺼 꼬 꾸 끼 냐 녀
노 뇨 누 뉴"""

# 43자 세트
CHARS_43 = """각 간 감 갑 객 건 걸 검
겁 게 격 견 결 경 곡 곤
골 공 관 광 국 군 굴 궁
권 균 극 근 글 금 급 긍
긴 길 김 깊 꽃 꿈 끝 낙
난 날 남"""


def parse_chars(char_string):
    """문자열에서 글자 리스트 추출"""
    return [c for c in char_string.replace('\n', ' ').split() if c]


class KoreanPDF(FPDF):
    def __init__(self):
        super().__init__()
        # 한글 폰트 설정 (NanumGothic 사용)
        font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
        if os.path.exists(font_path):
            self.add_font("NanumGothic", "", font_path, uni=True)
        else:
            # 대체 폰트 경로
            alt_paths = [
                "/home/ubuntu/madstamp-automation/fonts/NanumGothic.ttf",
                "/home/ubuntu/madstamp-automation/assets/fonts/NanumGothic.ttf"
            ]
            for path in alt_paths:
                if os.path.exists(path):
                    self.add_font("NanumGothic", "", path, uni=True)
                    break


def generate_template_pdf(chars, output_path, title, cols=8, cell_size=20):
    """템플릿 PDF 생성"""
    pdf = KoreanPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # 페이지 설정
    pdf.add_page()
    pdf.set_font("NanumGothic", size=16)
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("NanumGothic", size=10)
    pdf.cell(0, 8, "각 칸에 해당 글자를 손글씨로 작성해주세요.", ln=True, align='C')
    pdf.ln(10)
    
    # 글자 그리드 생성
    char_list = parse_chars(chars)
    rows = (len(char_list) + cols - 1) // cols
    
    # 시작 위치 계산 (중앙 정렬)
    start_x = (210 - cols * cell_size) / 2
    start_y = pdf.get_y()
    
    pdf.set_font("NanumGothic", size=8)
    
    for i, char in enumerate(char_list):
        row = i // cols
        col = i % cols
        
        x = start_x + col * cell_size
        y = start_y + row * cell_size
        
        # 새 페이지 필요 시
        if y + cell_size > 280:
            pdf.add_page()
            start_y = 20
            y = start_y + (row % ((280 - 20) // cell_size)) * cell_size
        
        # 셀 그리기
        pdf.rect(x, y, cell_size, cell_size)
        
        # 가이드 글자 (연한 색)
        pdf.set_text_color(200, 200, 200)
        pdf.set_xy(x, y + 2)
        pdf.cell(cell_size, 5, char, align='C')
        pdf.set_text_color(0, 0, 0)
    
    pdf.output(output_path)
    print(f"생성 완료: {output_path}")


def generate_all_templates():
    """모든 템플릿 생성"""
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    templates = [
        (CHARS_8, "template_8chars.pdf", "8자 손글씨 템플릿", 8, 25),
        (CHARS_28, "template_28chars.pdf", "28자 손글씨 템플릿", 8, 22),
        (CHARS_43, "template_43chars.pdf", "43자 손글씨 템플릿", 8, 22),
        (CHARS_256, "template_256chars.pdf", "256자 손글씨 템플릿", 8, 20),
    ]
    
    for chars, filename, title, cols, cell_size in templates:
        output_path = os.path.join(output_dir, filename)
        generate_template_pdf(chars, output_path, title, cols, cell_size)


if __name__ == "__main__":
    generate_all_templates()
