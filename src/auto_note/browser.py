from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import re

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from .article import Article, body_with_tags


NOTE_HOME_URL = "https://note.com/"
NOTE_LOGIN_URL = "https://note.com/login"
NOTE_NEW_TEXT_URL = "https://note.com/notes/new"


@dataclass(frozen=True)
class BrowserOptions:
    profile_dir: Path
    headless: bool = False
    timeout_ms: int = 45_000
    slow_mo_ms: int = 0
    browser_channel: str | None = None


class NoteAutomationError(RuntimeError):
    pass


async def open_login(options: BrowserOptions) -> None:
    options.profile_dir.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(options.profile_dir),
            headless=False,
            slow_mo=options.slow_mo_ms,
            **_browser_channel_kwargs(options),
        )
        page = context.pages[0] if context.pages else await context.new_page()
        page.set_default_timeout(options.timeout_ms)
        await page.goto(NOTE_LOGIN_URL, wait_until="domcontentloaded")
        print("note.com にログインしてください。ログイン後、このターミナルで Enter を押すと保存して閉じます。")
        input()
        await context.close()


async def post_article(
    article: Article,
    *,
    publish: bool,
    append_tags: bool,
    keep_open: bool,
    options: BrowserOptions,
) -> None:
    options.profile_dir.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(options.profile_dir),
            headless=options.headless,
            slow_mo=options.slow_mo_ms,
            **_browser_channel_kwargs(options),
        )
        page = context.pages[0] if context.pages else await context.new_page()
        page.set_default_timeout(options.timeout_ms)

        await page.goto(NOTE_NEW_TEXT_URL, wait_until="domcontentloaded")
        await _ensure_logged_in(page)
        await _fill_title(page, article.title)
        await _fill_body(page, body_with_tags(article) if append_tags else article.body)

        if publish:
            await _publish(page)
            await _soft_wait_for_idle(page)
            print(f"posted: {article.source}")
        else:
            print(f"draft filled: {article.source}")
            if keep_open and not options.headless:
                print("確認が終わったら、このターミナルで Enter を押してブラウザを閉じます。")
                input()

        await context.close()


async def fill_note_post(
    article: Article,
    *,
    publish: bool,
    append_tags: bool,
    options: BrowserOptions,
    should_close=None,  # Callable[[], bool] | None
    on_event=None,  # Callable[[str], None] | None
) -> str | None:
    options.profile_dir.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(options.profile_dir),
            headless=options.headless,
            slow_mo=options.slow_mo_ms,
            **_browser_channel_kwargs(options),
        )
        guard_context_close = not publish
        try:
            page = context.pages[0] if context.pages else await context.new_page()
            page.set_default_timeout(options.timeout_ms)

            await page.goto(NOTE_NEW_TEXT_URL, wait_until="domcontentloaded")
            await _ensure_logged_in(page)
            await _fill_title(page, article.title)
            await _fill_body(page, body_with_tags(article) if append_tags else article.body)
            if on_event is not None:
                on_event("下書きを入力しました")

            if publish:
                await _publish(page)
                await _soft_wait_for_idle(page)
                if on_event is not None:
                    on_event("公開しました")

                url = page.url
                if (
                    url.startswith("https://note.com/")
                    and "/notes/new" not in url
                    and "/login" not in url
                ):
                    return url
                return None

            if should_close is not None:
                while True:
                    if should_close is not None and should_close():
                        break
                    try:
                        if not context.pages:
                            break
                    except Exception:
                        break
                    await asyncio.sleep(0.3)

            return None
        finally:
            if guard_context_close:
                try:
                    await context.close()
                except PlaywrightError:
                    pass
            else:
                await context.close()


async def _ensure_logged_in(page: Page) -> None:
    await page.wait_for_load_state("domcontentloaded")
    if "/login" in page.url:
        raise NoteAutomationError(
            "note.com にログインしていません。先に `auto-note login` を実行してください。"
        )

    login_links = page.get_by_role("link", name=re.compile("ログイン|login", re.I))
    try:
        if await login_links.count() and await login_links.first.is_visible():
            raise NoteAutomationError(
                "note.com にログインしていません。先に `auto-note login` を実行してください。"
            )
    except PlaywrightError:
        pass


async def _fill_title(page: Page, title: str) -> None:
    locators = [
        page.get_by_placeholder(re.compile("タイトル|Title", re.I)).first,
        page.locator("textarea[placeholder*='タイトル']").first,
        page.locator("input[placeholder*='タイトル']").first,
        page.locator("[contenteditable='true'][aria-label*='タイトル']").first,
        page.get_by_role("textbox", name=re.compile("タイトル|Title", re.I)).first,
    ]
    for fallback in [
        lambda: page.locator('[aria-label*="記事タイトル"]').first,
        lambda: page.locator('[placeholder*="記事タイトル"]').first,
        lambda: page.locator('[aria-label*="見出し"]').first,
        lambda: page.get_by_role("textbox", name="タイトル", exact=False).first,
    ]:
        try:
            locators.append(fallback())
        except PlaywrightError:
            pass
    locator = await _first_visible(locators, "title field")
    await _replace_text(locator, title)


