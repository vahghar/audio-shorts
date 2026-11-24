import os
import json
import time
import warnings
from dotenv import load_dotenv

# Silence library warnings
warnings.filterwarnings("ignore")

# Load environment keys
load_dotenv()

def get_live_news(topic: str) -> str:
    """
    Pulls 3-4 current news snippets from DuckDuckGo to ground the debate.
    """
    print(f"\n[1/3] Searching live news for: '{topic}'...")
    try:
        from duckduckgo_search import DDGS
        results = DDGS().text(f"{topic} news today", max_results=4)
        if not results:
            return "No recent news found. Rely on foundational knowledge."
        snippets = [f"- {r.get('title')}: {r.get('body')}" for r in results]
        return "\n".join(snippets)
    except Exception as e:
        print(f"Note: News fetch skipped ({e}). Proceeding with base knowledge.")
        return f"Recent developments regarding {topic}."

def get_llm_client_and_model():
    """
    Returns Groq client and an available chat model supporting JSON mode.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("\n[!] GROQ_API_KEY not found in your environment or .env file.")
        api_key = input("Paste your free Groq API key here: ").strip()
        if not api_key:
            raise SystemExit("Exiting: Groq API key required.")
        with open(".env", "a", encoding="utf-8") as f:
            f.write(f"\nGROQ_API_KEY={api_key}\n")

    from groq import Groq
    client = Groq(api_key=api_key)

    preferred_models = [
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "openai/gpt-oss-20b"
    ]
    
    try:
        available_ids = {m.id for m in client.models.list().data}
        selected_model = next((m for m in preferred_models if m in available_ids), "qwen/qwen3.8-27b")
    except Exception:
        selected_model = "qwen/qwen3.8-27b"

    return client, selected_model

def generate_podcast_script(topic: str, turns: int = 10):
    """
    Upgraded writer loop:
    - Enforces strict F5-TTS text normalization (no ALL-CAPS, spells out symbols/acronyms).
    - Injects mixing metadata (interrupt, speed, pause_after_ms) for Colab audio stitching.
    - Eliminates double-user role bug.
    - Uses Groq json_object mode with max_tokens=220 to prevent mid-sentence cutoffs.
    - Wraps up cleanly on the final turn.
    """
    with open("personas.json", "r", encoding="utf-8") as f:
        personas = json.load(f)

    p1 = personas["joe_rogan"]
    p2 = personas["nikhil_kamath"]

    news_brief = get_live_news(topic)
    client, model_name = get_llm_client_and_model()
    print(f"Using Groq model: {model_name} (JSON Mode)")

    transcript = []
    # Running history formatted as clean speaker: text lines
    history_lines = []

    print(f"\n[2/3] Generating {turns}-turn podcast: {p1['name']} & {p2['name']}")
    print("=" * 68)

    speakers = [("joe_rogan", p1), ("nikhil_kamath", p2)]

    for turn_idx in range(turns):
        speaker_id, speaker_meta = speakers[turn_idx % 2]
        other_speaker_id, other_speaker_meta = speakers[(turn_idx + 1) % 2]
        is_first_turn = (turn_idx == 0)
        is_final_turn = (turn_idx == turns - 1)
        is_spice_turn = (turn_idx == 5)

        # Contextual turn goal injected into system instructions
        turn_cue = "React directly to what was just said and push the debate forward."
        if is_first_turn:
            turn_cue = f"Open the podcast episode. Hook the listener and ask {other_speaker_meta['name']} about {topic}."
        elif is_spice_turn:
            turn_cue = "DIRECTOR CUE: Shift into a wilder, more contrarian, or personal tangent right now."
        elif is_final_turn:
            turn_cue = "FINAL TURN: Deliver a sharp, memorable closing punchline or philosophical conclusion to end the episode cleanly."

        # Complete persona injection with cadence, examples, and negative constraints
        system_prompt = f"""You are {speaker_meta['name']} in an intense, fast-paced 2-person podcast with {other_speaker_meta['name']}.
Current Topic: {topic}

LIVE NEWS BRIEF:
{news_brief}

