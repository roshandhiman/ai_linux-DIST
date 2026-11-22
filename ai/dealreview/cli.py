"""Run mino-review, ai dealreview, or an explicit public CUAD review request."""
import argparse
import json
import os
import sys
from pathlib import Path
from .core import ReviewError, download_demo, generate, save
from .intent import DEFAULT_PROMPT, validate


def main(argv=None):
    parser=argparse.ArgumentParser(prog='mino-review',description='Reviewed public CUAD demo. Local PDF checks and deadline calculation; research snapshot 22 Nov 2026.')
    parser.add_argument('--dealroom',type=Path,default=Path.home()/'DealRoom')
    parser.add_argument('--prompt',default=DEFAULT_PROMPT)
    parser.add_argument('--gui',action='store_true')
    parser.add_argument('--autorun',action='store_true',help='Start the GUI review with the supplied prompt')
    parser.add_argument('--cli',action='store_true',help='Use Terminal rather than the review window')
    parser.add_argument('--check',action='store_true',help='Validate and generate in RAM; do not ask to save')
    parser.add_argument('--json',action='store_true',help='Print machine-readable progress and summary')
    parser.add_argument('--download-demo',action='store_true',help='Explicitly download and hash-check the 20 public PDFs')
    args=parser.parse_args(argv);root=args.dealroom.expanduser().resolve()
    def emit(event):
        if args.json:print(json.dumps(event),flush=True)
        elif event['stage']=='reviewed':print(f'  [{event["index"]:02d}/20] {event["id"]}  {event["pages"]} pages  source evidence checked',flush=True)
        elif event['stage']=='download':print(f'  [{event["index"]:02d}/20] Prepared {event["id"]}',flush=True)
        elif event['stage']=='deadlines':print('  Calculating notice dates and renewal deadlines…',flush=True)
    try:
        if args.download_demo:download_demo(root,emit);return 0
        validate(args.prompt)
        if not args.cli and not args.check and (args.gui or os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
            from .gui import main as gui
            return gui(root,args.prompt,args.autorun)
        if not args.json:print('Mino · Deal Review\n20 public CUAD contracts · reviewed demo · closing 31 March 2027\n')
        draft=generate(root,emit)
        if args.json:print(json.dumps({'stage':'summary','stats':draft.stats,'deadlines':draft.deadlines,'saved':False}),flush=True)
        else:
            print(f'\nDraft ready: {draft.stats["flagged_rows"]} flagged entries; {draft.stats["not_found_rows"]} NOT FOUND items.')
            print('5/20 documents have conditional express acquisition-related loss clauses; this is not an actual live-portfolio percentage.')
            print('Current entity/contract status and other external facts remain unverified. See the full draft after saving.')
        if args.check:return 0
        if not sys.stdin.isatty():
            print('No interactive approval available. Nothing saved. Use mino-review in your desktop.',file=sys.stderr);return 2
        print('\n'+draft.markdown.split('### Scope, assumptions and ratings')[0])
        existing=any((root/n).exists() for n in ('RedFlag_Report.md','RedFlag_Report.html'))
        answer=input(('Replace' if existing else 'Save')+' Markdown + HTML reports in '+str(root)+'? [y/N] ').strip().lower()
        if answer not in ('y','yes'):print('Draft left unsaved.');return 0
        paths=save(draft,approved=True,overwrite=existing)
        print('Saved: '+str(paths[0]));return 0
    except (OSError,ValueError,ReviewError,ImportError) as error:
        print(f'Mino Deal Review: {error}',file=sys.stderr);return 1
    except KeyboardInterrupt:
        print('\nStopped. No new report was saved.',file=sys.stderr);return 130


if __name__=='__main__':raise SystemExit(main())
