from __future__ import annotations

import asyncio
import time
import random
from typing import Optional, Dict, Any, List
from pathlib import Path

from playwright.async_api import Page

from app.core.playwright_manager import get_playwright_manager
from app.core.settings import XIAOHONGSHU_USERNAME, XIAOHONGSHU_PASSWORD, XIAOHONGSHU_HEADLESS, XIAOHONGSHU_TIMEOUT


class XiaohongshuPublisher:
    """小红书自动发布服务"""

    def __init__(self):
        self.username = XIAOHONGSHU_USERNAME
        self.password = XIAOHONGSHU_PASSWORD
        self.logged_in = False
        self.base_url = "https://www.xiaohongshu.com"

    async def _human_like_delay(self, min_ms: int = 500, max_ms: int = 2000) -> None:
        """模拟人类操作延迟"""
        delay = random.uniform(min_ms / 1000.0, max_ms / 1000.0)
        await asyncio.sleep(delay)

    async def _type_human_like(self, page: Page, selector: str, text: str) -> None:
        """模拟人类打字"""
        await page.click(selector)
        await page.evaluate(f"document.querySelector('{selector}').value = ''")

        for char in text:
            await page.type(selector, char, delay=random.uniform(50, 150) / 1000.0)
            await self._human_like_delay(10, 50)

    async def _wait_for_navigation(self, page: Page) -> None:
        """等待页面导航完成"""
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except:
            await page.wait_for_load_state("domcontentloaded")

    async def _is_logged_in(self, page: Page) -> bool:
        """检查是否已登录"""
        try:
            # 检查登录后的典型元素
            await page.wait_for_selector('img[alt*="头像"]', timeout=5000)
            return True
        except:
            try:
                # 检查登录按钮是否存在（表示未登录）
                await page.wait_for_selector('button:has-text("登录")', timeout=3000)
                return False
            except:
                # 默认认为已登录
                return True

    async def login(self, page: Page) -> bool:
        """登录小红书账号"""
        if not self.username or not self.password:
            raise ValueError("小红书账号或密码未配置")

        try:
            # 访问首页
            await page.goto(self.base_url)
            await self._wait_for_navigation(page)
            await self._human_like_delay(1000, 2000)

            # 检查是否已登录
            if await self._is_logged_in(page):
                print("Already logged in to Xiaohongshu")
                self.logged_in = True
                return True

            # 点击登录按钮
            try:
                login_button = await page.wait_for_selector('button:has-text("登录")', timeout=5000)
                await login_button.click()
                await self._human_like_delay(1000, 1500)
            except:
                # 尝试其他可能的登录按钮选择器
                login_buttons = await page.query_selector_all('button, a')
                for btn in login_buttons:
                    text = await btn.text_content()
                    if text and ("登录" in text or "Sign in" in text or "Log in" in text):
                        await btn.click()
                        await self._human_like_delay(1000, 1500)
                        break

            # 等待登录弹窗出现
            await self._human_like_delay(1000, 2000)

            # 尝试多种登录方式
            login_success = False

            # 方式1：账号密码登录
            try:
                # 切换到账号密码登录
                password_tab = await page.wait_for_selector('div[role="tab"]:has-text("密码登录")', timeout=3000)
                await password_tab.click()
                await self._human_like_delay(500, 1000)

                # 输入用户名
                username_input = await page.wait_for_selector('input[placeholder*="手机号"], input[placeholder*="邮箱"], input[placeholder*="账号"]', timeout=3000)
                await self._type_human_like(page, username_input, self.username)

                # 输入密码
                password_input = await page.wait_for_selector('input[type="password"]', timeout=3000)
                await self._type_human_like(page, password_input, self.password)

                # 点击登录按钮
                submit_button = await page.wait_for_selector('button[type="submit"]:has-text("登录"), button:has-text("登录")', timeout=3000)
                await submit_button.click()

                # 等待登录完成
                await self._human_like_delay(2000, 3000)

                # 检查登录是否成功
                if await self._is_logged_in(page):
                    login_success = True
                    print("Logged in to Xiaohongshu successfully (password login)")

            except Exception as e:
                print(f"Password login failed: {e}")

            # 方式2：短信验证码登录
            if not login_success:
                try:
                    # 返回到登录页面
                    await page.goto(f"{self.base_url}/login")
                    await self._wait_for_navigation(page)
                    await self._human_like_delay(1000, 2000)

                    # 切换到短信登录
                    sms_tab = await page.wait_for_selector('div[role="tab"]:has-text("短信登录")', timeout=3000)
                    await sms_tab.click()
                    await self._human_like_delay(500, 1000)

                    # 输入手机号
                    phone_input = await page.wait_for_selector('input[placeholder*="手机号"]', timeout=3000)
                    await self._type_human_like(page, phone_input, self.username)

                    # 点击获取验证码
                    sms_button = await page.wait_for_selector('button:has-text("获取验证码")', timeout=3000)
                    await sms_button.click()
                    await self._human_like_delay(1000, 1500)

                    # 注意：这里需要用户手动输入验证码
                    print("Please check your phone for SMS verification code")
                    print("Waiting 60 seconds for manual verification...")
                    await asyncio.sleep(60)

                    # 检查登录是否成功
                    if await self._is_logged_in(page):
                        login_success = True
                        print("Logged in to Xiaohongshu successfully (SMS login)")

                except Exception as e:
                    print(f"SMS login failed: {e}")

            if login_success:
                self.logged_in = True
                # 保存登录状态
                manager = await get_playwright_manager()
                await manager.save_storage_state()
                return True
            else:
                print("All login methods failed")
                return False

        except Exception as e:
            print(f"Login failed: {e}")
            # 截图保存错误信息
            manager = await get_playwright_manager()
            await manager.take_screenshot(page, "login_error")
            return False

    async def create_draft(self, page: Page, title: str, content: str, images: Optional[List[str]] = None) -> bool:
        """创建小红书草稿"""
        try:
            # 确保已登录
            if not self.logged_in:
                if not await self.login(page):
                    return False

            # 访问发布页面
            await page.goto(f"{self.base_url}/creation")
            await self._wait_for_navigation(page)
            await self._human_like_delay(1000, 2000)

            # 等待发布页面加载
            try:
                await page.wait_for_selector('div[contenteditable="true"], textarea, input[placeholder*="分享"]', timeout=10000)
            except:
                # 尝试找到创建按钮
                create_buttons = await page.query_selector_all('button:has-text("发布"), button:has-text("创作"), button:has-text("写笔记")')
                if create_buttons:
                    await create_buttons[0].click()
                    await self._human_like_delay(1000, 2000)

            # 输入标题/正文
            content_selectors = [
                'div[contenteditable="true"]',
                'textarea',
                'input[placeholder*="分享"]',
                'input[placeholder*="标题"]'
            ]

            content_element = None
            for selector in content_selectors:
                try:
                    content_element = await page.wait_for_selector(selector, timeout=3000)
                    if content_element:
                        break
                except:
                    continue

            if content_element:
                # 清空现有内容
                await content_element.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")

                # 输入内容
                await self._type_human_like(page, content_element, f"{title}\n\n{content}")
            else:
                print("Could not find content input field")
                return False

            # 上传图片
            if images:
                try:
                    upload_button = await page.wait_for_selector('input[type="file"], button:has-text("上传图片"), button:has-text("添加图片")', timeout=5000)

                    for i, image_path in enumerate(images):
                        if Path(image_path).exists():
                            await upload_button.set_input_files(image_path)
                            await self._human_like_delay(1000, 2000)

                            # 等待图片上传完成
                            try:
                                await page.wait_for_selector(f'img[alt*="图片{i+1}"], img[src*="{Path(image_path).name}"]', timeout=10000)
                            except:
                                pass
                except Exception as e:
                    print(f"Image upload failed: {e}")

            # 添加标签
            try:
                tag_input = await page.wait_for_selector('input[placeholder*="添加标签"], input[placeholder*="#"]', timeout=3000)
                if tag_input:
                    # 添加一些常用标签
                    tags = ["旅游", "美食", "生活分享", "日常"]
                    for tag in tags[:2]:  # 只添加前两个标签
                        await self._type_human_like(page, tag_input, f"#{tag}")
                        await page.keyboard.press("Enter")
                        await self._human_like_delay(300, 600)
            except:
                pass  # 标签功能可选

            # 保存为草稿
            try:
                draft_button = await page.wait_for_selector('button:has-text("存草稿"), button:has-text("保存草稿")', timeout=5000)
                await draft_button.click()
                await self._human_like_delay(1000, 2000)

                # 等待保存成功
                await page.wait_for_selector('div:has-text("保存成功"), div:has-text("草稿已保存")', timeout=10000)
                print("Draft saved successfully")
                return True

            except:
                # 如果找不到保存草稿按钮，可能已经自动保存
                print("Draft may have been auto-saved")
                return True

        except Exception as e:
            print(f"Create draft failed: {e}")
            manager = await get_playwright_manager()
            await manager.take_screenshot(page, "create_draft_error")
            return False

    async def publish(self, page: Page, title: str, content: str, images: Optional[List[str]] = None) -> Dict[str, Any]:
        """发布小红书笔记"""
        try:
            # 先创建草稿
            if not await self.create_draft(page, title, content, images):
                return {
                    "success": False,
                    "error": "Failed to create draft",
                    "task_id": None,
                }

            # 尝试发布
            try:
                publish_button = await page.wait_for_selector('button:has-text("发布"), button:has-text("发布笔记")', timeout=5000)
                await publish_button.click()
                await self._human_like_delay(1000, 2000)

                # 检查发布确认弹窗
                try:
                    confirm_button = await page.wait_for_selector('button:has-text("确认发布"), button:has-text("确定")', timeout=3000)
                    await confirm_button.click()
                    await self._human_like_delay(2000, 3000)
                except:
                    pass  # 可能没有确认弹窗

                # 等待发布成功
                await page.wait_for_selector('div:has-text("发布成功"), div:has-text("发布完成")', timeout=15000)

                # 获取发布后的链接
                post_url = page.url
                if "creation" in post_url or "draft" in post_url:
                    # 尝试获取实际帖子链接
                    try:
                        link_element = await page.wait_for_selector('a[href*="/explore/"], a[href*="/discovery/"]', timeout=5000)
                        post_url = await link_element.get_attribute("href")
                        if post_url and not post_url.startswith("http"):
                            post_url = f"{self.base_url}{post_url}"
                    except:
                        pass

                print(f"Published successfully: {post_url}")

                return {
                    "success": True,
                    "post_url": post_url,
                    "title": title,
                    "content_length": len(content),
                    "image_count": len(images) if images else 0,
                }

            except Exception as e:
                print(f"Publish failed, but draft may have been saved: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "draft_saved": True,
                }

        except Exception as e:
            print(f"Publish process failed: {e}")
            manager = await get_playwright_manager()
            await manager.take_screenshot(page, "publish_error")
            return {
                "success": False,
                "error": str(e),
                "draft_saved": False,
            }

    async def publish_article(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """发布文章到小红书"""
        manager = await get_playwright_manager()
        page = await manager.get_page("xiaohongshu")

        try:
            title = article_data.get("title", "创作内容分享")
            content = article_data.get("content", "")
            images = article_data.get("images", [])

            # 确保有内容
            if not content:
                return {
                    "success": False,
                    "error": "No content provided",
                }

            # 小红书内容格式优化
            # 1. 限制长度（小红书适合短文）
            if len(content) > 1000:
                content = content[:1000] + "..."

            # 2. 添加一些表情符号（小红书风格）
            emojis = ["✨", "🌟", "💫", "🔥", "❤️", "👍", "📝", "🎯"]
            if len(content.split("\n")) > 3:
                content = emojis[0] + " " + content

            # 3. 添加话题标签
            if "#" not in content:
                content += "\n\n#创作分享 #内容创作 #生活记录"

            result = await self.publish(page, title, content, images)

            # 保存发布记录
            if result.get("success"):
                # TODO: 保存到数据库
                pass

            return result

        except Exception as e:
            print(f"Publish article failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        finally:
            await manager.save_storage_state()


async def test_xiaohongshu_publisher():
    """测试小红书发布功能"""
    publisher = XiaohongshuPublisher()
    manager = await get_playwright_manager()
    page = await manager.get_page("test")

    try:
        # 测试登录
        print("Testing login...")
        if await publisher.login(page):
            print("Login test passed")

            # 测试发布
            test_data = {
                "title": "测试小红书发布",
                "content": "这是通过自动化脚本发布的小红书测试内容。✨\n\n测试AI内容创作系统的发布功能。",
                "images": [],  # 可以添加测试图片路径
            }

            print("Testing publish...")
            result = await publisher.publish_article(test_data)
            print(f"Publish result: {result}")

            return result
        else:
            print("Login test failed")
            return {"success": False, "error": "Login failed"}

    except Exception as e:
        print(f"Test failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        await manager.save_storage_state()