YOUR CHARACTER PROFILE:
- Worldview: {speaker_meta['worldview']}
- Cadence: {speaker_meta['cadence']}
- Speech Quirks: {speaker_meta['quirks']}
- Friction Rule: {speaker_meta['friction_rule']}
- Things you NEVER do: {speaker_meta['never_do']}
- Tone Reference Lines:
{json.dumps(speaker_meta.get('example_lines', []), indent=2)}

CURRENT TURN DIRECTIVE:
{turn_cue}

CRITICAL RULES FOR SPEECH & TTS COMPATIBILITY:
1. BREVITY: Speak 2 to 3 sentences max (under 55 words).
2. NO ALL-CAPS: F5-TTS will spell out ALL-CAPS words letter-by-letter. Never write 'WAIT' or 'WILD' (write 'wait', 'wild').
3. SPELL OUT SYMBOLS & ACRONYMS:
   - Write 'twelve billion dollars' instead of '$12B'
   - Write 'P to E ratio' instead of 'P/E'
   - Write 'percent' instead of '%'
   - Write 'A I' or 'artificial intelligence' instead of 'AI'
   - Write 'G P Us' instead of 'GPUs'
4. OUTPUT FORMAT:
You MUST respond with a valid JSON object matching this schema:
{{
  "text": "Your clean spoken dialogue formatted for TTS",
  "interrupt": true or false,  // true if you are cutting in or reacting sharply
  "speed": 1.02,               // float between 0.98 and 1.08
  "pause_after_ms": 300        // int: 150 if interrupt is true, else 250 to 400
}}
"""

        # Build clean dialogue prompt without consecutive duplicate roles
        formatted_history = "\n".join(history_lines[-6:]) if history_lines else "(Podcast starting now)"
        user_message = f"TRANSCRIPT SO FAR:\n{formatted_history}\n\nDeliver your next turn as {speaker_meta['name']} in JSON:"

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                temperature=0.85,
                max_tokens=220
            )

            raw_json = response.choices[0].message.content.strip()
            turn_data = json.loads(raw_json)
        except Exception as e:
            # Resilient fallback if JSON decoding hiccups
            print(f"Warning on turn {turn_idx+1}: {e}")
            turn_data = {
                "text": f"Bro, honestly, when you look at {topic}, the incentives are just completely upside down.",
                "interrupt": False,
                "speed": 1.02,
                "pause_after_ms": 300
            }

        speech_text = turn_data.get("text", "").strip()
        interrupt = bool(turn_data.get("interrupt", False))
        speed = float(turn_data.get("speed", 1.02))
        pause_after_ms = int(turn_data.get("pause_after_ms", 150 if interrupt else 300))

        # Record into history
        history_lines.append(f"{speaker_meta['name']}: {speech_text}")

        # Store rich episode item with mixing metadata for Colab
        transcript.append({
            "speaker": speaker_id,
            "speaker_name": speaker_meta["name"],
            "voice_file": speaker_meta.get("voice_file", "rogan.wav" if "joe" in speaker_id else "kamath.wav"),
            "text": speech_text,
            "interrupt": interrupt,
            "speed": speed,
            "pause_after_ms": pause_after_ms
        })

        # Print live in console
        color = "\033[93m" if speaker_id == "joe_rogan" else "\033[96m"
        reset = "\033[0m"
        tag = " [INTERRUPTING]" if interrupt else ""
        print(f"\n{color}[Turn {turn_idx+1}/10] {speaker_meta['name']}{tag}:{reset}")
        print(f'"{speech_text}"')
        
        time.sleep(0.3)

    print("\n" + "=" * 68)

    output_file = "episode.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(transcript, f, indent=2)

    print(f"\n[3/3] Success! Upgraded episode saved to '{output_file}'.")
    print("Each turn now includes F5-TTS normalization + Colab audio mixing cues (speed, interrupt, pauses).")

if __name__ == "__main__":
    import sys
    topic_input = "Jensen Huang's Nvidia comeback"
    if len(sys.argv) > 1:
        topic_input = " ".join(sys.argv[1:])
    else:
        user_choice = input(f"Enter topic (Default: '{topic_input}'): ").strip()
        if user_choice:
            topic_input = user_choice

    generate_podcast_script(topic=topic_input, turns=10)
