import io
import logging
import os
import sys

from dotenv import load_dotenv
from google.genai import types as genai_types
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    EndpointingOptions,
    JobContext,
    TurnHandlingOptions,
    cli,
    room_io,
)
from livekit.agents.beta.tools import EndCallTool
from livekit.plugins import ai_coustics, google

from browser import BrowserManager
from mcp_client import MCPClientManager
from prompts import AGENT_INSTRUCTIONS
from tools import BrowserTools

load_dotenv(".env.local")

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    os.environ["PYTHONIOENCODING"] = "utf-8"

logging.basicConfig(level=logging.INFO, encoding="utf-8", errors="replace")


class Assistant(Agent):
    def __init__(
        self,
        browser: BrowserManager | None = None,
        extra_tools: list | None = None,
    ) -> None:
        self.browser = browser or BrowserManager()
        self.browser_tools = BrowserTools(self.browser)
        self._end_call_tool = EndCallTool(
            extra_description=(
                "Only end the call after the user clearly says they are finished, "
                "says goodbye, or directly asks to end the call."
            ),
            end_instructions=(
                "Give Jarvis's brief, polite British-English farewell, then end the call."
            ),
        )
        tools = [
            *self.browser_tools.tools,
            *self._end_call_tool.tools,
            *(extra_tools or []),
        ]
        super().__init__(
            llm=google.beta.realtime.RealtimeModel(
                model="gemini-3.1-flash-live-preview",
                voice="Puck",
                language="te-IN",
            ),
            instructions=AGENT_INSTRUCTIONS,
            tools=tools,
        )


server = AgentServer()


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Lazy browser management (starts automatically on first browser tool call)
    browser = BrowserManager()
    ctx.add_shutdown_callback(browser.close)

    mcp_manager = MCPClientManager()
    await mcp_manager.initialize()
    ctx.add_shutdown_callback(mcp_manager.close)

    # Optimized AgentSession for sub-second turn-taking and low latency
    session = AgentSession(
        turn_handling=TurnHandlingOptions(
            endpointing=EndpointingOptions(
                mode="dynamic",
                min_delay=0.3,
                max_delay=1.0,
            ),
            preemptive_generation={"enabled": True},
        ),
    )

    enable_nc = os.getenv("ENABLE_NOISE_CANCELLATION", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    noise_canceller = ai_coustics.audio_enhancement() if enable_nc else None

    await session.start(
        agent=Assistant(browser, extra_tools=mcp_manager.tools),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            video_input=True,
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=noise_canceller,
                frame_size_ms=20,
            ),
            audio_output=room_io.AudioOutputOptions(
                track_publish_options=rtc.TrackPublishOptions(
                    red=True,
                    dtx=True,
                ),
            ),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
