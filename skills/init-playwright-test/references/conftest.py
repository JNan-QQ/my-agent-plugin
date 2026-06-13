import os
import pytest
from playwright.sync_api import Page


# 示例：认证页面 fixture，根据实际项目修改选择器后取消注释
#
# @pytest.fixture
# def authenticated_page(page: Page):
#     username = os.environ.get("TEST_USER", "testuser")
#     password = os.environ.get("TEST_PASSWORD", "password123")
#
#     page.goto("/login")
#     page.locator("#username").fill(username)
#     page.locator("#password").fill(password)
#     page.locator("#login-btn").click()
#     page.wait_for_url("**/dashboard")
#     return page
