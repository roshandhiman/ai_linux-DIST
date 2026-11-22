"""Read actual PDFs, validate reviewed evidence, recompute dates, preview, approve.

The annotated public demo is intentionally explicit. It does not claim to infer
new legal conclusions or perform live online research. No model/API is called.
"""
from __future__ import annotations

import copy
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

DATA = Path(__file__).with_name('data') / 'cuad_demo.json'
PDF_SCRIPT = ('import json,sys; from pypdf import PdfReader; '
              'print(json.dumps([p.extract_text() or "" for p in PdfReader(sys.argv[1]).pages]))')


class ReviewError(RuntimeError):
    pass


class Cancelled(ReviewError):
    pass


def pack_data() -> dict:
    return json.loads(DATA.read_text(encoding='utf-8'))


def fingerprint(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ReviewError(f'Missing regular PDF: {path.name}. Prepare the public CUAD demo first.')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _cancelled(cancel: threading.Event | None) -> None:
    if cancel and cancel.is_set():
        raise Cancelled('Review stopped. No report was saved.')


def download_demo(root: Path, emit: Callable[[dict], None] = lambda event: None) -> None:
    """Explicit download action, never called implicitly by report generation."""
    docs = pack_data()['docs']
    folder = root / 'Contracts'
    folder.mkdir(parents=True, exist_ok=True)
    for i, doc in enumerate(docs, 1):
        path = folder / doc['filename']
        if path.exists():
            if fingerprint(path) != doc['sha256']:
                raise ReviewError(f'{path.name} differs from the reviewed demo. It was not replaced.')
        else:
            url = ('https://huggingface.co/datasets/theatticusproject/cuad/resolve/main/'
                   + urllib.parse.quote(doc['pdf_path'], safe='/'))
            temporary = None
            try:
                with urllib.request.urlopen(url, timeout=30) as response, tempfile.NamedTemporaryFile(
                        dir=folder, prefix='.download-', delete=False) as output:
                    temporary = Path(output.name)
                    size = 0
                    while block := response.read(65536):
                        size += len(block)
                        if size > 20_000_000:
                            raise ReviewError('Public PDF download exceeded the expected size limit.')
                        output.write(block)
                if fingerprint(temporary) != doc['sha256']:
                    raise ReviewError(f'Public source changed: {doc["filename"]}. Expected hash did not match.')
                # Exclusive creation: never replace a file that appeared during download.
                os.link(temporary, path)
            finally:
                if temporary:
                    temporary.unlink(missing_ok=True)
        emit({'stage': 'download', 'index': i, 'total': len(docs), 'id': doc['id'], 'file': doc['filename']})


def deadline_checks() -> dict:
    closing = date(2027, 3, 31)
    monthly = []
    for y, m in [(2027, m) for m in range(4, 13)] + [(2028, m) for m in range(1, 4)]:
        end = date(y, m, 23)
        monthly.append({'anniversary': end.isoformat(), 'notice': (end-timedelta(days=30)).isoformat()})
    return {'closing': closing.isoformat(), 'window_end': date(2028,3,31).isoformat(),
            'acquisition_plus_30': (closing+timedelta(days=30)).isoformat(),
            'annual_notice': (date(2027,12,23)-timedelta(days=30)).isoformat(),
            'fund_60_day_notice': (date(2027,6,24)-timedelta(days=60)).isoformat(),
            'convenience_90': (closing-timedelta(days=90)).isoformat(),
            'convenience_180': (closing-timedelta(days=180)).isoformat(), 'monthly': monthly}


@dataclass
class Draft:
    root: Path
    markdown: str
    stats: dict
    hashes: dict[str, str]
    deadlines: dict


def generate(root: Path, emit: Callable[[dict], None] = lambda event: None,
             cancel: threading.Event | None = None) -> Draft:
    from .report import Renderer
    root = root.expanduser().resolve()
    pack = pack_data()
    docs = copy.deepcopy(pack['docs'])
    start = time.monotonic()
    checked = 0
    hashes = {}
    for index, doc in enumerate(docs, 1):
        _cancelled(cancel)
        if time.monotonic() - start > 100:
            raise ReviewError('Review exceeded 100 seconds. No report was saved. Retry after checking the PDFs.')
        emit({'stage': 'reading', 'index': index, 'total': len(docs), 'id': doc['id'], 'file': doc['filename']})
        path = root / 'Contracts' / doc['filename']
        sha = fingerprint(path)
        if sha != doc['sha256']:
            raise ReviewError(f'{doc["id"]}: PDF changed since the reviewed source. Re-review required; stale analysis refused.')
        hashes[doc['filename']] = sha
        try:
            process = subprocess.run([sys.executable, '-I', '-c', PDF_SCRIPT, str(path)],
                                     capture_output=True, text=True, timeout=20, check=True)
            pages = json.loads(process.stdout)
        except subprocess.TimeoutExpired:
            raise ReviewError(f'{doc["id"]}: PDF extraction timed out after 20 seconds.') from None
        except (subprocess.CalledProcessError, ValueError) as exc:
            detail = getattr(exc, 'stderr', '')
            message = ('Install the pinned PDF dependency with scripts/install-dealreview.sh.'
                       if 'No module named' in detail else 'The source PDF could not be extracted.')
            raise ReviewError(f'{doc["id"]}: {message}') from None
        if len(pages) != doc['page_count']:
            raise ReviewError(f'{doc["id"]}: PDF page count changed; page references cannot be certified.')
        doc['pages'] = pages
        # Every supplied quotation must still occur on its identified original page.
        groups = list(doc['evidence'].values())
        groups += [x['quotes'] for x in pack['manual'] if x['contract'] == index]
        groups += [x[4] for x in pack['extra'] if x[0] == index]
        for entries in groups:
            for item in entries:
                if not item['text']:
                    continue
                page = item['page']
                if not 1 <= page <= len(pages) or item['text'] not in re.sub(r'\s+', ' ', pages[page-1]).strip():
                    raise ReviewError(f'{doc["id"]}, page {page}: reviewed quotation mismatch. No generated report was saved.')
                checked += 1
        _cancelled(cancel)
        emit({'stage': 'reviewed', 'index': index, 'total': len(docs), 'id': doc['id'],
              'file': doc['filename'], 'pages': len(pages), 'quotes': checked})
    emit({'stage': 'deadlines', 'index': 20, 'total': 20})
    deadlines = deadline_checks()
    renderer = Renderer(pack, root, docs)
    markdown, stats = renderer.build_report()
    _cancelled(cancel)
    # The online research belongs to the reviewed reference pack, not this offline run.
    markdown = markdown.replace('**Draft for supervising-partner review — not approved for saving or distribution.**',
        '**Reviewed public CUAD demonstration — draft pending save approval.**\n\n'
        '**Run method:** MineOS read and hash-checked the 20 original PDFs and verified their quoted pages. '
        'Legal interpretations are from a reviewed reference pack, not new model inference. '
        'Deadline arithmetic is recomputed locally. External sources are a 22 November 2026 research snapshot; '
        'this run made no online searches. It is not an autonomous live-deal legal review.')
    markdown = markdown.replace('The following queries were displayed in the chat before submission.',
        'Historical preparation log: the following queries were displayed in the original preparation chat before submission. '
        'They were NOT submitted by this offline MineOS run.')
    markdown = markdown.replace('Full download verified against repository listing:',
        'During original preparation, the full dataset download was verified against its repository listing:')
    markdown = markdown.replace('Full download verified', 'Original preparation download verified')
    markdown = markdown.replace('this draft has not been saved as `RedFlag_Report.md` and has not been sent to anyone. '
        'Proposed destination only after express approval: `~/DealRoom/RedFlag_Report.md`.',
        'this generated draft has not been saved or distributed. Saving requires approval in this window or terminal. '
        'Destination: `~/DealRoom/RedFlag_Report.md`. No external distribution function is provided.')
    stats.update({'quote_checks': checked, 'seconds': round(time.monotonic()-start, 2),
                  'research_cutoff': pack['research_cutoff'], 'method': 'reviewed-public-cuad-demo',
                  'characters': len(markdown), 'words': len(markdown.split())})
    emit({'stage': 'ready', 'stats': stats})
    return Draft(root, markdown, stats, hashes, deadlines)


def html_report(markdown: str) -> str:
    import markdown as md
    body = md.markdown(markdown, extensions=['tables', 'fenced_code'])
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Mino · CUAD due diligence demo</title><style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#eef2f5;color:#172533;font:16px/1.65 system-ui,sans-serif}
main{max-width:1480px;margin:40px auto;padding:45px;background:#fff;border-radius:16px}h1{font-size:30px;line-height:1.25}h2{margin-top:58px;border-top:2px solid #e1e7ec;padding-top:24px}h3{margin-top:32px}h4{margin-top:28px}a{color:#076767;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;font-size:14px;margin:20px 0;table-layout:fixed}td,th{border:1px solid #d9e2e8;padding:12px;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#e7f4f1}tr:nth-child(even){background:#f8fafb}code{background:#edf2f5;border-radius:4px;padding:2px 5px;overflow-wrap:anywhere}p{max-width:1050px}@media print{main{padding:0;margin:0}table{font-size:9px}h2{break-before:page}tr{break-inside:avoid}}
</style><main>'''+body+'</main></html>'


def save(draft: Draft, *, approved: bool = False, overwrite: bool = False) -> tuple[Path, Path]:
    if not approved:
        raise ReviewError('Saving requires explicit user approval.')
    md_path = draft.root / 'RedFlag_Report.md'
    html_path = draft.root / 'RedFlag_Report.html'
    for path in (md_path, html_path):
        if path.is_symlink() or (path.exists() and not overwrite):
            raise ReviewError(f'{path.name} already exists. Confirm replacement first.')
    for name, sha in draft.hashes.items():
        if fingerprint(draft.root / 'Contracts' / name) != sha:
            raise ReviewError('A source PDF changed after preview. Generate and review a fresh draft.')
    text = draft.markdown.replace('draft pending save approval', 'draft approved for local saving')
    text = text.replace('this generated draft has not been saved or distributed. Saving requires approval in this window or terminal.',
                        'the user approved local saving in MineOS. The report has not been externally distributed.')
    # Render before changing either existing report. Failed rendering leaves previous files untouched.
    outputs = [(md_path, text), (html_path, html_report(text))]
    pending = []
    try:
        for path, content in outputs:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=draft.root, prefix='.review-', delete=False) as stream:
                stream.write(content);stream.flush();os.fsync(stream.fileno());pending.append((Path(stream.name), path))
        for temporary, path in pending:
            if overwrite:
                os.replace(temporary, path)
            else:
                os.link(temporary, path);temporary.unlink()
        return md_path, html_path
    finally:
        for temporary, _ in pending:
            temporary.unlink(missing_ok=True)
