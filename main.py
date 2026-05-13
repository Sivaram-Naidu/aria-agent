import os
import uuid
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

load_dotenv()

from aria.core.agent import build_aria_graph
from aria.voice.stt import listen
from aria.voice.tts import speak

console = Console()

EMOTION_COLORS = {
    "HAPPY":   "yellow",
    "EXCITED": "bright_yellow",
    "SAD":     "blue",
    "ANGRY":   "red",
    "ANXIOUS": "orange3",
    "NEUTRAL": "white"
}

EMOTION_ICONS = {
    "HAPPY":   "😊",
    "EXCITED": "🎉",
    "SAD":     "💙",
    "ANGRY":   "😤",
    "ANXIOUS": "😟",
    "NEUTRAL": "😐"
}

MODE_LABELS = {
    "support": "[bold blue]💜 Support Mode[/bold blue]",
    "friend":  "[bold yellow]✨ Friend Mode[/bold yellow]"
}


def print_welcome(voice_mode: bool):
    mode_str = "[bold green]VOICE[/bold green]" if voice_mode else "[bold cyan]TEXT[/bold cyan]"
    console.print(Panel.fit(
        f"[bold magenta]ARIA[/bold magenta] — [italic]Your Adaptive Intelligent Companion[/italic]\n"
        f"[dim]Powered by LangGraph + Groq + Whisper + edge-tts[/dim]\n"
        f"Input mode: {mode_str}  [dim]| Type 'switch' to toggle | 'quit' to exit[/dim]",
        border_style="magenta"
    ))
    console.print()


def run_aria(aria, config, user_input: str):
    """Send input through the LangGraph agent and return result."""
    result = aria.invoke(
        {
            "user_input": user_input,
            "messages": [HumanMessage(content=user_input)],
            "emotion": "NEUTRAL",
            "mode": "friend",
            "aria_response": ""
        },
        config=config
    )
    return result


def display_response(result: dict):
    """Pretty print emotion, mode and ARIA's response."""
    emotion  = result.get("emotion", "NEUTRAL")
    mode     = result.get("mode", "friend")
    response = result.get("aria_response", "")

    color      = EMOTION_COLORS.get(emotion, "white")
    icon       = EMOTION_ICONS.get(emotion, "")
    mode_label = MODE_LABELS.get(mode, "")

    console.print(
        f"[dim]Emotion: [{color}]{icon} {emotion}[/{color}]  |  {mode_label}[/dim]"
    )
    console.print()
    console.print(Panel(
        Text(response, style="white"),
        title="[bold magenta]✨ ARIA[/bold magenta]",
        border_style="magenta",
        padding=(0, 1)
    ))
    console.print()

    return response


def main():
    # ── Startup mode selection ──
    console.print("\n[bold]How do you want to talk to ARIA?[/bold]")
    console.print("  [bold cyan]1[/bold cyan] → Text mode")
    console.print("  [bold green]2[/bold green] → Voice mode")
    console.print()
    console.print("[dim]Enter 1 or 2:[/dim] ", end="")

    choice = input().strip()
    voice_mode = (choice == "2")

    print_welcome(voice_mode)

    # ── Build agent ──
    aria   = build_aria_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    # ── Hardcoded greeting — does NOT go through the graph ──
    # This keeps memory clean so ARIA never re-introduces herself
    greeting = "Hey! I'm ARIA. What's on your mind?"
    console.print(Panel(
        Text(greeting, style="white"),
        title="[bold magenta]✨ ARIA[/bold magenta]",
        border_style="magenta",
        padding=(0, 1)
    ))
    console.print()

    if voice_mode:
        with console.status("[dim]ARIA is speaking...[/dim]", spinner="dots"):
            speak(greeting)

    # ── Main conversation loop ──
    while True:
        try:
            if voice_mode:
                console.print("[bold green]🎙️  Press ENTER to speak (5 sec)[/bold green] ", end="")
                input()  # wait for enter key

                with console.status("[dim]Recording...[/dim]", spinner="dots"):
                    user_input = listen(duration=5)

                if not user_input:
                    console.print("[dim]Didn't catch that — try again[/dim]\n")
                    continue

                console.print(f"[bold cyan]You (heard):[/bold cyan] {user_input}")

            else:
                console.print("[bold cyan]You:[/bold cyan] ", end="")
                user_input = input().strip()

            if not user_input:
                continue

            # ── Mode toggle ──
            if user_input.lower() == "switch":
                voice_mode = not voice_mode
                status = "VOICE 🎙️" if voice_mode else "TEXT ⌨️"
                console.print(f"[dim]Switched to {status} mode[/dim]\n")
                continue

            # ── Exit ──
            if user_input.lower() in ["quit", "exit", "bye"]:
                farewell = "Take care! I'm always here when you need me."
                console.print(f"\n[magenta]ARIA:[/magenta] {farewell} 💜")
                if voice_mode:
                    speak(farewell)
                break

            # ── Run through LangGraph agent ──
            with console.status("[dim]ARIA is thinking...[/dim]", spinner="dots"):
                result = run_aria(aria, config, user_input)

            response = display_response(result)

            # ── Speak if voice mode ──
            if voice_mode:
                with console.status("[dim]ARIA is speaking...[/dim]", spinner="dots"):
                    speak(response)

        except KeyboardInterrupt:
            console.print("\n\n[magenta]ARIA:[/magenta] Goodbye! 💜")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
