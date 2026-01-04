# Realtime_counseling.html 重構計劃

**日期**: 2025-12-26
**當前狀態**: realtime_counseling.html = 4361 行（超大單體檔案）
**目標**: 拆分為多個檔案（Partial Templates + 獨立 JS/CSS）

---

## 📊 現況分析

### 檔案統計
```
總行數: 4,361 lines
HTML + CSS + JavaScript 混合單檔
JavaScript 變數/函數: 409 個
Event Listeners: 47+ 個
API 端點調用: 多個 fetch() 調用
```

### 檔案結構

```
realtime_counseling.html (4361 lines)
├── HTML (約 1000 行)
│   ├── Header & Meta tags
│   ├── Initial UI (首頁)
│   ├── Practice Intro UI (練習介紹)
│   ├── Recording UI (錄音界面)
│   ├── Completion Screen (結束畫面)
│   ├── Report Screen (報告畫面)
│   └── Settings Modal
├── CSS (約 300 行)
│   ├── Custom styles
│   ├── Animations
│   ├── Mobile-specific styles
│   └── Component styles
└── JavaScript (約 3000 行)
    ├── State management (27 sections)
    ├── Event listeners (47+)
    ├── Core functions
    ├── API integrations
    └── UI logic
```

### JavaScript 主要區塊（27 個）

| 區塊 | 功能 | 行數估計 |
|------|------|---------|
| 1. Feature Flags | URL 參數處理 | ~10 |
| 2. State Management | 全域狀態變數 | ~30 |
| 3. ElevenLabs STT State | WebSocket 狀態 | ~10 |
| 4. Audio Simulation | 音訊模擬狀態 | ~10 |
| 5. Web Speech API (TTS) | 語音合成狀態 | ~10 |
| 6. Inactivity Timeout | 閒置計時器 | ~5 |
| 7. Analysis State | 分析狀態 | ~5 |
| 8. DOM Elements | DOM 元素引用 | ~100 |
| 9. Counseling Mode Setup | 模式設定 | ~40 |
| 10. Event Listeners | 事件監聽器綁定 | ~150 |
| 11. Preset Transcript Testing | 測試快捷鍵 | ~100 |
| 12. Initialization | 初始化邏輯 | ~40 |
| 13. ElevenLabs Functions | STT 整合 | ~450 |
| 14. Settings Modal | 設定彈窗 | ~30 |
| 15. Core Functions | 核心功能 | ~800 |
| 16. Transcript Management | 逐字稿管理 | ~40 |
| 17. AI Analysis | API 分析調用 | ~140 |
| 18. Mock Data Generator | 假資料生成 | ~430 |
| 19. Auto-Analysis Notification | 自動分析通知 | ~20 |
| 20. Manual Analysis Triggers | 手動觸發分析 | ~10 |
| 21. localStorage Management | 本地存儲 | ~90 |
| 22. Carousel Navigation | 輪播導航 | ~40 |
| 23. Report Screen | 報告畫面 | ~150 |
| 24. Demo Mode | Demo 模式 | ~270 |
| 25. Audio Simulation | 音訊模擬播放 | ~20 |
| 26. Web Speech API (TTS) | TTS 功能 | ~270 |
| 27. Initialize | 最終初始化 | ~40 |

---

## 🎯 重構策略

### 目標架構

