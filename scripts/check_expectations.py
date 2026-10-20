#!/usr/bin/env python3
"""预期声明规则检查：有“本期不做”、验收三问齐全且兜底到岗位、变更方式明确。不验证事实。"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commslib import ERROR, PLACEHOLDER, WARN, col, cell, parse_table_rows, report, section, strip_md, unfilled  # noqa: E402

CONFIRM = ('签字', '邮件回复', '邮件', '会议纪要')
VAGUE_OWNER = re.compile(r'^(系统|AI|模型|算法|它|机器)')


def _bullets(sec):
    return [ln.strip()[1:].strip() for ln in (sec or '').splitlines() if ln.strip().startswith(('-', '*'))]


def _field(sec, label):
    m = re.search(rf'{label}[^:：\n]*[:：]\s*(.*)', sec or '')
    return None if m is None else m.group(1).strip()


def check(text, final=False):
    f = []
    head = text.splitlines()[0] if text.strip() else ''
    if not re.search(r'立项|Demo|上线前|变更|运行期', head):
        f.append((WARN, 'E01', '标题未写明阶段（立项 / Demo / 上线前 / 变更 / 运行期）'))
    m = re.search(r'确认方式[:：]\s*(.*)', text)
    if not m:
        f.append((ERROR, 'E02', '缺少“确认方式”（签字 / 邮件回复 / 会议纪要）'))
    elif not any(k in m.group(1) for k in CONFIRM):
        f.append((ERROR, 'E02', '确认方式未写明'))
    elif '/' in m.group(1) and '待选' in m.group(1):
        f.append((ERROR if final else WARN, 'E02', '确认方式仍是待选'))

    do = section(text, r'本期做什么')
    if do is None or not strip_md(do):
        f.append((ERROR, 'E03', '缺少“本期做什么”或内容为空'))
    nd = section(text, r'本期不做')
    nb = [b for b in _bullets(nd) if strip_md(b)]
    if nd is None:
        f.append((ERROR, 'E04', '缺少“本期不做什么”'))
    elif not nb:
        f.append((ERROR, 'E04', '“本期不做什么”没有任何条目'))
    elif all(unfilled(b) for b in nb):
        f.append((ERROR if final else WARN, 'E04', '“本期不做什么”条目仍是占位'))

    lim = section(text, r'已知局限')
    rows = []
    for header, r in parse_table_rows((lim or '').splitlines()):
        rows = r
        break
    if lim is None or not rows:
        f.append((ERROR, 'E05', '缺少已知局限（错误画像）表或没有任何行；没测过请写“待测”'))
    else:
        for n, row in enumerate(rows, 1):
            if len([c for c in row if c.strip()]) < 2:
                f.append((WARN, 'E05', f'局限第 {n} 行内容过少'))
            freq = cell(row, 1)
            if re.search(r'\d+\s*%|每[天周月]', freq) and '待测' not in freq and not re.search(r'来源|测|日志|抽检', ' '.join(row)):
                f.append((WARN, 'E06', f'局限第 {n} 行有频率数字但没有来源；未测请写“待测”'))

    acc = section(text, r'验收')
    if acc is None:
        f.append((ERROR, 'E07', '缺少“验收”'))
    else:
        for label in ('合格标准', '绝对不能接受', '谁兜底'):
            v = _field(acc, label)
            if v is None:
                f.append((ERROR, 'E07', f'验收缺少“{label}”'))
            elif strip_md(v) == '':
                f.append((ERROR, 'E07', f'验收“{label}”为空'))
            elif PLACEHOLDER.search(v):
                f.append((ERROR if final else WARN, 'E08', f'验收“{label}”仍是占位'))
        owner = _field(acc, '谁兜底')
        if owner and VAGUE_OWNER.match(strip_md(owner)):
            f.append((ERROR, 'E09', '兜底不能是系统/AI，应具体到岗位'))
        std = _field(acc, '合格标准')
        if std and re.search(r'\d+\s*%', std) and not re.search(r'客户(已)?确认|待客户确认|由客户|业务方', std):
            f.append((WARN, 'E10', '合格标准含百分比，但没有写明由客户确认'))

    chg = section(text, r'变更方式')
    if chg is None or not strip_md(chg):
        f.append((ERROR, 'E11', '缺少“变更方式”或内容为空'))
    if re.search(r'做不到|无法实现', text) and not re.search(r'风险|替代|代价', text):
        f.append((WARN, 'E12', '出现“做不到”，却没有风险、代价和替代方案'))
    ph = len(PLACEHOLDER.findall(text))
    if ph:
        f.append((ERROR if final else WARN, 'E13', f'仍有 {ph} 处占位'))
    return f


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('file')
    ap.add_argument('--final', action='store_true')
    ap.add_argument('--strict', action='store_true')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    return report(check(Path(a.file).read_text(encoding='utf-8'), a.final), a.json, a.strict)


if __name__ == '__main__':
    sys.exit(main())
