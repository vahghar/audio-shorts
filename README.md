# AI Podcast Generator: Joe Rogan & Nikhil Kamath

A lightweight, zero-model architecture that creates dynamic debates between **Joe Rogan** and **Nikhil Kamath** grounded in real-time news.

---

## 🏗️ Architecture

```
[Local PC (0 MB Models)]
Topic Input -> DuckDuckGo Search (live news) -> Groq Llama-3.3-70B -> episode.json

[Google Colab (Free T4 GPU)]
episode.json -> Kokoro-82M Voice Synthesis -> pydub Stitching -> final_podcast.mp3
```

---

## Step 1: Generate Script on Your PC (Takes ~5 seconds)

1. Make sure you have your free Groq API key (from [console.groq.com](https://console.groq.com/keys)).
2. Run the script:
   ```powershell
   py generate_script.py
   ```
3. Type any topic (e.g., `Nvidia stock hitting all-time high`, `Elon Musk Mars colonization`, `India becoming a $10T economy`).
4. Watch the 10-turn dialogue stream live in your terminal.
5. It saves the dialogue to `episode.json`.

---

## Step 2: Render Audio on Google Colab (0 MB on your Laptop)

1. Go to [colab.research.google.com](https://colab.research.google.com).
2. Click **Upload** and upload `voice_studio.ipynb`.
3. Select **Runtime -> Run all**.
4. When prompted in Step 2, upload your `episode.json`.
5. Colab will synthesize the voices using **Kokoro-82M**, stitch them with natural 300ms pauses, and automatically download `final_podcast.mp3` to your computer.