```
app/templates/
├── realtime_counseling/
│   ├── base.html                    (~100L) ← Main layout
│   ├── partials/
│   │   ├── initial_ui.html          (~150L) ← 首頁 UI
│   │   ├── practice_intro.html      (~150L) ← 練習介紹
│   │   ├── recording_ui.html        (~300L) ← 錄音界面
│   │   ├── completion_screen.html   (~150L) ← 結束畫面
│   │   ├── report_screen.html       (~250L) ← 報告畫面
│   │   └── settings_modal.html      (~100L) ← 設定彈窗
│   └── index.html                   (~50L)  ← Entry point
│
├── static/
│   ├── css/
│   │   └── realtime_counseling.css  (~300L) ← All CSS
│   └── js/
│       └── realtime_counseling/
│           ├── config.js             (~50L)  ← Configuration & Constants
│           ├── state.js              (~100L) ← State Management
│           ├── dom.js                (~100L) ← DOM Elements
│           ├── api.js                (~200L) ← API Integration
│           ├── elevenlabs.js         (~450L) ← ElevenLabs STT
│           ├── analysis.js           (~300L) ← AI Analysis Logic
│           ├── transcript.js         (~150L) ← Transcript Management
│           ├── ui.js                 (~500L) ← UI Control & Events
│           ├── audio.js              (~300L) ← Audio Simulation & TTS
│           ├── demo.js               (~700L) ← Demo Mode & Mock Data
│           ├── storage.js            (~100L) ← localStorage Management
│           └── main.js               (~100L) ← Initialization
```

---

## 📋 詳細執行步驟

### Phase 1: CSS 提取 (最簡單)

**目標**: 創建獨立的 CSS 檔案

#### Step 1.1: 提取 CSS
```bash
# 創建 CSS 檔案
mkdir -p app/static/css
touch app/static/css/realtime_counseling.css
```

**提取內容**:
- Lines ~8-300: 所有 `<style>` 標籤內的 CSS
- 包含：custom styles, animations, scrollbar, mobile styles

**新檔案結構**:
```css
/* app/static/css/realtime_counseling.css */

/* Custom CSS for commercial-grade UI */
* {
    -webkit-tap-highlight-color: transparent;
}

/* ... (所有現有 CSS) */
```

**更新 base.html**:
```html
<link rel="stylesheet" href="{{ url_for('static', path='/css/realtime_counseling.css') }}">
```

**驗證**:
```bash
# 檢查 CSS 檔案
wc -l app/static/css/realtime_counseling.css

# 測試頁面載入
curl http://localhost:8000/realtime-counseling | grep "realtime_counseling.css"
```

---

### Phase 2: JavaScript 模塊化

#### Step 2.1: 創建 config.js (~50 lines)

**目標**: 所有配置和常量

```javascript
// app/static/js/realtime_counseling/config.js

export const CONFIG = {
    // Feature Flags
    SHOW_CODEER: new URLSearchParams(window.location.search).get('show_codeer') === 'true',

    // Analysis Intervals (seconds)
    ANALYSIS_INTERVALS: {
        red: 15,
        yellow: 30,
        green: 60
    },

    // Safety Window
    SAFETY_WINDOW_TURNS: 10,
    ANNOTATED_WINDOW_TURNS: 5,

    // Default Settings
    DEFAULT_PROVIDER: 'gemini',
    DEFAULT_CODEER_MODEL: 'gemini-flash',
    DEFAULT_COUNSELING_MODE: 'emergency',

    // API Endpoints
    API: {
        ANALYZE: '/api/v1/transcript/deep-analyze',
        PARENTS_REPORT: '/api/v1/transcript/report',
        ELEVENLABS_TOKEN: '/api/v1/transcript/elevenlabs-token'
    },

    // ElevenLabs
    ELEVENLABS: {
        AGENT_ID: 'your-agent-id',
        SAMPLE_RATE: 16000
    },

    // Timeouts
    INACTIVITY_WARNING: 180000, // 3 minutes
    INACTIVITY_TIMEOUT: 300000  // 5 minutes
};

export const PARENTING_KEYWORDS = [
    '孩子', '小孩', '兒子', '女兒', '教養',
    // ... (完整關鍵字列表)
];

export const MOCK_SCRIPTS = {
    emergency: [
        // ... (Demo 模式腳本)
    ],
    practice: [
        // ...
    ]
};
```

---

#### Step 2.2: 創建 state.js (~100 lines)

**目標**: 集中式狀態管理

