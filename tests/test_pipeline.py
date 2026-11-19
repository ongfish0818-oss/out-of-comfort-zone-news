import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pipeline import clean,is_original_article,caption,load_history,ROOT
import json,datetime as dt

class SafetyTests(unittest.TestCase):
    def test_article_allowlist(self):
        self.assertTrue(is_original_article('https://theedgemalaysia.com/node/1234'))
        self.assertFalse(is_original_article('https://theedgemalaysia.com.evil.example/node/1234'))
        self.assertFalse(is_original_article('http://theedgemalaysia.com/node/1234'))
    def test_strip_html(self):
        self.assertEqual(clean('<p>Growth &amp; profits</p>'),'Growth & profits')
    def test_demo_caption(self):
        items=json.loads((ROOT/'tests'/'fixtures.json').read_text())
        c=caption(items,dt.date(2026,11,19))
        self.assertIn('SAMPLE ONLY:',c)
        self.assertEqual(c.count('https://theedgemalaysia.com/node/'),5)

if __name__=='__main__':unittest.main()
