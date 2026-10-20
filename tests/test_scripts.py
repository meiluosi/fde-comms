import json
import subprocess
import sys
import unittest
from pathlib import Path

R = Path(__file__).resolve().parents[1]
FX = R / 'tests' / 'fixtures'
sys.path.insert(0, str(R / 'scripts'))
import check_expectations  # noqa: E402
import check_notes  # noqa: E402
import check_onepager  # noqa: E402


def read(name):
    return (FX / name).read_text(encoding='utf-8')


def rules(findings, level=None):
    return {r for l, r, _ in findings if level is None or l == level}


class NotesTests(unittest.TestCase):
    def test_good_passes_clean(self):
        self.assertEqual(check_notes.check(read('notes-good.md')), [])

    def test_bad_catches_core_rules(self):
        f = check_notes.check(read('notes-bad.md'))
        errs = rules(f, 'ERROR')
        self.assertTrue({'N01', 'N04', 'N05', 'N09'} <= errs)
        self.assertIn('N08', rules(f, 'WARN'))

    def test_oral_claim_recorded_as_fact_warns_in_both_table_shapes(self):
        row = '| ID | 命题 | 状态 | 来源 |\n|---|---|---|---|\n| E1 | 核对 10 分钟 | 事实 | 班长，口头访谈 |\n'
        self.assertIn('N08', rules(check_notes.check('我理解您说的是……对吗\n' + row)))
        col = '| 字段 | E1 |\n|---|---|\n| 状态 | 事实 |\n| 来源 | 口头访谈 |\n'
        self.assertIn('N08', rules(check_notes.check('我理解您说的是……对吗\n' + col)))

    def test_fact_with_evidence_does_not_warn(self):
        row = '| ID | 命题 | 状态 | 来源 |\n|---|---|---|---|\n| E1 | 核对 10 分钟 | 事实 | 系统日志，口头访谈核对 |\n'
        self.assertNotIn('N08', rules(check_notes.check('我理解您说的是……对吗\n' + row)))

    def test_named_person_error_and_summary_mode(self):
        t = read('notes-good.md')
        self.assertIn('N10', rules(check_notes.check(t + '\n张三说', names=['张三']), 'ERROR'))
        bad = read('notes-bad.md')
        self.assertNotIn('N11', rules(check_notes.check(bad), 'ERROR'))
        s = check_notes.check(bad, for_summary=True)
        self.assertIn('N11', rules(s, 'ERROR'))
        self.assertIn('N07', rules(s, 'ERROR'))

    def test_common_words_are_not_names(self):
        t = read('notes-good.md') + '\n高管关心周期，方案由负责人周期性评估。'
        self.assertNotIn('N11', rules(check_notes.check(t, for_summary=True)))

    def test_caliber_marked_pending_is_not_blank(self):
        t = read('notes-good.md').replace('口径未知：起止点、哪类单、是否实测均未问', '三张表分别是哪三张：待确认')
        self.assertNotIn('N05', rules(check_notes.check(t)))

    def test_missing_table_and_unknown_caliber_ok(self):
        self.assertIn('N03', rules(check_notes.check('我理解您说的是……对吗')))
        t = read('notes-good.md').replace('口径未知：起止点、哪类单、是否实测均未问', '未知')
        self.assertNotIn('N05', rules(check_notes.check(t)))


