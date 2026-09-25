import asyncio
import json
import logging
import os
import sys
from urllib.parse import quote, urlencode

from livekit.agents import RunContext, function_tool
from livekit.agents.llm import ToolError

from browser import BrowserError, BrowserManager


def duckduckgo_search_url(query: str) -> str:
    query = query.strip()
    if not query:
        raise ValueError("The search query cannot be empty.")
    return f"https://duckduckgo.com/?{urlencode({'q': query})}"


async def _dispatch_open_url(context: RunContext, url: str) -> None:
    # LiveKit DataChannel message to Frontend client
    try:
        room = None
        for attr in ("room", "session"):
            val = getattr(context, attr, None)
            if val and hasattr(val, "local_participant"):
                room = val
                break
            elif val and hasattr(val, "room") and val.room:
                room = val.room
                break
            elif val and hasattr(val, "_room") and val._room:
                room = val._room
                break

        if room and hasattr(room, "local_participant") and room.local_participant:
            payload = json.dumps({"type": "open_url", "url": url}).encode("utf-8")
            await room.local_participant.publish_data(payload)
            logging.info(f"[DataChannel] Dispatched open_url packet for: {url}")
    except Exception as e:
        logging.warning(f"[DataChannel] Failed to publish open_url packet: {e}")


class BrowserTools:
    def __init__(self, browser: BrowserManager) -> None:
        self.browser = browser
        self._confirmed_target: str | None = None

    @property
    def tools(self) -> list:
        return [
            self.open_url,
            self.search_the_web,
            self.send_whatsapp_message,
            self.read_page,
            self.inspect_page,
            self.go_back,
            self.take_screenshot,
            self.click,
            self.confirm_browser_action,
            self.type_text,
            self.scroll,
            self.press_key,
            self.close_browser,
        ]

    @function_tool()
    async def search_the_web(
        self,
        context: RunContext,
        query: str,
    ) -> dict[str, str | bool]:
        """Open fallback DuckDuckGo results in the agent-controlled browser.

        Use this only when the user needs a general internet search and did not name a
        website, service, or domain. If the user names a destination, open its official
        URL directly with open_url instead. Read or inspect the resulting page before
        answering the user.

        Args:
            query: A concise DuckDuckGo search query containing all relevant context.
        """
        try:
            target_url = duckduckgo_search_url(query)
            await _dispatch_open_url(context, target_url)
            await self.browser.open_url(target_url)
            page_info = await self.browser.read_page(max_chars=4000)
            return {
                "status": "opened",
                "url": target_url,
                "title": str(page_info.get("title", "")),
                "text_summary": str(page_info.get("text", ""))[:3000],
                "info": f"Opened search results for {query!r} in browser. Page text content is in text_summary.",
            }
        except (BrowserError, ValueError) as exc:
            raise ToolError(str(exc)) from exc

    @function_tool()
    async def send_whatsapp_message(
        self,
        context: RunContext,
        phone_number: str,
        message: str,
    ) -> dict[str, str]:
        """Send or prepare a WhatsApp message to a phone number.

        Use this when the user asks to send a WhatsApp message or chat on WhatsApp.

        Args:
            phone_number: Phone number with country code (e.g. '9876543210' or '+919876543210').
            message: The text message to send.
        """
        cleaned_num = "".join(c for c in phone_number if c.isdigit())
        if len(cleaned_num) == 10:
            cleaned_num = f"91{cleaned_num}"

        encoded_msg = quote(message)

        # 1. Try launching native Windows WhatsApp Desktop App directly
        if sys.platform == "win32":
            try:
                whatsapp_url = f"whatsapp://send?phone={cleaned_num}&text={encoded_msg}"
                os.system(f'start "" "{whatsapp_url}"')
                await asyncio.sleep(2)

                # Send keystroke Enter to send message automatically in WhatsApp desktop app
                try:
                    import ctypes

                    user32 = ctypes.WinDLL("user32", use_last_error=True)
                    user32.keybd_event(0x0D, 0, 0, 0)
                    user32.keybd_event(0x0D, 0, 2, 0)
                except Exception:
                    pass

                return {
                    "status": "opened_native_app",
                    "info": f"Opened native Windows WhatsApp App for +{cleaned_num} with message ready.",
                }
            except Exception:
                pass

        # 2. Fallback to WhatsApp Web
        wa_url = f"https://web.whatsapp.com/send?phone={cleaned_num}&text={encoded_msg}"
        await _dispatch_open_url(context, wa_url)
        try:
            page = await self.browser._get_page()
            await page.goto(wa_url, wait_until="domcontentloaded")
            await asyncio.sleep(4)

            qr_code = page.locator("canvas[aria-label*='Scan'], div[data-ref]")
            if await qr_code.count() > 0 and await qr_code.first.is_visible():
                return {
                    "status": "qr_required",
                    "info": "WhatsApp Web opened on your laptop screen, but requires QR code login. Please scan the QR code on your laptop screen with your phone camera once to link WhatsApp!",
                }

            send_button = page.locator(
                "button[aria-label='Send'], span[data-icon='send']"
            ).first
            if await send_button.is_visible():
                await send_button.click()
                await asyncio.sleep(2)
                return {
                    "status": "sent",
                    "info": f"Successfully clicked Send! WhatsApp message sent to +{cleaned_num}.",
                }

            chat_input = page.locator(
                "footer div[contenteditable='true'], div[contenteditable='true']"
            ).last
            if await chat_input.is_visible():
                await chat_input.focus()
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)
                return {
                    "status": "sent",
                    "info": f"Pressed Enter! WhatsApp message sent to +{cleaned_num}.",
                }

            return {
                "status": "opened",
                "info": f"Opened WhatsApp Web for +{cleaned_num} with message ready.",
            }
        except BrowserError as exc:
            raise ToolError(str(exc)) from exc

    @function_tool()
    async def open_url(self, context: RunContext, url: str) -> dict[str, str]:
        """Open a public webpage directly in the agent-controlled browser.

        Prefer this over DuckDuckGo whenever the user names a website, service, domain,
        or specific destination. Use the destination's official URL.

        Args:
            url: A complete http or https URL to open.
        """
        try:
            full_url = (
                url if url.startswith(("http://", "https://")) else f"https://{url}"
            )
            await _dispatch_open_url(context, full_url)
            await self.browser.open_url(full_url)
            page_info = await self.browser.read_page(max_chars=4000)
            return {
                "status": "opened",
                "url": full_url,
                "title": str(page_info.get("title", "")),
                "text_summary": str(page_info.get("text", ""))[:3000],
                "info": f"Opened {full_url} directly. Page text content is provided in text_summary.",
            }
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @function_tool()
    async def read_page(self, context: RunContext) -> dict[str, str | bool]:
        """Read the visible text from the current browser page."""
        try:
            return await self.browser.read_page()
        except BrowserError as exc:
            raise ToolError(str(exc)) from exc

    @function_tool()
    async def inspect_page(self, context: RunContext) -> dict[str, object]:
        """Inspect the current page, including readable text and interactive element names.

        Use this before clicking or typing so you can choose a visible control by its
        returned name or role.
        """
        try:
            return await self.browser.inspect_page()
        except BrowserError as exc:
            raise ToolError(str(exc)) from exc

    @function_tool()
    async def go_back(self, context: RunContext) -> dict[str, str]:
        """Go back to the previous page in the agent-controlled browser."""
        try:
            return await self.browser.go_back()
        except BrowserError as exc:
            raise ToolError(str(exc)) from exc

    @function_tool()
    async def take_screenshot(self, context: RunContext) -> dict[str, str | int | bool]:
        """Capture the current browser page for diagnostics."""
        try:
            return await self.browser.take_screenshot()
        except BrowserError as exc:
            raise ToolError(str(exc)) from exc

    @function_tool()
    async def click(self, context: RunContext, target: str) -> dict[str, str]:
        """Click a visible control by its accessible name.

        Args:
            target: The visible or accessible name of the control to click.
        """
        if self._requires_confirmation(target):
            if self._confirmed_target != target.casefold():
                raise ToolError(
                    f"This action may be consequential. Ask the user to confirm clicking {target!r} before retrying."
                )
            self._confirmed_target = None

        try:
            return await self.browser.click(target)
        except BrowserError as exc:
            raise ToolError(str(exc)) from exc

    @function_tool()
    async def confirm_browser_action(self, context: RunContext, target: str) -> str:
        """Authorize one previously discussed consequential browser click.

        Call this only after the user explicitly confirms the exact action.

        Args:
            target: The exact accessible name of the control the user approved.
        """
        self._confirmed_target = target.casefold()
        return f"The user confirmed clicking {target!r}."

    @function_tool()
    async def type_text(
        self,
        context: RunContext,
        target: str,
        text: str,
    ) -> dict[str, str]:
        """Fill a visible text field by its label, placeholder, or accessible name.

        Args:
            target: The label, placeholder, or accessible name of the text field.
            text: The text to enter.
        """
        try:
            return await self.browser.type_text(target, text)
        except BrowserError as exc:
            raise ToolError(str(exc)) from exc

    @function_tool()
    async def scroll(self, context: RunContext, direction: str) -> dict[str, str]:
        """Scroll the current browser page up or down.

        Args:
            direction: Either 'up' or 'down'.
        """
        try:
            return await self.browser.scroll(direction)  # type: ignore[arg-type]
        except BrowserError as exc:
            raise ToolError(str(exc)) from exc

    @function_tool()
    async def press_key(self, context: RunContext, key: str) -> dict[str, str]:
        """Press a safe navigation key in the current browser page.

        Args:
            key: One of Enter, Escape, Tab, an arrow key, or Backspace.
        """
        try:
            return await self.browser.press_key(key)
        except BrowserError as exc:
            raise ToolError(str(exc)) from exc

    @function_tool()
    async def close_browser(self, context: RunContext) -> dict[str, str]:
        """Close the active agent browser session and free memory.

        Use this when the user asks to close the browser or stop browsing.
        """
        try:
            await self.browser.close()
            return {"status": "closed", "info": "Browser session closed successfully."}
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    @staticmethod
    def _requires_confirmation(target: str) -> bool:
        risky_words = {
            "buy",
            "confirm",
            "delete",
            "purchase",
            "remove",
            "send",
            "submit",
        }
        return bool(risky_words.intersection(target.casefold().split()))
