# agent/memory/extractor.py

import json
from agent.llm import llm


EXTRACT_PROMPT = """
You are extracting structured data from a document.

Document text:
\"\"\"
{content}
\"\"\"

Extract the following fields if present:
- vendor
- invoice_number
- amount
- due_date
- po_number

Rules:
- Return ONLY valid JSON. No markdown. No explanation.
- If a field is missing, use null.
- For amount, return a number (not a string).
- For dates, return them in ISO format (YYYY-MM-DD) if possible.

Output format:
{{"vendor": "...", "invoice_number": "...", "amount": 0.0, "due_date": "...", "po_number": "..."}}
"""


def extract_fields(content: str) -> dict:
    prompt = EXTRACT_PROMPT.format(content=content[:4000])  # safety cap
    response = llm.invoke(prompt)
    raw = response.content.strip()

    if raw.startswith("```"):
        raw = raw.strip("`").replace("json\n", "", 1)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}