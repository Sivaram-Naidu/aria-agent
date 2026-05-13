import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
import os

# Load model once at module level — not every time you record
_model = None

def get_model():
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model


def record_audio(duration: int = 5, sample_rate: int = 16000) -> str:
    """
    Records audio from mic for `duration` seconds.
    Returns path to a temp .wav file.
    """
    print(f"\n🎙️  Listening for {duration} seconds... (speak now)")
    
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32"
    )
    sd.wait()  # wait until recording is done
    
    # Save to temp file
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, audio, sample_rate)
    return tmp.name


def transcribe(audio_path: str) -> str:
    """
    Transcribes a .wav file using Whisper base.
    Returns the transcribed text string.
    """
    model = get_model()
    result = model.transcribe(audio_path, fp16=False, language="en")
    
    # Cleanup temp file
    try:
        os.remove(audio_path)
    except:
        pass
    
    text = result["text"].strip()
    return text


def listen(duration: int = 5) -> str:
    """
    Full pipeline: record → transcribe → return text.
    This is the main function called from main.py
    """
    audio_path = record_audio(duration=duration)
    text = transcribe(audio_path)
    return text
