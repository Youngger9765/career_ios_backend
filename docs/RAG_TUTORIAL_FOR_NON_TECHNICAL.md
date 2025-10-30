# RAG 系統完整教學指南 - 從零到有建立智能問答系統

**目標讀者**：產品經理、非技術背景人員、想了解 RAG 的初學者

**預計學習時間**：1 小時

**學完你將會**：
- 理解 RAG 是什麼、為什麼需要它
- 學會如何上傳文件並建立知識庫
- 能夠測試和使用智能問答系統
- 了解如何整合到你的產品中

---

## 📊 教學架構視覺化

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAG 系統完整學習路徑                           │
└─────────────────────────────────────────────────────────────────┘

第1部分：理解概念 🧠                    第2部分：技術原理 ⚙️
┌────────────────────┐                 ┌────────────────────┐
│  什麼是 RAG？       │────關聯───────▶ │  Embedding 原理     │
│  • 開卷考試比喻     │                 │  • 文字→向量轉換    │
│  • 解決 AI 限制     │                 │  • 語意相似度搜尋   │
│  • 實際應用案例     │                 │  • OpenAI API       │
└────────────────────┘                 └────────────────────┘
         │                                       │
         │                                       │
         └──────────┬────────────────────────────┘
                    ▼
         第3部分：資料儲存 💾
         ┌────────────────────┐
         │  Supabase + pgvector │
         │  • 向量資料庫        │
         │  • 相似度搜尋引擎    │
         │  • 資料表設計        │
         └────────────────────┘
                    │
                    ▼
         第4部分：實際操作 🚀
         ┌────────────────────────────────────┐
         │          RAG 系統運作流程            │
         ├────────────────────────────────────┤
         │  1️⃣ 上傳文件 (PDF)                 │
         │     └─▶ 切片 (Chunking)            │
         │         └─▶ 生成 Embedding          │
         │             └─▶ 儲存到 Supabase     │
         │                                     │
         │  2️⃣ 使用者提問                      │
         │     └─▶ 問題 Embedding              │
         │         └─▶ 搜尋相似文本            │
         │             └─▶ 找到相關段落        │
         │                                     │
         │  3️⃣ AI 生成答案                     │
         │     └─▶ 問題 + 相關段落             │
         │         └─▶ ChatGPT 回答            │
         │             └─▶ 基於事實的答案      │
         └────────────────────────────────────┘
                    │
                    ▼
         第5部分：部署上線 ☁️
         ┌────────────────────────────────────┐
         │     Google Cloud Run 部署          │
         ├────────────────────────────────────┤
         │  • 只在有請求時計費（省錢）        │
         │  • 自動擴展（彈性處理流量）        │
         │  • 免費額度 200萬次請求/月         │
         │  • CI/CD 自動部署（GitHub Actions）│
         │  • Secret Manager 安全管理環境變數 │
         └────────────────────────────────────┘
```

### 🎯 各章節學習目標與關聯

| 章節 | 目的 | 關鍵產出 | 與其他章節的關係 |
|------|------|----------|-----------------|
| **1️⃣ RAG 基礎** | 建立概念框架 | 理解 RAG 價值 | 為後續技術章節提供動機 |
| **2️⃣ Embedding** | 理解核心技術 | 知道如何將文字轉向量 | 連結「概念」與「實作」 |
| **3️⃣ Supabase** | 建立資料基礎 | 完成資料庫設定 | 提供 Embedding 的儲存空間 |
| **4️⃣ 實際操作** | 整合所有知識 | 可運作的 RAG 系統 | 驗證前三章的學習成果 |
| **5️⃣ 部署上雲** | 產品化 | 24/7 可用的服務 | 從開發環境到生產環境 |

### 📈 學習路徑建議

```
新手路徑（基礎理解）：
1️⃣ → 2️⃣ → 4️⃣（跳過深入技術細節）

完整學習路徑（全面掌握）：
1️⃣ → 2️⃣ → 3️⃣ → 4️⃣ → 5️⃣

快速部署路徑（已有系統）：
3️⃣ → 4️⃣ → 5️⃣（直接建置）
```

### 🔑 核心概念關係圖

```
                    使用者問題
                        │
                        ▼
        ┌───────────────────────────┐
        │   Embedding 轉換          │
        │   (OpenAI API)            │
        └───────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────┐
        │   向量相似度搜尋           │
        │   (Supabase pgvector)     │
        └───────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────┐
        │   找到最相關的文件段落      │
        │   (Top K 結果)            │
        └───────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────┐
        │   組合成 Prompt           │
        │   問題 + 相關內容         │
        └───────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────┐
        │   AI 生成答案             │
        │   (ChatGPT)               │
        └───────────────────────────┘
                        │
                        ▼
                    返回答案
```

---

## 📚 目錄

### [第 1 部分：RAG 基礎概念（15 分鐘）](#第-1-部分rag-基礎概念)
- [1.1 什麼是 RAG？](#11-什麼是-rag)
- [1.2 為什麼需要 RAG？](#12-為什麼需要-rag)
- [1.3 RAG 如何運作？](#13-rag-如何運作)
- [1.4 實際應用案例](#14-實際應用案例)

### [第 2 部分：OpenAI Embedding 原理（15 分鐘）](#第-2-部分openai-embedding-原理)
- [2.1 什麼是 Embedding？](#21-什麼是-embedding)
- [2.2 為什麼需要 Embedding？](#22-為什麼需要-embedding)
- [2.3 Embedding 如何幫助搜尋？](#23-embedding-如何幫助搜尋)
- [2.4 成本與選擇](#24-成本與選擇)

### [第 3 部分：Supabase 資料庫設定（15 分鐘）](#第-3-部分supabase-資料庫設定)
- [3.1 為什麼選擇 Supabase？](#31-為什麼選擇-supabase)
- [3.2 資料如何儲存？](#32-資料如何儲存)
- [3.3 設定 Supabase 專案](#33-設定-supabase-專案)
- [3.4 設定環境變數（.env 檔案）](#34-設定環境變數env-檔案)
- [3.5 理解資料表結構](#35-理解資料表結構)

### [第 4 部分：實際操作 - 建立你的 RAG 系統（15 分鐘）](#第-4-部分實際操作建立你的-rag-系統)
- [4.1 上傳文件到知識庫](#41-上傳文件到知識庫)
- [4.2 測試搜尋功能](#42-測試搜尋功能)
- [4.3 測試智能問答](#43-測試智能問答)
- [4.4 整合到你的應用](#44-整合到你的應用)

### [第 5 部分：建立完整的前後端系統（進階）](#第-5-部分建立完整的前後端系統)
- 📌 如果你想要完整的文件管理介面（上傳、CRUD、搜尋測試）
- 👉 請參考：[RAG 前後端完整實作教學](./RAG_FRONTEND_BACKEND_TUTORIAL.md)

### [附錄](#附錄)
- [常見問題 FAQ](#常見問題-faq)
- [名詞對照表](#名詞對照表)
- [延伸學習資源](#延伸學習資源)

---

## 第 1 部分：RAG 基礎概念

### 1.1 什麼是 RAG？

**RAG = Retrieval-Augmented Generation**（檢索增強生成）

**最簡單的解釋**：
想像你在考試時可以「翻書找答案」，而不是只靠背誦記憶。

- **傳統 AI（ChatGPT）**：像是閉卷考試，只能回答「訓練時學到的知識」（2021 年之前的資料）
- **RAG 系統**：像是開卷考試，可以先「翻書找相關內容」，再根據找到的內容回答問題

**實際範例**：

❌ **沒有 RAG**
```
使用者：「我們公司的請假政策是什麼？」
AI：「我不知道你們公司的具體政策...」
```

✅ **有 RAG**
```
使用者：「我們公司的請假政策是什麼？」

系統內部流程：
1. 先去「員工手冊」裡搜尋相關段落
2. 找到：「年假 7 天、病假 14 天、特休依年資計算...」
3. 根據找到的內容生成回答

AI：「根據員工手冊，年假 7 天、病假 14 天，特休依年資計算...」
```

---

### 1.2 為什麼需要 RAG？

**問題 1：AI 的知識有時效性**
- ChatGPT 的訓練資料截至 2021 年
- 無法回答「2024 年最新產品功能」「昨天的會議記錄」

**問題 2：AI 不知道你的私有資料**
- 無法回答「我們公司的內部規範」
- 無法回答「客戶的產品文件」

**問題 3：AI 可能產生幻覺（Hallucination）**
- 當 AI 不確定時，可能會「編造」聽起來合理的答案
- 例如：編造不存在的政策條文

**RAG 的解決方案**：
1. ✅ **即時性**：隨時可以上傳最新文件
2. ✅ **私有知識**：使用你自己的資料庫
3. ✅ **可驗證**：回答會附上來源文件，可以檢查
4. ✅ **降低幻覺**：AI 只根據「找到的內容」回答，不能亂編

---

### 1.3 RAG 如何運作？

**完整流程圖解**：

```
┌─────────────────────────────────────────────────────────┐
│  第一階段：建立知識庫（只需做一次）                          │
└─────────────────────────────────────────────────────────┘

📄 上傳文件（PDF、Word、網頁）
    ↓
📝 提取文字內容
    ↓
✂️ 切成小段落（Chunking）
    例：每 400 字一段，段落間重疊 80 字
    ↓
🧮 轉換成數字向量（Embedding）
    例："請假政策" → [0.23, -0.45, 0.67, ..., 0.12]（1536 個數字）
    ↓
💾 儲存到向量資料庫（Supabase + pgvector）


┌─────────────────────────────────────────────────────────┐
│  第二階段：回答問題（每次提問時）                           │
└─────────────────────────────────────────────────────────┘

🗣️ 使用者提問：「請假政策是什麼？」
    ↓
🧮 問題轉換成向量
    "請假政策是什麼？" → [0.21, -0.43, 0.69, ..., 0.15]
    ↓
🔍 向量相似度搜尋（在知識庫裡找最相關的段落）
    計算問題向量 vs. 所有段落向量的「距離」
    找出最相似的 Top 5 段落
    ↓
📚 取得相關段落：
    1. 「年假 7 天、病假 14 天...」（相似度 0.92）
    2. 「特休假計算方式...」（相似度 0.85）
    3. ...
    ↓
🤖 GPT-4 生成回答
    系統提示：「根據以下文件回答問題，不要編造內容...」
    相關文件：[段落 1、段落 2、...]
    使用者問題：「請假政策是什麼？」
    ↓
✅ 回傳答案 + 來源引用
```

**關鍵步驟解釋**：

1. **Chunking（文字切片）**
   - 為什麼要切？整份文件太長，AI 無法一次處理
   - 怎麼切？每 400 字切一段，段落間重疊 80 字（避免重要句子被切斷）

2. **Embedding（向量化）**
   - 把文字轉成數字陣列，讓電腦可以「計算相似度」
   - 例如：「貓」和「狗」的向量距離很近，「貓」和「汽車」的向量距離很遠

3. **Vector Search（向量搜尋）**
   - 計算問題向量和所有段落向量的「距離」
   - 距離越近 = 語意越相似
   - 找出最相關的 Top K 段落

4. **GPT-4 生成**
   - 根據找到的段落，生成自然語言回答
   - 附上引用來源（哪份文件、第幾頁）

---

### 1.4 實際應用案例

**案例 1：客服知識庫**
```
知識來源：產品說明書 10 份、FAQ 文件 5 份
使用者問：「如何重設密碼？」
系統回答：根據《使用手冊 v2.3》第 12 頁，重設密碼步驟為...
```

**案例 2：企業內部文件問答（本專案）**
```
知識來源：Google Docs 文件 10-20 份
使用者問：「產品 A 的定價策略是什麼？」
系統回答：根據《產品策略文件》，定價採用階梯式收費...
```

**案例 3：職涯諮詢助手（本專案實際案例）**
```
知識來源：心理諮詢理論文獻、職涯發展理論
諮商師上傳會談逐字稿
系統自動生成報告，並引用相關理論：
「根據 Super 生涯發展理論 [1]，案主處於探索期...」
```

---

## 第 2 部分：OpenAI Embedding 原理

### 2.1 什麼是 Embedding？

**Embedding = 把文字轉換成數字向量（一串數字）**

**生活化比喻**：
想像你要在地圖上標記「咖啡店的位置」
- 文字描述：「信義區市政府站附近」❌ 電腦無法計算距離
- 座標位置：(25.0330, 121.5654) ✅ 可以計算距離

Embedding 就是把文字轉成「語意座標」：
- 「貓」 → [0.2, 0.5, -0.3, 0.1, ...]（1536 個數字）
- 「狗」 → [0.3, 0.6, -0.2, 0.2, ...]
- 「汽車」→ [-0.5, -0.1, 0.8, -0.4, ...]

**重要特性**：
- 語意相近的詞，向量距離也近
- 「貓」和「狗」的距離 < 「貓」和「汽車」的距離

---

### 2.2 為什麼需要 Embedding？

**問題：傳統關鍵字搜尋的限制**

❌ **關鍵字搜尋**
```
使用者搜尋：「如何離職」
資料庫文件：「辭職流程說明」

