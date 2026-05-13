import edge_tts
import asyncio
import tempfile
import os
import pygame

# Neerja — clear, natural Indian English female voice
ARIA_VOICE = "en-IN-NeerjaNeural"

# Voice personality settings
ARIA_RATE  = "+0%"    # speech speed — 0% is natural, try +5% or -5%
ARIA_PITCH = "+5Hz"   # pitch — try +5Hz for slightly warmer tone


async def _speak_async(text: str):
    """
    Async function: converts text → audio using edge-tts,
    saves to temp file, plays it with pygame.
    """
    communicate = edge_tts.Communicate(
        text=text,
        voice=ARIA_VOICE,
        rate=ARIA_RATE,
        pitch=ARIA_PITCH
    )
    
    # Save to temp mp3
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_path = tmp.name
    tmp.close()
    
    await communicate.save(tmp_path)
    
    # Play with pygame
    pygame.mixer.init()
    pygame.mixer.music.load(tmp_path)
    pygame.mixer.music.play()
    
    # Wait until done playing
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)
    
    pygame.mixer.music.unload()
    pygame.mixer.quit()
    
    # Cleanup
    try:
        os.remove(tmp_path)
    except:
        pass


def speak(text: str):
    """
    Synchronous wrapper around the async TTS function.
    Call this from main.py — it handles the event loop internally.
    """
    # Clean text before speaking — remove any markdown artifacts
    clean = text.replace("*", "").replace("#", "").replace("_", "").strip()
    
    try:
        asyncio.run(_speak_async(clean))
    except RuntimeError:
        # If event loop already running (rare), use this fallback
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_speak_async(clean))
        loop.close()
