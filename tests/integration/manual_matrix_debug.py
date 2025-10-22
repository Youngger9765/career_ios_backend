"""Debug matrix page JavaScript errors"""
import time
from playwright.sync_api import sync_playwright

def test_matrix_with_console():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Listen to console messages
        console_messages = []
        def handle_console(msg):
            console_messages.append(f"[{msg.type}] {msg.text}")
            print(f"Console [{msg.type}]: {msg.text}")

        page.on("console", handle_console)

        # Listen to page errors
        def handle_error(error):
            print(f"❌ Page Error: {error}")

        page.on("pageerror", handle_error)

        print("=== 訪問 Matrix 頁面 ===")
        page.goto("http://localhost:8000/rag/evaluation/matrix")

        print("\n=== 等待頁面載入 ===")
        time.sleep(5)

        # Check if API was called
        print("\n=== 檢查網路請求 ===")

        # Take screenshot
        page.screenshot(path="/tmp/matrix_debug.png", full_page=True)
        print("✅ 截圖已保存")

        print("\n=== Console Messages ===")
        for msg in console_messages:
            print(msg)

        # Check DOM
        print("\n=== 檢查 DOM 元素 ===")
        loading = page.locator("#loadingState").is_visible()
        matrix = page.locator("#matrixContainer").is_visible()
        error = page.locator("#errorState").is_visible()

        print(f"Loading state visible: {loading}")
        print(f"Matrix container visible: {matrix}")
        print(f"Error state visible: {error}")

        if error:
            error_msg = page.locator("#errorMessage").text_content()
            print(f"Error message: {error_msg}")

        time.sleep(3)
        browser.close()

if __name__ == "__main__":
    test_matrix_with_console()