結果：找不到！（因為「離職」≠「辭職」）
```

✅ **語意搜尋（Embedding）**
```
使用者搜尋：「如何離職」 → 向量 A
資料庫文件：「辭職流程說明」 → 向量 B

計算相似度：距離很近！
結果：找到了！（AI 知道「離職」=「辭職」）
```

**更多範例**：

| 使用者問題 | 關鍵字搜尋 | 語意搜尋（Embedding） |
|----------|----------|-------------------|
| 「年假怎麼請？」 | ❌ 找不到（沒有「年假」關鍵字） | ✅ 找到「特休假申請流程」 |
| 「退費政策」 | ❌ 找不到（文件寫「退款規則」） | ✅ 找到「退款規則」 |
| 「How to reset password?」 | ❌ 找不到（中文資料庫） | ✅ 找到「如何重設密碼」（跨語言） |

---

### 2.3 Embedding 如何幫助搜尋？

**完整流程範例**：

**步驟 1：建立知識庫 Embedding**
```python
文件段落 1：「員工年假為 7 天，病假為 14 天」
→ OpenAI API 轉換
→ Embedding 1: [0.23, -0.45, 0.67, ..., 0.12]（1536 維向量）

文件段落 2：「特休假依年資計算，第一年 3 天」
→ OpenAI API 轉換
→ Embedding 2: [0.25, -0.42, 0.70, ..., 0.15]

文件段落 3：「產品退款政策：7 天內可全額退費」
→ OpenAI API 轉換
→ Embedding 3: [-0.10, 0.30, -0.50, ..., 0.80]
```

**步驟 2：使用者提問**
```python
問題：「請假規定是什麼？」
→ OpenAI API 轉換
→ Query Embedding: [0.24, -0.44, 0.68, ..., 0.13]
```

**步驟 3：計算相似度（向量距離）**
```python
Query vs. Embedding 1: 距離 0.08 ✅ 很相似！
Query vs. Embedding 2: 距離 0.12 ✅ 相似
Query vs. Embedding 3: 距離 0.95 ❌ 不相關
```

**步驟 4：返回最相關的段落**
```python
Top 1: 「員工年假為 7 天，病假為 14 天」（相似度 0.92）
Top 2: 「特休假依年資計算...」（相似度 0.88）
```

---

### 2.4 成本與選擇

**OpenAI Embedding 模型選擇**

| 模型 | 維度 | 成本 | 適用場景 |
|-----|------|-----|---------|
| `text-embedding-3-small` | 1536 | $0.02 / 百萬 tokens | ✅ **推薦**：CP 值最高 |
| `text-embedding-3-large` | 3072 | $0.13 / 百萬 tokens | 大型專案、需要極高精確度 |
| `text-embedding-ada-002`（舊版） | 1536 | $0.10 / 百萬 tokens | 已被 small 取代 |

**成本估算範例**：
```
假設：上傳 20 份文件，每份 5000 字
總字數：20 × 5000 = 100,000 字
Token 數：約 150,000 tokens（中文 1 字 ≈ 1.5 tokens）

使用 text-embedding-3-small：
成本 = 0.15M tokens × $0.02 = $0.003（約 0.1 台幣）

每月 1000 次查詢（每次 100 字）：
成本 = 0.15M tokens × $0.02 = $0.003（約 0.1 台幣）

總計：約 0.2 台幣/月
```

**結論**：成本非常低廉，不用擔心！

---

## 第 3 部分：Supabase 資料庫設定

### 3.1 為什麼選擇 Supabase？

**Supabase = 開源的 Firebase 替代品（基於 PostgreSQL）**

**為什麼選它？**
1. ✅ **內建向量搜尋**（pgvector extension）- 專為 RAG 設計
2. ✅ **免費額度**：500 MB 資料庫 + 1 GB 檔案儲存
3. ✅ **簡單易用**：網頁介面管理，不需要寫 SQL
4. ✅ **自動備份**：資料不會遺失
5. ✅ **即時擴展**：流量變大時可以一鍵升級

**其他選擇比較**：

| 方案 | 優點 | 缺點 | 適用 |
|-----|------|-----|------|
| **Supabase + pgvector** | 免費、易用、向量搜尋原生支援 | 免費版有資料量限制 | ✅ 推薦新手 |
| Pinecone | 專為向量搜尋設計、效能極佳 | 付費（$70/月起） | 大型專案 |
| Weaviate | 開源、功能強大 | 需要自己架設伺服器 | 技術團隊 |
| 自建 PostgreSQL | 完全控制、無限制 | 需要維護、設定複雜 | 進階使用者 |

---

### 3.2 資料如何儲存？

**資料庫結構（ER Diagram）**

```
┌─────────────────┐
│   datasources   │ 資料來源（文件的來源）
│─────────────────│
│ id              │ 編號
│ type            │ 類型（pdf、url、text）
│ source_uri      │ 檔案路徑或網址
│ created_at      │ 建立時間
└─────────────────┘
         │
         │ 1 對多
         ↓
┌─────────────────┐
│   documents     │ 文件（每份 PDF、網頁）
│─────────────────│
│ id              │ 編號
│ datasource_id   │ 來源編號（外鍵）
│ title           │ 文件標題
│ bytes           │ 檔案大小
│ pages           │ 頁數
│ text_length     │ 文字長度
│ created_at      │ 建立時間
└─────────────────┘
         │
         │ 1 對多
         ↓
┌─────────────────┐
│     chunks      │ 文字片段（切好的段落）
│─────────────────│
│ id              │ 編號
│ doc_id          │ 文件編號（外鍵）
│ ordinal         │ 順序（第幾段）
│ text            │ 段落文字內容
│ chunk_strategy  │ 切片策略（sentence、fixed、semantic）
│ created_at      │ 建立時間
└─────────────────┘
         │
         │ 1 對 1
         ↓
