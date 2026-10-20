#!/usr/bin/env python3
"""访谈纪要规则检查：复述句、记录类型、口径、原话、联系方式与人名。不验证内容真假。"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commslib import ERROR, WARN, col, cell, parse_table_rows, report, strip_md, unfilled  # noqa: E402

TYPES = ('对方说的', '实物', '日志', '我的推断', '推断')
SURNAMES = '王李张刘陈杨黄赵周吴徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾萧田董潘袁蔡蒋余于杜叶程魏苏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤'
ROLES = '专员|班长|主管|经理|总监|工程师|师傅|负责人|组长|助理|会计|司机'
NAME_PATTERNS = [
    re.compile(rf'[{SURNAMES}][一-龥]{{1,2}}（[^）]{{0,12}}({ROLES})[^）]{{0,6}}）'),  # 张三（理赔专员）
    re.compile(rf'({ROLES})[{SURNAMES}][一-龥]{{1,2}}?(?=[，。、：:；;（）\s]|说|认为|表示|称|提到|讲|$)'),  # 班长王五
    re.compile(rf'[小老][{SURNAMES}]'),  # 小陈、老李
]
STOP = ('周期', '周一', '周二', '周三', '周四', '周五', '周六', '周日', '周末', '高管', '高层', '高效', '高级', '高度', '方案', '方向',
        '方式', '方便', '方面', '金额', '金融', '任务', '任何', '任意', '向上', '向下', '万一', '白名单', '马上', '何时', '余额', '于是',
        '程序', '程度', '石油', '何必', '方法')
PHONE = re.compile(r'(?<!\d)1[3-9]\d{9}(?!\d)')
EMAIL = re.compile(r'[\w.+-]+@[\w-]+(\.[\w-]+)+')
CLAIM = re.compile(r'\d|[一二三四五六七八九十两]+\s*(分钟|小时|天|周|次|件|单|张|个)|%|一般|经常|总是|每次')
EVIDENCE_HINT = re.compile(r'日志|实物|记录|时间戳|系统导出|台账')
ORAL_HINT = re.compile(r'口头|访谈|他说|对方说|自述|口述')


def check(text, names=(), for_summary=False):
    f = []
    if not re.search(r'我理解您说的是|对吗', text):
        f.append((ERROR, 'N01', '缺少复述句（“我理解您说的是……对吗？”）'))
    if not re.search(r'^状态[:：]', text, re.M):
        f.append((WARN, 'N02', '缺少“状态：草稿/已发送确认/已确认”行'))

    rec = None
    for header, rows in parse_table_rows(text.splitlines()):
        if col(header, '类型') is not None and col(header, '内容') is not None:
            rec = (header, rows)
            break
    if rec is None:
        f.append((ERROR, 'N03', '缺少记录表（需含“内容”“类型”列）'))
    else:
        header, rows = rec
        ti, ci, qi, oi = col(header, '类型'), col(header, '内容'), col(header, '口径'), col(header, '原话')
        if not rows:
            f.append((ERROR, 'N03', '记录表没有任何记录'))
        for n, row in enumerate(rows, 1):
            typ = strip_md(cell(row, ti))
            content = cell(row, ci)
            if not typ.startswith(TYPES):
                f.append((ERROR, 'N04', f'记录 {n} 的类型“{typ or "空"}”不在 对方说的 / 实物或日志里有的 / 我的推断'))
                continue
            if typ.startswith('对方说的'):
                if CLAIM.search(content) and (qi is None or strip_md(cell(row, qi)) in ('', '-', '—')):
                    f.append((ERROR, 'N05', f'记录 {n}“{content[:20]}”含数字或频率说法，但口径栏为空；未知请写“未知”'))
                if oi is not None and unfilled(cell(row, oi)):
                    f.append((WARN, 'N06', f'记录 {n} 缺少原话（用户转述时可写“转述，无逐字原话”）'))
            if for_summary and re.search(r'仅限本人|汇总时删除|汇总.{0,4}删', cell(row, ti) + content):
                f.append((ERROR, 'N07', f'记录 {n} 标为仅限本人/汇总时删除，不能进入对外汇总'))

    # 台账式表格：口述命题不应记为“事实”
    for header, rows in parse_table_rows(text.splitlines()):
        si = col(header, '状态')
        if si is not None:
            for n, row in enumerate(rows, 1):
                if strip_md(cell(row, si)).startswith('事实') and ORAL_HINT.search(' '.join(row)) and not EVIDENCE_HINT.search(' '.join(row)):
                    f.append((WARN, 'N08', f'条目 {n} 来自口述却记为“事实”；命题应记“假设”，“他这样说”写进来源'))
        for row in rows:
            if row and strip_md(row[0]) == '状态':
                if any(strip_md(c).startswith('事实') for c in row[1:]) and ORAL_HINT.search(text) and not EVIDENCE_HINT.search(' '.join(row)):
                    f.append((WARN, 'N08', '状态行把口述命题记为“事实”；应记“假设”'))

    for pat in (PHONE, EMAIL):
        m = pat.search(text)
        if m:
            f.append((ERROR, 'N09', f'含联系方式“{m.group(0)}”，需去除'))
    for nm in names:
        if nm and nm in text:
            f.append((ERROR, 'N10', f'含指定人名“{nm}”'))
    level = ERROR if for_summary else WARN
    seen = set()
    for pat in NAME_PATTERNS:
        for m in pat.finditer(text):
            if m.group(0) not in seen and not any(w in m.group(0) for w in STOP):
                seen.add(m.group(0))
                f.append((level, 'N11', f'疑似人名“{m.group(0)}”（启发式，请人工确认；汇总前应去除姓名）'))
    return f


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('file')
    ap.add_argument('--names', default='', help='逗号分隔的、必须不出现的人名')
    ap.add_argument('--for-summary', action='store_true', help='对外/跨人汇总模式：疑似人名与仅限本人记录视为错误')
    ap.add_argument('--strict', action='store_true', help='警告也视为失败')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    text = Path(a.file).read_text(encoding='utf-8')
    names = [n.strip() for n in a.names.split(',') if n.strip()]
    return report(check(text, names, a.for_summary), a.json, a.strict)


if __name__ == '__main__':
    sys.exit(main())
