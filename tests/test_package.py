import re, unittest
from pathlib import Path
R = Path(__file__).resolve().parents[1]

class PackageTests(unittest.TestCase):
    def test_skill_frontmatter(self):
        t = (R / 'SKILL.md').read_text()
        m = re.match(r'---\nname: (\S+)\ndescription: (.+)\n---\n', t)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), R.name)

    def test_links(self):
        for p in R.rglob('*.md'):
            for dest in re.findall(r'\]\(([^)]+)\)', p.read_text()):
                if '://' in dest or dest.startswith('#'):
                    continue
                with self.subTest(file=str(p), link=dest):
                    self.assertTrue((p.parent / dest.split('#')[0]).exists())

    def test_portable_paths(self):
        for p in R.rglob('*.md'):
            self.assertNotIn('/Users/', p.read_text(), str(p))

    def test_templates_exist(self):
        for n in ['interview-guide', 'interview-notes', 'one-pager', 'bad-news']:
            self.assertTrue((R / 'templates' / f'{n}.md').exists())

    def test_modes_have_references(self):
        t = (R / 'SKILL.md').read_text()
        for n in ['interview', 'upward', 'core', 'handoff']:
            self.assertIn(f'references/{n}.md', t + (R / 'references' / 'interview.md').read_text())

if __name__ == '__main__':
    unittest.main()
