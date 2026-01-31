
# Contract-Analysis-Risk-Assessment-Bot

This repository implements a lightweight contract analysis and risk assessment prototype with a Streamlit UI. The goal is to provide a practical, extensible pipeline that:

- Accepts PDFs (text-based), DOCX and TXT contract files.
- Extracts text reliably using open-source tools (PyMuPDF for PDFs, python-docx for DOCX).
- Optionally normalizes Hindi contracts to English for downstream NLP.
- Sends the cleaned text to an LLM (OpenAI) using structured prompts and multiple system messages for focused extraction.
- Performs light heuristic risk scoring and clause highlighting locally to complement the LLM output.
- Provides user-facing outputs: simplified summary, clause-by-clause highlights, unfavorable clause flags, downloadable JSON and PDF reports.

Why this design?

- Streamlit UI: fast to build and easy for legal users to run locally or on simple cloud instances. A single command (streamlit run) launches an interactive interface.
- PyMuPDF & python-docx: these libraries are mature, fast, and work well for real-world documents. PyMuPDF is especially efficient for large PDFs.
- LLM for structured extraction: the most reliable way to extract nuanced legal fields (obligations, indemnities, governing law) is to ask a strong LLM with clear instructions and ask for strict JSON output. To improve precision we support multiple system prompts so SMEs or legal teams can bias the model toward specific fields (e.g., IP, penalties, auto-renewal).
- Local heuristics + LLM: heuristics (keyword-based) provide an explainable, fast safety net for flagging obvious risk indicators while the LLM handles the semantic extraction.
- Hindi support (best-effort): translation is optional and done pre-NLP to reuse the same English prompts and LLM behavior. This keeps the pipeline simpler and reduces prompt complexity.

Files added/changed

- `src/app.py` — Streamlit app (file upload, extraction, LLM analysis, downloads)
- `src/core/extractor.py` — PDF / DOCX / TXT extraction with optional Hindi→English normalization
- `src/core/llm.py` — OpenAI Chat wrapper and structured extraction prompt
- `src/core/intelligence.py` — Orchestration + light risk heuristics and clause highlighting
- `requirements.txt` — Python dependencies for quick setup
 - `src/core/prompts.py` — HTML-formatted system prompts and presets

Model and prompts notes

- Default model: `gpt-4o-mini` is used for both translation (if enabled) and structured extraction by default. You can override the model from the UI sidebar.
- System prompts: `src/core/prompts.py` contains HTML-formatted, detailed system prompts (general extractor, IP focus, penalties focus, plain-English summary). The app will use these by default when no custom prompt is provided; you can pass additional system prompts from the UI to bias the extraction.

How to run (local)

1. Create and activate a Python environment (Python 3.9+ recommended).
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Set your OpenAI API key in the environment (Windows PowerShell):

```powershell
$env:OPENAI_API_KEY = 'sk-...'
```

4. Launch the Streamlit UI:

```powershell
streamlit run src/app.py
```

Notes and next steps

- Validation & tests: This is a prototype. Adding unit tests for extraction and small integration tests against a static LLM mock will increase reliability.
- Clause segmentation: current clause extraction relies on the LLM returning a `clauses` list. For higher accuracy add a local clause-splitting preprocessor (regexes or layout analysis) before LLM calls.
- Security & PII: Do not send secret or sensitive documents to any third-party LLMs without legal review. For production, consider on-prem or private LLM deployments and encryption-at-rest and in-transit.

If you want, I can:

- Add a small test suite and a sample contract to demonstrate the pipeline.
- Wire this up to an internal LLM (if you have one) or add batching for large contract sets.
