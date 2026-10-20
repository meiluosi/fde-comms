"""fde-comms 规则检查的共用小工具。只检查结构与规则，不验证内容真假。"""
import json
import re
import sys

ERROR, WARN = 'ERROR', 'WARN'
PLACEHOLDER = re.compile(r'【[^】]*】|待填|待定|待确认|待补')


def parse_table_rows(lines):
    """返回 [(header_cells, [row_cells, ...]), ...]，识别连续以 | 开头的行。"""
    tables, cur = [], []
    for line in list(lines) + ['']:
        if line.strip().startswith('|'):
            cur.append(line.strip())
        elif cur:
            cells = [[c.strip() for c in r.strip('|').split('|')] for r in cur]
            body = [c for c in cells if not all(re.fullmatch(r':?-{2,}:?', x or '-') or not x for x in c)]
            if body:
                tables.append((body[0], body[1:]))
            cur = []
    return tables


def col(header, name):
    for i, h in enumerate(header):
        if name in h:
            return i
    return None


def cell(row, i):
    return row[i].strip() if i is not None and i < len(row) else ''


def strip_md(s):
    return re.sub(r'[*`_]', '', s).strip()


def unfilled(s):
    s = strip_md(s)
    return s in ('', '-', '—', '无') or bool(PLACEHOLDER.search(s))


def section(text, title_pat):
    """取标题含 title_pat 的段落（到下一个同级或更高级标题）。"""
    lines = text.splitlines()
    out, level = [], None
    for ln in lines:
        m = re.match(r'^(#+)\s*(.*)', ln)
        if level is None:
            if m and re.search(title_pat, m.group(2)):
                level = len(m.group(1))
            continue
        if m and len(m.group(1)) <= level:
            break
        out.append(ln)
    return None if level is None else '\n'.join(out)


def report(findings, as_json=False, strict=False, out=sys.stdout):
    errs = [f for f in findings if f[0] == ERROR]
    warns = [f for f in findings if f[0] == WARN]
    if as_json:
        out.write(json.dumps([{'level': l, 'rule': r, 'msg': m} for l, r, m in findings], ensure_ascii=False, indent=1) + '\n')
    else:
        for l, r, m in findings:
            out.write(f'[{l}] {r}: {m}\n')
        out.write(f'共 {len(errs)} 个错误，{len(warns)} 个警告\n')
    return 1 if errs or (strict and warns) else 0
