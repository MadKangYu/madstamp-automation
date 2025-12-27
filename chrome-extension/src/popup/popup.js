/**
 * Madstamp - Popup Dashboard Script
 */

// ============================================
// 상수 및 설정
// ============================================
const PROMPT_TEMPLATES = {
  traditional_korean: 'Traditional Korean seal stamp (Nakgwan), red ink impression, elegant calligraphy style, circular or square shape, high contrast black and white design suitable for rubber stamp production, clean lines, minimalist, professional quality',
  modern_logo: 'Modern logo stamp design, clean geometric shapes, professional business seal, high contrast black and white, vector-like quality, suitable for rubber stamp production, minimalist design',
  handwriting_style: 'Handwritten signature style stamp, elegant cursive script, personal seal design, high contrast black and white, suitable for rubber stamp production, artistic calligraphy',
  company_seal: 'Official company seal stamp, formal corporate design, circular shape with company name, professional business stamp, high contrast black and white, clean typography, suitable for rubber stamp production',
  custom: ''
};

// ============================================
// DOM 요소
// ============================================
const elements = {
  // 탭
  tabBtns: document.querySelectorAll('.tab-btn'),
  tabPanels: document.querySelectorAll('.tab-panel'),
  
  // 대시보드
  statPending: document.getElementById('stat-pending'),
  statProcessing: document.getElementById('stat-processing'),
  statCompleted: document.getElementById('stat-completed'),
  orderList: document.getElementById('order-list'),
  btnRefreshOrders: document.getElementById('btn-refresh-orders'),
  btnOpenGmail: document.getElementById('btn-open-gmail'),
  btnOpenLovart: document.getElementById('btn-open-lovart'),
  
  // Lovart
  lovartTemplate: document.getElementById('lovart-template'),
  lovartDetails: document.getElementById('lovart-details'),
  lovartCustom: document.getElementById('lovart-custom'),
  customPromptGroup: document.getElementById('custom-prompt-group'),
  btnCopyPrompt: document.getElementById('btn-copy-prompt'),
  btnGenerateLovart: document.getElementById('btn-generate-lovart'),
  lovartStatus: document.getElementById('lovart-status'),
  
  // Gmail
  gmailMonitoring: document.getElementById('gmail-monitoring'),
  monitoringEmail: document.getElementById('monitoring-email'),
  btnCheckGmail: document.getElementById('btn-check-gmail'),
  
  // 기타
  btnSettings: document.getElementById('btn-settings'),
  linkHelp: document.getElementById('link-help')
};

// ============================================
// 탭 전환
// ============================================
function initTabs() {
  elements.tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.dataset.tab;
      
      // 버튼 활성화 상태 변경
      elements.tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      // 패널 표시 상태 변경
      elements.tabPanels.forEach(panel => {
        panel.classList.remove('active');
        if (panel.id === `tab-${tabId}`) {
          panel.classList.add('active');
        }
      });
    });
  });
}

// ============================================
// 주문 관리
// ============================================
async function loadOrders() {
  try {
    const result = await chrome.storage.local.get(['orders']);
    const orders = result.orders || [];
    
    updateStats(orders);
    renderOrderList(orders);
  } catch (error) {
    console.error('주문 로드 실패:', error);
  }
}

function updateStats(orders) {
  const pending = orders.filter(o => o.status === 'pending').length;
  const processing = orders.filter(o => o.status === 'processing').length;
  const completed = orders.filter(o => o.status === 'completed').length;
  
  elements.statPending.textContent = pending;
  elements.statProcessing.textContent = processing;
  elements.statCompleted.textContent = completed;
}