```javascript
// app/static/js/realtime_counseling/state.js

export class AppState {
    constructor() {
        // Recording State
        this.isRecording = false;
        this.isPaused = false;
        this.pausedTime = 0;
        this.pauseStartTime = null;
        this.currentSpeaker = 'counselor';
        this.startTime = null;

        // Session State
        this.sessionMode = 'practice';
        this.counselingMode = 'emergency';
        this.currentSessionId = null;
        this.isDemoMode = false;

        // Analysis State
        this.isAnalyzing = false;
        this.lastAutoAnalysisTime = 0;
        this.nextAnalysisInterval = 60;
        this.lastSafetyLevel = 'green';
        this.analysisHistory = [];

        // Provider State
        this.currentProvider = 'gemini';
        this.currentCodeerModel = 'gemini-flash';

        // Transcript State
        this.transcriptSegments = [];
        this.partialTranscriptText = '';

        // ElevenLabs State
        this.elevenLabsWs = null;
        this.audioContext = null;
        this.audioWorkletNode = null;
        this.audioStream = null;
        this.elevenlabsToken = null;

        // Audio Simulation State
        this.audioSimulation = {
            isPlaying: false,
            currentTime: 0,
            duration: 0,
            lastDisplayedIndex: 0,
            animationFrame: null,
            startTimeMs: 0
        };

        // TTS State
        this.ttsState = {
            voices: [],
            counselorVoice: null,
            clientVoice: null,
            isSupported: 'speechSynthesis' in window,
            currentUtterance: null
        };

        // Timers
        this.timerInterval = null;
        this.analysisInterval = null;
        this.inactivityCheckInterval = null;
        this.countdownInterval = null;
        this.lastActivityTime = Date.now();
    }

    reset() {
        // Reset all state to initial values
        this.isRecording = false;
        this.transcriptSegments = [];
        // ... (reset all properties)
    }
}

export const appState = new AppState();
```

---

#### Step 2.3: 創建 dom.js (~100 lines)

**目標**: DOM 元素引用集中管理

```javascript
// app/static/js/realtime_counseling/dom.js

export class DOMElements {
    constructor() {
        // Buttons
        this.startBtn = this.get('startBtn');
        this.stopBtn = this.get('stopBtn');
        this.practiceBtn = this.get('practiceBtn');
        this.realTalkBtn = this.get('realTalkBtn');
        this.pauseBtnMobile = this.get('pauseBtnMobile');
        this.stopBtnMobile = this.get('stopBtnMobile');

        // Displays
        this.timer = this.get('timer');
        this.status = this.get('status');
        this.nextAnalysis = this.get('nextAnalysis');
        this.transcript = this.get('transcript');
        this.analysisCards = this.get('analysisCards');

        // Speaker Toggle
        this.speakerCounselorBtn = this.get('speakerCounselor');
        this.speakerClientBtn = this.get('speakerClient');
        this.speakerToggleSection = this.get('speakerToggleSection');

        // Mobile UI
        this.mainHeader = this.get('mainHeader');
        this.initialUI = this.get('initialUI');
        this.practiceIntroUI = this.get('practiceIntroUI');
        this.recordingUI = this.get('recordingUI');
        this.completionScreen = this.get('completionScreen');
        this.reportScreen = this.get('reportScreen');
        this.mobileCarousel = this.get('mobileCarousel');

        // ... (所有其他 DOM 元素)
    }

    get(id) {
        const element = document.getElementById(id);
        if (!element) {
            console.warn(`Element not found: ${id}`);
        }
        return element;
    }

    show(element) {
        if (element) element.classList.remove('hidden');
    }

    hide(element) {
        if (element) element.classList.add('hidden');
    }
}

export const dom = new DOMElements();
```

---

#### Step 2.4: 創建 api.js (~200 lines)

**目標**: API 調用統一管理

