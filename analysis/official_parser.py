"""Parse the platform's adjudication text (`official_text`) into structured fields.

A typical adjudication looks like:

    经查，此微博称“……”不实。@德州运河公安分局 已辟谣：…… 。
    被举报人言论构成“发布不实信息”。
    现根据《微博举报投诉操作细则》（http://service.account.weibo.com/roles/xize ）第19条，
    对被举报人处理如下：扣除信用积分2分。上述处理在公布后60分钟内生效。

This module extracts: verdict, cited rule articles, penalties (type + magnitude),
debunker mentions and effectiveness delay. All parsing is regex-based and
dependency-free so it can run over the full 36k-record dump quickly.
"""

import re

# Verdict -------------------------------------------------------------------

VERDICT_UPHELD = 'upheld'          # 构成“发布不实信息”
VERDICT_UPHELD_HARMFUL = 'upheld_harmful'  # 构成“有害信息”（如地震谣言援引防震减灾法）
VERDICT_UPHELD_INFORMAL = 'upheld_informal'  # 认定不实/已辟谣，但无正式“构成”句、通常无处罚
VERDICT_REJECTED = 'rejected'      # 不构成“发布不实信息” / 举报不成立
VERDICT_UNDETERMINED = 'undetermined'  # 暂无法判定 etc.

_RE_REJECTED = re.compile(r'不构成\s*[“"『]?(?:发布)?不实信息|举报不成立|无法支持举报')
_RE_UPHELD = re.compile(r'构成\s*[“"『]?(?:发布)?不实信息')
_RE_UPHELD_HARMFUL = re.compile(r'构成\s*[“"『]?(?:发布)?(?:时政)?有害信息')
_RE_UNDETERMINED = re.compile(r'暂无法判定|无法判定|暂不处理|中止处理')
_RE_INFORMAL_FALSE = re.compile(r'经查[^。]{0,200}?不实|已(?:对此事件)?辟谣')


def parse_verdict(text):
    if not text:
        return None
    # Check rejection first: “不构成…” also matches the upheld pattern.
    if _RE_REJECTED.search(text):
        return VERDICT_REJECTED
    if _RE_UPHELD.search(text):
        return VERDICT_UPHELD
    if _RE_UPHELD_HARMFUL.search(text):
        return VERDICT_UPHELD_HARMFUL
    if _RE_UNDETERMINED.search(text):
        return VERDICT_UNDETERMINED
    # Some verdicts assert falsity ("经查…不实。@XX 已辟谣") without the formal
    # “构成” clause; they typically carry no penalty.
    if _RE_INFORMAL_FALSE.search(text):
        return VERDICT_UPHELD_INFORMAL
    return None


# Cited rule articles --------------------------------------------------------

# Platform rulebooks only (《微博举报投诉操作细则》,《新浪微博社区管理规定(试行)》,
# 《微博社区公约》…). Verdicts also cite external documents as *evidence* —
# laws, IAAF competition rules, etc. — which must not be counted.
_RE_RULES_DOC = re.compile(
    r'《([^《》]{0,26}?(?:微博|社区)[^《》]{0,26}?(?:细则|规定|公约|规则)(?:\s*[（(]试行[)）])?)》')
_RE_ARTICLE = re.compile(r'第\s*([0-9一二三四五六七八九十百]+)\s*条')
# Article numbers that follow a platform rulebook citation (URL may sit between).
_RE_DOC_ARTICLE = re.compile(_RE_RULES_DOC.pattern + r'[^《》第]{0,80}?' + _RE_ARTICLE.pattern)

_CN_DIGITS = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
              '六': 6, '七': 7, '八': 8, '九': 9}


def _cn_num_to_int(s):
    if s.isdigit():
        return int(s)
    # Handles 一..九十九 which covers all rule articles in practice.
    if s == '十':
        return 10
    if '十' in s:
        tens, _, units = s.partition('十')
        return _CN_DIGITS.get(tens, 1) * 10 + (_CN_DIGITS.get(units, 0) if units else 0)
    if '百' in s:
        hundreds, _, rest = s.partition('百')
        return _CN_DIGITS.get(hundreds, 1) * 100 + (_cn_num_to_int(rest) if rest else 0)
    return _CN_DIGITS.get(s)


