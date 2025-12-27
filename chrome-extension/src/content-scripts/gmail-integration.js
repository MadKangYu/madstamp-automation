/**
 * Madstamp - Gmail 연동 Content Script
 * 
 * Gmail에서 도장 제작 요청 이메일을 감지하고 분석합니다.
 * - 첨부 이미지 감지
 * - 제작 요청 키워드 분석
 * - 빠른 작업 버튼 제공
 */

(function() {
  'use strict';

  // ============================================
  // 상수 정의
  // ============================================
  const MADSTAMP_GMAIL_PANEL_ID = 'madstamp-gmail-panel';
  const STORAGE_KEY = 'madstamp_gmail_settings';
  
  // 도장 제작 관련 키워드
  const STAMP_KEYWORDS = [
    '도장', '스탬프', 'stamp', '인장', '직인', '낙관',
    '제작', '주문', '의뢰', '요청', '만들어', '만들고',
    '로고', 'logo', '회사', '업체', '사업자',
    'goopick', '구픽', 'madstamp', '매드스탬프'
  ];

  // 이미지 확장자
  const IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ai', 'eps', 'pdf'];

  // ============================================
  // 유틸리티 함수
  // ============================================
  
  /**
   * 요소가 나타날 때까지 대기
   */
  function waitForElement(selector, timeout = 10000) {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      
      const checkElement = () => {
        const element = document.querySelector(selector);
        if (element) {
          resolve(element);
          return;
        }
        
        if (Date.now() - startTime > timeout) {
          reject(new Error(`Element not found: ${selector}`));
          return;
        }
        
        requestAnimationFrame(checkElement);
      };
      
      checkElement();
    });
  }

  /**
   * 알림 표시
   */
  function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `madstamp-gmail-notification madstamp-gmail-notification-${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
      notification.classList.add('madstamp-gmail-notification-fade');
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  // ============================================
  // Gmail 분석 클래스
  // ============================================
  class GmailAnalyzer {
    constructor() {
      this.currentEmail = null;
      this.detectedRequests = [];
    }

    /**
     * 현재 열린 이메일 정보 추출
     */
    extractEmailInfo() {
      const emailInfo = {
        subject: '',
        sender: '',
        senderEmail: '',
        body: '',
        attachments: [],
        hasImages: false,
        isStampRequest: false,
        confidence: 0
      };

      try {
        // 제목 추출
        const subjectEl = document.querySelector('h2[data-thread-perm-id]') || 
                          document.querySelector('.hP');
        if (subjectEl) {
          emailInfo.subject = subjectEl.textContent.trim();
        }

        // 발신자 추출
        const senderEl = document.querySelector('.gD') || 
                         document.querySelector('[email]');
        if (senderEl) {
          emailInfo.sender = senderEl.getAttribute('name') || senderEl.textContent;
          emailInfo.senderEmail = senderEl.getAttribute('email') || '';
        }

        // 본문 추출
        const bodyEl = document.querySelector('.a3s.aiL') || 
                       document.querySelector('.ii.gt');
        if (bodyEl) {
          emailInfo.body = bodyEl.textContent.trim();
        }

        // 첨부파일 추출
        const attachmentEls = document.querySelectorAll('.aQH .aZo, .aQH .aV3');
        attachmentEls.forEach(el => {
          const filename = el.getAttribute('download') || 
                          el.textContent.trim() ||
                          el.querySelector('.aV3')?.textContent.trim();
          if (filename) {
            const ext = filename.split('.').pop().toLowerCase();
            emailInfo.attachments.push({
              filename: filename,
              extension: ext,
              isImage: IMAGE_EXTENSIONS.includes(ext)
            });
            if (IMAGE_EXTENSIONS.includes(ext)) {
              emailInfo.hasImages = true;
            }
          }
        });

        // 인라인 이미지 확인
        const inlineImages = document.querySelectorAll('.a3s img, .ii img');
        if (inlineImages.length > 0) {
          emailInfo.hasImages = true;
          inlineImages.forEach((img, idx) => {
            if (img.src && !img.src.includes('googleusercontent.com/proxy')) {
              emailInfo.attachments.push({
                filename: `inline_image_${idx + 1}`,
                extension: 'inline',
                isImage: true,
                src: img.src
              });
            }
          });
        }

        // 도장 제작 요청 여부 판단
        const analysisResult = this.analyzeStampRequest(emailInfo);
        emailInfo.isStampRequest = analysisResult.isStampRequest;
        emailInfo.confidence = analysisResult.confidence;
        emailInfo.matchedKeywords = analysisResult.matchedKeywords;

      } catch (error) {
        console.error('이메일 정보 추출 오류:', error);
      }

      this.currentEmail = emailInfo;
      return emailInfo;
    }

    /**
     * 도장 제작 요청 분석
     */
    analyzeStampRequest(emailInfo) {
      const result = {
        isStampRequest: false,
        confidence: 0,
        matchedKeywords: []
      };

      const textToAnalyze = `${emailInfo.subject} ${emailInfo.body}`.toLowerCase();
      
      // 키워드 매칭
      let keywordScore = 0;
      STAMP_KEYWORDS.forEach(keyword => {
        if (textToAnalyze.includes(keyword.toLowerCase())) {
          keywordScore += 1;
          result.matchedKeywords.push(keyword);
        }
      });

      // 이미지 첨부 여부
      const hasImageAttachment = emailInfo.hasImages;

      // 신뢰도 계산
      if (keywordScore >= 3 && hasImageAttachment) {
        result.confidence = 95;
        result.isStampRequest = true;
      } else if (keywordScore >= 2 && hasImageAttachment) {
        result.confidence = 80;
        result.isStampRequest = true;
      } else if (keywordScore >= 1 && hasImageAttachment) {
        result.confidence = 60;
        result.isStampRequest = true;
      } else if (keywordScore >= 2) {
        result.confidence = 50;
        result.isStampRequest = true;
      } else if (hasImageAttachment && keywordScore >= 1) {
        result.confidence = 40;
        result.isStampRequest = true;
      }

      return result;
    }

    /**
     * 첨부 이미지 다운로드 URL 추출
     */
    getImageDownloadUrls() {
      const urls = [];
      
      // 첨부파일 다운로드 링크
      const downloadLinks = document.querySelectorAll('.aQH a[download], .aZo');
      downloadLinks.forEach(link => {
        const href = link.href || link.getAttribute('data-url');
        if (href) {
          urls.push({
            url: href,
            filename: link.getAttribute('download') || 'attachment'
          });
        }
      });

      // 인라인 이미지
      const inlineImages = document.querySelectorAll('.a3s img[src], .ii img[src]');
      inlineImages.forEach((img, idx) => {
        if (img.src && !img.src.startsWith('data:')) {
          urls.push({
            url: img.src,
            filename: `inline_image_${idx + 1}.png`
          });
        }
      });

      return urls;
    }
  }

  // ============================================
  // UI 컨트롤러
  // ============================================
  class GmailUIController {
    constructor(analyzer) {
      this.analyzer = analyzer;
      this.panel = null;
      this.isVisible = false;
    }

    /**
     * 사이드 패널 생성
     */
    createSidePanel() {
      // 기존 패널 제거
      const existingPanel = document.getElementById(MADSTAMP_GMAIL_PANEL_ID);
      if (existingPanel) {
        existingPanel.remove();
      }

      const panel = document.createElement('div');
      panel.id = MADSTAMP_GMAIL_PANEL_ID;
      panel.innerHTML = `
        <div class="madstamp-gmail-header">
          <span class="madstamp-gmail-logo">🔴 Madstamp</span>
          <div class="madstamp-gmail-header-actions">
            <button class="madstamp-gmail-refresh-btn" title="새로고침">↻</button>
            <button class="madstamp-gmail-close-btn" title="닫기">×</button>
          </div>
        </div>
        <div class="madstamp-gmail-content">
          <div class="madstamp-gmail-section" id="madstamp-email-info">
            <div class="madstamp-gmail-placeholder">
              이메일을 선택하면 분석 결과가 표시됩니다.
            </div>
          </div>
        </div>
      `;

      document.body.appendChild(panel);
      this.panel = panel;

      // 이벤트 리스너
      this.setupEventListeners();

      return panel;
    }

    /**
     * 이벤트 리스너 설정
     */
    setupEventListeners() {
      // 닫기 버튼
      this.panel.querySelector('.madstamp-gmail-close-btn').addEventListener('click', () => {
        this.hide();
      });

      // 새로고침 버튼
      this.panel.querySelector('.madstamp-gmail-refresh-btn').addEventListener('click', () => {
        this.analyzeCurrentEmail();
      });
    }

    /**
     * 현재 이메일 분석 및 표시
     */
    analyzeCurrentEmail() {
      const emailInfo = this.analyzer.extractEmailInfo();
      this.updatePanel(emailInfo);
    }

    /**
     * 패널 내용 업데이트
     */
    updatePanel(emailInfo) {
      const contentEl = this.panel.querySelector('#madstamp-email-info');
      
      if (!emailInfo.subject && !emailInfo.body) {
        contentEl.innerHTML = `
          <div class="madstamp-gmail-placeholder">
            이메일을 선택하면 분석 결과가 표시됩니다.
          </div>
        `;
        return;
      }

      const confidenceClass = emailInfo.confidence >= 80 ? 'high' : 
                              emailInfo.confidence >= 50 ? 'medium' : 'low';

      contentEl.innerHTML = `
        <div class="madstamp-gmail-email-header">
          <div class="madstamp-gmail-subject">${this.escapeHtml(emailInfo.subject)}</div>
          <div class="madstamp-gmail-sender">${this.escapeHtml(emailInfo.sender)} &lt;${this.escapeHtml(emailInfo.senderEmail)}&gt;</div>
        </div>
        
        <div class="madstamp-gmail-analysis">
          <div class="madstamp-gmail-analysis-header">
            <span>분석 결과</span>
            <span class="madstamp-gmail-confidence madstamp-gmail-confidence-${confidenceClass}">
              ${emailInfo.confidence}% 확신
            </span>
          </div>
          
          ${emailInfo.isStampRequest ? `
            <div class="madstamp-gmail-stamp-detected">
              ✅ 도장 제작 요청으로 감지됨
            </div>
            ${emailInfo.matchedKeywords.length > 0 ? `
              <div class="madstamp-gmail-keywords">
                <span class="madstamp-gmail-keywords-label">감지된 키워드:</span>
                ${emailInfo.matchedKeywords.map(k => `<span class="madstamp-gmail-keyword">${k}</span>`).join('')}
              </div>
            ` : ''}
          ` : `
            <div class="madstamp-gmail-stamp-not-detected">
              ❌ 도장 제작 요청이 아닌 것으로 판단됨
            </div>
          `}
        </div>
        
        <div class="madstamp-gmail-attachments">
          <div class="madstamp-gmail-attachments-header">
            첨부파일 (${emailInfo.attachments.length}개)
          </div>
          ${emailInfo.attachments.length > 0 ? `
            <ul class="madstamp-gmail-attachment-list">
              ${emailInfo.attachments.map(att => `
                <li class="${att.isImage ? 'madstamp-gmail-attachment-image' : ''}">
                  ${att.isImage ? '🖼️' : '📎'} ${this.escapeHtml(att.filename)}
                </li>
              `).join('')}
            </ul>
          ` : `
            <div class="madstamp-gmail-no-attachments">첨부파일 없음</div>
          `}
        </div>
        
        ${emailInfo.isStampRequest ? `
          <div class="madstamp-gmail-actions">
            <button class="madstamp-gmail-btn madstamp-gmail-btn-primary" id="madstamp-create-order">
              📝 주문 생성
            </button>
            <button class="madstamp-gmail-btn madstamp-gmail-btn-secondary" id="madstamp-open-lovart">
              🎨 Lovart AI 열기
            </button>
          </div>
        ` : ''}
      `;

      // 액션 버튼 이벤트
      if (emailInfo.isStampRequest) {
        this.panel.querySelector('#madstamp-create-order')?.addEventListener('click', () => {
          this.createOrder(emailInfo);
        });

        this.panel.querySelector('#madstamp-open-lovart')?.addEventListener('click', () => {
          chrome.runtime.sendMessage({ action: 'openLovart' });
        });
      }
    }

    /**
     * 주문 생성
     */
    createOrder(emailInfo) {
      const orderData = {
        id: `MS${Date.now()}`,
        subject: emailInfo.subject,
        sender: emailInfo.sender,
        senderEmail: emailInfo.senderEmail,
        attachments: emailInfo.attachments,
        confidence: emailInfo.confidence,
        keywords: emailInfo.matchedKeywords,
        createdAt: new Date().toISOString()
      };

      // Background Script로 전송
      chrome.runtime.sendMessage({
        action: 'createOrder',
        orderData: orderData
      }, (response) => {
        if (response?.success) {
          showNotification('주문이 생성되었습니다!', 'success');
        } else {
          showNotification('주문 생성 실패: ' + (response?.error || '알 수 없는 오류'), 'error');
        }
      });
    }

    /**
     * HTML 이스케이프
     */
    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text || '';
      return div.innerHTML;
    }

    /**
     * 패널 표시
     */
    show() {
      if (!this.panel) {
        this.createSidePanel();
      }
      this.panel.classList.add('madstamp-gmail-panel-visible');
      this.isVisible = true;
      this.analyzeCurrentEmail();
    }

    /**
     * 패널 숨기기
     */
    hide() {
      if (this.panel) {
        this.panel.classList.remove('madstamp-gmail-panel-visible');
      }
      this.isVisible = false;
    }

    /**
     * 패널 토글
     */
    toggle() {
      if (this.isVisible) {
        this.hide();
      } else {
        this.show();
      }
    }
  }

  // ============================================
  // Gmail 페이지 변경 감지
  // ============================================
  class GmailObserver {
    constructor(uiController) {
      this.uiController = uiController;
      this.observer = null;
      this.lastUrl = '';
    }

    /**
     * 관찰 시작
     */
    start() {
      // URL 변경 감지 (이메일 열기/닫기)
      this.checkUrlChange();
      setInterval(() => this.checkUrlChange(), 1000);

      // DOM 변경 감지
      this.observer = new MutationObserver((mutations) => {
        // 이메일 본문이 로드되었는지 확인
        const emailBody = document.querySelector('.a3s.aiL, .ii.gt');
        if (emailBody && this.uiController.isVisible) {
          this.uiController.analyzeCurrentEmail();
        }
      });

      this.observer.observe(document.body, {
        childList: true,
        subtree: true
      });
    }

    /**
     * URL 변경 확인
     */
    checkUrlChange() {
      const currentUrl = window.location.href;
      if (currentUrl !== this.lastUrl) {
        this.lastUrl = currentUrl;
        
        // 이메일 상세 페이지인지 확인
        if (currentUrl.includes('#inbox/') || currentUrl.includes('#sent/') || 
            currentUrl.includes('#all/') || currentUrl.includes('#search/')) {
          // 이메일이 열렸을 때
          setTimeout(() => {
            if (this.uiController.isVisible) {
              this.uiController.analyzeCurrentEmail();
            }
          }, 500);
        }
      }
    }

    /**
     * 관찰 중지
     */
    stop() {
      if (this.observer) {
        this.observer.disconnect();
      }
    }
  }

  // ============================================
  // 플로팅 버튼 생성
  // ============================================
  function createFloatingButton(uiController) {
    const button = document.createElement('button');
    button.id = 'madstamp-gmail-fab';
    button.innerHTML = '🔴';
    button.title = 'Madstamp 패널 열기';
    
    button.addEventListener('click', () => {
      uiController.toggle();
    });

    document.body.appendChild(button);
    return button;
  }

  // ============================================
  // 메시지 리스너
  // ============================================
  let uiController = null;

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    switch (message.action) {
      case 'togglePanel':
        if (uiController) {
          uiController.toggle();
        }
        sendResponse({ success: true });
        break;

      case 'analyzeEmail':
        if (uiController) {
          uiController.analyzeCurrentEmail();
        }
        sendResponse({ success: true });
        break;

      case 'getEmailInfo':
        if (uiController && uiController.analyzer.currentEmail) {
          sendResponse({ emailInfo: uiController.analyzer.currentEmail });
        } else {
          sendResponse({ emailInfo: null });
        }
        break;

      default:
        sendResponse({ error: 'Unknown action' });
    }
  });

  // ============================================
  // 초기화
  // ============================================
  function initialize() {
    const analyzer = new GmailAnalyzer();
    uiController = new GmailUIController(analyzer);
    const observer = new GmailObserver(uiController);

    // 플로팅 버튼 생성
    createFloatingButton(uiController);

    // 관찰 시작
    observer.start();

    console.log('Madstamp Gmail Integration 초기화 완료');
  }

  // Gmail 페이지 로드 완료 후 초기화
  if (document.readyState === 'complete') {
    setTimeout(initialize, 1000);
  } else {
    window.addEventListener('load', () => setTimeout(initialize, 1000));
  }

})();