function renderOrderList(orders) {
  if (orders.length === 0) {
    elements.orderList.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">📭</span>
        <p>아직 주문이 없습니다.</p>
      </div>
    `;
    return;
  }
  
  // 최근 5개만 표시
  const recentOrders = orders.slice(-5).reverse();
  
  elements.orderList.innerHTML = recentOrders.map(order => `
    <div class="order-item" data-order-id="${order.id}">
      <div class="order-icon">${getOrderIcon(order.status)}</div>
      <div class="order-info">
        <div class="order-title">${escapeHtml(order.subject || order.id)}</div>
        <div class="order-meta">${formatDate(order.createdAt)}</div>
      </div>
      <span class="order-status ${order.status}">${getStatusText(order.status)}</span>
    </div>
  `).join('');
  
  // 주문 클릭 이벤트
  elements.orderList.querySelectorAll('.order-item').forEach(item => {
    item.addEventListener('click', () => {
      const orderId = item.dataset.orderId;
      showOrderDetail(orderId);
    });
  });
}

function getOrderIcon(status) {
  switch (status) {
    case 'pending': return '⏳';
    case 'processing': return '🔄';
    case 'completed': return '✅';
    default: return '📋';
  }
}

function getStatusText(status) {
  switch (status) {
    case 'pending': return '대기';
    case 'processing': return '처리중';
    case 'completed': return '완료';
    default: return status;
  }
}

function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diff = now - date;
  
  if (diff < 60000) return '방금 전';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}분 전`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}시간 전`;
  return date.toLocaleDateString('ko-KR');
}

function showOrderDetail(orderId) {
  // TODO: 주문 상세 모달 표시
  console.log('주문 상세:', orderId);
}

// ============================================
// Lovart AI 기능
// ============================================
function initLovart() {
  // 템플릿 변경 시 커스텀 프롬프트 표시/숨김
  elements.lovartTemplate.addEventListener('change', () => {
    const isCustom = elements.lovartTemplate.value === 'custom';
    elements.customPromptGroup.style.display = isCustom ? 'block' : 'none';
  });
  
  // 프롬프트 복사
  elements.btnCopyPrompt.addEventListener('click', async () => {
    const prompt = generatePrompt();
    await copyToClipboard(prompt);
    showToast('프롬프트가 복사되었습니다!');
  });
  
  // Lovart에서 생성
  elements.btnGenerateLovart.addEventListener('click', () => {
    const prompt = generatePrompt();
    openLovartWithPrompt(prompt);
  });
  
  // Lovart 상태 확인
  checkLovartStatus();
}

function generatePrompt() {
  const template = elements.lovartTemplate.value;
  const details = elements.lovartDetails.value.trim();
  const custom = elements.lovartCustom.value.trim();
  
  let prompt = '';
  
  if (template === 'custom' && custom) {
    prompt = custom;
  } else {
    prompt = PROMPT_TEMPLATES[template] || PROMPT_TEMPLATES.traditional_korean;
  }
  
  if (details) {
    prompt += `, ${details}`;
  }
  
  return prompt;
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (error) {
    console.error('클립보드 복사 실패:', error);
    return false;
  }
}

function openLovartWithPrompt(prompt) {
  // Lovart AI 페이지 열기
  chrome.tabs.create({
    url: 'https://www.lovart.ai/ko/home'
  }, (tab) => {
    // 페이지 로드 후 프롬프트 전달
    setTimeout(() => {
      chrome.tabs.sendMessage(tab.id, {
        action: 'runAutomation',
        orderData: {
          customPrompt: prompt,
          orderId: `popup_${Date.now()}`
        }
      });
    }, 3000);
  });
}

async function checkLovartStatus() {
  try {
    // Lovart 탭이 열려있는지 확인
    const tabs = await chrome.tabs.query({ url: '*://www.lovart.ai/*' });
    
    if (tabs.length > 0) {
      elements.lovartStatus.classList.add('connected');
      elements.lovartStatus.classList.remove('disconnected');
      elements.lovartStatus.querySelector('.status-text').textContent = '연결됨 (탭 열림)';
    } else {
      elements.lovartStatus.classList.remove('connected');
      elements.lovartStatus.classList.add('disconnected');
      elements.lovartStatus.querySelector('.status-text').textContent = '연결 안됨';
    }
  } catch (error) {
    elements.lovartStatus.querySelector('.status-text').textContent = '상태 확인 실패';
  }
}

// ============================================
// Gmail 기능
// ============================================
function initGmail() {
  // 모니터링 토글
  elements.gmailMonitoring.addEventListener('change', async () => {
    const enabled = elements.gmailMonitoring.checked;
    await chrome.storage.local.set({ gmailMonitoring: enabled });
    
    // Background에 알림
    chrome.runtime.sendMessage({
      action: 'setGmailMonitoring',
      enabled: enabled
    });
  });
  
  // Gmail 열기
  elements.btnCheckGmail.addEventListener('click', () => {
    chrome.tabs.create({
      url: 'https://mail.google.com/'
    });
  });
  
  // 설정 로드
  loadGmailSettings();
}

async function loadGmailSettings() {
  try {
    const result = await chrome.storage.local.get(['gmailMonitoring', 'monitoringEmail']);
    
    elements.gmailMonitoring.checked = result.gmailMonitoring !== false;
    
    if (result.monitoringEmail) {
      elements.monitoringEmail.textContent = result.monitoringEmail;
    }
  } catch (error) {
    console.error('Gmail 설정 로드 실패:', error);
  }
}

// ============================================
// 공통 기능
// ============================================
function initCommon() {
  // Gmail 열기
  elements.btnOpenGmail.addEventListener('click', () => {
    chrome.tabs.create({ url: 'https://mail.google.com/' });
  });
  
  // Lovart 열기
  elements.btnOpenLovart.addEventListener('click', () => {
    chrome.tabs.create({ url: 'https://www.lovart.ai/ko/home' });
  });
  
  // 주문 새로고침
  elements.btnRefreshOrders.addEventListener('click', () => {
    loadOrders();
    showToast('주문 목록을 새로고침했습니다.');
  });
  
  // 설정
  elements.btnSettings.addEventListener('click', () => {
    // TODO: 설정 페이지 열기
    showToast('설정 기능은 준비 중입니다.');
  });
  
  // 도움말
  elements.linkHelp.addEventListener('click', (e) => {
    e.preventDefault();
    chrome.tabs.create({
      url: 'https://github.com/MadKangYu/madstamp-automation#readme'
    });
  });
}

// ============================================
// 토스트 메시지
// ============================================
function showToast(message) {
  // 기존 토스트 제거
  const existingToast = document.querySelector('.toast');
  if (existingToast) {
    existingToast.remove();
  }
  
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed;
    bottom: 60px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 10px 20px;
    border-radius: 20px;
    font-size: 13px;
    z-index: 1000;
    animation: fadeIn 0.3s ease;
  `;
  
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.style.animation = 'fadeOut 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 2000);
}

// ============================================
// 유틸리티
// ============================================
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

// ============================================
// 메시지 리스너
// ============================================
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.action) {
    case 'orderCreated':
    case 'orderUpdated':
      loadOrders();
      break;
      
    case 'lovartStatusChanged':
      checkLovartStatus();
      break;
  }
});

// ============================================
// 초기화
// ============================================
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initCommon();
  initLovart();
  initGmail();
  loadOrders();
});

// CSS 애니메이션 추가
const style = document.createElement('style');
style.textContent = `
  @keyframes fadeIn {
    from { opacity: 0; transform: translateX(-50%) translateY(10px); }
    to { opacity: 1; transform: translateX(-50%) translateY(0); }
  }
  @keyframes fadeOut {
    from { opacity: 1; }
    to { opacity: 0; }
  }
`;
document.head.appendChild(style);
