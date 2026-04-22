from __future__ import annotations

import asyncio
import os
import time
from typing import Optional, Dict, Any
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from app.core.settings import PLAYWRIGHT_BROWSER_TYPE, PLAYWRIGHT_HEADLESS, XIAOHONGSHU_TIMEOUT


class PlaywrightManager:
    """Playwright浏览器管理器，提供浏览器实例的创建、管理和复用"""

    def __init__(self):
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._pages: Dict[str, Page] = {}
        self._playwright = None
        self._initialized = False
        self._user_data_dir = Path("/tmp/playwright_data")

    async def initialize(self) -> None:
        """初始化Playwright和浏览器"""
        if self._initialized:
            return

        try:
            self._playwright = await async_playwright().start()

            # 创建用户数据目录
            self._user_data_dir.mkdir(parents=True, exist_ok=True)

            # 启动浏览器
            browser_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
            ]

            if PLAYWRIGHT_BROWSER_TYPE == "chromium":
                self._browser = await self._playwright.chromium.launch(
                    headless=PLAYWRIGHT_HEADLESS,
                    args=browser_args,
                    timeout=XIAOHONGSHU_TIMEOUT,
                )
            elif PLAYWRIGHT_BROWSER_TYPE == "firefox":
                self._browser = await self._playwright.firefox.launch(
                    headless=PLAYWRIGHT_HEADLESS,
                    timeout=XIAOHONGSHU_TIMEOUT,
                )
            else:
                self._browser = await self._playwright.webkit.launch(
                    headless=PLAYWRIGHT_HEADLESS,
                    timeout=XIAOHONGSHU_TIMEOUT,
                )

            # 创建上下文
            self._context = await self._browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                java_script_enabled=True,
                bypass_csp=True,
                ignore_https_errors=True,
                storage_state=self._user_data_dir / "storage_state.json" if self._user_data_dir.exists() else None,
            )

            self._initialized = True
            print(f"Playwright manager initialized with {PLAYWRIGHT_BROWSER_TYPE} (headless={PLAYWRIGHT_HEADLESS})")

        except Exception as e:
            print(f"Failed to initialize Playwright: {e}")
            await self.cleanup()
            raise

    async def get_page(self, name: str = "default") -> Page:
        """获取或创建页面"""
        if not self._initialized:
            await self.initialize()

        if name not in self._pages:
            page = await self._context.new_page()
            await page.set_default_timeout(XIAOHONGSHU_TIMEOUT)
            self._pages[name] = page

        return self._pages[name]

    async def close_page(self, name: str) -> None:
        """关闭指定页面"""
        if name in self._pages:
            await self._pages[name].close()
            del self._pages[name]

    async def save_storage_state(self) -> None:
        """保存存储状态（Cookies、LocalStorage等）"""
        if self._context:
            await self._context.storage_state(path=self._user_data_dir / "storage_state.json")

    async def take_screenshot(self, page: Page, name: str) -> str:
        """截取页面截图并保存"""
        screenshot_dir = self._user_data_dir / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        timestamp = int(time.time())
        screenshot_path = screenshot_dir / f"{name}_{timestamp}.png"

        await page.screenshot(path=str(screenshot_path), full_page=True)
        return str(screenshot_path)

    async def cleanup(self) -> None:
        """清理所有资源"""
        # 关闭所有页面
        for name, page in list(self._pages.items()):
            try:
                await page.close()
            except:
                pass
        self._pages.clear()

        # 关闭上下文
        if self._context:
            try:
                await self._context.close()
            except:
                pass
            self._context = None

        # 关闭浏览器
        if self._browser:
            try:
                await self._browser.close()
            except:
                pass
            self._browser = None

        # 停止Playwright
        if self._playwright:
            try:
                await self._playwright.stop()
            except:
                pass
            self._playwright = None

        self._initialized = False

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()


# 全局Playwright管理器实例
_playwright_manager: Optional[PlaywrightManager] = None


async def get_playwright_manager() -> PlaywrightManager:
    """获取全局Playwright管理器实例"""
    global _playwright_manager
    if _playwright_manager is None:
        _playwright_manager = PlaywrightManager()
        await _playwright_manager.initialize()
    return _playwright_manager


async def close_playwright_manager() -> None:
    """关闭全局Playwright管理器"""
    global _playwright_manager
    if _playwright_manager:
        await _playwright_manager.cleanup()
        _playwright_manager = None