"""Playwright-based form filler — fills application forms, NEVER submits."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from playwright.async_api import Page, async_playwright

from jobhunter.domain.application_fill import (
    Blocker,
    BlockerKind,
    FieldType,
    FilledField,
    ReviewPacket,
)

if TYPE_CHECKING:
    from jobhunter.adapters.storage.local_storage import LocalStorageService

logger = structlog.get_logger()


def _detect_blockers(page_content: str) -> list[Blocker]:
    """Detect CAPTCHA or login walls from page HTML."""
    blockers: list[Blocker] = []
    content_lower = page_content.lower()

    if "g-recaptcha" in content_lower or "recaptcha" in content_lower:
        blockers.append(Blocker(kind=BlockerKind.CAPTCHA, detail="reCAPTCHA detected on page"))

    if 'type="password"' in content_lower:
        blockers.append(
            Blocker(kind=BlockerKind.LOGIN_WALL, detail="Password field detected — login required")
        )

    has_sign_in = "sign in" in content_lower or "log in" in content_lower
    if (
        has_sign_in
        and "password" in content_lower
        and not any(b.kind == BlockerKind.LOGIN_WALL for b in blockers)
    ):
        blockers.append(
            Blocker(
                kind=BlockerKind.LOGIN_WALL,
                detail="Login form detected on page",
            )
        )

    return blockers


async def _screenshot(page: Page, storage: LocalStorageService, app_id: str, step: str) -> str:
    """Take a screenshot and store it; return the storage key."""
    png_bytes = await page.screenshot(full_page=True)
    key = f"screenshots/{app_id}/{step}.png"
    await storage.store(key, png_bytes)
    return key


async def _fill_text_field(page: Page, selector: str, value: str) -> None:
    await page.fill(selector, value)


async def _fill_select(page: Page, selector: str, value: str) -> None:
    await page.select_option(selector, value)


async def _fill_radio(page: Page, name: str, value: str) -> None:
    await page.check(f"input[name='{name}'][value='{value}']")


async def _fill_checkbox(page: Page, selector: str, check: bool = True) -> None:
    if check:
        await page.check(selector)
    else:
        await page.uncheck(selector)


async def _fill_file(page: Page, selector: str, file_path: str) -> None:
    await page.set_input_files(selector, file_path)


class PlaywrightFormFiller:
    """Fills application forms via Playwright. NEVER clicks submit."""

    def __init__(self, storage: LocalStorageService, *, headless: bool = True) -> None:
        self._storage = storage
        self._headless = headless

    async def fill(
        self,
        url: str,
        field_plan: dict[str, str],
        files: dict[str, str],
        application_id: str,
        job_id: str,
        profile_id: str,
    ) -> ReviewPacket:
        filled_fields: list[FilledField] = []
        uploaded_files: list[str] = []
        screenshots: list[str] = []
        blockers: list[Blocker] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self._headless)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded")

            # Check for blockers first
            content = await page.content()
            blockers.extend(_detect_blockers(content))

            if blockers:
                screenshots.append(
                    await _screenshot(page, self._storage, application_id, "blocked")
                )
                await browser.close()
                packet = ReviewPacket(
                    application_id=application_id,
                    job_id=job_id,
                    profile_id=profile_id,
                    url=url,
                    filled_fields=filled_fields,
                    uploaded_files=uploaded_files,
                    screenshots=screenshots,
                    blockers=blockers,
                    is_ready_for_review=False,
                )
                packet.fill_hash = packet.compute_fill_hash()
                return packet

            # Fill page 1 fields
            filled_fields.extend(
                await self._fill_page_fields(page, field_plan, files, uploaded_files)
            )
            screenshots.append(
                await _screenshot(page, self._storage, application_id, "page1_filled")
            )

            # Navigate to page 2 if a "Next" button exists
            next_btn = page.locator("#next-btn")
            if await next_btn.count() > 0:
                await next_btn.click()
                await page.wait_for_timeout(300)

                filled_fields.extend(
                    await self._fill_page_fields(page, field_plan, files, uploaded_files)
                )
                screenshots.append(
                    await _screenshot(page, self._storage, application_id, "page2_filled")
                )

            # Check for unmapped required fields
            required_inputs = await page.query_selector_all("[required]")
            for el in required_inputs:
                name = await el.get_attribute("name") or ""
                value = await el.get_attribute("value") or ""
                el_type = await el.get_attribute("type") or "text"
                if el_type == "file":
                    files_attr = await el.get_attribute("data-filled")
                    is_unmapped = (
                        not files_attr
                        and name not in files
                        and not any(f.selector == f"[name='{name}']" for f in filled_fields)
                    )
                    if is_unmapped:
                        blockers.append(
                            Blocker(
                                kind=BlockerKind.UNMAPPED_REQUIRED_FIELD,
                                detail=f"Required file field '{name}' has no mapping",
                            )
                        )
                else:
                    el_id = await el.get_attribute("id") or ""
                    is_empty = not value and not any(
                        f.selector == f"[name='{name}']" or f.selector == f"#{el_id}"
                        for f in filled_fields
                    )
                    if is_empty:
                        blockers.append(
                            Blocker(
                                kind=BlockerKind.UNMAPPED_REQUIRED_FIELD,
                                detail=f"Required field '{name}' has no mapping",
                            )
                        )

            await browser.close()

        packet = ReviewPacket(
            application_id=application_id,
            job_id=job_id,
            profile_id=profile_id,
            url=url,
            filled_fields=filled_fields,
            uploaded_files=uploaded_files,
            screenshots=screenshots,
            blockers=blockers,
            is_ready_for_review=len(blockers) == 0,
        )
        packet.fill_hash = packet.compute_fill_hash()
        return packet

    async def _fill_page_fields(
        self,
        page: Page,
        field_plan: dict[str, str],
        files: dict[str, str],
        uploaded_files: list[str],
    ) -> list[FilledField]:
        """Fill visible fields on the current page based on the field plan."""
        filled: list[FilledField] = []

        # Text/email/tel/date inputs
        for input_el in await page.query_selector_all(
            "input:not([type='radio']):not([type='checkbox']):not([type='file']):not([type='submit']):not([type='button']):not([type='hidden'])"
        ):
            if not await input_el.is_visible():
                continue
            name = await input_el.get_attribute("name") or ""
            el_id = await input_el.get_attribute("id") or ""
            el_type = await input_el.get_attribute("type") or "text"
            placeholder = await input_el.get_attribute("placeholder") or ""

            value = self._match_field(name, el_id, placeholder, field_plan)
            if value is not None:
                selector = f"#{el_id}" if el_id else f"[name='{name}']"
                await _fill_text_field(page, selector, value)
                filled.append(
                    FilledField(
                        selector=selector,
                        label=name or el_id or placeholder,
                        field_type=(
                            FieldType(el_type)
                            if el_type in FieldType.__members__.values()
                            else FieldType.TEXT
                        ),
                        value=value,
                        source=field_plan.get(f"_source_{name}", f"field_plan.{name or el_id}"),
                    )
                )

        # Textareas
        for ta in await page.query_selector_all("textarea"):
            if not await ta.is_visible():
                continue
            name = await ta.get_attribute("name") or ""
            el_id = await ta.get_attribute("id") or ""
            value = self._match_field(name, el_id, "", field_plan)
            if value is not None:
                selector = f"#{el_id}" if el_id else f"[name='{name}']"
                await page.fill(selector, value)
                filled.append(
                    FilledField(
                        selector=selector,
                        label=name or el_id,
                        field_type=FieldType.TEXTAREA,
                        value=value,
                        source=field_plan.get(f"_source_{name}", f"field_plan.{name or el_id}"),
                    )
                )

        # Selects
        for sel in await page.query_selector_all("select"):
            if not await sel.is_visible():
                continue
            name = await sel.get_attribute("name") or ""
            el_id = await sel.get_attribute("id") or ""
            value = self._match_field(name, el_id, "", field_plan)
            if value is not None:
                selector = f"#{el_id}" if el_id else f"[name='{name}']"
                await _fill_select(page, selector, value)
                filled.append(
                    FilledField(
                        selector=selector,
                        label=name or el_id,
                        field_type=FieldType.SELECT,
                        value=value,
                        source=field_plan.get(f"_source_{name}", f"field_plan.{name or el_id}"),
                    )
                )

        # Radio groups
        radio_names_done: set[str] = set()
        for radio in await page.query_selector_all("input[type='radio']"):
            if not await radio.is_visible():
                continue
            name = await radio.get_attribute("name") or ""
            if name in radio_names_done:
                continue
            value = field_plan.get(name)
            if value is not None:
                await _fill_radio(page, name, value)
                radio_names_done.add(name)
                filled.append(
                    FilledField(
                        selector=f"input[name='{name}'][value='{value}']",
                        label=name,
                        field_type=FieldType.RADIO,
                        value=value,
                        source=field_plan.get(f"_source_{name}", f"field_plan.{name}"),
                    )
                )

        # Checkboxes
        for cb in await page.query_selector_all("input[type='checkbox']"):
            if not await cb.is_visible():
                continue
            name = await cb.get_attribute("name") or ""
            cb_value = await cb.get_attribute("value") or ""
            key = f"{name}:{cb_value}" if cb_value else name
            plan_value = field_plan.get(key)
            if plan_value is not None:
                selector = (
                    f"input[name='{name}'][value='{cb_value}']"
                    if cb_value
                    else f"input[name='{name}']"
                )
                should_check = plan_value.lower() in ("true", "yes", "1", "checked")
                await _fill_checkbox(page, selector, should_check)
                filled.append(
                    FilledField(
                        selector=selector,
                        label=f"{name}={cb_value}" if cb_value else name,
                        field_type=FieldType.CHECKBOX,
                        value=plan_value,
                        source=field_plan.get(f"_source_{key}", f"field_plan.{key}"),
                    )
                )

        # File inputs
        for file_input in await page.query_selector_all("input[type='file']"):
            if not await file_input.is_visible():
                continue
            name = await file_input.get_attribute("name") or ""
            el_id = await file_input.get_attribute("id") or ""
            file_path = files.get(name) or files.get(el_id)
            if file_path and Path(file_path).is_file():  # noqa: ASYNC240
                selector = f"#{el_id}" if el_id else f"[name='{name}']"
                await _fill_file(page, selector, file_path)
                uploaded_files.append(file_path)
                filled.append(
                    FilledField(
                        selector=selector,
                        label=name or el_id,
                        field_type=FieldType.FILE,
                        value=file_path,
                        source=f"file:{name or el_id}",
                    )
                )

        return filled

    def _match_field(
        self,
        name: str,
        el_id: str,
        placeholder: str,
        field_plan: dict[str, str],
    ) -> str | None:
        """Try to match a field to a value in the field plan by name/id/placeholder."""
        if name and name in field_plan:
            return field_plan[name]
        if el_id and el_id in field_plan:
            return field_plan[el_id]
        if placeholder:
            for key, val in field_plan.items():
                if key.lower() in placeholder.lower():
                    return val
        return None
