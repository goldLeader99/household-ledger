"""Synthetic fixtures only. Never replace them with a real bank statement."""
import base64
import importlib.util
import io
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]

def synthetic_statement():
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(612, 792))
    pdf.setFont('Helvetica', 10)
    for y, text in [(760, 'RoyalBankofCanada'),
                    (740, 'FromJanuary1,2024toJanuary31,2024'),
                    (720, 'Youraccountnumber:00000-0000000'),
                    (690, 'YouropeningbalanceonJanuary1,2024 $100.00'),
                    (670, 'Totaldepositsintoyouraccount +200.00'),
                    (650, 'Totalwithdrawalsfromyouraccount -25.00'),
                    (630, 'YourclosingbalanceonJanuary31,2024 =$275.00')]:
        pdf.drawString(40, y, text)
    for x, text in [(40, 'Date'), (90, 'Description'), (300, 'Withdrawals($)'), (420, 'Deposits($)'), (520, 'Balance($)')]:
        pdf.drawString(x, 580, text)
    pdf.drawString(90, 560, 'OpeningBalance')
    pdf.drawString(550, 560, '100.00')
    pdf.drawString(40, 540, '2Jan')
    pdf.drawString(90, 540, 'PayrollDeposit DEMO')
    pdf.drawString(440, 540, '200.00')
    pdf.drawString(550, 540, '300.00')
    pdf.drawString(40, 520, '3Jan')
    pdf.drawString(90, 520, 'Purchase DEMO STORE')
    pdf.drawString(330, 520, '25.00')
    pdf.drawString(550, 520, '275.00')
    pdf.drawString(90, 500, 'ClosingBalance')
    pdf.drawString(550, 500, '$275.00')
    pdf.save()
    return buffer.getvalue()

class LedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=os.environ.get('LEDGER_TEST_TEMP_DIR'))
        cls.previous = os.environ.get('LEDGER_DATA_DIR')
        os.environ['LEDGER_DATA_DIR'] = cls.temp.name
        spec = importlib.util.spec_from_file_location('public_ledger_test', ROOT / 'app.py')
        cls.app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.app)
        cls.server = cls.app.ThreadingHTTPServer(('127.0.0.1', 0), cls.app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()
        if cls.previous is None:
            os.environ.pop('LEDGER_DATA_DIR', None)
        else:
            os.environ['LEDGER_DATA_DIR'] = cls.previous

    def setUp(self):
        with self.app.connect() as connection:
            connection.executescript('DELETE FROM imports; DELETE FROM transactions; DELETE FROM rules; DELETE FROM bills;')

    def call(self, endpoint, payload=None, origin=None):
        headers = {'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        request = urllib.request.Request(
            f'http://127.0.0.1:{self.server.server_port}/api/{endpoint}',
            data=json.dumps(payload).encode() if payload is not None else None,
            headers=headers)
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def preview(self, raw=None):
        return self.call('preview', {'file': base64.b64encode(raw or synthetic_statement()).decode(),
                                    'name': 'synthetic.pdf', 'account_id': 'primary-chequing'})

    def test_extract_and_reconcile(self):
        result = self.app.parse_pdf(synthetic_statement(), 'Member 1')
        self.assertTrue(result['report']['valid'])
        self.assertEqual([t['amount'] for t in result['transactions']], [20000, -2500])
        self.assertEqual([t['date'] for t in result['transactions']], ['2024-01-02', '2024-01-03'])
        self.assertEqual(result['report']['calculated_closing'], 27500)
        self.assertEqual(result['report']['balance_checks'], 2)

    def test_staging_confirmation_and_duplicates(self):
        raw = synthetic_statement()
        status, preview = self.preview(raw)
        self.assertEqual(status, 200)
        self.assertEqual(self.call('state')[1]['transactions'], [])
        self.assertEqual(self.call('confirm', {'id': preview['id']})[0], 200)
        self.assertEqual(self.call('state')[1]['imports'][0]['account_id'], 'primary-chequing')
        self.assertEqual(self.call('preview', {'file': base64.b64encode(raw).decode(), 'name': 'renamed.pdf'})[0], 400)
        status, overlap = self.preview(raw + b'\n% synthetic duplicate fixture\n')
        self.assertEqual(status, 200)
        self.assertEqual(self.call('confirm', {'id': overlap['id']})[0], 400)
        self.assertEqual(len(self.call('state')[1]['transactions']), 2)

    def test_manual_accept_and_signed_memory(self):
        status, preview = self.preview()
        self.assertEqual(status, 200)
        self.call('confirm', {'id': preview['id']})
        transaction = self.call('state')[1]['transactions'][1]
        self.assertEqual(self.call('transaction', {'id': transaction['id'], 'category': 'Shopping',
                                                 'owner': 'Member 1', 'remember': True})[0], 200)
        self.assertEqual(self.call('state')[1]['transactions'][1]['category'], 'Shopping')
        self.assertEqual(self.app.categorise('DEMO', -100, {'DEMO|debit': 'Shopping'})[1], 'Shopping')
        self.assertEqual(self.app.categorise('DEMO', 100, {'DEMO|debit': 'Shopping'})[1], 'Uncategorised')

    def test_unsupported_account_and_foreign_origin(self):
        payload = {'file': base64.b64encode(synthetic_statement()).decode(), 'name': 'synthetic.pdf',
                   'account_id': 'example-credit'}
        self.assertEqual(self.call('preview', payload)[0], 400)
        self.assertEqual(self.call('preview', payload, origin='https://example.invalid')[0], 400)

    def test_bill_tracking(self):
        status, _ = self.call('bill', {'name': 'Demo bill', 'amount': '20.00', 'due': '2024-01-31',
                                      'category': 'Utilities', 'owner': 'Joint'})
        self.assertEqual(status, 200)
        bill = self.call('state')[1]['bills'][0]
        self.assertEqual(bill['amount'], 2000)
        self.assertEqual(self.call('bill', {'id': bill['id'], 'status': 'Paid'})[0], 200)
        self.assertEqual(self.call('state')[1]['bills'][0]['status'], 'Paid')

if __name__ == '__main__':
    unittest.main()
