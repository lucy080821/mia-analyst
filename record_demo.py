import asyncio
import os
import glob
# pyrefly: ignore [missing-import]
from playwright.async_api import async_playwright

async def run():
    print("Starting Playwright...")
    async with async_playwright() as p:
        # Mở Chrome ở chế độ có giao diện (headless=False)
        # Quay video kích thước 1280x720 và lưu vào thư mục 'landing_media'
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            record_video_dir="landing_media/",
            record_video_size={"width": 1280, "height": 720},
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        print("1. Accessing home and logging in...")
        await page.goto('http://127.0.0.1:8001/auth/login/')
        await page.fill('input[name="username"]', 'admin')
        await page.fill('input[name="password"]', 'admin')
        await page.click('button[type="submit"]')
        await asyncio.sleep(2) # Chờ login xong
        
        # Chuyển hướng sang Dashboard
        print("2. Accessing Dashboard...")
        await page.goto('http://127.0.0.1:8001/analytics/', wait_until="networkidle")

        # Skip Guide Modal if exists
        try:
            await page.click('button[onclick="closeGuide()"]', timeout=3000)
            print("Đã đóng guide modal.")
        except:
            pass

        # Upload file dữ liệu test
        print("3. Uploading test_sales.csv...")
        csv_path = os.path.abspath('test_sales.csv')
        await page.set_input_files('#excel-upload', csv_path)
        
        # Chờ hệ thống parse xong file và pop-up hiện lên
        await asyncio.sleep(5)
        # Tắt popup/modal báo thành công nếu có
        try:
            await page.click('#confirm-upload-btn', timeout=3000)
            print("Đã xác nhận upload.")
        except:
            pass
        
        await asyncio.sleep(2)

        print("4. Typing AI question...")
        await page.click('#chat-input')
        
        # Gõ chậm từng chữ để video nhìn chân thật và đẹp
        question = "Chào Mia, hãy phân tích xu hướng doanh thu của tôi trong quý vừa rồi và đưa ra 3 lời khuyên tối ưu."
        for char in question:
            await page.keyboard.type(char)
            await asyncio.sleep(0.05) # Tốc độ gõ phím
            
        await asyncio.sleep(1)
        # Bấm Enter để gửi
        print("5. Waiting for AI response...")
        await page.keyboard.press("Enter")
        
        # Đợi AI xử lý và sinh ra output
        await asyncio.sleep(15) 

        # Cuộn nhẹ để biểu diễn
        try:
            await page.mouse.wheel(0, 500)
            await asyncio.sleep(5)
        except:
            pass
        
        print("Process complete! Closing browser...")
        
        await context.close()
        await browser.close()
        
        await asyncio.sleep(2) # Wait for video to flush
        
        print("Saving video...")
        # Ensure target directory exists
        os.makedirs('static/videos', exist_ok=True)
        
        video_files = glob.glob('landing_media/*.webm')
        if video_files:
            latest_file = max(video_files, key=os.path.getctime)
            target_name = 'static/videos/demo_ai_mia.webm'
            if os.path.exists(target_name):
                os.remove(target_name)
            import shutil
            shutil.copy(latest_file, target_name)
            print(f"Success! Video saved at: {target_name}")
            print("Note: WebM is better than GIF for landing pages!")

if __name__ == '__main__':
    asyncio.run(run())
