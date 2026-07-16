"""Extract per-reporter features for the "who reports rumors" analysis.

Works on the `reports` array of a complaint record (see README sample):
each reporter has profile fields (name/gender/location/description) and,
when matched, a report statement (`report_text`) with its timestamp.
"""

import re

# Institutional-account cues in profile descriptions. CMC reporter profiles for
# government/legal/media accounts almost always self-describe with one of these.
_GOV_KEYWORDS = ('官方微博', '官微', '政务', '公安', '普法', '法院', '检察',
                 '司法', '政府', '委员会', '宣传部', '网信')
_DEBUNK_KEYWORDS = ('辟谣', '谣言')
_MEDIA_KEYWORDS = ('日报', '晚报', '电视台', '广播', '新闻', '媒体', '记者')
_LEGAL_KEYWORDS = ('律师', '法律')

_RE_URL = re.compile(r'https?://\S+')
_RE_DEBUNK_TAG = re.compile(r'#微博辟谣#|#辟谣#')


def classify_reporter_type(description):
    """Coarse account-type label from the profile description."""
    d = description or ''
    if any(k in d for k in _GOV_KEYWORDS):
        return 'government'
    if any(k in d for k in _MEDIA_KEYWORDS):
        return 'media'
    if any(k in d for k in _LEGAL_KEYWORDS):
        return 'legal'
    if any(k in d for k in _DEBUNK_KEYWORDS):
        return 'debunker'
    return 'ordinary'


def strip_reporter_prefix(reporter_name, report_text):
    """report_text is scraped as '<name>：<statement>' — drop the prefix."""
    if not report_text:
        return ''
    text = report_text
    if reporter_name and text.startswith(reporter_name):
        text = text[len(reporter_name):]
    return text.lstrip('：: ').strip()


def extract_report_features(reporter):
    """Features for one entry of the `reports` array."""
    statement = strip_reporter_prefix(
        reporter.get('reporter_name'), reporter.get('report_text'))
    return {
        'reporter_name': reporter.get('reporter_name'),
        'reporter_gender': reporter.get('reporter_gender'),
        'reporter_location': (reporter.get('reporter_location') or '').strip(),
        'reporter_type': classify_reporter_type(reporter.get('reporter_description')),
        'report_time': reporter.get('report_time'),
        'statement': statement,
        'statement_length': len(statement),
        'has_evidence_url': bool(_RE_URL.search(statement)),
        'uses_debunk_hashtag': bool(_RE_DEBUNK_TAG.search(statement)),
    }


def extract_complaint_reporter_features(complaint):
    """Features for all reporters of one complaint record."""
    return [extract_report_features(r) for r in complaint.get('reports') or []]