async def _fill_body(page: Page, body: str) -> None:
    contenteditable = page.locator("[contenteditable='true']")
    locators = [
        page.locator(".ProseMirror[contenteditable='true']").first,
        page.locator("[contenteditable='true'][data-placeholder*='本文']").first,
        page.locator("[contenteditable='true'][aria-label*='本文']").first,
        page.get_by_role("textbox", name=re.compile("本文|内容|Body|Content", re.I)).first,
    ]

    try:
        count = await contenteditable.count()
        if count > 1:
            locators.append(contenteditable.nth(1))
        elif count == 1:
            locators.append(contenteditable.first)
    except PlaywrightError:
        pass

    for fallback in [
        lambda: page.locator('[data-placeholder*="本文を入力"]').first,
        lambda: page.locator('[aria-label*="本文を入力"]').first,
        lambda: page.locator('[aria-label*="記事を書く"]').first,
        lambda: page.get_by_role("textbox", name="エディタ", exact=False).first,
    ]:
        try:
            locators.append(fallback())
        except PlaywrightError:
            pass

    locator = await _first_visible(locators, "body editor")
    await _replace_text(locator, body)


async def _replace_text(locator: Locator, text: str) -> None:
    await locator.click()
    try:
        await locator.fill(text)
        return
    except PlaywrightError:
        pass

    page = locator.page
    await _select_all(page)
    try:
        await page.keyboard.insert_text(text)
    except PlaywrightError as exc:
        raise NoteAutomationError("エディタへの本文入力に失敗しました。") from exc


async def _publish(page: Page) -> None:
    step_one_labels = [
        "公開設定",
        "公開に進む",
        "公開へ進む",
        "投稿",
        "公開",
        "次へ",
        "設定して公開",
        "Publish",
        "Next",
    ]
    step_two_labels = [
        "投稿する",
        "公開する",
        "無料で公開",
        "有料で公開",
        "この内容で公開",
        "公開",
        "投稿",
        "Publish",
        "Post",
    ]

    await _click_first_text(page, step_one_labels)
    await page.wait_for_timeout(500)
    try:
        step_two_selector = ", ".join(
            [f'button:has-text("{label}")' for label in step_two_labels]
            + [f'[role=button]:has-text("{label}")' for label in step_two_labels]
        )
        await page.wait_for_selector(step_two_selector, state="visible", timeout=3_000)
    except (PlaywrightError, PlaywrightTimeoutError):
        pass
    await _click_first_text(page, step_two_labels)


async def _click_first_text(page: Page, labels: Iterable[str]) -> None:
    last_error: Exception | None = None
    for label in labels:
        strategies = [
            lambda: page.get_by_role("button", name=label, exact=False).first,
            lambda: page.get_by_role("link", name=label, exact=False).first,
            lambda: page.locator(f'[aria-label*="{label}"]').first,
            lambda: page.locator(f'[role=button]:has-text("{label}")').first,
            lambda: page.get_by_text(label).first,
            lambda: page.locator(f'button:has-text("{label}")').first,
        ]
        for strategy in strategies:
            try:
                locator = strategy()
                if await locator.count() == 0:
                    continue
                await locator.wait_for(state="visible", timeout=3_000)
                try:
                    await locator.scroll_into_view_if_needed()
                except (PlaywrightError, PlaywrightTimeoutError):
                    pass
                if not await locator.is_enabled():
                    continue
                await locator.click()
                return
            except (PlaywrightError, PlaywrightTimeoutError) as exc:
                last_error = exc

    raise NoteAutomationError("publish button が見つかりませんでした。note の画面変更により調整が必要かもしれません。") from last_error


async def _first_visible(locators: Iterable[Locator], label: str) -> Locator:
    last_error: Exception | None = None
    for locator in locators:
        try:
            await locator.wait_for(state="visible", timeout=3_000)
            try:
                await locator.scroll_into_view_if_needed()
            except (PlaywrightError, PlaywrightTimeoutError):
                pass
            if await locator.is_enabled():
                return locator
        except PlaywrightTimeoutError as exc:
            last_error = exc
            try:
                if await locator.count() == 0:
                    continue
            except PlaywrightError as count_exc:
                last_error = count_exc
        except PlaywrightError as exc:
            last_error = exc

    raise NoteAutomationError(f"{label} が見つかりませんでした。note の画面変更により調整が必要かもしれません。") from last_error


async def _select_all(page: Page) -> None:
    if page.context.browser and page.context.browser.browser_type.name == "webkit":
        await page.keyboard.press("Meta+A")
    else:
        await page.keyboard.press("Control+A")


async def _soft_wait_for_idle(page: Page) -> None:
    try:
        await page.wait_for_load_state("networkidle", timeout=10_000)
    except PlaywrightTimeoutError:
        pass


def _browser_channel_kwargs(options: BrowserOptions) -> dict[str, str]:
    if not options.browser_channel or options.browser_channel == "chromium":
        return {}
    return {"channel": options.browser_channel}