┌─────────────────┐
│   embeddings    │ 向量（數字陣列）
│─────────────────│
│ id              │ 編號
│ chunk_id        │ 段落編號（外鍵）
│ embedding       │ 向量（1536 維陣列）⭐
│ created_at      │ 建立時間
└─────────────────┘
```

**實際資料範例**：

**documents 表**
| id | title | pages | text_length |
|----|-------|-------|-------------|
| 1 | 員工手冊.pdf | 50 | 25000 |
| 2 | 產品說明.pdf | 30 | 15000 |

**chunks 表**
| id | doc_id | ordinal | text |
|----|--------|---------|------|
| 1 | 1 | 0 | 「員工年假為 7 天，病假為 14 天...」 |
| 2 | 1 | 1 | 「特休假依年資計算，第一年 3 天...」 |
| 3 | 2 | 0 | 「產品功能包含：用戶管理、權限設定...」 |

**embeddings 表**
| id | chunk_id | embedding |
|----|----------|-----------|
| 1 | 1 | [0.23, -0.45, 0.67, ..., 0.12] |
| 2 | 2 | [0.25, -0.42, 0.70, ..., 0.15] |
| 3 | 3 | [-0.10, 0.30, -0.50, ..., 0.80] |

---

### 3.3 設定 Supabase 專案

**步驟 1：建立 Supabase 專案**

1. 前往 [https://supabase.com](https://supabase.com)
2. 點擊「Start your project」
3. 使用 GitHub 帳號登入
4. 點擊「New Project」
5. 填寫資訊：
   - **Name**: `my-rag-project`
   - **Database Password**: 設定強密碼（記下來！）
   - **Region**: 選擇「Northeast Asia (Tokyo)」（離台灣最近）
   - **Pricing Plan**: Free（免費版即可）
6. 點擊「Create new project」
7. 等待 2-3 分鐘，專案建立完成

---

**步驟 2：啟用 pgvector 擴充功能**

1. 點擊左側選單「Database」→「Extensions」
2. 搜尋「vector」
3. 找到「vector」，點擊「Enable」
4. 啟用成功！（現在可以儲存和搜尋向量）

---

**步驟 3：建立資料表**

1. 點擊左側選單「SQL Editor」
2. 點擊「New query」
3. 複製貼上以下 SQL（完整建表語法）：

```sql
-- 1. 建立 datasources 表
CREATE TABLE datasources (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    source_uri TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. 建立 documents 表
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    datasource_id INTEGER REFERENCES datasources(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    bytes INTEGER,
    pages INTEGER,
    text_length INTEGER,
    meta_json JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 3. 建立 chunks 表
CREATE TABLE chunks (
    id SERIAL PRIMARY KEY,
    doc_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    text TEXT NOT NULL,
    chunk_strategy VARCHAR(50) DEFAULT 'sentence',
    meta_json JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. 建立 embeddings 表（含向量欄位）
CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES chunks(id) ON DELETE CASCADE UNIQUE,
    embedding vector(1536),  -- ⭐ 向量欄位（1536 維）
    created_at TIMESTAMP DEFAULT NOW()
);

-- 5. 建立索引（加速向量搜尋）
CREATE INDEX idx_embeddings_vector
ON embeddings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 6. 建立外鍵索引（加速查詢）
CREATE INDEX idx_documents_datasource ON documents(datasource_id);
CREATE INDEX idx_chunks_doc ON chunks(doc_id);
CREATE INDEX idx_embeddings_chunk ON embeddings(chunk_id);
```

4. 點擊「Run」執行
5. 看到「Success. No rows returned」代表成功！

---

**步驟 4：取得連線資訊**

1. 點擊左側選單「Settings」→「Database」
2. 找到「Connection string」
3. 選擇「URI」模式
4. 複製類似這樣的連線字串：
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   ```
5. 將 `[YOUR-PASSWORD]` 替換成步驟 1 設定的密碼
6. **儲存起來**（後面會用到）

---

**步驟 5：設定儲存空間（Storage）**

1. 點擊左側選單「Storage」
2. 點擊「Create a new bucket」
3. 填寫：
   - **Name**: `documents`
   - **Public bucket**: 關閉（保持私有）
4. 點擊「Create bucket」
5. 完成！（用來儲存上傳的 PDF 檔案）

---

### 3.4 設定環境變數（.env 檔案）

**什麼是環境變數？為什麼要用 .env 檔案？**

**問題**：程式碼需要使用各種「密碼」和「金鑰」
- 資料庫密碼
- OpenAI API Key
- Supabase 金鑰

**❌ 錯誤做法：直接寫在程式碼裡**
```python
# ❌ 危險！千萬不要這樣做
DATABASE_URL = "postgresql://admin:YOUR_PASSWORD_HERE@db.example.com/mydb"
OPENAI_API_KEY = "sk-YOUR_OPENAI_API_KEY_HERE"

# 問題：
# 1. 上傳到 GitHub 時，全世界都看得到你的密碼
# 2. 開發/測試/正式環境的密碼不同，每次都要改程式碼
# 3. 團隊成員的密碼可能不同
```

**✅ 正確做法：使用 .env 檔案**
```python
# ✅ 安全！從環境變數讀取
import os
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 優點：
# 1. .env 檔案不會上傳到 GitHub（在 .gitignore 裡）
# 2. 每個環境可以有不同的 .env
# 3. 每個開發者可以用自己的密碼
```

---

**步驟 1：取得所需的金鑰和密碼**

**1.1 取得 Supabase 連線資訊**

前往你的 Supabase 專案：

1. 點擊左側選單「Settings」→「Database」
2. 找到「Connection string」區塊
3. 選擇「URI」模式
4. 複製連線字串，類似：
   ```
   postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres
   ```
5. **記下來**，等等會用到

---

**1.2 取得 Supabase API Keys**

1. 點擊左側選單「Settings」→「API」
2. 找到「Project API keys」區塊
3. 複製兩個 Key：

**Anon Key**（公開金鑰，前端可用）
```
your-supabase-anon-key-from-dashboard
```

**Service Role Key**（私密金鑰，後端專用）⚠️ 千萬不要外洩
```
your-supabase-anon-key-from-dashboard
```

4. **複製並儲存這兩個 Key**

---

**1.3 取得 Supabase URL**

在同一頁面「Settings」→「API」，找到：

**Project URL**
```
https://xxxxx.supabase.co
```

複製儲存

---

**1.4 取得 OpenAI API Key**

1. 前往 [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. 點擊「Create new secret key」
3. 命名：`rag-project-key`
4. 點擊「Create secret key」
5. **立即複製並儲存**（只會顯示一次！）
   ```
   sk-YOUR_OPENAI_API_KEY_STARTS_WITH_SK_PROJ
   ```
6. 如果忘記了，只能刪除重建

---

**步驟 2：建立 .env 檔案**

**2.1 在專案根目錄建立 .env 檔案**

**Mac / Linux 使用者**：
```bash
# 進入專案資料夾
cd /path/to/your/project

# 建立 .env 檔案
touch .env

# 用文字編輯器開啟
nano .env
# 或
code .env  # 如果有安裝 VS Code
```

**Windows 使用者**：
```bash
# 進入專案資料夾
cd C:\path\to\your\project

# 建立 .env 檔案
echo. > .env

# 用記事本開啟
notepad .env
```

---

**2.2 填寫環境變數**

在 `.env` 檔案中，貼上以下內容並**替換成你的實際值**：

```bash
# ============================================
# RAG 系統環境變數設定
# ============================================
# ⚠️ 此檔案包含敏感資訊，請勿上傳到 GitHub
# ============================================

# === 資料庫連線 ===
# 格式：postgresql://使用者名稱:密碼@主機位址:埠號/資料庫名稱
DATABASE_URL=postgresql://postgres.xxxxx:你的密碼@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres

# Direct connection（直接連線，不經過 Pooler）
DATABASE_URL_DIRECT=postgresql://postgres.xxxxx:你的密碼@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres

# === 系統安全金鑰 ===
# 用於加密 Session、JWT 等（至少 32 字元）
# 建議產生方式：openssl rand -hex 32
SECRET_KEY=請用亂數產生至少32字元的密鑰例如a1b2c3d4e5f6...

# === OpenAI API ===
OPENAI_API_KEY=sk-YOUR_OPENAI_API_KEY_HERE

# === Supabase ===
SUPABASE_URL=https://你的專案ID.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key-here
SUPABASE_SERVICE_KEY=your-supabase-service-key-here
```

---

**2.3 產生安全的 SECRET_KEY**

**方法 1：使用 OpenSSL（Mac / Linux）**
```bash
openssl rand -hex 32
```
輸出範例：
```
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```
複製這串，貼到 `.env` 的 `SECRET_KEY=` 後面

**方法 2：使用 Python**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**方法 3：線上產生器**
前往：[https://randomkeygen.com/](https://randomkeygen.com/)
選擇「Fort Knox Passwords」（256-bit 金鑰）

---

**步驟 3：驗證 .env 檔案格式**

**✅ 正確格式**：
```bash
DATABASE_URL=postgresql://user:pass@host:5432/db
OPENAI_API_KEY=sk-YOUR_OPENAI_API_KEY_HERE
```

**❌ 錯誤格式**：
```bash
# ❌ 不要有空格
DATABASE_URL = postgresql://...

# ❌ 不要用引號（除非值本身包含空格）
OPENAI_API_KEY="sk-YOUR_OPENAI_API_KEY_HERE"

# ❌ 不要有換行
DATABASE_URL=postgresql://user:pass
@host:5432/db
```

---

**步驟 4：確保 .env 不會上傳到 GitHub**

**4.1 檢查 .gitignore 檔案**

確認專案根目錄的 `.gitignore` 檔案包含：

```bash
# 環境變數（絕對不能上傳！）
.env
.env.local
.env.*.local

# 備份檔案
.env.backup
```

**4.2 驗證 .env 是否被忽略**

```bash
# 查看 Git 狀態
git status

# 如果看到 .env 出現在清單中 → ❌ 危險！
# 如果沒有看到 .env → ✅ 安全
```

**4.3 如果不小心已經 commit 了 .env 怎麼辦？**

```bash
# ⚠️ 緊急處理：從 Git 歷史中移除
git rm --cached .env
git commit -m "Remove .env from git history"

# ⚠️ 立即更換所有金鑰！
# 1. 重新產生 OpenAI API Key
# 2. 重設 Supabase 資料庫密碼
# 3. 重新產生 Supabase Service Key（在 Dashboard → Settings → API）
```

---

**步驟 5：測試環境變數是否正確載入**

**5.1 建立測試腳本**

建立檔案 `test_env.py`：

```python
import os
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

# 測試讀取
print("=== 環境變數測試 ===")
print(f"DATABASE_URL: {os.getenv('DATABASE_URL')[:30]}...")  # 只顯示前 30 字元
print(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')[:20]}...")
print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
print(f"SECRET_KEY length: {len(os.getenv('SECRET_KEY', ''))}")

# 驗證必要變數存在
required_vars = [
    "DATABASE_URL",
    "OPENAI_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "SECRET_KEY"
]

missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print("\n❌ 缺少以下環境變數：")
    for var in missing_vars:
        print(f"  - {var}")
else:
    print("\n✅ 所有必要的環境變數都已設定！")
```

**5.2 執行測試**

```bash
python test_env.py
```

**預期輸出**：
```
=== 環境變數測試 ===
DATABASE_URL: postgresql://postgres.xxxxx...
OPENAI_API_KEY: sk-YOUR_OPENAI_API_KEY_HERE...
SUPABASE_URL: https://xxxxx.supabase.co
SECRET_KEY length: 64

✅ 所有必要的環境變數都已設定！
```

如果看到 `❌ 缺少以下環境變數`，回到步驟 2 補齊。

---

**步驟 6：不同環境的 .env 管理**

**實務上，你會需要多個環境**：

```
專案/
├── .env                  # 本地開發（你自己的電腦）
├── .env.example          # 範本檔案（可上傳 GitHub）
├── .env.staging          # 測試環境（選用）
└── .env.production       # 正式環境（伺服器上）
```

---

**6.1 建立 .env.example 範本**

**目的**：告訴其他開發者需要哪些環境變數，但不包含實際的金鑰

建立檔案 `.env.example`：

```bash
# === SECRETS ONLY ===
# 請複製此檔案為 .env，並填入你的實際金鑰
# 本檔案可以上傳到 GitHub（範本用）

# 資料庫連線
DATABASE_URL=postgresql://YOUR_USER:YOUR_PASSWORD@YOUR_HOST:5432/YOUR_DATABASE
DATABASE_URL_DIRECT=postgresql://YOUR_USER:YOUR_PASSWORD@YOUR_HOST:5432/YOUR_DATABASE

# 系統安全金鑰（使用 openssl rand -hex 32 產生）
SECRET_KEY=your-secret-key-min-32-chars

# OpenAI API Key
OPENAI_API_KEY=sk-YOUR_OPENAI_KEY

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
```

這個檔案**可以安全上傳到 GitHub**，因為都是假的範例值。

---

**6.2 新開發者加入專案的步驟**

```bash
# 1. Clone 專案
git clone https://github.com/your-org/your-project.git
cd your-project

# 2. 複製範本
cp .env.example .env

# 3. 編輯 .env，填入自己的金鑰
nano .env
# 或
code .env

# 4. 測試
python test_env.py
```

---

**6.3 伺服器部署時的環境變數設定**

**雲端平台（Cloud Run、Heroku、Vercel 等）**：

不用上傳 `.env` 檔案！在平台的 Dashboard 設定環境變數：

**Google Cloud Run 範例**：
```bash
gcloud run deploy my-service \
  --set-env-vars DATABASE_URL="postgresql://..." \
  --set-env-vars OPENAI_API_KEY="sk-proj-..." \
  --set-env-vars SUPABASE_URL="https://..."
```

**或在 Web Console**：
1. 進入 Cloud Run → 選擇服務
2. 點擊「Edit & Deploy New Revision」
3. 展開「Variables & Secrets」
4. 點擊「Add Variable」
5. 逐一新增環境變數

---

**步驟 7：安全最佳實踐**

**✅ 應該做的**：
- ✅ 使用 `.env` 檔案儲存金鑰
- ✅ 將 `.env` 加入 `.gitignore`
- ✅ 提供 `.env.example` 範本
- ✅ 定期輪換金鑰（每 3-6 個月）
- ✅ 不同環境使用不同金鑰
- ✅ 限制 API Key 權限（例如設定每月預算上限）

**❌ 不應該做的**：
- ❌ 將 `.env` 上傳到 GitHub
- ❌ 在程式碼裡寫死金鑰
- ❌ 用 Email、Slack 傳送金鑰（用密碼管理器）
- ❌ 將正式環境的金鑰用在開發環境
- ❌ 將金鑰寫在截圖、文件裡

---

**步驟 8：常見問題排解**

**Q1：執行程式時出現 `KeyError: 'DATABASE_URL'`**

A：環境變數沒有正確載入

```python
# 確認有載入 .env
from dotenv import load_dotenv
load_dotenv()  # ← 加上這行

import os
DATABASE_URL = os.getenv("DATABASE_URL")
```

---

**Q2：.env 檔案在哪裡？**

A：專案根目錄（與 `app/`、`docs/` 同層）

```
your-project/
├── app/
├── docs/
├── .env          ← 在這裡
├── .env.example
├── .gitignore
└── README.md
```

---

**Q3：如何確認 .env 沒有上傳到 GitHub？**

```bash
# 方法 1：檢查 git status
git status
# 如果沒有看到 .env → 安全

# 方法 2：檢查遠端 repo
git ls-files | grep .env
# 如果沒有輸出 → 安全

# 方法 3：上 GitHub 網頁確認
# 專案頁面 → 檔案列表 → 不應該看到 .env
```

---

**Q4：團隊成員的 .env 檔案內容應該一樣嗎？**

A：**不一定**

- **相同**：開發環境的資料庫（共用測試 DB）
- **不同**：OpenAI API Key（每人自己申請，方便追蹤用量）

範例：
```bash
# 小明的 .env
DATABASE_URL=postgresql://shared-dev-db/...
OPENAI_API_KEY=sk-XIAOMING_OPENAI_KEY

# 小華的 .env
DATABASE_URL=postgresql://shared-dev-db/...
OPENAI_API_KEY=sk-XIAOHUA_OPENAI_KEY
```

---

**Q5：如何在 Docker 容器中使用 .env？**

**方法 1：使用 `--env-file`**
```bash
docker run --env-file .env my-image
```

**方法 2：在 `docker-compose.yml` 中**
```yaml
services:
  app:
    image: my-image
    env_file:
      - .env
```

---

### 3.5 理解資料表結構

**為什麼需要這麼多表？**

**❌ 錯誤設計：全部塞在一張表**
```sql
CREATE TABLE knowledge (
    id SERIAL,
    file_name TEXT,
    full_text TEXT,  -- ❌ 整份文件 10000 字
    embedding vector(1536)  -- ❌ 只有一個向量，無法精準搜尋
);
```
問題：
- 整份文件太長，AI 無法處理
- 只有一個向量，搜尋不精準

---

**✅ 正確設計：分層儲存**

1. **datasources**：記錄文件「來源」
   - 例如：「從 PDF 上傳」「從網址爬取」

2. **documents**：記錄「文件本身」
   - 例如：員工手冊.pdf（50 頁，25000 字）

3. **chunks**：將文件「切成小段落」
   - 例如：員工手冊切成 100 段，每段 400 字

4. **embeddings**：為每段落生成「向量」
   - 例如：段落 1 → 向量 1，段落 2 → 向量 2

**好處**：
- ✅ 搜尋更精準（段落級別搜尋）
- ✅ 可以追蹤來源（哪份文件、第幾段）
- ✅ 節省成本（只重新處理修改的段落）

---

## 第 4 部分：實際操作 - 建立你的 RAG 系統

### 4.1 上傳文件到知識庫

**方式 1：使用 Swagger UI（最簡單）**

1. 開啟 API 測試介面：
   ```
   https://your-api-url.com/docs
   ```

2. 找到 `POST /api/rag/ingest/files` 端點

3. 點擊「Try it out」

4. 填寫參數：
   ```json
   {
     "chunk_size": 400,
     "overlap": 80,
     "split_by_sentence": true
   }
   ```

5. 選擇檔案（點擊「Choose File」上傳 PDF）

6. 點擊「Execute」

7. 等待處理（約 10-30 秒）

8. 看到 Response：
   ```json
   {
     "message": "Successfully processed document",
     "document_id": 123,
     "chunks_created": 25,
     "time_taken": "15.3s"
   }
   ```

9. 完成！文件已上傳並向量化

---

**方式 2：使用 cURL 指令（適合批次上傳）**

```bash
curl -X POST "https://your-api-url.com/api/rag/ingest/files" \
  -F "file=@/path/to/your/document.pdf" \
  -F "chunk_size=400" \
  -F "overlap=80" \
  -F "split_by_sentence=true"
```

**批次上傳多個檔案**：

```bash
# 上傳資料夾內所有 PDF
for file in /path/to/documents/*.pdf; do
  curl -X POST "https://your-api-url.com/api/rag/ingest/files" \
    -F "file=@$file" \
    -F "chunk_size=400" \
    -F "overlap=80"
  echo "✅ Uploaded: $file"
done
```

---

**參數說明**：

| 參數 | 說明 | 建議值 |
|-----|------|--------|
| `chunk_size` | 每段落字數 | 400（中文約 200-250 字） |
| `overlap` | 段落重疊字數 | 80（避免重要句子被切斷） |
| `split_by_sentence` | 是否按句子切割 | true（更自然） |

---

**檢查上傳結果**：

1. 前往 Supabase 專案
2. 點擊「Table Editor」
3. 查看 `documents` 表：應該有新的文件
4. 查看 `chunks` 表：應該有 20-50 個段落
5. 查看 `embeddings` 表：應該有對應的向量

---

### 4.2 測試搜尋功能

**步驟 1：使用 Swagger UI 測試**

1. 開啟 `https://your-api-url.com/docs`
2. 找到 `POST /api/rag/search/` 端點
3. 點擊「Try it out」
4. 填寫測試問題：
   ```json
   {
     "query": "請假政策是什麼？",
     "top_k": 5,
     "similarity_threshold": 0.7
   }
   ```
5. 點擊「Execute」
6. 查看結果：
   ```json
   {
     "query": "請假政策是什麼？",
     "results": [
       {
         "chunk_id": 42,
         "document_title": "員工手冊.pdf",
         "text": "員工年假為 7 天，病假為 14 天...",
         "similarity_score": 0.92,
         "ordinal": 3
       },
       {
         "chunk_id": 43,
         "document_title": "員工手冊.pdf",
         "text": "特休假依年資計算...",
         "similarity_score": 0.85,
         "ordinal": 4
       }
     ],
     "total_results": 2
   }
   ```

---

**步驟 2：理解搜尋結果**

重要欄位解釋：

| 欄位 | 說明 | 範例值 |
|-----|------|--------|
| `text` | 找到的段落內容 | 「員工年假為 7 天...」 |
| `similarity_score` | 相似度分數（0-1） | 0.92（越高越相關） |
| `document_title` | 來源文件 | 「員工手冊.pdf」 |
| `ordinal` | 段落順序 | 3（第 3 段） |

---

**步驟 3：調整搜尋參數**

**參數 1：top_k（回傳數量）**
```json
{
  "query": "請假政策",
  "top_k": 3  // 只要前 3 個最相關的段落
}
```

**參數 2：similarity_threshold（相似度門檻）**
```json
{
  "query": "請假政策",
  "similarity_threshold": 0.8  // 只要相似度 > 0.8 的結果
}
```

**建議設定**：
- **一般搜尋**：`top_k=5`, `threshold=0.7`
- **精準搜尋**：`top_k=3`, `threshold=0.85`
- **廣泛搜尋**：`top_k=10`, `threshold=0.6`

---

### 4.3 測試智能問答

**步驟 1：使用完整 RAG 問答 API**

1. 找到 `POST /api/rag/chat` 端點（如果有的話）
2. 或使用本專案的報告生成 API：`POST /api/report/generate`

**範例 Request**：
```json
{
  "transcript": "我最近在考慮轉職，但不知道該往哪個方向發展...",
  "num_participants": 2,
  "mode": "enhanced",
  "rag_system": "openai",
  "top_k": 7,
  "similarity_threshold": 0.25
}
```

**範例 Response**：
```json
{
  "mode": "enhanced",
  "report": {
    "conceptualization": "【五、多層次因素分析】\n根據 Super 生涯發展理論 [1]，案主處於探索期...",
    "theories": [
      {
        "text": "Super 生涯發展理論指出...",
        "document": "職涯諮詢理論.pdf",
        "score": 0.89
      }
    ]
  }
}
```

**重點**：
- ✅ 系統會自動搜尋相關理論文獻
- ✅ 引用來源可追蹤（document 欄位）
- ✅ 相似度分數可驗證相關性（score 欄位）

---

**步驟 2：驗證 RAG 是否正常運作**

**測試 1：問已知問題**
```json
問題：「Super 生涯發展理論是什麼？」
預期：應該找到相關文獻並正確回答
```

**測試 2：問不存在的內容**
```json
問題：「我們公司的太空旅遊政策是什麼？」
預期：應該回答「沒有找到相關資料」（不會編造）
```

**測試 3：檢查引用來源**
```json
檢查回答中的 [1], [2] 引用編號
對照 theories 陣列中的 document 欄位
確認來源正確
```

---

### 4.4 整合到你的應用

**情境 1：整合到網站**

**前端 JavaScript 範例**：
```javascript
async function askQuestion() {
  const question = document.getElementById('question').value;

  const response = await fetch('https://your-api-url.com/api/rag/search/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      query: question,
      top_k: 5,
      similarity_threshold: 0.7
    })
  });

  const data = await response.json();

  // 顯示結果
  const resultsDiv = document.getElementById('results');
  data.results.forEach(result => {
    resultsDiv.innerHTML += `
      <div class="result">
        <p><strong>來源：</strong>${result.document_title}</p>
        <p><strong>內容：</strong>${result.text}</p>
        <p><strong>相似度：</strong>${(result.similarity_score * 100).toFixed(1)}%</p>
      </div>
    `;
  });
}
```

---

**情境 2：整合到 iOS App**

**Swift 範例**：
```swift
struct SearchRequest: Codable {
    let query: String
    let topK: Int
    let similarityThreshold: Double

    enum CodingKeys: String, CodingKey {
        case query
        case topK = "top_k"
        case similarityThreshold = "similarity_threshold"
    }
}

struct SearchResult: Codable {
    let chunkId: Int
    let documentTitle: String
    let text: String
    let similarityScore: Double

    enum CodingKeys: String, CodingKey {
        case chunkId = "chunk_id"
        case documentTitle = "document_title"
        case text
        case similarityScore = "similarity_score"
    }
}

func searchRAG(query: String) async throws -> [SearchResult] {
    let url = URL(string: "https://your-api-url.com/api/rag/search/")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")

    let requestBody = SearchRequest(
        query: query,
        topK: 5,
        similarityThreshold: 0.7
    )

    let encoder = JSONEncoder()
    request.httpBody = try encoder.encode(requestBody)

    let (data, _) = try await URLSession.shared.data(for: request)
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase

    let response = try decoder.decode([String: [SearchResult]].self, from: data)
    return response["results"] ?? []
}
```

---

**情境 3：整合到 Chatbot**

**基本流程**：
```python
# 1. 使用者提問
user_question = "如何申請特休假？"

# 2. 搜尋相關段落
search_results = rag_search(
    query=user_question,
    top_k=3,
    threshold=0.75
)

# 3. 組合 Prompt
context = "\n\n".join([r["text"] for r in search_results])
prompt = f"""
根據以下資料回答問題：

{context}

問題：{user_question}

請根據上述資料回答，不要編造不存在的資訊。
"""

# 4. 呼叫 GPT-4
answer = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}]
)

# 5. 回傳答案 + 來源
return {
    "answer": answer.choices[0].message.content,
    "sources": [r["document_title"] for r in search_results]
}
```

---

## 第 5 部分：建立完整的前後端系統（2-3 小時）

**目標**：建立一個完整的 RAG 文件管理系統，包含：
1. 📤 上傳文件介面
2. 📊 查看文件資訊
3. ✂️ CRUD 文件 Chunks 管理
4. 🔍 搜尋測試介面

**為什麼需要前後端系統？**

在前面的章節中，我們學會了 RAG 的概念、OpenAI Embedding、Supabase 資料庫設定，以及如何用指令建立搜尋功能。但是，這些都是通過指令行（Terminal）來操作的。

想像一下：如果你的同事或客戶想要上傳文件、查看文件資訊、或是測試搜尋功能，你總不能要求他們打開 Terminal 輸入指令吧？這就是為什麼我們需要一個**使用者介面（UI）**。

**前後端系統的角色分工**：

- **後端（Backend）**：處理業務邏輯的「大廚」
  - 接收前端的請求（上傳文件、搜尋等）
  - 處理 PDF 文字提取
  - 調用 OpenAI API 生成 embeddings
  - 操作 Supabase 資料庫
  - 回傳處理結果給前端

- **前端（Frontend）**：使用者互動的「服務生」
  - 提供漂亮的介面讓使用者操作
  - 拖拉上傳檔案
  - 顯示文件列表
  - 編輯 Chunks
  - 顯示搜尋結果

**這一章節你會學到**：

1. 如何用 FastAPI 建立 REST API（後端）
2. 如何建立 HTML/CSS/JavaScript 前端介面
3. 如何讓前後端溝通（AJAX requests）
4. 如何部署到雲端（Google Cloud Run）

**預計完成時間**：2-3 小時

---

### 5.1 後端 API 實作（45 分鐘）

#### 5.1.1 專案架構設計

**完整架構圖**：

```
your-rag-project/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 主程式
│   ├── core/
│   │   ├── config.py            # 環境變數設定
│   │   └── database.py          # 資料庫連線
│   ├── models/
│   │   └── document.py          # SQLAlchemy 模型
│   ├── services/
│   │   ├── openai_service.py    # OpenAI API
│   │   ├── pdf_service.py       # PDF 處理
│   │   ├── chunking.py          # 文字切片
│   │   └── storage.py           # Supabase Storage
│   └── api/
│       ├── rag_ingest.py        # 文件上傳 API
│       ├── rag_stats.py         # 文件統計 API
│       ├── rag_chunks.py        # Chunks CRUD API
│       └── rag_search.py        # 搜尋 API
├── static/
│   └── index.html               # 前端介面
├── .env                         # 環境變數（不上傳）
├── .env.example                 # 環境變數範本
├── requirements.txt             # Python 套件
└── README.md
```

**說明**：

- `app/core/`: 核心設定（資料庫連線、環境變數）
- `app/models/`: 資料庫模型（對應 documents, chunks, embeddings 表格）
- `app/services/`: 業務邏輯（OpenAI、PDF 處理、文字切片）
- `app/api/`: API 端點（處理 HTTP 請求）
- `static/`: 前端 HTML 檔案

---

#### 5.1.2 建立 FastAPI 專案

**步驟 1：初始化專案**

```bash
# 建立專案資料夾
mkdir rag-system
cd rag-system

# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境
source venv/bin/activate  # Mac/Linux
# 或
venv\Scripts\activate  # Windows

# 安裝套件
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv openai supabase pypdf
```

---

**步驟 2：建立 requirements.txt**

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
python-dotenv==1.0.0
openai==1.3.5
supabase==2.0.3
pypdf==3.17.1
pydantic==2.5.0
pydantic-settings==2.1.0
pgvector==0.2.3
```

---

**步驟 3：建立專案結構**

```bash
# 建立資料夾
mkdir -p app/core app/models app/services app/api static

# 建立檔案
touch app/__init__.py
touch app/main.py
touch app/core/__init__.py
touch app/core/config.py
touch app/core/database.py
touch app/models/__init__.py
touch app/models/document.py
touch app/services/__init__.py
touch app/api/__init__.py
touch .env
touch .env.example
```

---

#### 5.1.3 實作核心模組

**app/core/config.py**（環境變數設定）

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
```

**說明**：這個檔案會自動從 `.env` 讀取環境變數。

---

**app/core/database.py**（資料庫連線）

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# 建立資料庫引擎
engine = create_engine(settings.DATABASE_URL)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """Dependency for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**說明**：`get_db()` 是一個 Dependency，FastAPI 會在每次請求時自動注入資料庫 session。

---

**app/models/document.py**（資料庫模型）

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSONB
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class Datasource(Base):
    __tablename__ = "datasources"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False)  # "pdf", "url", "text"
    source_uri = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(Integer, ForeignKey("datasources.id", ondelete="CASCADE"))
    title = Column(String(500), nullable=False)
    bytes = Column(Integer)
    pages = Column(Integer)
    text_length = Column(Integer)
    content = Column(Text)  # 原始文字
    meta_json = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    ordinal = Column(Integer, nullable=False)  # 順序
    text = Column(Text, nullable=False)
    chunk_strategy = Column(String(50), default="sentence")
    meta_json = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(Integer, ForeignKey("chunks.id", ondelete="CASCADE"), unique=True)
    embedding = Column(Vector(1536))  # OpenAI embedding 維度
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**說明**：
- `ondelete="CASCADE"`：刪除 document 時，自動刪除關聯的 chunks 和 embeddings
- `Vector(1536)`：OpenAI text-embedding-3-small 的向量維度

---

#### 5.1.4 實作文件上傳 API

**app/api/rag_ingest.py**

```python
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models.document import Datasource, Document, Chunk, Embedding
from app.services.openai_service import OpenAIService
from app.services.pdf_service import PDFService
from app.services.chunking import ChunkingService
from app.services.storage import StorageService

router = APIRouter(prefix="/api/rag/ingest", tags=["rag-ingest"])

class IngestResponse(BaseModel):
    datasource_id: int
    document_id: int
    chunks_created: int
    embeddings_created: int
    message: str

@router.post("/files", response_model=IngestResponse)
async def ingest_file(
    file: UploadFile = File(...),
    chunk_size: int = 400,
    overlap: int = 80,
    db: Session = Depends(get_db)
):
    """上傳並處理 PDF 文件"""

    # 驗證檔案類型
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支援 PDF 檔案")

    # 讀取檔案內容
    file_content = await file.read()

    # 1. 上傳到 Supabase Storage
    storage = StorageService()
    safe_filename = f"{uuid.uuid4()}.pdf"
    storage_url = await storage.upload_file(
        file_content,
        f"documents/{safe_filename}",
        content_type="application/pdf"
    )

    # 2. 提取 PDF 文字
    pdf_service = PDFService()
    text = pdf_service.extract_text(file_content)
    metadata = pdf_service.extract_metadata(file_content)

    # 移除 PostgreSQL 無法儲存的 NUL 字元
    text = text.replace("\x00", "")

    # 3. 建立資料庫記錄
    datasource = Datasource(type="pdf", source_uri=storage_url)
    db.add(datasource)
    db.flush()

    document = Document(
        datasource_id=datasource.id,
        title=file.filename,
        bytes=len(file_content),
        pages=metadata.get("pages", 0),
        content=text,
        text_length=len(text),
        meta_json=metadata
    )
    db.add(document)
    db.flush()

    # 4. 文字切片
    chunking = ChunkingService(chunk_size=chunk_size, overlap=overlap)
    chunks = chunking.split_text(text, split_by_sentence=True)

    # 5. 生成 embeddings
    openai = OpenAIService()

    for idx, chunk_text in enumerate(chunks):
        chunk_text = chunk_text.replace("\x00", "")

        # 建立 chunk 記錄
        chunk = Chunk(
            doc_id=document.id,
            ordinal=idx,
            text=chunk_text,
            chunk_strategy=f"rec_{chunk_size}_{overlap}"
        )
        db.add(chunk)
        db.flush()

        # 生成 embedding
        embedding_vector = await openai.create_embedding(chunk_text)
        embedding = Embedding(chunk_id=chunk.id, embedding=embedding_vector)
        db.add(embedding)

    db.commit()

    return IngestResponse(
        datasource_id=datasource.id,
        document_id=document.id,
        chunks_created=len(chunks),
        embeddings_created=len(chunks),
        message=f"成功處理 {file.filename}"
    )
```

**流程說明**：

1. **驗證檔案**：確認是 PDF 檔案
2. **上傳到 Supabase Storage**：儲存原始檔案
3. **提取 PDF 文字**：使用 PyPDF 提取文字內容
4. **建立資料庫記錄**：datasource → document
5. **文字切片**：將長文本切成 400 字的 chunks
6. **生成 embeddings**：調用 OpenAI API 生成向量

---

#### 5.1.5 實作文件統計 API

**app/api/rag_stats.py**

```python
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db

router = APIRouter(prefix="/api/rag/stats", tags=["rag-stats"])

class DocumentStats(BaseModel):
    id: int
    title: str
    pages: int
    bytes: int
    chunks_count: int
    embeddings_count: int
    text_length: int
    created_at: str

class DatabaseStats(BaseModel):
    total_documents: int
    total_chunks: int
    total_embeddings: int
    total_bytes: int
    documents: List[DocumentStats]

@router.get("/", response_model=DatabaseStats)
def get_stats(db: Session = Depends(get_db)):
    """取得資料庫統計資料"""

    # 總計
    total_docs = db.execute(text("SELECT COUNT(*) FROM documents")).scalar()
    total_chunks = db.execute(text("SELECT COUNT(*) FROM chunks")).scalar()
    total_embeddings = db.execute(text("SELECT COUNT(*) FROM embeddings")).scalar()
    total_bytes = db.execute(text("SELECT COALESCE(SUM(bytes), 0) FROM documents")).scalar()

    # 文件詳情
    query = text("""
        SELECT
            d.id, d.title, d.pages, d.bytes, d.text_length, d.created_at,
            COUNT(c.id) as chunks_count,
            COUNT(e.id) as embeddings_count
        FROM documents d
        LEFT JOIN chunks c ON d.id = c.doc_id
        LEFT JOIN embeddings e ON c.id = e.chunk_id
        GROUP BY d.id
        ORDER BY d.created_at DESC
    """)

    result = db.execute(query)
    rows = result.fetchall()

    documents = [
        DocumentStats(
            id=row.id,
            title=row.title,
            pages=row.pages or 0,
            bytes=row.bytes or 0,
            chunks_count=row.chunks_count or 0,
            embeddings_count=row.embeddings_count or 0,
            text_length=row.text_length or 0,
            created_at=str(row.created_at)
        )
        for row in rows
    ]

    return DatabaseStats(
        total_documents=total_docs or 0,
        total_chunks=total_chunks or 0,
        total_embeddings=total_embeddings or 0,
        total_bytes=total_bytes or 0,
        documents=documents
    )

@router.delete("/documents/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    """刪除文件（cascade 刪除 chunks 和 embeddings）"""

    # 檢查文件是否存在
    doc = db.execute(
        text("SELECT id FROM documents WHERE id = :id"),
        {"id": doc_id}
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")

    # Cascade 刪除（FK constraint 會自動處理）
    db.execute(
        text("DELETE FROM documents WHERE id = :id"),
        {"id": doc_id}
    )
    db.commit()

    return {"success": True, "message": f"成功刪除文件 {doc_id}"}
```

**功能**：
- `GET /api/rag/stats/`：取得資料庫統計（總文件數、chunks 數、embeddings 數、總大小）
- `DELETE /api/rag/stats/documents/{doc_id}`：刪除文件（自動刪除關聯的 chunks 和 embeddings）

---

#### 5.1.6 實作 Chunks CRUD API

**app/api/rag_chunks.py**

```python
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.services.openai_service import OpenAIService

router = APIRouter(prefix="/api/rag/chunks", tags=["rag-chunks"])

class ChunkDetail(BaseModel):
    id: int
    ordinal: int
    text: str
    text_length: int
    document_title: str

class ChunkUpdate(BaseModel):
    text: str

@router.get("/{doc_id}", response_model=List[ChunkDetail])
def get_chunks(doc_id: int, db: Session = Depends(get_db)):
    """取得文件的所有 chunks"""

    query = text("""
        SELECT
            c.id, c.ordinal, c.text,
            LENGTH(c.text) as text_length,
            d.title as document_title
        FROM chunks c
        JOIN documents d ON c.doc_id = d.id
        WHERE c.doc_id = :doc_id
        ORDER BY c.ordinal
    """)

    result = db.execute(query, {"doc_id": doc_id})
    rows = result.fetchall()

    return [
        ChunkDetail(
            id=row.id,
            ordinal=row.ordinal,
            text=row.text,
            text_length=row.text_length,
            document_title=row.document_title
        )
        for row in rows
    ]

@router.put("/{chunk_id}")
async def update_chunk(
    chunk_id: int,
    data: ChunkUpdate,
    db: Session = Depends(get_db)
):
    """更新 chunk 文字（會重新生成 embedding）"""

    # 檢查 chunk 是否存在
    chunk = db.execute(
        text("SELECT id FROM chunks WHERE id = :id"),
        {"id": chunk_id}
    ).first()

    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk 不存在")

    # 更新文字
    db.execute(
        text("UPDATE chunks SET text = :text WHERE id = :id"),
        {"text": data.text, "id": chunk_id}
    )

    # 重新生成 embedding
    openai = OpenAIService()
    new_embedding = await openai.create_embedding(data.text)

    db.execute(
        text("UPDATE embeddings SET embedding = :embedding WHERE chunk_id = :chunk_id"),
        {"embedding": new_embedding, "chunk_id": chunk_id}
    )

    db.commit()

    return {"success": True, "message": "Chunk 更新成功"}

@router.delete("/{chunk_id}")
def delete_chunk(chunk_id: int, db: Session = Depends(get_db)):
    """刪除 chunk（會自動刪除 embedding）"""

    db.execute(
        text("DELETE FROM chunks WHERE id = :id"),
        {"id": chunk_id}
    )
    db.commit()

    return {"success": True, "message": "Chunk 刪除成功"}

@router.post("/")
async def create_chunk(
    doc_id: int,
    text: str,
    ordinal: int,
    db: Session = Depends(get_db)
):
    """新增 chunk"""

    # 建立 chunk
    result = db.execute(
        text("""
            INSERT INTO chunks (doc_id, ordinal, text, chunk_strategy)
            VALUES (:doc_id, :ordinal, :text, 'manual')
            RETURNING id
        """),
        {"doc_id": doc_id, "ordinal": ordinal, "text": text}
    )
    chunk_id = result.scalar()

    # 生成 embedding
    openai = OpenAIService()
    embedding_vector = await openai.create_embedding(text)

    db.execute(
        text("INSERT INTO embeddings (chunk_id, embedding) VALUES (:chunk_id, :embedding)"),
        {"chunk_id": chunk_id, "embedding": embedding_vector}
    )

    db.commit()

    return {"success": True, "chunk_id": chunk_id, "message": "Chunk 建立成功"}
```

**功能**：
- `GET /api/rag/chunks/{doc_id}`：取得文件的所有 chunks
- `PUT /api/rag/chunks/{chunk_id}`：更新 chunk（會重新生成 embedding）
- `DELETE /api/rag/chunks/{chunk_id}`：刪除 chunk
- `POST /api/rag/chunks/`：新增 chunk

**重點**：更新 chunk 文字時，必須重新調用 OpenAI API 生成新的 embedding。

---

#### 5.1.7 實作搜尋 API

**app/api/rag_search.py**

```python
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.services.openai_service import OpenAIService

router = APIRouter(prefix="/api/rag/search", tags=["rag-search"])

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    similarity_threshold: float = 0.7

class SearchResult(BaseModel):
    chunk_id: int
    document_title: str
    text: str
    similarity_score: float
    ordinal: int

@router.post("/", response_model=List[SearchResult])
async def search(request: SearchRequest, db: Session = Depends(get_db)):
    """向量相似度搜尋"""

    # 生成 query embedding
    openai = OpenAIService()
    query_embedding = await openai.create_embedding(request.query)
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    # 向量搜尋
    query_sql = text("""
        SELECT
            c.id as chunk_id,
            c.ordinal,
            c.text,
            d.title as document_title,
            1 - (e.embedding <=> CAST(:query_embedding AS vector)) as similarity_score
        FROM chunks c
        JOIN embeddings e ON c.id = e.chunk_id
        JOIN documents d ON c.doc_id = d.id
        WHERE 1 - (e.embedding <=> CAST(:query_embedding AS vector)) >= :threshold
        ORDER BY e.embedding <=> CAST(:query_embedding AS vector)
        LIMIT :top_k
    """)

    result = db.execute(query_sql, {
        "query_embedding": embedding_str,
        "threshold": request.similarity_threshold,
        "top_k": request.top_k
    })

    rows = result.fetchall()

    return [
        SearchResult(
            chunk_id=row.chunk_id,
            document_title=row.document_title,
            text=row.text,
            similarity_score=float(row.similarity_score),
            ordinal=row.ordinal
        )
        for row in rows
    ]
```

**說明**：
- `<=>` 是 pgvector 的餘弦距離運算子
- `1 - (embedding <=> query_embedding)` 轉換成相似度（越接近 1 越相似）
- `ORDER BY ... LIMIT :top_k` 取得前 K 個最相似的結果

---

#### 5.1.8 主程式

**app/main.py**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api import rag_ingest, rag_stats, rag_chunks, rag_search

app = FastAPI(title="RAG 文件管理系統", version="1.0.0")

# CORS（允許前端存取）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊 API 路由
app.include_router(rag_ingest.router)
app.include_router(rag_stats.router)
app.include_router(rag_chunks.router)
app.include_router(rag_search.router)

# 靜態檔案（前端介面）
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return {"message": "RAG 文件管理系統 API"}

@app.get("/health")
def health():
    return {"status": "ok"}
```

**說明**：
- `CORSMiddleware`：允許前端跨域請求
- `app.include_router()`：註冊 API 路由
- `app.mount("/static", ...)`：提供靜態檔案服務

---

### 5.2 前端介面實作（60 分鐘）

前端使用純 HTML + CSS + JavaScript（不需要 React/Vue），適合快速建立原型。

**static/index.html**（完整前端介面，包含 4 個功能頁籤）

由於完整的 HTML 檔案較長（約 700 行），這裡我將分段解釋關鍵部分。

#### 5.2.1 HTML 結構

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAG 文件管理系統</title>
    <style>
        /* CSS 樣式（見下方） */
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>📚 RAG 文件管理系統</h1>
            <p>上傳文件、管理 Chunks、測試搜尋</p>

            <!-- Tabs -->
            <div class="tabs">
                <button class="tab active" onclick="switchTab('upload')">📤 上傳文件</button>
                <button class="tab" onclick="switchTab('documents')">📊 文件列表</button>
                <button class="tab" onclick="switchTab('chunks')">✂️ Chunks 管理</button>
                <button class="tab" onclick="switchTab('search')">🔍 搜尋測試</button>
            </div>
        </div>

        <!-- Tab 1: 上傳文件 -->
        <div id="tab-upload" class="tab-content active">
            <!-- 上傳介面 -->
        </div>

        <!-- Tab 2: 文件列表 -->
        <div id="tab-documents" class="tab-content">
            <!-- 統計卡片 + 文件表格 -->
        </div>

        <!-- Tab 3: Chunks 管理 -->
        <div id="tab-chunks" class="tab-content">
            <!-- Chunks 列表 + 編輯功能 -->
        </div>

        <!-- Tab 4: 搜尋測試 -->
        <div id="tab-search" class="tab-content">
            <!-- 搜尋框 + 結果顯示 -->
        </div>
    </div>

    <!-- Edit Chunk Modal -->
    <div id="editModal" class="modal">
        <!-- 編輯 Chunk 的彈出視窗 -->
    </div>

    <script>
        /* JavaScript 程式（見下方） */
    </script>
</body>
</html>
```

**結構說明**：

- **4 個 Tab**：上傳文件、文件列表、Chunks 管理、搜尋測試
- **Modal**：用於編輯 Chunk 的彈出視窗
- **CSS**：內嵌在 `<style>` 標籤中
- **JavaScript**：內嵌在 `<script>` 標籤中

完整的 `static/index.html` 檔案內容請參考專案中的 `docs/RAG_FRONTEND_BACKEND_TUTORIAL.md` 第 2 部分（lines 708-1372），或直接使用以下完整版本。

---

#### 5.2.2 關鍵 JavaScript 功能

**1. Tab 切換**

```javascript
function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    event.target.classList.add('active');
    document.getElementById(`tab-${tabName}`).classList.add('active');

    if (tabName === 'documents') loadDocuments();
    if (tabName === 'chunks') loadDocumentList();
}
```

**2. 檔案上傳（拖拉功能）**

```javascript
const uploadZone = document.getElementById('uploadZone');

uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        document.getElementById('fileInput').files = files;
        handleFileSelect({target: {files}});
    }
});
```

**3. 調用後端 API 上傳檔案**

```javascript
async function uploadFile() {
    if (!selectedFile) {
        alert('請先選擇檔案');
        return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('chunk_size', document.getElementById('chunkSize').value);
    formData.append('overlap', document.getElementById('overlap').value);

    const status = document.getElementById('uploadStatus');
    status.innerHTML = '<div class="loading">⏳ 處理中...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/rag/ingest/files`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            status.innerHTML = `
                <div class="result-card">
                    <h3>✅ 上傳成功！</h3>
                    <p>文件 ID: ${data.document_id}</p>
                    <p>建立 ${data.chunks_created} 個 chunks</p>
                    <p>建立 ${data.embeddings_created} 個 embeddings</p>
                </div>
            `;
            selectedFile = null;
            document.getElementById('fileInput').value = '';
            document.getElementById('uploadZone').innerHTML = '<p>📄 點擊或拖曳 PDF 檔案到這裡</p>';
        } else {
            status.innerHTML = `<div class="result-card" style="border-left-color: #dc3545;">❌ 錯誤: ${data.detail}</div>`;
        }
    } catch (error) {
        status.innerHTML = `<div class="result-card" style="border-left-color: #dc3545;">❌ 網路錯誤: ${error.message}</div>`;
    }
}
```

**4. 載入文件列表**

```javascript
async function loadDocuments() {
    const tbody = document.getElementById('documentsTableBody');
    const statsGrid = document.getElementById('statsGrid');
    tbody.innerHTML = '<tr><td colspan="7" class="loading">載入中...</td></tr>';

    try {
        const response = await fetch(`${API_BASE}/api/rag/stats/`);
        const data = await response.json();

        // 統計卡片
        statsGrid.innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${data.total_documents}</div>
                <div class="stat-label">文件總數</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.total_chunks}</div>
                <div class="stat-label">Chunks 總數</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.total_embeddings}</div>
                <div class="stat-label">Embeddings 總數</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${(data.total_bytes / 1024 / 1024).toFixed(2)} MB</div>
                <div class="stat-label">總大小</div>
            </div>
        `;

        // 文件表格
        tbody.innerHTML = data.documents.map(doc => `
            <tr>
                <td>${doc.id}</td>
                <td>${doc.title}</td>
                <td>${doc.pages}</td>
                <td>${(doc.bytes / 1024).toFixed(2)} KB</td>
                <td>${doc.chunks_count}</td>
                <td>${new Date(doc.created_at).toLocaleString('zh-TW')}</td>
                <td>
                    <button class="btn" onclick="viewChunks(${doc.id})">檢視 Chunks</button>
                    <button class="btn btn-danger" onclick="deleteDocument(${doc.id})">刪除</button>
                </td>
            </tr>
        `).join('');

    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading">載入失敗</td></tr>';
    }
}
```

**5. 編輯 Chunk**

```javascript
function editChunk(chunkId, text) {
    currentChunkId = chunkId;
    document.getElementById('chunkEditor').value = text;
    document.getElementById('editModal').classList.add('active');
}

async function saveChunk() {
    const newText = document.getElementById('chunkEditor').value;

    try {
        const response = await fetch(`${API_BASE}/api/rag/chunks/${currentChunkId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text: newText})
        });

        if (response.ok) {
            alert('儲存成功');
            closeModal();
            loadChunks();
        }
    } catch (error) {
        alert('儲存失敗: ' + error.message);
    }
}
```

**6. 執行搜尋**

```javascript
async function performSearch() {
    const query = document.getElementById('searchQuery').value;
    const topK = parseInt(document.getElementById('topK').value);
    const threshold = parseFloat(document.getElementById('threshold').value);
    const resultsDiv = document.getElementById('searchResults');

    if (!query) {
        alert('請輸入搜尋問題');
        return;
    }

    resultsDiv.innerHTML = '<div class="loading">搜尋中...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/rag/search/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                query: query,
                top_k: topK,
                similarity_threshold: threshold
            })
        });

        const results = await response.json();

        if (results.length === 0) {
            resultsDiv.innerHTML = '<div class="loading">😔 沒有找到相關結果，試著降低相似度門檻</div>';
            return;
        }

        resultsDiv.innerHTML = `
            <h3>找到 ${results.length} 個結果</h3>
            ${results.map((result, idx) => `
                <div class="result-card">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div style="flex: 1;">
                            <div>
                                <strong>結果 #${idx + 1}</strong>
                                <span class="result-score">${(result.similarity_score * 100).toFixed(1)}%</span>
                            </div>
                            <p style="color: #666; margin-top: 5px;">📄 ${result.document_title} (Chunk #${result.ordinal})</p>
                            <p style="margin-top: 10px; color: #333;">${result.text}</p>
                        </div>
                    </div>
                </div>
            `).join('')}
        `;

    } catch (error) {
        resultsDiv.innerHTML = `<div class="loading">❌ 搜尋失敗: ${error.message}</div>`;
    }
}
```

---

### 5.3 本地測試（15 分鐘）

**步驟 1：確認環境變數**

確保你的 `.env` 檔案包含以下內容（從第 3 部分複製）：

```bash
DATABASE_URL=postgresql://postgres.xxx:password@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
OPENAI_API_KEY=sk-YOUR_OPENAI_KEY
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=your-supabase-key-here
SECRET_KEY=your-secret-key-min-32-chars
```

---

**步驟 2：安裝套件**

```bash
pip install -r requirements.txt
```

---

**步驟 3：啟動後端**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

你應該會看到：

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

**步驟 4：開啟前端**

瀏覽器前往：`http://localhost:8000/static/index.html`

---

**步驟 5：測試功能**

1. **上傳 PDF 文件**
   - 點擊「📤 上傳文件」頁籤
   - 拖曳一個 PDF 檔案到上傳區域
   - 點擊「🚀 開始上傳」
   - 等待處理完成（可能需要 10-30 秒，取決於檔案大小）

2. **查看文件列表**
   - 點擊「📊 文件列表」頁籤
   - 查看統計卡片（文件總數、Chunks 總數、Embeddings 總數、總大小）
   - 查看文件表格（檔名、頁數、大小、Chunks 數量、上傳時間）

3. **管理 Chunks**
   - 點擊「✂️ Chunks 管理」頁籤
   - 從下拉選單選擇一個文件
   - 查看該文件的所有 chunks
   - 點擊「編輯」按鈕，修改 chunk 文字
   - 點擊「刪除」按鈕，刪除 chunk

4. **測試搜尋**
   - 點擊「🔍 搜尋測試」頁籤
   - 輸入搜尋問題（例如：「職業探索的方法」）
   - 設定 Top K（回傳數量）和相似度門檻
   - 點擊「🔍 搜尋」
   - 查看搜尋結果（包含相似度分數、文件標題、chunk 內容）

---

### 5.4 部署到 Cloud Run（30 分鐘）

**步驟 1：建立 Dockerfile**

在專案根目錄建立 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**說明**：
- `FROM python:3.11-slim`：使用精簡版 Python 映像檔
- `WORKDIR /app`：設定工作目錄
- `COPY requirements.txt .`：複製套件清單
- `RUN pip install ...`：安裝套件
- `COPY . .`：複製所有專案檔案
- `CMD ["uvicorn", ...]`：啟動 FastAPI（Cloud Run 使用 port 8080）

---

**步驟 2：部署到 Cloud Run**

```bash
# 登入 Google Cloud
gcloud auth login

# 設定專案 ID
gcloud config set project YOUR_PROJECT_ID

# 部署
gcloud run deploy rag-system \
  --source . \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL="postgresql://postgres.xxx:password@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres" \
  --set-env-vars OPENAI_API_KEY="sk-YOUR_OPENAI_KEY" \
  --set-env-vars SUPABASE_URL="https://xxx.supabase.co" \
  --set-env-vars SUPABASE_SERVICE_KEY="your-supabase-key-here" \
  --set-env-vars SECRET_KEY="your-secret-key-min-32-chars"
```

**說明**：
- `--source .`：使用當前目錄的原始碼（Cloud Run 會自動建立 Docker 映像檔）
- `--region asia-east1`：部署到亞洲東部（台灣鄰近地區）
- `--allow-unauthenticated`：允許未認證的請求（公開存取）
- `--set-env-vars ...`：設定環境變數

---

**步驟 3：取得部署 URL**

部署完成後，你會看到：

```
Service [rag-system] revision [rag-system-00001-abc] has been deployed and is serving 100 percent of traffic.
Service URL: https://rag-system-abcdefg-de.a.run.app
```

複製 Service URL，例如：`https://rag-system-abcdefg-de.a.run.app`

---

**步驟 4：開啟前端**

瀏覽器前往：`https://rag-system-abcdefg-de.a.run.app/static/index.html`

現在你的 RAG 系統已經在雲端上運行了！

---

### 5.5 常見問題排解

**Q1: CORS 錯誤**

```
Access to fetch at 'http://localhost:8000/api/rag/stats/' from origin 'http://localhost:3000' has been blocked by CORS policy
```

**A**：確認 `app/main.py` 有加入 CORS middleware

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

**Q2: 上傳檔案失敗**

```
HTTPException: Supabase bucket 'documents' not found
```

**A**：檢查 Supabase Storage bucket 是否建立

1. 前往 Supabase Dashboard → Storage
2. 建立一個名為 `documents` 的 bucket
3. 設定為 Public（或設定適當的存取權限）

---

**Q3: 搜尋沒有結果**

**A**：降低相似度門檻

- 預設門檻是 `0.7`（70% 相似度）
- 試著降低到 `0.5` 或 `0.3`
- 或者增加 `top_k` 數量（從 5 改成 10）

---

**Q4: Database connection failed**

**A**：檢查 `DATABASE_URL` 格式

確保 `.env` 檔案中的 `DATABASE_URL` 格式正確：

```bash
DATABASE_URL=postgresql://postgres.xxx:password@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
```

---

**Q5: OpenAI API rate limit**

```
openai.error.RateLimitError: You exceeded your current quota
```

**A**：檢查 OpenAI API 額度

1. 前往 https://platform.openai.com/account/usage
2. 確認你有足夠的額度
3. 或升級到付費方案

---

### 5.6 總結

恭喜！你已經建立了一個完整的 RAG 文件管理系統！

**功能清單**：
- ✅ 上傳 PDF 文件
- ✅ 自動切片 + 生成 embeddings
- ✅ 文件列表與統計
- ✅ Chunks CRUD 管理
- ✅ 向量相似度搜尋
- ✅ 漂亮的前端介面
- ✅ 部署到 Cloud Run

**你學到了**：

1. **後端開發**：
   - FastAPI 路由設計
   - SQLAlchemy ORM
   - Pydantic 資料驗證
   - 非同步處理（async/await）
   - CORS 設定

2. **前端開發**：
   - HTML/CSS/JavaScript
   - Fetch API（AJAX 請求）
   - DOM 操作
   - 拖拉上傳功能
   - Modal 彈出視窗

3. **系統整合**：
   - 前後端溝通
   - RESTful API 設計
   - 環境變數管理
   - Docker 容器化
   - Cloud Run 部署

**下一步**：

1. 🎨 **客製化介面樣式**：修改 CSS 顏色、字型、排版
2. 🔐 **加入使用者認證**：使用 Supabase Auth 或 JWT
3. 📊 **進階統計分析**：圖表視覺化（Chart.js）
4. 🤖 **整合 Chatbot 功能**：使用 OpenAI Chat API + RAG 搜尋結果
5. 📱 **RWD 響應式設計**：支援手機、平板
6. 🧪 **單元測試**：使用 pytest 測試 API
7. 📈 **監控與日誌**：使用 Sentry 或 Google Cloud Logging

---

## 附錄

### 常見問題 FAQ

**Q1：上傳文件後多久可以搜尋？**

A：立即可以搜尋！流程如下：
- 上傳 PDF（5 秒）
- 提取文字（5 秒）
- 切片 + 生成向量（10-20 秒）
- 總計：約 20-30 秒

---

**Q2：支援哪些檔案格式？**

A：目前支援：
- ✅ PDF
- ✅ 純文字（.txt）
- ✅ 網頁 URL（自動爬取）
- ⚠️ Word（需轉 PDF）
- ⚠️ PowerPoint（需轉 PDF）

---

**Q3：文件太多會很慢嗎？**

A：不會！向量搜尋的特性：
- 1000 個段落：< 100 ms
- 10000 個段落：< 300 ms
- 100000 個段落：< 1 秒

**原因**：pgvector 使用 IVFFlat 索引，時間複雜度接近 O(log n)

---

**Q4：如何刪除或更新文件？**

A：
```bash
# 刪除文件（會自動刪除所有段落和向量）
curl -X DELETE "https://your-api-url.com/api/rag/documents/123"

# 更新：先刪除，再重新上傳
curl -X DELETE ".../documents/123"
curl -X POST ".../ingest/files" -F "file=@new_version.pdf"
```

---

**Q5：搜尋結果不準確怎麼辦？**

**方法 1：調整切片參數**
```json
{
  "chunk_size": 300,  // 改小一點，更精準
  "overlap": 100      // 重疊多一點，避免斷句
}
```

**方法 2：降低相似度門檻**
```json
{
  "similarity_threshold": 0.6  // 從 0.7 降到 0.6
}
```

**方法 3：增加檢索數量**
```json
{
  "top_k": 10  // 從 5 增加到 10
}
```

---

**Q6：中文和英文可以混合搜尋嗎？**

A：可以！OpenAI Embedding 支援多語言：
```
問題（中文）：「如何重設密碼？」
找到文件（英文）："How to reset password..."
✅ 可以找到！
```

---

**Q7：成本會很高嗎？**

A：非常便宜！以 20 份文件為例：

| 項目 | 用量 | 成本 |
|-----|------|------|
| 上傳文件（一次性） | 100,000 字 | $0.003 |
| 每月 1000 次查詢 | 100,000 字 | $0.003 |
| 每月 GPT-4 回答 | 1000 次 × 500 tokens | $15 |
| **總計** | | **約 $15.01/月** |

**最貴的是 GPT-4 生成**，不是 Embedding！

---

**Q8：可以限制特定使用者只能搜尋特定文件嗎？**

A：可以！兩種方式：

**方式 1：使用 Agent 隔離**（本專案已實作）
```sql
-- 每個部門建立專屬 Agent
INSERT INTO agents (name, slug) VALUES
  ('人事部門', 'hr'),
  ('技術部門', 'tech');

-- 上傳時指定 Agent
POST /api/rag/ingest/files?agent=hr

-- 搜尋時過濾
POST /api/rag/search?agent=hr
```

**方式 2：使用標籤過濾**
```sql
-- 為文件加標籤
UPDATE documents SET tags = ['internal', 'hr'] WHERE id = 123;

-- 搜尋時過濾
WHERE '{"hr"}' && tags
```

---

### 名詞對照表

| 英文 | 中文 | 解釋 |
|-----|------|------|
| RAG | 檢索增強生成 | 先搜尋再回答的 AI 系統 |
| Embedding | 向量嵌入 | 把文字轉成數字陣列 |
| Vector | 向量 | 一串數字（例如 1536 個浮點數） |
| Chunk | 文字片段/段落 | 切好的文字段落 |
| Similarity | 相似度 | 兩個向量的距離（越小越相似） |
| pgvector | PostgreSQL 向量擴充 | 資料庫的向量搜尋功能 |
| Top-K | 前 K 名 | 取最相關的前幾個結果 |
| Threshold | 門檻值 | 最低相似度標準 |
| Token | 標記/詞元 | AI 處理的最小單位（約 0.75 英文字） |

---

### 延伸學習資源

**官方文件**：
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [Supabase Vector Documentation](https://supabase.com/docs/guides/ai)
- [pgvector GitHub](https://github.com/pgvector/pgvector)

**進階主題**：
- Hybrid Search（混合搜尋：關鍵字 + 語意）
- Re-ranking（重新排序提升精確度）
- Fine-tuning Embeddings（客製化 Embedding 模型）
- Multi-Agent RAG（多知識庫管理）

**相關工具**：
- [LangChain](https://www.langchain.com/)（RAG 框架）
- [LlamaIndex](https://www.llamaindex.ai/)（RAG 框架）
- [Weaviate](https://weaviate.io/)（向量資料庫）
- [Pinecone](https://www.pinecone.io/)（向量資料庫）

---

## 總結

恭喜你完成 RAG 系統教學！🎉

**你現在已經學會**：
1. ✅ RAG 是什麼、為什麼需要它
2. ✅ Embedding 如何把文字轉成向量
3. ✅ Supabase + pgvector 如何儲存和搜尋向量
4. ✅ 如何上傳文件、測試搜尋、整合到應用

**下一步建議**：
1. 🚀 上傳你自己的文件，建立第一個知識庫
2. 🧪 測試不同的切片參數（chunk_size、overlap）
3. 🎨 整合到你的產品（網站、App、Chatbot）
4. 📈 監控使用量和成本
5. 🔧 進階：研究 Hybrid Search、Re-ranking

---

## 部署上雲

### 為什麼要部署到雲端？

**本地開發 vs 雲端部署**：

| 項目 | 本地開發 | 雲端部署 |
|------|----------|----------|
| 存取方式 | 只能在自己電腦 | 全球任何地方 |
| 穩定性 | 關機就斷線 | 24/7 運行 |
| 效能 | 受限於個人電腦 | 彈性擴充 |
| 成本 | 免費（電費） | 按使用量付費 |
| 適用場景 | 測試、開發 | 正式產品 |

**什麼時候該部署？**
- ✅ 需要讓團隊成員使用
- ✅ 要整合到手機 App 或網站
- ✅ 需要 24 小時不間斷服務
- ✅ 流量超過本機負荷

---

### Google Cloud Run 部署（推薦）

**優點**：
- ✅ 只在有請求時計費（省錢）
- ✅ 自動擴展（流量大自動加機器）
- ✅ 免費額度豐富（每月 200 萬次請求免費）
- ✅ Google 基礎建設穩定

**缺點**：
- ❌ 需要 Docker 知識
- ❌ 設定較複雜

**價格**：
- 免費額度：每月 200 萬次請求、36 萬 vCPU-秒
- 超額：約 $0.00002/次請求
- 預估成本：輕量使用幾乎免費

**部署步驟**：

```bash
# 1. 建立 Dockerfile（專案根目錄）
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT

# 2. 建立 .dockerignore
__pycache__
*.pyc
.env
.git
.venv
venv/

# 3. 安裝 Google Cloud CLI
# macOS:
brew install google-cloud-sdk

# Windows:
# 下載安裝器 https://cloud.google.com/sdk/docs/install

# 4. 登入並設定專案
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 5. 啟用 Cloud Run API
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# 6. 部署（一鍵完成 build + deploy）
gcloud run deploy rag-api \
  --source . \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=sk-...,SUPABASE_URL=https://...,SUPABASE_KEY=eyJh...

# 7. 取得部署網址
部署完成後會顯示：
Service URL: https://rag-api-xxx-uc.a.run.app
```

**設定環境變數（推薦用 Secret Manager）**：
```bash
# 建立 secrets
echo -n "sk-xxx" | gcloud secrets create openai-api-key --data-file=-
echo -n "https://xxx.supabase.co" | gcloud secrets create supabase-url --data-file=-
echo -n "your-supabase-key-here" | gcloud secrets create supabase-key --data-file=-

# 更新 Cloud Run 使用 secrets
gcloud run services update rag-api \
  --update-secrets OPENAI_API_KEY=openai-api-key:latest,SUPABASE_URL=supabase-url:latest,SUPABASE_KEY=supabase-key:latest
```

---

### 設定 GitHub Actions CI/CD

**自動部署流程**：每次 push 到 `main` 分支自動部署到 Cloud Run

**步驟 1：建立 Service Account**

```bash
# 1. 建立 Service Account
gcloud iam service-accounts create github-actions \
  --description="GitHub Actions deployment" \
  --display-name="github-actions"

# 2. 賦予權限
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# 3. 建立金鑰（JSON）
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com

# 4. 查看 key.json 內容（等下要貼到 GitHub Secrets）
cat key.json
```

---

**步驟 2：設定 GitHub Secrets**

前往你的 GitHub Repository → Settings → Secrets and variables → Actions → New repository secret

新增以下 Secrets：

| Secret Name | Value | 說明 |
|-------------|-------|------|
| `GCP_PROJECT_ID` | `your-project-id` | GCP 專案 ID |
| `GCP_SA_KEY` | `key.json 完整內容` | Service Account 金鑰 |
| `OPENAI_API_KEY` | `sk-...` | OpenAI API Key |
| `SUPABASE_URL` | `https://xxx.supabase.co` | Supabase URL |
| `SUPABASE_KEY` | `your-supabase-key-here` | Supabase Key |

---

**步驟 3：建立 GitHub Actions Workflow**

建立檔案：`.github/workflows/deploy.yml`

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches:
      - main  # 當 push 到 main 分支時觸發

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  SERVICE_NAME: rag-api
  REGION: asia-east1

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      # 1. Checkout 程式碼
      - name: Checkout code
        uses: actions/checkout@v4

      # 2. 驗證 GCP
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      # 3. 設定 Cloud SDK
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      # 4. 建立 .env 檔案（從 GitHub Secrets）
      - name: Create .env file
        run: |
          echo "OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}" >> .env
          echo "SUPABASE_URL=${{ secrets.SUPABASE_URL }}" >> .env
          echo "SUPABASE_KEY=${{ secrets.SUPABASE_KEY }}" >> .env

      # 5. 部署到 Cloud Run
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy ${{ env.SERVICE_NAME }} \
            --source . \
            --platform managed \
            --region ${{ env.REGION }} \
            --allow-unauthenticated \
            --set-env-vars OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }},SUPABASE_URL=${{ secrets.SUPABASE_URL }},SUPABASE_KEY=${{ secrets.SUPABASE_KEY }}

      # 6. 顯示部署網址
      - name: Show deployment URL
        run: |
          echo "Deployment complete!"
          gcloud run services describe ${{ env.SERVICE_NAME }} --region ${{ env.REGION }} --format 'value(status.url)'
```

---

**步驟 4：觸發自動部署**

```bash
# 提交 workflow 設定
git add .github/workflows/deploy.yml
git commit -m "ci: add Cloud Run deployment workflow"
git push origin main

# 查看部署進度
# 前往 GitHub Repository → Actions 查看執行狀態
```

---

**進階：使用 Secret Manager（推薦生產環境）**

不在 GitHub Actions 中明文設定環境變數，改用 GCP Secret Manager：

```yaml
# 修改 deploy.yml 的部署步驟
- name: Deploy to Cloud Run with Secret Manager
  run: |
    gcloud run deploy ${{ env.SERVICE_NAME }} \
      --source . \
      --platform managed \
      --region ${{ env.REGION }} \
      --allow-unauthenticated \
      --update-secrets OPENAI_API_KEY=openai-api-key:latest,SUPABASE_URL=supabase-url:latest,SUPABASE_KEY=supabase-key:latest
```

這樣環境變數就不會出現在 GitHub Actions logs 中，更安全！

---

### 部署後檢查清單

**部署完成後必做**：

```bash
# 1. 健康檢查
curl https://your-deployed-url/health

# 2. 測試上傳
curl -X POST "https://your-deployed-url/ingest" \
  -F "file=@test.pdf"

# 3. 測試搜尋
curl -X POST "https://your-deployed-url/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "什麼是 RAG？", "top_k": 3}'

# 4. 監控日誌
gcloud run logs read rag-api --limit 50

# 5. 設定 CORS（如果前端呼叫）
# 在 app/main.py 加入：
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 正式環境改成你的網域
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### 成本估算與省錢技巧

**每月成本預估（1000 次 API 呼叫）**：

| 項目 | Cloud Run |
|------|-----------|
| 運算 | 免費（在免費額度內） |
| OpenAI API | $5-20 |
| Supabase | 免費 |
| **總計** | **$5-20/月** |

**省錢技巧**：

1. **快取常見查詢**：
   ```python
   # 使用 Redis 或記憶體快取
   from functools import lru_cache

   @lru_cache(maxsize=100)
   def cached_search(query: str):
       return search_vectors(query)
   ```

2. **批次處理上傳**：
   ```python
   # 一次上傳多個文件，減少 API 呼叫
   async def batch_ingest(files: List[UploadFile]):
       embeddings = await openai.Embedding.create(
           input=[chunk for file in files for chunk in chunks],
           model="text-embedding-3-small"  # 使用較小模型
       )
   ```

3. **使用較小的 Embedding 模型**：
   ```python
   # text-embedding-3-small（便宜 5 倍）
   # 而非 text-embedding-3-large
   ```

4. **設定最大 token 限制**：
   ```python
   # 限制每次搜尋的結果數量
   TOP_K_LIMIT = 5
   MAX_CONTEXT_LENGTH = 3000
   ```

---

### 疑難排解

**常見問題**：

1. **部署後 500 錯誤**
   ```bash
   # 檢查環境變數是否正確設定
   gcloud run services describe rag-api --region asia-east1

   # 檢查日誌
   gcloud run logs read rag-api --region asia-east1 --limit 50
   ```

2. **CORS 錯誤**
   ```python
   # 確保加入 CORS middleware（見上方範例）
   ```

3. **檔案上傳失敗（檔案太大）**
   ```python
   # 設定最大檔案大小（app/main.py）
   app.add_middleware(
       LimitUploadSize, max_upload_size=10_000_000  # 10MB
   )
   ```

4. **冷啟動太慢**
   ```bash
   # 設定最小實例數（避免冷啟動，但會增加成本）
   gcloud run services update rag-api \
     --region asia-east1 \
     --min-instances 1
   ```

5. **OpenAI API 超時**
   ```python
   # 增加 timeout
   openai.timeout = 30  # 秒
   ```

---

### 生產環境最佳實踐

**必做項目**：

1. **設定日誌監控**
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)

   @app.middleware("http")
   async def log_requests(request: Request, call_next):
       logging.info(f"{request.method} {request.url}")
       response = await call_next(request)
       return response
   ```

2. **加入速率限制**
   ```bash
   pip install slowapi

   # app/main.py
   from slowapi import Limiter
   from slowapi.util import get_remote_address

   limiter = Limiter(key_func=get_remote_address)
   app.state.limiter = limiter

   @app.post("/search")
   @limiter.limit("10/minute")  # 每分鐘最多 10 次
   async def search(request: Request):
       ...
   ```

3. **健康檢查端點**
   ```python
   @app.get("/health")
   async def health():
       # 檢查資料庫連線
       try:
           supabase.table("documents").select("id").limit(1).execute()
           return {"status": "healthy"}
       except:
           raise HTTPException(status_code=503, detail="Database unavailable")
   ```

4. **版本管理**
   ```python
   @app.get("/version")
   async def version():
       return {"version": "1.0.0", "updated": "2024-10-30"}
   ```

5. **錯誤追蹤（Sentry）**
   ```bash
   pip install sentry-sdk

   # app/main.py
   import sentry_sdk
   sentry_sdk.init(dsn="https://xxx@sentry.io/xxx")
   ```

---

### 部署流程總結

**建議流程**：
1. 本地開發測試（確保功能正常）
2. 設定 GCP 專案與 Cloud Run
3. 設定 GitHub Secrets
4. 建立 CI/CD Workflow
5. Push 程式碼自動部署
6. 測試生產環境

**為什麼選擇 Cloud Run？**
- ✅ 只在有請求時計費（省錢）
- ✅ 自動擴展（流量大自動增加實例）
- ✅ 免費額度豐富（每月 200 萬次請求）
- ✅ 與 GCP 生態整合完善
- ✅ 支援 Docker 容器化部署

---

**需要幫助？**
- 📧 Email: your-email@example.com
- 💬 Slack: #rag-support
- 📖 內部文件: [連結]

---

**最後更新**：2024-10-30
**版本**：v1.1
**作者**：Claude Code
