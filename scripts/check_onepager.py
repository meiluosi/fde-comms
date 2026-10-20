#!/usr/bin/env python3
"""高管一页汇报 / 坏消息稿规则检查：指标不超过三个且带口径，请求具体，风险唯一。不验证数字真假。"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commslib import ERROR, PLACEHOLDER, WARN, col, cell, parse_table_rows, report, strip_md, unfilled  # noqa: E402

TECH = re.compile(r'RAG|向量库|提示词|切片|召回率|模型选型|微调|token|Embedding|embedding')
TIME = re.compile(r'\d+\s*[月日号周天]|[月日周]前|期限|截止|本周|下周|本月|下月|【日期】|X\s*日')
PERSON = re.compile(r'负责人|部门|经理|总监|老板|CEO|CTO|CFO|IT|姓名|岗位|指定|【.*】')


def _line_after(text, label):
    m = re.search(rf'\*\*{label}[^*]*\*\*[^:：\n]*[:：]?\s*(.*)', text)
    return m.group(1).strip() if m else None


def _bullets_after(text, label):
    m = re.search(rf'\*\*{label}[^*]*\*\*', text)
    if not m:
        return None
    out = []
    for ln in text[m.end():].splitlines()[1:]:
        s = ln.strip()
        if s.startswith('**') or s.startswith('#') or (not s and out):
            break
        if s.startswith(('-', '*', '•')) or re.match(r'\d+[.、]', s):
            out.append(s)
    return out


def check_onepager(text, final=False):
    f = []
    body = re.split(r'^\*\*附件|^#+\s*附件', text, flags=re.M)[0]
    concl = _line_after(text, '结论')
    if concl is None or unfilled(concl) and not concl:
        f.append((ERROR, 'O01', '缺少“结论”一行'))
    elif len(concl) > 120:
        f.append((WARN, 'O01', '结论超过 120 字，应一句话'))

    tbl = None
    for header, rows in parse_table_rows(text.splitlines()):
        if col(header, '指标') is not None and col(header, '当前值') is not None:
            tbl = (header, rows)
            break
    if tbl is None:
        f.append((ERROR, 'O02', '缺少指标表（需含“指标”“当前值”列）'))
    else:
        header, rows = tbl
        if not rows:
            f.append((ERROR, 'O02', '指标表没有任何指标'))
        if len(rows) > 3:
            f.append((ERROR, 'O02', f'指标 {len(rows)} 个，超过三个；其余放附件'))
        ci, di, pi = col(header, '口径'), col(header, '测量日期'), col(header, '置信度')
        for n, row in enumerate(rows, 1):
            name, cur = strip_md(cell(row, 0)), cell(row, col(header, '当前值'))
            pending = '待测' in cur
            req = [('口径', ci)] + ([] if pending else [('测量日期', di), ('置信度', pi)])
            for label, idx in req:
                v = cell(row, idx)
                if idx is None or strip_md(v) in ('', '-', '—'):
                    f.append((ERROR, 'O03', f'指标 {n}“{name}”缺少{label}'))
                elif PLACEHOLDER.search(v) and not (pending and label == '口径'):
                    f.append((ERROR if final else WARN, 'O04', f'指标 {n}“{name}”的{label}仍是占位'))
            if not pending and re.search(r'\d', cur) is None:
                f.append((WARN, 'O03', f'指标 {n}“{name}”当前值没有数字，也不是“待测”'))

    risk = _line_after(text, '最大风险')
    if risk is None:
        f.append((ERROR, 'O05', '缺少“最大风险”'))
    else:
        rb = _bullets_after(text, '最大风险')
        if rb and len(rb) > 1:
            f.append((WARN, 'O06', f'风险列了 {len(rb)} 条，应只写最大的一个'))

    ask = _bullets_after(text, '请您做什么')
    if not ask:
        f.append((ERROR, 'O07', '缺少“请您做什么”，或其下没有具体事项'))
    else:
        for n, b in enumerate(ask, 1):
            if not TIME.search(b):
                f.append((WARN, 'O08', f'请求 {n} 没有期限'))
            if b.count('｜') < 2 and not PERSON.search(b):
                f.append((WARN, 'O09', f'请求 {n} 没有具体到人或岗位'))
    if not re.search(r'供知悉|请决策', text):
        f.append((WARN, 'O10', '缺少“类型：供知悉 / 请决策”'))
    if len(re.sub(r'\s', '', body)) > 1500:
        f.append((WARN, 'O11', '正文超过约 1500 字，超出一页'))
    m = TECH.search(body)
    if m:
        f.append((WARN, 'O12', f'正文含技术细节“{m.group(0)}”，高管汇报应放附件'))
    ph = len(PLACEHOLDER.findall(text))
    if ph:
        f.append((ERROR if final else WARN, 'O13', f'仍有 {ph} 处占位（【】、待填、待确认等）'))
    return f


def check_badnews(text, final=False):
    f = []
    items = [('发生了什么', 'B01'), ('影响是什么', 'B02'), ('我们打算怎么办', 'B03'), ('需要您做什么', 'B04')]
    for label, rid in items:
        line = re.search(rf'^\s*(?:\d+[.、]\s*)?\**{label}.*$', text, re.M) or re.search(rf'^.*{label}.*$', text, re.M)
        if not line:
            f.append((ERROR, rid, f'缺少“{label}”'))
            continue
        rest = line.group(0)[line.group(0).find(label) + len(label):]
        m = re.search(r'[:：]\s*(.*)', rest)
        if not m or not m.group(1).strip():
            f.append((ERROR, rid, f'“{label}”内容为空'))
    for label, rid in (('已核实', 'B05'), ('仍未知', 'B05'), ('下次更新', 'B06')):
        if label not in text:
            f.append((ERROR, rid, f'缺少“{label}”（坏消息稿必须写明已核实、仍未知、下次更新时间）'))
    impact = re.search(r'影响是什么[^\n]*', text)
    if impact and not re.search(r'\d|未知', impact.group(0)):
        f.append((WARN, 'B07', '“影响”既没有量化数字，也没有写“未知”'))
    if '预沟通' not in text:
        f.append((WARN, 'B08', '缺少“预沟通”状态'))
    if re.search(r'应该是|可能是|估计|大概率', text) and '未知' not in text:
        f.append((WARN, 'B09', '出现推测用语，请确认已区分“已核实”和“未知”'))
    ph = len(PLACEHOLDER.findall(text)) + len(re.findall(r'\[[^\]\n]{2,}\]', text))
    if ph:
        f.append((ERROR if final else WARN, 'B10', f'仍有 {ph} 处占位'))
    return f


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('file')
    ap.add_argument('--kind', choices=['onepager', 'bad-news'], default='onepager')
    ap.add_argument('--final', action='store_true', help='定稿模式：占位视为错误')
    ap.add_argument('--strict', action='store_true')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    text = Path(a.file).read_text(encoding='utf-8')
    fn = check_onepager if a.kind == 'onepager' else check_badnews
    return report(fn(text, a.final), a.json, a.strict)


if __name__ == '__main__':
    sys.exit(main())
