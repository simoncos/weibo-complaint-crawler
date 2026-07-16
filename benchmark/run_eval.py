"""Evaluate an LLM as the platform adjudicator (direction A).

For each benchmark instance, Claude is shown the reported post and the
reporters' statements — the same materials the platform saw — and must return
a structured adjudication (verdict, cited rule articles, penalties). Agreement
with the platform's real decision is then scored.

Requires: pip install anthropic pydantic
Auth: ANTHROPIC_API_KEY env var (or `ant auth login`).

Usage:
    python -m benchmark.run_eval benchmark/instances.jsonl \
        --out results.jsonl --limit 50 [--rules rules.md]
"""

import argparse
import json
from typing import List, Literal, Optional

import anthropic
from pydantic import BaseModel

MODEL = 'claude-opus-4-8'

SYSTEM_PROMPT = """\
你是微博社区管理中心的官方裁决员，负责裁决「不实信息」类举报案件。

你会看到：被举报微博的内容与发布者概况、若干举报人的举报陈述。请依据《微博举报投诉操作细则》\
作出裁决，输出：
- verdict：被举报言论是否构成「发布不实信息」（upheld=构成 / rejected=不构成 / undetermined=暂无法判定）
- cited_articles：你引用的细则条款号列表（如第19条 -> [19]）
- penalties：对被举报人的处理决定列表；credit_deduction 的 magnitude 为扣除的信用积分分数，\
mute / follow_ban 的 magnitude 为天数（永久禁言为 null），delete_post / account_closure 的 magnitude 为 null

请像真实平台裁决一样保持克制与一致：证据不足时选择 undetermined，处理力度与情节严重程度相称。
"""


class Penalty(BaseModel):
    type: Literal['credit_deduction', 'mute', 'follow_ban',
                  'delete_post', 'account_closure']
    magnitude: Optional[int]


class Adjudication(BaseModel):
    verdict: Literal['upheld', 'rejected', 'undetermined']
    cited_articles: List[int]
    penalties: List[Penalty]
    reasoning_summary: str


def render_case(instance):
    inp = instance['input']
    lines = ['## 被举报微博', inp['reported_post'], '',
             f"发布时间：{inp.get('post_time') or '未知'}",
             f"发布者：{inp['reported_user']['alias']}"
             f"（{inp['reported_user'].get('location') or '地区未知'}；"
             f"简介：{inp['reported_user'].get('description') or '无'}）", '',
             f"## 举报陈述（共 {inp.get('reporter_count') or len(inp['reports'])} 人举报）"]
    for i, r in enumerate(inp['reports'], 1):
        lines.append(f"{i}. [{r['reporter_alias']}，账号类型:{r['reporter_type']}，"
                     f"{r.get('report_time') or '时间未知'}] {r['statement']}")
    if not inp['reports']:
        lines.append('（无举报陈述文本）')
    return '\n'.join(lines)


def adjudicate(client, instance, system_blocks):
    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        thinking={'type': 'adaptive'},
        system=system_blocks,
        messages=[{'role': 'user', 'content': render_case(instance)}],
        output_format=Adjudication,
    )
    if response.stop_reason == 'refusal':
        return None
    return response.parsed_output


def score(gold, pred):
    gold_articles, pred_articles = set(gold['cited_articles']), set(pred.cited_articles)
    gold_ptypes = {p['type'] for p in gold['penalties']}
    pred_ptypes = {p.type for p in pred.penalties}

    def jaccard(a, b):
        return len(a & b) / len(a | b) if (a | b) else 1.0

    gold_credit = next((p['magnitude'] for p in gold['penalties']
                        if p['type'] == 'credit_deduction'), None)
    pred_credit = next((p.magnitude for p in pred.penalties
                        if p.type == 'credit_deduction'), None)
    return {
        'verdict_match': pred.verdict == gold['verdict'],
        'articles_exact': pred_articles == gold_articles,
        'articles_jaccard': jaccard(pred_articles, gold_articles),
        'penalty_types_jaccard': jaccard(pred_ptypes, gold_ptypes),
        'credit_gold': gold_credit,
        'credit_pred': pred_credit,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('benchmark', help='instances.jsonl from build_benchmark')
    parser.add_argument('--out', default='eval_results.jsonl')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--rules', help='optional file with the full 细则 text '
                                        'to prepend (policy-as-prompt condition)')
    args = parser.parse_args(argv)

    # Stable prefix first (cacheable), so repeated runs hit the prompt cache.
    system_blocks = [{'type': 'text', 'text': SYSTEM_PROMPT}]
    if args.rules:
        with open(args.rules, encoding='utf-8') as f:
            system_blocks.append({'type': 'text', 'text': '《微博举报投诉操作细则》全文：\n' + f.read()})
    system_blocks[-1]['cache_control'] = {'type': 'ephemeral'}

    client = anthropic.Anthropic()
    totals, n, refused = {}, 0, 0
    with open(args.benchmark, encoding='utf-8') as fin, \
         open(args.out, 'w', encoding='utf-8') as fout:
        for line in fin:
            if args.limit and n + refused >= args.limit:
                break
            instance = json.loads(line)
            try:
                pred = adjudicate(client, instance, system_blocks)
            except anthropic.APIStatusError as e:
                print(f"[{instance['case_id']}] API error {e.status_code}: {e.message}")
                continue
            if pred is None:
                refused += 1
                continue
            result = score(instance['gold'], pred)
            n += 1
            for key, value in result.items():
                if isinstance(value, (bool, int, float)) and not key.startswith('credit'):
                    totals[key] = totals.get(key, 0) + float(value)
            fout.write(json.dumps({
                'case_id': instance['case_id'],
                'gold': instance['gold'],
                'pred': pred.model_dump(),
                'score': result,
            }, ensure_ascii=False) + '\n')
            print(f"[{n}] {instance['case_id']} verdict_match={result['verdict_match']}")

    if n:
        print('\n=== Aggregate ===')
        print(f'cases scored: {n}, refused: {refused}')
        for key, value in totals.items():
            print(f'{key}: {value / n:.3f}')


if __name__ == '__main__':
    main()
