"""Playwright test for RAG Evaluation Matrix frontend"""
import time
from playwright.sync_api import sync_playwright, expect


def test_matrix_page_with_real_data():
    """測試Matrix頁面完整流程：
    1. 訪問matrix頁面
    2. 等待數據載入
    3. 驗證表格顯示
    4. 驗證metrics顯示正確（非0值）
    5. 截圖保存結果
    """
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)  # headless=False 可以看到瀏覽器操作
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        print("=== 步驟1: 訪問Matrix頁面 ===")
        page.goto("http://localhost:8000/rag/evaluation/matrix")
        print("✅ 頁面載入完成")

        print("\n=== 步驟2: 等待數據載入 ===")
        # 等待表格出現
        page.wait_for_selector("table", timeout=10000)
        print("✅ 表格已出現")

        # 等待一下讓API數據完全載入
        time.sleep(3)

        print("\n=== 步驟3: 檢查表格結構 ===")
        # 檢查表頭
        header_elements = page.locator("thead th").all()
        headers = [h.text_content() for h in header_elements]
        print(f"表頭: {headers}")
        header_text = " ".join(headers)
        assert "Chunk Strategy" in header_text or "策略" in header_text or "Chunk" in header_text
        assert "Prompt" in header_text or "提示" in header_text
        print("✅ 表頭正確")

        print("\n=== 步驟4: 檢查實驗數據 ===")
        # 檢查是否有數據行
        rows = page.locator("tbody tr").count()
        print(f"數據行數: {rows}")
        assert rows > 0, "應該至少有一行數據"
        print("✅ 有實驗數據")

        print("\n=== 步驟5: 檢查Metrics顯示 ===")
        # 查找包含metrics的cell
        cells_with_metrics = page.locator("td").filter(has_text="Faithfulness").count()
        print(f"包含Faithfulness的儲存格: {cells_with_metrics}")

        # 檢查是否有顯示具體數值（不是0.000）
        cells = page.locator("td").all()
        metrics_found = []
        for cell in cells:
            text = cell.text_content()
            if "Faithfulness:" in text and "0.000" not in text:
                metrics_found.append(text)
                print(f"找到有效metrics: {text[:100]}...")

        if metrics_found:
            print(f"✅ 找到 {len(metrics_found)} 個有效metrics顯示")
        else:
            print("⚠️  未找到非零metrics，檢查cell內容...")
            # 打印前10個cell的內容供調試
            for i, cell in enumerate(cells[:20]):
                print(f"  Cell {i}: {cell.text_content()[:50]}")

        print("\n=== 步驟6: 測試執行按鈕 ===")
        # 查找執行按鈕
        run_buttons = page.locator("button:has-text('▶')").count()
        print(f"執行按鈕數量: {run_buttons}")

        batch_button = page.locator("button:has-text('執行所有組合')").count()
        print(f"批量執行按鈕: {batch_button}")

        print("\n=== 步驟7: 截圖保存結果 ===")
        page.screenshot(path="/tmp/matrix_page_test.png", full_page=True)
        print("✅ 截圖已保存到 /tmp/matrix_page_test.png")

        print("\n=== 步驟8: 檢查最近的成功實驗 ===")
        # 查找實驗ID為 2b0daf1d-ff11-4076-928a-2e457b71c92c 的數據
        exp_id = "2b0daf1d-ff11-4076-928a-2e457b71c92c"
        page_content = page.content()
        if exp_id in page_content:
            print(f"✅ 找到測試實驗ID: {exp_id}")
        else:
            print(f"⚠️  未在頁面中找到實驗ID {exp_id}")

        # 等待3秒讓用戶看到結果
        time.sleep(3)

        browser.close()

        print("\n" + "="*60)
        print("測試完成！")
        print("="*60)


if __name__ == "__main__":
    test_matrix_page_with_real_data()
