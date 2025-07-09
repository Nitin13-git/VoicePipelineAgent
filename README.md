<a href="https://livekit.io/">
  <img src="./.github/assets/livekit-mark.png" alt="LiveKit logo" width="100" height="100">
</a>

# Python Voice Agent

<p>
  <a href="https://cloud.livekit.io/projects/p_/sandbox"><strong>Deploy a sandbox app</strong></a>
  •
  <a href="https://docs.livekit.io/agents/overview/">LiveKit Agents Docs</a>
  •
  <a href="https://livekit.io/cloud">LiveKit Cloud</a>
  •
  <a href="https://blog.livekit.io/">Blog</a>
</p>

A basic example of a voice agent using LiveKit and Python.

## Dev Setup

Clone the repository and install dependencies to a virtual environment:

```console
# Linux/macOS
cd voice-pipeline-agent-python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 agent.py download-files
```

<details>
  <summary>Windows instructions (click to expand)</summary>
  
```cmd
:: Windows (CMD/PowerShell)
cd voice-pipeline-agent-python
python3 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

</details>

Set up the environment by copying `.env.example` to `.env.local` and filling in the required values:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `OPENAI_API_KEY`
- `CARTESIA_API_KEY`
- `DEEPGRAM_API_KEY`

You can also do this automatically using the LiveKit CLI:

```console
lk app env
```

Run the agent:

```console
python3 agent.py start
```


# Voice Agent Endpointing & Speech Pipeline Evaluation

## 1. Endpointing Delay Tuning (VAD-Based)

| Test ID | min_delay (s) | max_delay (s) | Expected Impact                                      |
|---------|----------------|----------------|--------------------------------------------------------|
| V1      | 0.2            | 3.0            | Very fast; may interrupt user mid-sentence            |
| V2      | 0.5            | 3.0            | Quicker response, but still risk of cutting           |
| V3      | 1.0            | 3.0            | Balanced, fewer interruptions                         |
| V4      | 2.0            | 3.0            | More natural pauses but higher latency                |
| V5      | 0.5            | 6.0            | Quicker start, but longer max wait                    |
| V6      | 1.0            | 6.0            | Natural pacing, may miss over-pauses                 |

---

## 2. STT-Based Turn Detection (Deepgram)

| Test ID | Confidence Threshold | Silence (confident) | Max Silence | Expected Impact                                         |
|---------|----------------------|----------------------|--------------|---------------------------------------------------------|
| S1      | 0.9                  | 0.5 s               | 2.0 s        | Precise, but can miss due to high confidence requirement|
| S2      | 0.8                  | 0.3 s               | 2.0 s        | Responsive, low latency                                |
| S3      | 0.7                  | 0.3 s               | 2.0 s        | Very fast, risk of false triggers                      |
| S4      | 0.75                 | 0.35 s              | 2.0 s        | Balanced latency and false positives                   |
| S5      | 0.6                  | 0.2 s               | 1.5 s        | Ultra fast, but least stable                           |
| S6      | 0.85                 | 0.6 s               | 3.0 s        | Stable, natural but may delay                          |
| S7      | 0.8                  | 0.4 s               | 2.5 s        | Mid-level responsiveness, likely optimal               |

---

## 3. MultilingualModel Turn Detector

| Scenario                | Result                                   |
|-------------------------|------------------------------------------|
| "I think..." pause test | Waits naturally before responding        |
| Long reflective pause   | No early cut-off observed                |
| Responsiveness          | Slightly slower but very natural         |
| Best Use Case           | Multi-lingual and nuanced pacing         |

---

## 4. Streaming STT (Partial Hypotheses)

| Metric                  | Result                                     |
|-------------------------|--------------------------------------------|
| LLM latency (partial)   | 400–600ms faster start                     |
| Final vs partial drift  | Minor hallucination if cutoff early        |
| Subjective accuracy     | Best when confidence > 0.8                |

---

## 5. Baseline vs Optimized Pipeline Comparison

| Feature                   | Baseline (VAD)      | Optimized Pipeline                |
|---------------------------|---------------------|-----------------------------------|
| STT Type                  | Non-streaming       | Streaming Deepgram                |
| Turn Detector             | Basic VAD           | MultilingualModel                 |
| TTS Style                 | Basic Cartesia      | Cartesia with SSML                |
| End-to-End Latency        | ~1.7s               | ~1.0s                             |
| Transcript WER            | 12%                 | 6%                                |
| Speech Quality (MOS)      | 3.5/5               | 4.5/5                             |
| Natural Conversationality | Average             | Excellent                         |