class OnepagerTests(unittest.TestCase):
    def test_good_passes_clean(self):
        self.assertEqual(check_onepager.check_onepager(read('onepager-good.md')), [])

    def test_bad_catches_core_rules(self):
        f = check_onepager.check_onepager(read('onepager-bad.md'))
        self.assertTrue({'O02', 'O03'} <= rules(f, 'ERROR'))
        self.assertTrue({'O06', 'O08', 'O09', 'O10', 'O12'} <= rules(f, 'WARN'))

    def test_three_metrics_allowed_four_not(self):
        g = read('onepager-good.md')
        self.assertNotIn('O02', rules(check_onepager.check_onepager(g)))
        g4 = g.replace('| 月调用成本 |', '| 额外指标 | 1 | 2 | 口径 | 10 月 | 中 |\n| 月调用成本 |')
        self.assertIn('O02', rules(check_onepager.check_onepager(g4), 'ERROR'))

    def test_pending_metric_needs_only_caliber(self):
        g = read('onepager-good.md').replace('人工抽检 50 单，方案 10 月 28 日前确定', '')
        self.assertIn('O03', rules(check_onepager.check_onepager(g), 'ERROR'))

    def test_tech_terms_in_attachment_are_allowed(self):
        self.assertNotIn('O12', rules(check_onepager.check_onepager(read('onepager-good.md'))))

    def test_final_turns_placeholders_into_errors(self):
        g = read('onepager-good.md').replace('2026-10-25', '【日期】')
        self.assertIn('O13', rules(check_onepager.check_onepager(g), 'WARN'))
        self.assertIn('O13', rules(check_onepager.check_onepager(g, final=True), 'ERROR'))

    def test_badnews_prefers_numbered_item_over_prose(self):
        t = '先解释一下：第 4 句“需要您做什么”是请老板协助。\n' + read('badnews-good.md')
        self.assertNotIn('B04', rules(check_onepager.check_badnews(t)))

    def test_badnews_good_and_bad(self):
        self.assertEqual(check_onepager.check_badnews(read('badnews-good.md')), [])
        f = check_onepager.check_badnews(read('badnews-bad.md'))
        self.assertTrue({'B01', 'B05', 'B06'} <= rules(f, 'ERROR'))
        self.assertTrue({'B07', 'B08', 'B09', 'B10'} <= rules(f, 'WARN'))


class ExpectationsTests(unittest.TestCase):
    def test_good_passes_clean(self):
        self.assertEqual(check_expectations.check(read('expectations-good.md')), [])

    def test_bad_catches_core_rules(self):
        f = check_expectations.check(read('expectations-bad.md'))
        self.assertTrue({'E02', 'E04', 'E05', 'E09', 'E11'} <= rules(f, 'ERROR'))
        self.assertTrue({'E10', 'E12'} <= rules(f, 'WARN'))

    def test_all_three_acceptance_questions_required(self):
        g = read('expectations-good.md').replace('- 绝对不能接受的错误：金额、被保险人错误\n', '')
        self.assertIn('E07', rules(check_expectations.check(g), 'ERROR'))

    def test_owner_must_be_a_role_not_the_system(self):
        g = read('expectations-good.md').replace('理赔组长', 'AI 系统')
        self.assertIn('E09', rules(check_expectations.check(g), 'ERROR'))

    def test_unmeasured_frequency_needs_source(self):
        g = read('expectations-good.md').replace('| 字段读错 | 待测 |', '| 字段读错 | 每周 5% |')
        self.assertIn('E06', rules(check_expectations.check(g), 'WARN'))


class CliTests(unittest.TestCase):
    def run_cli(self, script, *args):
        return subprocess.run([sys.executable, '-I', str(R / 'scripts' / script), *args], capture_output=True, text=True)

    def test_exit_codes(self):
        self.assertEqual(self.run_cli('check_notes.py', str(FX / 'notes-good.md')).returncode, 0)
        self.assertEqual(self.run_cli('check_notes.py', str(FX / 'notes-bad.md')).returncode, 1)
        self.assertEqual(self.run_cli('check_onepager.py', str(FX / 'badnews-good.md'), '--kind', 'bad-news').returncode, 0)
        self.assertEqual(self.run_cli('check_expectations.py', str(FX / 'expectations-bad.md')).returncode, 1)

    def test_strict_fails_on_warnings(self):
        p = FX / 'onepager-good.md'
        self.assertEqual(self.run_cli('check_onepager.py', str(p), '--strict').returncode, 0)
        tmp = R / 'tests' / 'fixtures' / '_tmp_warn.md'
        try:
            tmp.write_text(p.read_text(encoding='utf-8').replace('类型：供知悉（耗时、成本、风险）＋ 请决策（权限协调）', ''), encoding='utf-8')
            self.assertEqual(self.run_cli('check_onepager.py', str(tmp)).returncode, 0)
            self.assertEqual(self.run_cli('check_onepager.py', str(tmp), '--strict').returncode, 1)
        finally:
            tmp.unlink(missing_ok=True)

    def test_json_output(self):
        r = self.run_cli('check_notes.py', str(FX / 'notes-bad.md'), '--json')
        data = json.loads(r.stdout)
        self.assertTrue(any(d['rule'] == 'N01' for d in data))

    def test_missing_file_is_an_error(self):
        self.assertNotEqual(self.run_cli('check_notes.py', str(FX / 'nope.md')).returncode, 0)


if __name__ == '__main__':
    unittest.main()