```javascript
// app/static/js/realtime_counseling/api.js

import { CONFIG } from './config.js';

export class API {
    constructor() {
        this.baseURL = window.location.origin;
    }

    async analyze(requestData) {
        try {
            const response = await fetch(CONFIG.API.ANALYZE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`Analysis failed: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('❌ Analysis API error:', error);
            throw error;
        }
    }

    async getParentsReport(requestData) {
        try {
            const response = await fetch(CONFIG.API.PARENTS_REPORT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`Parents report failed: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('❌ Parents report API error:', error);
            throw error;
        }
    }

    async getElevenLabsToken() {
        try {
            const response = await fetch(CONFIG.API.ELEVENLABS_TOKEN, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error(`Token fetch failed: ${response.status}`);
            }

            const data = await response.json();
            return data.token;
        } catch (error) {
            console.error('❌ ElevenLabs token error:', error);
            throw error;
        }
    }
}

export const api = new API();
```

---

#### Step 2.5: 創建 elevenlabs.js (~450 lines)

**目標**: ElevenLabs STT 整合

```javascript
// app/static/js/realtime_counseling/elevenlabs.js

import { CONFIG } from './config.js';
import { appState } from './state.js';
import { api } from './api.js';

export class ElevenLabsSTT {
    constructor() {
        this.ws = null;
        this.audioContext = null;
        this.workletNode = null;
        this.stream = null;
    }

    async initialize() {
        // Get token from backend
        appState.elevenlabsToken = await api.getElevenLabsToken();

        // Initialize Web Audio API
        this.audioContext = new AudioContext({ sampleRate: CONFIG.ELEVENLABS.SAMPLE_RATE });

        // Load AudioWorklet
        await this.audioContext.audioWorklet.addModule('/static/js/pcm-processor.js');

        console.log('✅ ElevenLabs STT initialized');
    }

    async start() {
        // ... (現有 startElevenLabs 邏輯)
    }

    stop() {
        // ... (現有 stopElevenLabs 邏輯)
    }

    handleMessage(data) {
        // ... (WebSocket message handling)
    }
}

export const elevenLabsSTT = new ElevenLabsSTT();
```

---

#### Step 2.6: 創建 analysis.js (~300 lines)

**目標**: AI 分析邏輯

```javascript
// app/static/js/realtime_counseling/analysis.js

import { api } from './api.js';
import { appState } from './state.js';
import { dom } from './dom.js';
import { transcript } from './transcript.js';

export class Analysis {
    async triggerAnalysis(isAutomatic = false) {
        if (appState.isAnalyzing) {
            console.log('⏸️ Analysis already in progress, skipping');
            return;
        }

        appState.isAnalyzing = true;

        try {
            // Build request
            const requestData = this.buildAnalysisRequest();

            // Call API
            const result = appState.isDemoMode
                ? this.getMockData()
                : await api.analyze(requestData);

            // Update UI
            this.displayAnalysisResult(result);

            // Update next interval
            this.updateAnalysisInterval(result.safety_level);

        } catch (error) {
            console.error('❌ Analysis failed:', error);
            this.showError(error.message);
        } finally {
            appState.isAnalyzing = false;
        }
    }

    buildAnalysisRequest() {
        // ... (build request from transcript)
    }

    displayAnalysisResult(result) {
        // ... (update analysis cards)
    }

    updateAnalysisInterval(safetyLevel) {
        // ... (adjust polling interval)
    }

    getMockData() {
        // ... (generate mock analysis)
    }
}

export const analysis = new Analysis();
```

---

#### Step 2.7: 創建 transcript.js (~150 lines)

**目標**: 逐字稿管理

```javascript
// app/static/js/realtime_counseling/transcript.js

import { appState } from './state.js';
import { dom } from './dom.js';

export class Transcript {
    addSegment(speaker, text) {
        const segment = { speaker, text };
        appState.transcriptSegments.push(segment);
        this.render();
    }

    render() {
        const segments = appState.transcriptSegments;

        if (segments.length === 0) {
            dom.show(dom.transcriptEmpty);
            return;
        }

        dom.hide(dom.transcriptEmpty);

        dom.transcript.innerHTML = segments.map(seg => {
            const label = seg.speaker === 'counselor' ? '諮詢師' : '案主';
            return `
                <div class="mb-3">
                    <span class="font-medium ${seg.speaker === 'counselor' ? 'text-blue-600' : 'text-purple-600'}">
                        ${label}：
                    </span>
                    <span class="text-gray-700">${seg.text}</span>
                </div>
            `;
        }).join('');

        // Auto-scroll to bottom
        dom.transcript.scrollTop = dom.transcript.scrollHeight;
    }

    clear() {
        appState.transcriptSegments = [];
        this.render();
    }

    getText() {
        return appState.transcriptSegments
            .map(seg => `${seg.speaker === 'counselor' ? '諮詢師' : '案主'}：${seg.text}`)
            .join('\n');
    }
}

export const transcript = new Transcript();
```

---

#### Step 2.8: 創建 ui.js (~500 lines)

**目標**: UI 控制與事件處理

```javascript
// app/static/js/realtime_counseling/ui.js

import { dom } from './dom.js';
import { appState } from './state.js';
import { analysis } from './analysis.js';
import { transcript } from './transcript.js';
import { elevenLabsSTT } from './elevenlabs.js';

export class UI {
    constructor() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Start button
        dom.startBtn?.addEventListener('click', () => this.startSession());

        // Stop button
        dom.stopBtn?.addEventListener('click', () => this.stopSession());

        // Pause button (mobile)
        dom.pauseBtnMobile?.addEventListener('click', () => this.togglePause());

        // Speaker toggle
        dom.speakerCounselorBtn?.addEventListener('click', () => this.setSpeaker('counselor'));
        dom.speakerClientBtn?.addEventListener('click', () => this.setSpeaker('client'));

        // Analysis trigger
        dom.triggerAnalysisBtn?.addEventListener('click', () => analysis.triggerAnalysis(false));

        // ... (所有其他事件監聽器)
    }

    async startSession() {
        // ... (start recording logic)
    }

    async stopSession() {
        // ... (stop recording logic)
    }

    togglePause() {
        // ... (pause/resume logic)
    }

    setSpeaker(speaker) {
        appState.currentSpeaker = speaker;
        this.updateSpeakerUI();
    }

    updateSpeakerUI() {
        // ... (update speaker button styles)
    }

    showScreen(screenName) {
        // Hide all screens
        dom.hide(dom.initialUI);
        dom.hide(dom.practiceIntroUI);
        dom.hide(dom.recordingUI);
        dom.hide(dom.completionScreen);
        dom.hide(dom.reportScreen);

        // Show target screen
        switch(screenName) {
            case 'initial':
                dom.show(dom.initialUI);
                break;
            case 'practice-intro':
                dom.show(dom.practiceIntroUI);
                break;
            case 'recording':
                dom.show(dom.recordingUI);
                break;
            case 'completion':
                dom.show(dom.completionScreen);
                break;
            case 'report':
                dom.show(dom.reportScreen);
                break;
        }
    }
}

export const ui = new UI();
```

---

#### Step 2.9: 創建 audio.js (~300 lines)

**目標**: 音訊模擬與 TTS

```javascript
// app/static/js/realtime_counseling/audio.js

import { appState } from './state.js';

export class Audio {
    constructor() {
        this.initTTS();
    }

    initTTS() {
        if (!appState.ttsState.isSupported) {
            console.warn('⚠️ Text-to-Speech not supported');
            return;
        }

        // Wait for voices to load
        speechSynthesis.onvoiceschanged = () => {
            appState.ttsState.voices = speechSynthesis.getVoices();
            this.selectVoices();
        };
    }

    selectVoices() {
        // ... (voice selection logic)
    }

    speak(text, speaker) {
        // ... (TTS playback logic)
    }

    stopSpeaking() {
        speechSynthesis.cancel();
    }

    // Audio Simulation
    playAudioSimulation() {
        // ... (simulate audio playback)
    }

    stopAudioSimulation() {
        // ... (stop simulation)
    }
}

export const audio = new Audio();
```

---

#### Step 2.10: 創建 demo.js (~700 lines)

**目標**: Demo 模式與 Mock 資料

```javascript
// app/static/js/realtime_counseling/demo.js

import { MOCK_SCRIPTS } from './config.js';
import { appState } from './state.js';
import { transcript } from './transcript.js';

export class Demo {
    generateMockAnalysis(transcriptText) {
        // ... (現有 generateMockAnalysis 邏輯)
    }

    startDemoPlayback() {
        // ... (Demo mode playback)
    }

    stopDemoPlayback() {
        // ... (Stop demo)
    }

    simulateTranscript(script, startIndex = 0) {
        // ... (Simulate typing transcript)
    }
}

export const demo = new Demo();
```

---

#### Step 2.11: 創建 storage.js (~100 lines)

**目標**: localStorage 管理

```javascript
// app/static/js/realtime_counseling/storage.js

export class Storage {
    save(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('❌ localStorage save error:', error);
        }
    }

    load(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('❌ localStorage load error:', error);
            return defaultValue;
        }
    }

    remove(key) {
        localStorage.removeItem(key);
    }

    clear() {
        localStorage.clear();
    }

    // Specific getters/setters
    saveSessionId(sessionId) {
        this.save('currentSessionId', sessionId);
    }

    loadSessionId() {
        return this.load('currentSessionId');
    }

    saveTranscript(segments) {
        this.save('transcriptSegments', segments);
    }

    loadTranscript() {
        return this.load('transcriptSegments', []);
    }
}

export const storage = new Storage();
```

---

#### Step 2.12: 創建 main.js (~100 lines)

**目標**: 應用初始化與協調

```javascript
// app/static/js/realtime_counseling/main.js

import { CONFIG } from './config.js';
import { appState } from './state.js';
import { dom } from './dom.js';
import { ui } from './ui.js';
import { api } from './api.js';
import { analysis } from './analysis.js';
import { transcript } from './transcript.js';
import { elevenLabsSTT } from './elevenlabs.js';
import { audio } from './audio.js';
import { demo } from './demo.js';
import { storage } from './storage.js';

class App {
    async initialize() {
        console.log('🚀 Initializing Realtime Counseling App...');

        // Load saved session ID
        appState.currentSessionId = storage.loadSessionId() || this.generateSessionId();
        storage.saveSessionId(appState.currentSessionId);

        // Initialize components
        await this.initializeComponents();

        // Setup global error handlers
        this.setupErrorHandlers();

        console.log('✅ App initialized successfully');
    }

    async initializeComponents() {
        // Initialize ElevenLabs (if not demo mode)
        if (!appState.isDemoMode) {
            try {
                await elevenLabsSTT.initialize();
            } catch (error) {
                console.error('❌ ElevenLabs init failed:', error);
            }
        }

        // Initialize TTS
        audio.initTTS();

        // Show initial screen
        ui.showScreen('initial');
    }

    generateSessionId() {
        const timestamp = Date.now();
        const random = Math.random().toString(36).substring(7);
        return `session-${timestamp}-${random}`;
    }

    setupErrorHandlers() {
        window.addEventListener('error', (event) => {
            console.error('❌ Global error:', event.error);
        });

        window.addEventListener('unhandledrejection', (event) => {
            console.error('❌ Unhandled promise rejection:', event.reason);
        });
    }
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        const app = new App();
        app.initialize();
    });
} else {
    const app = new App();
    app.initialize();
}
```

---

### Phase 3: HTML Partial Templates

#### Step 3.1: 創建 base.html (~100 lines)

**目標**: 主要 Layout 模板

```html
<!-- app/templates/realtime_counseling/base.html -->
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>{% block title %}AI 即時親子諮詢分析{% endblock %}</title>

    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- Custom CSS -->
    <link rel="stylesheet" href="{{ url_for('static', path='/css/realtime_counseling.css') }}">

    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- Main Header -->
    {% include "realtime_counseling/partials/header.html" %}

    <!-- Main Content -->
    <main id="mainContent">
        {% block content %}{% endblock %}
    </main>

    <!-- Modals -->
    {% include "realtime_counseling/partials/settings_modal.html" %}

    <!-- JavaScript Modules -->
    <script type="module" src="{{ url_for('static', path='/js/realtime_counseling/main.js') }}"></script>

    {% block extra_js %}{% endblock %}
</body>
</html>
```

---

#### Step 3.2: 創建各 Partial Templates

**檔案結構**:
```
app/templates/realtime_counseling/partials/
├── header.html              (~50L)  ← 頁面標題與導航
├── initial_ui.html          (~150L) ← 首頁 UI
├── practice_intro.html      (~150L) ← 練習介紹
├── recording_ui.html        (~300L) ← 錄音界面
├── completion_screen.html   (~150L) ← 結束畫面
├── report_screen.html       (~250L) ← 報告畫面
└── settings_modal.html      (~100L) ← 設定彈窗
```

**範例 - initial_ui.html**:
```html
<!-- app/templates/realtime_counseling/partials/initial_ui.html -->
<div id="initialUI" class="min-h-screen flex flex-col items-center justify-center p-4">
    <div class="max-w-md w-full space-y-6">
        <!-- Logo & Title -->
        <div class="text-center">
            <h1 class="text-3xl font-bold text-gray-800 mb-2">
                AI 即時親子諮詢分析
            </h1>
            <p class="text-gray-600">
                專業督導陪伴，即時回饋支持
            </p>
        </div>

        <!-- Mode Selection Buttons -->
        <div class="space-y-4">
            <button id="practiceBtn" class="w-full py-4 bg-blue-500 text-white rounded-2xl">
                練習模式
            </button>
            <button id="realTalkBtn" class="w-full py-4 bg-purple-500 text-white rounded-2xl">
                和孩子談談
            </button>
        </div>
    </div>
</div>
```

---

## ✅ 驗證檢查清單

### Phase 1 完成後

- [ ] **CSS 提取**: realtime_counseling.css 存在
- [ ] **樣式正常**: 頁面載入 CSS，樣式無異常
- [ ] **檔案大小**: CSS ~300 行

### Phase 2 完成後

- [ ] **JS 模塊**: 所有 12 個 JS 檔案存在
- [ ] **Import 正確**: 沒有 import 錯誤
- [ ] **功能正常**: 所有功能正常運作
- [ ] **檔案大小**: 每個 JS 檔案 ≤500 行

### Phase 3 完成後

- [ ] **Partial Templates**: 7 個 partial 檔案存在
- [ ] **Template 渲染**: 頁面正確顯示
- [ ] **導航正常**: 各畫面切換無誤
- [ ] **檔案大小**: 每個 partial ≤300 行

### 最終驗證

```bash
# 檢查檔案結構
tree app/templates/realtime_counseling/
tree app/static/js/realtime_counseling/
tree app/static/css/

# 測試頁面載入
curl http://localhost:8000/realtime-counseling

# 瀏覽器測試
# 1. 開啟頁面
# 2. 測試所有功能
# 3. 檢查 Console 無錯誤
```

---

## 🎯 成功標準

### 檔案數量
- **Original**: 1 個巨大檔案 (4361 行)
- **After**: 20+ 個模組化檔案（平均每個 <500 行）

### 檔案大小目標

| 類型 | 檔案數 | 平均行數 | 總行數估計 |
|------|--------|---------|----------|
| CSS | 1 | ~300 | 300 |
| JS Modules | 12 | ~200-500 | ~3200 |
| HTML Templates | 8 | ~100-300 | ~1200 |
| **Total** | **21** | - | **~4700** |

### 可維護性提升
- ✅ **關注點分離**: HTML / CSS / JS 完全分離
- ✅ **模組化**: 每個 JS 檔案負責單一功能
- ✅ **可重用**: 組件可在其他頁面重用
- ✅ **易測試**: 每個模組可獨立測試

---

## ⚠️ 注意事項

### ES6 模塊支援
- 使用 `type="module"` 載入 JS
- 所有檔案使用 `export`/`import`
- 注意瀏覽器兼容性

### FastAPI 靜態檔案配置
確保 FastAPI 正確配置靜態檔案路由：
```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="app/static"), name="static")
```

### Template 渲染
確保 Jinja2 可以找到 partial templates：
```python
templates = Jinja2Templates(directory="app/templates")
```

### 向後兼容
- 保持 API 端點不變
- 功能行為完全一致
- 只有內部結構改變

---

## 🚀 執行建議

### 分階段執行
1. **Phase 1** (CSS) - 最簡單，先做
2. **Phase 2** (JS) - 最複雜，分 12 步逐個完成
3. **Phase 3** (HTML) - 最後整合

### 測試策略
每完成一個 Phase:
1. 瀏覽器測試所有功能
2. 檢查 Console 無錯誤
3. 測試 Demo 模式
4. 測試真實錄音模式
5. 測試手機版響應式

### Commit 策略
```bash
# Phase 1
git commit -m "refactor(html): extract CSS to separate file"

# Phase 2 - 每個模塊一個 commit
git commit -m "refactor(html): extract config.js module"
git commit -m "refactor(html): extract state.js module"
# ... 依此類推

# Phase 3
git commit -m "refactor(html): create HTML partial templates"
```

---

## 📊 進度追蹤

### Phase 1: CSS 提取

| Task | Status | Notes |
|------|--------|-------|
| 創建 CSS 檔案 | ⏳ | - |
| 提取樣式 | ⏳ | ~300 lines |
| 更新 HTML link | ⏳ | - |
| 測試驗證 | ⏳ | - |

### Phase 2: JavaScript 模塊化

| Module | Lines | Status | Notes |
|--------|-------|--------|-------|
| config.js | ~50 | ⏳ | Configuration |
| state.js | ~100 | ⏳ | State Management |
| dom.js | ~100 | ⏳ | DOM Elements |
| api.js | ~200 | ⏳ | API Integration |
| elevenlabs.js | ~450 | ⏳ | ElevenLabs STT |
| analysis.js | ~300 | ⏳ | AI Analysis |
| transcript.js | ~150 | ⏳ | Transcript Mgmt |
| ui.js | ~500 | ⏳ | UI Control |
| audio.js | ~300 | ⏳ | Audio & TTS |
| demo.js | ~700 | ⏳ | Demo Mode |
| storage.js | ~100 | ⏳ | localStorage |
| main.js | ~100 | ⏳ | Initialization |

### Phase 3: HTML Partial Templates

| Template | Lines | Status | Notes |
|----------|-------|--------|-------|
| base.html | ~100 | ⏳ | Main Layout |
| header.html | ~50 | ⏳ | Header |
| initial_ui.html | ~150 | ⏳ | Home Screen |
| practice_intro.html | ~150 | ⏳ | Practice Intro |
| recording_ui.html | ~300 | ⏳ | Recording UI |
| completion_screen.html | ~150 | ⏳ | Completion |
| report_screen.html | ~250 | ⏳ | Report |
| settings_modal.html | ~100 | ⏳ | Settings |

**圖例**:
- ⏳ 待執行
- 🔄 進行中
- ✅ 已完成
- ❌ 失敗需修正

---

**最後更新**: 2025-12-26
**文檔版本**: 1.0
**狀態**: 分析完成，等待執行
**預估工時**: 8-12 小時（分 3 個 Phase，每個 Phase 2-4 小時）