def parse_cited_articles(text):
    """Return sorted unique platform-rule article numbers cited, e.g. [19].

    Only articles following a platform rulebook citation count; if the text
    cites no platform rulebook at all, fall back to any 第N条 occurrence.
    """
    if not text:
        return []
    articles = set()
    for m in _RE_DOC_ARTICLE.finditer(text):
        n = _cn_num_to_int(m.group(2))
        if n:
            articles.add(n)
    if not articles and not _RE_RULES_DOC.search(text):
        for m in _RE_ARTICLE.finditer(text):
            n = _cn_num_to_int(m.group(1))
            if n:
                articles.add(n)
    return sorted(articles)


def parse_cited_documents(text):
    """Return normalized rulebook titles cited, e.g. ['微博举报投诉操作细则'].

    Scraped titles may contain stray whitespace/newlines and mixed-width
    parentheses; both are normalized away.
    """
    if not text:
        return []
    seen = []
    for m in _RE_RULES_DOC.finditer(text):
        title = re.sub(r'\s+', '', m.group(1)).replace('（', '(').replace('）', ')')
        if title not in seen:
            seen.append(title)
    return seen


# Penalties -------------------------------------------------------------------

PENALTY_CREDIT = 'credit_deduction'   # 扣除信用积分N分
PENALTY_MUTE = 'mute'                 # 禁言N天 / 永久禁言
PENALTY_FOLLOW_BAN = 'follow_ban'     # 禁被关注N天
PENALTY_DELETE_POST = 'delete_post'   # 删除该微博 / 此微博将被删除
PENALTY_ACCOUNT_CLOSURE = 'account_closure'  # 关闭账号 / 注销账号

_PENALTY_PATTERNS = [
    (PENALTY_CREDIT, re.compile(r'扣除信用积分\s*(\d+)\s*分')),
    (PENALTY_MUTE, re.compile(r'禁言\s*(\d+)\s*[天日]')),
    (PENALTY_FOLLOW_BAN, re.compile(r'禁(?:止)?被关注\s*(\d+)\s*[天日]')),
]
_RE_PERMANENT_MUTE = re.compile(r'永久禁言')
_RE_DELETE = re.compile(r'删除(?:该|相关|此)?微博|微博将?被删除|删除相关内容')
_RE_CLOSURE = re.compile(r'(?:关闭|注销)(?:其)?(?:账号|帐号)|账号予以(?:关闭|注销)')


def parse_penalties(text):
    """Return list of {'type': ..., 'magnitude': int or None} dicts.

    magnitude is points for credit_deduction, days for mute/follow_ban
    (None means permanent for mute), None for the rest.
    """
    if not text:
        return []
    penalties = []
    for ptype, pattern in _PENALTY_PATTERNS:
        for m in pattern.finditer(text):
            penalties.append({'type': ptype, 'magnitude': int(m.group(1))})
    if _RE_PERMANENT_MUTE.search(text):
        penalties.append({'type': PENALTY_MUTE, 'magnitude': None})
    if _RE_DELETE.search(text):
        penalties.append({'type': PENALTY_DELETE_POST, 'magnitude': None})
    if _RE_CLOSURE.search(text):
        penalties.append({'type': PENALTY_ACCOUNT_CLOSURE, 'magnitude': None})
    return penalties


# Misc ------------------------------------------------------------------------

_RE_EFFECT_DELAY = re.compile(r'公布后\s*(\d+)\s*分钟内生效')
_RE_DEBUNKER = re.compile(r'@([-\w一-鿿]+)\s*已辟谣')


def parse_effect_delay_minutes(text):
    if not text:
        return None
    m = _RE_EFFECT_DELAY.search(text)
    return int(m.group(1)) if m else None


def parse_debunkers(text):
    """Accounts credited in the verdict as having debunked the rumor."""
    if not text:
        return []
    return _RE_DEBUNKER.findall(text)


def parse_official(text):
    """Parse a full official_text into one structured dict."""
    return {
        'verdict': parse_verdict(text),
        'cited_documents': parse_cited_documents(text),
        'cited_articles': parse_cited_articles(text),
        'penalties': parse_penalties(text),
        'effect_delay_minutes': parse_effect_delay_minutes(text),
        'debunkers': parse_debunkers(text),
    }
