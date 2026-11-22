"""Narrow routing: explanatory legal questions must remain normal chat."""
import re

DEFAULT_PROMPT = ('Prepare the CUAD red-flag due diligence demo in ~/DealRoom '
                  'for the buyer, closing on 31 March 2027. Review all 20 contracts '
                  'with exact quotations, page references, risks and calculated deadlines. '
                  'Mark missing clauses NOT FOUND - human review. Preview before saving.')


def matches(text: str) -> bool:
    low = text.strip().casefold()
    if low in ('/dealreview', 'dealreview', 'deal review demo', 'cuad demo'):
        return True
    if re.match(r'^(what|how|why|when|explain)\b', low):
        return False
    action = re.search(r'\b(prepare|generate|review|run|create|make|start|open|banao|bna)\b', low)
    topic = re.search(r'\b(due[ -]diligence|red[ -]flag|contract review|deal review|cuad)\b', low)
    scope = re.search(r'\b(cuad|dealroom|demo)\b|\b20\s+(?:commercial\s+)?contracts\b', low)
    return bool(action and topic and scope)


def validate(text: str) -> None:
    if not matches(text):
        raise ValueError('Use the CUAD demo prompt, or /dealreview. This reviewed demo covers 20 public contracts.')
    dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b|\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b', text)
    for value in dates:
        if value.casefold() not in ('2027-03-31', '31 march 2027', '31 mar 2027', '31/03/2027', '03/31/2027'):
            raise ValueError('This reviewed demo uses closing 31 March 2027. Other closing dates need a new review.')
