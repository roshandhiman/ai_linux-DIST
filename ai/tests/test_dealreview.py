"""Approval, provenance and date boundaries for the reviewed CUAD workflow."""
import hashlib
import json
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from dealreview.core import Draft, ReviewError, Cancelled, deadline_checks, generate, save
from dealreview.intent import DEFAULT_PROMPT, matches, validate


class DealReviewTests(unittest.TestCase):
    def test_scoped_intent_and_fixed_closing(self):
        self.assertTrue(matches(DEFAULT_PROMPT))
        self.assertTrue(matches('/dealreview'))
        for question in ['What is due diligence?', 'How do I generate the CUAD report?', 'Create notes.txt',
                         'Review this confidentiality agreement']:
            self.assertFalse(matches(question),question)
        with self.assertRaises(ValueError):
            validate(DEFAULT_PROMPT.replace('31 March 2027','31 March 2028'))
        with self.assertRaises(ValueError):
            validate(DEFAULT_PROMPT.replace('31 March 2027','04/01/2027'))

    def test_calendar_days_and_leap_year(self):
        d=deadline_checks()
        self.assertEqual(d['acquisition_plus_30'],'2027-04-30')
        self.assertEqual(d['fund_60_day_notice'],'2027-04-25')
        self.assertEqual(d['convenience_180'],'2026-10-02')
        self.assertEqual(len(d['monthly']),12)
        self.assertEqual(d['monthly'][0],{'anniversary':'2027-04-23','notice':'2027-03-24'})
        self.assertEqual(d['monthly'][-1],{'anniversary':'2028-03-23','notice':'2028-02-22'})

    def test_changed_pdf_stops_before_parser_or_render(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'Contracts').mkdir();(root/'Contracts/x.pdf').write_bytes(b'changed')
            pack={'docs':[{'id':'C01','filename':'x.pdf','sha256':'0'*64}]}
            with patch('dealreview.core.pack_data',return_value=pack),patch('dealreview.core.subprocess.run') as parser:
                with self.assertRaisesRegex(ReviewError,'changed'):
                    generate(root)
                parser.assert_not_called()
            self.assertFalse((root/'RedFlag_Report.md').exists())

    def test_page_quote_mismatch_refuses_report(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'Contracts').mkdir();(root/'Contracts/x.pdf').write_bytes(b'pdf')
            doc={'id':'C01','filename':'x.pdf','sha256':hashlib.sha256(b'pdf').hexdigest(),'page_count':1,
                 'evidence':{'Change Of Control':[{'page':1,'text':'A quotation absent from the PDF'}]}}
            pack={'docs':[doc],'manual':[],'extra':[]}
            parsed=subprocess.CompletedProcess([],0,stdout=json.dumps(['Different source wording']))
            with patch('dealreview.core.pack_data',return_value=pack),patch('dealreview.core.subprocess.run',return_value=parsed):
                with self.assertRaisesRegex(ReviewError,'quotation mismatch'):
                    generate(root)
            self.assertFalse((root/'RedFlag_Report.md').exists())

    def test_cancel_does_not_generate_or_save(self):
        cancel=threading.Event();cancel.set()
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(Cancelled):generate(Path(folder),cancel=cancel)
            self.assertFalse((Path(folder)/'RedFlag_Report.md').exists())

    def test_save_requires_approval_and_refuses_stale_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'Contracts').mkdir();pdf=root/'Contracts/x.pdf';pdf.write_bytes(b'original')
            draft=Draft(root,'draft pending save approval',{}, {'x.pdf':hashlib.sha256(b'original').hexdigest()}, {})
            with self.assertRaisesRegex(ReviewError,'approval'):save(draft)
            self.assertFalse((root/'RedFlag_Report.md').exists())
            pdf.write_bytes(b'modified after preview')
            with self.assertRaisesRegex(ReviewError,'changed after preview'):save(draft,approved=True)
            self.assertFalse((root/'RedFlag_Report.md').exists())

    def test_existing_report_and_render_failure_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);existing=root/'RedFlag_Report.md';existing.write_text('previous')
            draft=Draft(root,'replacement',{}, {}, {})
            with self.assertRaisesRegex(ReviewError,'already exists'):save(draft,approved=True)
            with patch('dealreview.core.html_report',side_effect=ValueError('render failed')):
                with self.assertRaises(ValueError):save(draft,approved=True,overwrite=True)
            self.assertEqual(existing.read_text(),'previous')
            self.assertFalse((root/'RedFlag_Report.html').exists())


if __name__=='__main__':unittest.main()
