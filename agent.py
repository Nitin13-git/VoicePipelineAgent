import logging
import os
import argparse
from dotenv import load_dotenv
from livekit.agents import (
    Agent, AgentSession, AutoSubscribe, JobContext,
    JobProcess, WorkerOptions, cli, metrics, RoomInputOptions,
)
from livekit.plugins import cartesia, anthropic, deepgram, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("voice-agent")
logging.basicConfig(level=logging.INFO)

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

def get_turn_detection(args, vad):
    if args.turn_detection == 'vad':
        logger.info("Using VAD-based turn detection.")
        return 'vad'
    if args.turn_detection == 'stt':
        logger.info("Using STT-based turn detection.")
        return 'stt'
    if args.turn_detection == 'multilingual':
        logger.info("Using MultilingualModel turn detector.")
        return MultilingualModel()
    raise ValueError(f"Unknown turn_detection: {args.turn_detection}")

def get_stt(args):
    logger.info(f"Initializing Deepgram STT: model={args.deepgram_model}")
    return deepgram.STT(
        api_key=args.deepgram_api_key,
        model=args.deepgram_model,
        language=os.getenv('DEEPGRAM_LANGUAGE', 'en-US'),
        endpointing_ms=int(args.min_endpointing_delay * 1000),
        punctuate=True,
        smart_format=True,
        interim_results=True,
    )

def get_tts(args):
    logger.info(f"Initializing Cartesia TTS: model={args.cartesia_model}, voice={args.cartesia_voice}")
    return cartesia.TTS(
        model=args.cartesia_model,
        voice=args.cartesia_voice,
        language=os.getenv('CARTESIA_LANGUAGE', 'en'),
    )
# ---------------------- SSML EXPERIMENT START ----------------------
    # Injecting SSML-enhanced prompts into Cartesia TTS for better prosody control.
    # This example illustrates emphasis, prosody, and say-as for acronyms.

    # Example SSML string (used during internal testing):
    # ssml_text = '''
    # <speak>
    #   Please <emphasis level="strong">listen carefully</emphasis>.
    #   The code is <say-as interpret-as="spell-out">GPT</say-as>.
    #   Now I will speak <prosody rate="slow" pitch="+2st">slowly and clearly</prosody>.
    # </speak>
    # '''

    # During testing, passed to TTS like:
    # tts.speak(ssml_text, ssml=True)

    # This tested:
    # - Number and acronym pronunciation
    # - Expressiveness and clarity (Mean Opinion Score)
    # ----------------------- SSML EXPERIMENT END ----------------------


async def entrypoint(ctx: JobContext):
    # Parse only internal flags here
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--min_endpointing_delay', type=float, default=float(os.getenv('MIN_ENDPOINTING_DELAY', 0.5)))
    parser.add_argument('--max_endpointing_delay', type=float, default=float(os.getenv('MAX_ENDPOINTING_DELAY', 6.0)))
    parser.add_argument('--turn_detection', choices=['vad', 'stt', 'multilingual'], default=os.getenv('TURN_DETECTION', 'vad'))
    parser.add_argument('--allow_interruptions', action='store_true', default=os.getenv('ALLOW_INTERRUPtIONS', 'True') == 'True')
    parser.add_argument('--deepgram_api_key', default=os.getenv('DEEPGRAM_API_KEY'))
    parser.add_argument('--deepgram_model', default=os.getenv('DEEPGRAM_MODEL', 'nova'))
    parser.add_argument('--deepgram_tier', default=os.getenv('DEEPGRAM_TIER', 'enhanced'))
    parser.add_argument('--deepgram_version', default=os.getenv('DEEPGRAM_VERSION', 'latest'))
    parser.add_argument('--cartesia_model', default=os.getenv('CARTESIA_MODEL', 'sonic-2'))
    parser.add_argument('--cartesia_voice', default=os.getenv('CARTESIA_VOICE'))
    parser.add_argument('--end_of_turn_confidence_threshold', type=float, default=float(os.getenv('END_OF_TURN_CONFIDENCE_THRESHOLD', 0.8)))
    parser.add_argument('--min_end_of_turn_silence_when_confident', type=float, default=float(os.getenv('MIN_END_OF_TURN_SILENCE_WHEN_CONFIDENT', 0.3)))
    parser.add_argument('--max_turn_silence', type=float, default=float(os.getenv('MAX_TURN_SILENCE', 2.0)))
    args, _ = parser.parse_known_args()

    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    participant = await ctx.wait_for_participant()
    logger.info(f"starting voice assistant for {participant.identity}")

    usage = metrics.UsageCollector()
    session_metrics = lambda m: (metrics.log_metrics(m), usage.collect(m))

    vad = ctx.proc.userdata["vad"]
    stt = get_stt(args)
    tts = get_tts(args)
    turn_detection = get_turn_detection(args, vad)

    session = AgentSession(
        stt=stt,
        tts=tts,
        vad=(vad if args.turn_detection in ['vad','multilingual'] else None),
        turn_detection=turn_detection,
        min_endpointing_delay=args.min_endpointing_delay,
        max_endpointing_delay=args.max_endpointing_delay,
        allow_interruptions=args.allow_interruptions,
    )
    session.on("metrics_collected", session_metrics)

    await session.start(
        room=ctx.room,
        agent=Agent(
            instructions="You're a concise voice assistant demo.",
            stt=stt,
            llm=anthropic.LLM(model="claude-3-5-haiku-20241022"),
            tts=tts,
            turn_detection=turn_detection,
        ),
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
