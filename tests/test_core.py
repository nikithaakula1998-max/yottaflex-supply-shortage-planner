import csv, tempfile, unittest
from pathlib import Path
from src.main import build

class GeneratorTests(unittest.TestCase):
    def test_repeatable(self):
        with tempfile.TemporaryDirectory() as t:
            a=build(Path(t)/'a',5,2,4,3,10); b=build(Path(t)/'b',5,2,4,3,10)
            self.assertEqual(a['sha256'],b['sha256'])
    def test_balance_reconciles(self):
        with tempfile.TemporaryDirectory() as t:
            build(t,5,2,4,3,10)
            with open(Path(t)/'shortage.csv',newline='') as f:
                for x in csv.DictReader(f):
                    self.assertEqual(int(x['opening_balance'])+int(x['inbound'])-int(x['demand']),int(x['projected_balance']))
                    self.assertEqual(-int(x['projected_balance']),int(x['shortage_qty']))

if __name__=='__main__': unittest.main()
