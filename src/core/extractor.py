"""Document extraction utilities.

Provides functions to extract text from PDF/DOCX/TXT bytes using PyMuPDF and python-docx.
Includes optional Hindi->English translation using googletrans if available.
"""
from typing import Optional
import io
import re

try:
	import fitz  # PyMuPDF
except Exception:
	fitz = None

try:
	import docx
except Exception:
	docx = None

import os




def _extract_text_from_pdf_bytes(data: bytes) -> str:
	import logging
	logger = logging.getLogger(__name__)
	if fitz is None:
		raise ImportError("PyMuPDF (fitz) is required for PDF extraction. Install pymupdf.")
	text_chunks = []
	logger.info("Starting PDF text extraction (bytes=%d)", len(data))
	with fitz.open(stream=data, filetype="pdf") as doc:
		for page in doc:
			text_chunks.append(page.get_text("text"))
	logger.info("Finished PDF extraction: pages=%d", len(text_chunks))
	return "\n".join(text_chunks)


def _extract_text_from_docx_bytes(data: bytes) -> str:
	import logging
	logger = logging.getLogger(__name__)
	if docx is None:
		raise ImportError("python-docx is required for DOCX extraction. Install python-docx.")
	logger.info("Starting DOCX extraction (bytes=%d)", len(data))
	bio = io.BytesIO(data)
	document = docx.Document(bio)
	paragraphs = [p.text for p in document.paragraphs]
	logger.info("Finished DOCX extraction: paragraphs=%d", len(paragraphs))
	return "\n".join(paragraphs)


def _extract_text_from_txt_bytes(data: bytes) -> str:
	import logging
	logger = logging.getLogger(__name__)
	logger.info("Starting TXT extraction (bytes=%d)", len(data))
	try:
		out = data.decode("utf-8")
	except Exception:
		out = data.decode("latin-1", errors="ignore")
	logger.info("Finished TXT extraction (chars=%d)", len(out))
	return out


def normalize_whitespace(text: str) -> str:
	return re.sub(r"\s+", " ", text).strip()


def maybe_translate_hindi_to_english(text: str, enable: bool = False) -> str:
	"""If enabled, attempt to translate Hindi (or related languages) -> English using OpenAI.

	Best-effort: on any failure, return original text.
	"""
	if not enable:
		return text

	try:
		# lazy import to avoid requiring openai for users who don't enable translation
		from openai import OpenAI

		key = os.getenv("OPENAI_API_KEY") or os.getenv("openai_key")
		client = OpenAI(api_key=key) if key else OpenAI()

		# ask the model only to translate; do not add commentary
		msgs = [
			{
				"role": "system",
				"content": (
					"You are a concise translator.\nRespond with only the translated text in English. "
					"Do not add commentary or notes."
				),
			},
			{"role": "user", "content": f"Translate the following text to English (detect language automatically):\n\n{text[:20000]}"},
		]

		import logging
		logger = logging.getLogger(__name__)
		logger.info("Starting translation call (chars=%d)", len(text))
		resp = client.chat.completions.create(model="gpt-4o-mini", messages=msgs)
		try:
			translated = resp.choices[0].message.content
		except Exception:
			translated = resp["choices"][0]["message"]["content"]
		logger.info("Translation received (chars=%d)", len(translated))
		return translated
	except Exception:
		return text



def extract_text_from_bytes(data: bytes, filename: Optional[str] = None, translate_hindi: bool = False) -> str:
	"""Extract text from in-memory file bytes.

	filename helps route extraction by extension. Returns cleaned text.
	"""
	text = ""
	if filename:
		lower = filename.lower()
		if lower.endswith(".pdf"):
			text = _extract_text_from_pdf_bytes(data)
		elif lower.endswith(".docx") or lower.endswith(".doc"):
			text = _extract_text_from_docx_bytes(data)
		elif lower.endswith(".txt"):
			text = _extract_text_from_txt_bytes(data)
		else:
			# fallback: try PDF then txt
			try:
				text = _extract_text_from_pdf_bytes(data)
			except Exception:
				text = _extract_text_from_txt_bytes(data)
	else:
		# best-effort: try PDF then DOCX then text
		for fn in (_extract_text_from_pdf_bytes, _extract_text_from_docx_bytes, _extract_text_from_txt_bytes):
			try:
				text = fn(data)
				if text:
					break
			except Exception:
				continue

	text = normalize_whitespace(text)
	if translate_hindi:
		text = maybe_translate_hindi_to_english(text, enable=True)
	return text


__all__ = ["extract_text_from_bytes", "normalize_whitespace"]

