"""Streamlit UI for Contract Analysis and Risk Assessment.

Run with: streamlit run src/app.py

This provides a file uploader, extraction using `core.extractor`, an analysis button
that calls the LLM through `core.intelligence`, and shows results with download options.
"""
import json
import io
import streamlit as st
try:
	# Auto-load .env so the Streamlit process picks up openai_key if present
	from dotenv import load_dotenv
	load_dotenv()
except Exception:
	# python-dotenv is optional but recommended; if missing, user must export env vars manually
	pass

from core import extractor
from core import intelligence

from fpdf import FPDF


st.set_page_config(page_title="Contract Analysis — Risk Assessment", layout="wide")

st.title("Contract Analysis & Risk Assessment")

with st.sidebar:
	st.header("Settings")
	model = st.selectbox("LLM model", ["gpt-4o-mini", "gpt-5-nano"], index=0)
	translate_hindi = st.checkbox("Enable Hindi → English normalization (best-effort)", value=False)
	add_system_prompt = st.text_area("Additional system prompt (optional)", value="", height=120)

	# Diagnostic: show whether an OpenAI API key is available in the process (no secrets printed)
	import os as _os
	_key_present = bool(_os.getenv("OPENAI_API_KEY") or _os.getenv("openai_key"))
	if _key_present:
		st.success("OpenAI key found in environment")
	else:
		st.warning("OpenAI key not found — set OPENAI_API_KEY or openai_key (or add to .env)")

uploaded = st.file_uploader("Upload contract (PDF / DOCX / TXT)", type=["pdf", "docx", "doc", "txt"], accept_multiple_files=False)

if uploaded is not None:
	st.info(f"Received {uploaded.name} — extracting text...")
	bytes_data = uploaded.read()
	try:
		text = extractor.extract_text_from_bytes(bytes_data, filename=uploaded.name, translate_hindi=translate_hindi)
	except Exception as e:
		st.error(f"Failed to extract text: {e}")
		st.stop()

	if not text or len(text.strip()) == 0:
		st.warning("No text could be extracted from the document.")
	else:
		st.success("Text extracted — ready for analysis")

		with st.expander("Preview extracted text (first 5k chars)"):
			st.write(text[:5000])

		run = st.button("Run analysis")
		if run:
			with st.spinner("Analyzing with LLM — this may take a moment..."):
				system_prompts = []
				if add_system_prompt.strip():
					system_prompts.append(add_system_prompt.strip())

				result = intelligence.analyze_contract(text, system_prompts=system_prompts, model=model)

			st.subheader("Summary & Risk")
			# show contract-level risk metric
			st.metric("Contract-level risk", result.get("composite_risk_bucket"), delta=f"Score {result.get('composite_risk_score')}")

			# Render extracted fields in a human-friendly way (no raw JSON printed)
			def _render_parsed(parsed: dict) -> None:
				"""Render parsed dict as readable sections with bullets and expanders for long text."""
				if not parsed:
					st.info("No parsed fields available.")
					return
				# If LLM returned an unparsed raw string, don't print the raw JSON
				if isinstance(parsed, dict) and parsed.get("raw") and len(parsed.keys()) == 1:
					st.warning("The LLM response couldn't be parsed as JSON. The raw output is included in the PDF.")
					return

				for key, val in parsed.items():
					label = key.replace("_", " ").title()
					st.markdown(f"**{label}**")
					# simple primitives
					if val is None:
						st.write("—")
					elif isinstance(val, (str, int, float, bool)):
						# truncate long strings with expander
						if isinstance(val, str) and len(val) > 1000:
							st.write(val[:500] + "...")
							with st.expander(f"Show full {label}"):
								st.write(val)
						else:
							st.write(str(val))
					# lists
					elif isinstance(val, list):
						if len(val) == 0:
							st.write("(none)")
						for item in val:
							if isinstance(item, dict):
								# common clause object
								if item.get("title") or item.get("text"):
									title = item.get("title") or "(untitled)"
									st.markdown(f"- **{title}**")
									text = item.get("text") or ""
									if len(text) > 300:
										with st.expander(f"Show clause: {title}"):
											st.write(text)
									else:
										st.write(text)
							else:
								st.markdown(f"- {item}")
					# nested dicts
					elif isinstance(val, dict):
						for k2, v2 in val.items():
							st.markdown(f"- **{k2}**: {v2}")
					else:
						st.write(str(val))

			parsed = result.get("parsed")
			st.subheader("Extracted fields")
			# Show only the extracted fields in a human-friendly layout; no PDF preview or download
			_render_parsed(parsed)

		st.info("You can add an extra system prompt from the sidebar to bias the LLM (e.g., focus on IP clauses or penalties).")

else:
	st.info("Upload a contract file to begin. Supported: PDF (text-based), DOCX, TXT.")
