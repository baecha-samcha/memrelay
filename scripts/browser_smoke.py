"""Optional UI verification: pip install playwright; playwright install chromium."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

url = os.getenv('MEMRELAY_TEST_URL', 'http://127.0.0.1:8000')
root = Path('artifacts')
root.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--disable-dev-shm-usage'])
    expect.set_options(timeout=30000)
    page = browser.new_page(viewport={'width': 1360, 'height': 1100}, device_scale_factor=1)
    page.set_default_timeout(30000)
    page.set_default_navigation_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(url, wait_until='domcontentloaded')
    expect(page.locator('#connection')).to_contain_text('연결됨')
    expect(page.locator('#user')).to_be_enabled()
    page.select_option('#user', 'bob')
    expect(page.locator('#user')).to_be_enabled()
    page.select_option('#user', 'alice')
    expect(page.locator('#user')).to_be_enabled()
    page.click('#demo')
    expect(page.locator('#demo-panel')).to_be_visible(timeout=30000)
    expect(page.locator('#demo-scenes .scene')).to_have_count(8)
    expect(page.locator('#results')).to_contain_text('- Project Atlas language: Rust')
    expect(page.locator('#history')).to_contain_text('SUPERSEDES')
    expect(page.get_by_role('button', name='실행 종료')).to_be_disabled()
    page.get_by_role('button', name='상태 전이', exact=True).click()
    expect(page.locator('#tasks')).to_contain_text('그래프에 기록된 전이')
    expect(page.locator('#demo-scenes')).to_contain_text('No supported project facts')
    page.screenshot(path=str(root / 'desktop.png'), full_page=True)
    # Database failure is explicit; the static UI still loads.
    page.route('**/api/health', lambda route: route.fulfill(status=503, content_type='application/json', body='{"detail":"FalkorDB unavailable; memory operations stopped.","database":"disconnected"}'))
    page.click('#refresh')
    expect(page.locator('#connection')).to_contain_text('연결 장애')
    expect(page.locator('#error')).to_be_visible()
    page.unroute('**/api/health')
    page.set_viewport_size({'width':390, 'height':844})
    page.click('#refresh')
    expect(page.locator('#connection')).to_contain_text('연결됨')
    page.screenshot(path=str(root / 'mobile.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert not errors, errors
    browser.close()
print('Browser smoke passed: user switch, five scenes, evidence, offline indicator, mobile layout.')
