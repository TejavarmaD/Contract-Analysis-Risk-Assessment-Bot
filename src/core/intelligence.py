"""High-level orchestration for contract analysis.

Uses `llm.extract_contract_fields` to get structured fields, then applies light heuristics
to generate clause-level highlights and a composite risk score. Keep this module small —
the heavy lifting is done by the LLM.
"""
import json
from typing import Dict, Any, List

from . import llm


RISK_KEYWORDS = {
	"high": ["penalty", "indemnity", "unilateral", "terminate without", "liquidated damages"],
	"medium": ["auto-renew", "renewal", "notice period", "arbitration", "governing law"],
	"low": ["confidential", "nda", "non-disclosure"]
}


def _keyword_risk_score(text: str) -> int:
	"""Simple heuristic: count occurrences of risk keywords and map to score 0-100."""
	t = text.lower()
	score = 0
	for level, words in RISK_KEYWORDS.items():
		for w in words:
			if w in t:
				if level == "high":
					score += 30
				elif level == "medium":
					score += 15
				else:
					score += 5
	return min(100, score)


def _map_score_to_bucket(score: int) -> str:
	if score >= 60:
		return "High"
	if score >= 30:
		return "Medium"
	return "Low"


def analyze_contract(text: str, system_prompts: List[str] = None, model: str = "gpt-4o-mini") -> Dict[str, Any]:
	"""Main entry: return parsed fields (from LLM) plus heuristic risk summary.

	Returns a dict with keys: l;lm_json (raw assistant content), parsed (json if parseable), composite_risk,
	clause_highlights (list).
	"""
	assistant_content = llm.extract_contract_fields(text, system_prompts=system_prompts or [], model=model)

	def _extract_json_from_text(s: str):
		"""Try to locate and parse a JSON object inside a larger string.

		This handles common cases where the model added surrounding commentary or
		fenced code blocks. Returns a dict on success or None.
		"""
		import re

		if not s or not isinstance(s, str):
			return None

		# strip common markdown code fences
		s_clean = re.sub(r"```(?:json)?\n", "", s, flags=re.IGNORECASE)
		s_clean = s_clean.replace("```", "")

		# find the first balanced JSON object by scanning for braces
		start_idxs = [m.start() for m in re.finditer(r"\{", s_clean)]
		for start in start_idxs:
			depth = 0
			for i in range(start, len(s_clean)):
				if s_clean[i] == "{":
					depth += 1
				elif s_clean[i] == "}":
					depth -= 1
					if depth == 0:
						candidate = s_clean[start : i + 1]
						try:
							return json.loads(candidate)
						except Exception:
							break
		return None

	parsed = None
	try:
		parsed = json.loads(assistant_content)
	except Exception:
		# try to salvage a JSON object embedded in the assistant output
		salvaged = _extract_json_from_text(assistant_content)
		if salvaged is not None:
			parsed = salvaged
		else:
			# keep raw assistant content in 'raw' when parsing fails
			parsed = {"raw": assistant_content}

	# simple heuristics for clause highlights: if clauses present in parsed, compute risk per clause
	clause_highlights = []
	if isinstance(parsed, dict) and parsed.get("clauses"):
		for c in parsed.get("clauses", []):
			title = c.get("title") if isinstance(c, dict) else None
			body = c.get("text") if isinstance(c, dict) else (c if isinstance(c, str) else "")
			s = _keyword_risk_score(body)
			clause_highlights.append({"title": title, "text": body, "score": s, "bucket": _map_score_to_bucket(s)})
	else:
		# fallback: run heuristic on whole text
		s = _keyword_risk_score(text)
		clause_highlights.append({"title": None, "text": text[:1000], "score": s, "bucket": _map_score_to_bucket(s)})

	# composite contract risk: average of clause scores
	avg_score = int(sum(c["score"] for c in clause_highlights) / max(1, len(clause_highlights)))
	composite = _map_score_to_bucket(avg_score)

	return {
		"assistant_content": assistant_content,
		"parsed": parsed,
		"clause_highlights": clause_highlights,
		"composite_risk_score": avg_score,
		"composite_risk_bucket": composite,
	}


__all__ = ["analyze_contract"]

