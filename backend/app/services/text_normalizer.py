"""
Text Normalizer (Pre-LLM): clean raw OCR text for better parsing and lower token usage.
"""
import re
from typing import List

COMMON_OCR_FIXES = [
	("\u2013", "-"),  # en dash to hyphen
	("\u2014", "-"),  # em dash to hyphen
	("\u00a0", " "),  # non-breaking space
]

CHAR_CONFUSIONS = [
	("0", "O", re.compile(r"(?i)\b0([A-Z])\b")),  # context-aware could be added later
]


def _basic_cleanup(text: str) -> str:
	# Normalize line endings
	text = text.replace("\r\n", "\n").replace("\r", "\n")
	# Replace common unicode variants
	for src, tgt in COMMON_OCR_FIXES:
		text = text.replace(src, tgt)
	# Collapse excessive whitespace
	text = re.sub(r"[ \t]+", " ", text)
	# Trim spaces around newlines
	text = re.sub(r" *\n *", "\n", text)
	# Remove multiple blank lines
	text = re.sub(r"\n{3,}", "\n\n", text)
	return text.strip()


def _fix_common_ocr_confusions(text: str) -> str:
	# Conservative replacements only where safe; more rules can be added per dataset
	# Example: do not blanket-replace '0' with 'O'
	return text


def normalize_text(raw_text: str) -> str:
	"""Apply a series of cleaning steps to OCR text."""
	if not raw_text:
		return ""
	text = _basic_cleanup(raw_text)
	text = _fix_common_ocr_confusions(text)
	return text
