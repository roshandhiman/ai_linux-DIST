// Demo recordings that mirror what the MineOS terminal agent (`ai`,
// ai/mineos_agent/) does and writes to ~/.local/state/mineos/runs/.
//
// One real run-log record is one *turn*: request, route, mode, outcome,
// answer, model, and a list of steps. One real step is one model call that
// produced a Python block, plus the sandboxed run of that block (code,
// output, error, attempts, mine.* calls, seconds). Here a real step is split
// into the two parts a phone viewer cares about: the `modelCall` (the slow
// part on a CPU) and the `toolCall` (the sandbox run). `plan` is the router's
// decision, `error` is a refused or failed block that the agent retried,
// `approvalRequest` is the agent's real y/N prompt, and `result` is the
// turn's outcome and answer.
//
// The recordings respect the agent's real limits: at most 12 mine.* calls
// per block, find_files returns at most 25 paths, read_file refuses files
// over 2 MB, and a step gets 3 attempts before the turn ends. The trace text
// uses the CLI's own markers (> route, . thinking, > code, < output,
// ! error, ~ retrying, "The assistant wants to: ... Allow this? [y/N]").

/// One step of a recording, before it is stored.
class StepSpec {
  const StepSpec(this.kind, this.title, this.detail, this.durationMs);

  /// plan | modelCall | toolCall | approvalRequest | result | error
  final String kind;
  final String title;
  final String detail;
  final int durationMs;
}

/// One recorded agent session.
class SessionSpec {
  const SessionSpec({
    required this.task,
    required this.status,
    required this.route,
    required this.startedMinutesAgo,
    required this.steps,
    this.outcome,
    this.answer,
  });

  final String task;

  /// running | awaitingApproval | done | failed
  final String status;

  /// Turn.route as the agent logs it: "INTENT confidence via backend".
  final String route;

  /// Turn.outcome: answered | exhausted | confused | stuck | offline | declined.
  final String? outcome;
  final String? answer;
  final int startedMinutesAgo;
  final List<StepSpec> steps;
}

/// The local model, exactly as the agent records it (`record["model"]`).
const demoModelName = 'qwen2.5-1.5b-instruct';

/// `llm.provider`; "local" is llama.cpp's llama-server on 127.0.0.1:8080.
const demoProvider = 'local';

const demoRecordings = <SessionSpec>[
  // a) RUNNING: a long task. The replay loops it so the demo never goes dead.
  SessionSpec(
    task: 'Audit ~/Projects/acme-site, find the 5 largest files, summarise '
        'each, and draft a cleanup report',
    status: 'running',
    route: 'TASK 0.50 via rules',
    startedMinutesAgo: 4,
    steps: [
      StepSpec(
        'plan',
        'Routed to the local model',
        '> route  TASK 0.50 via rules\n'
            'The request names a folder, so it always goes to tier 2 (the '
            'language model), never the fast path.\n'
            'mode: tools, one sandboxed Python session for the whole task\n'
            'model: qwen2.5-1.5b-instruct, llama-server 127.0.0.1:8080\n'
            'budget: 6 steps, 3 attempts per step, 4,096-token window',
        40,
      ),
      StepSpec(
        'modelCall',
        'Step 1: the model writes a block',
        '. thinking (step 1, try 1)\n'
            'window ~1,410 tokens, temperature 0.2',
        13800,
      ),
      StepSpec(
        'toolCall',
        'List the project folder',
        '> code\n'
            '  | names = mine.list_dir("~/Projects/acme-site")\n'
            '  | print(names)\n'
            '< output\n'
            "  | ['assets/', 'backups/', 'build/', 'logs/', 'src/', "
            "'README.md', 'package.json']\n"
            'calls: list_dir',
        310,
      ),
      StepSpec(
        'modelCall',
        'Step 2: the model writes a block',
        '. thinking (step 2, try 1)\n'
            'window ~1,620 tokens, temperature 0.2',
        18200,
      ),
      StepSpec(
        'error',
        'Refused: too many calls in one block',
        '> code\n'
            '  | files = mine.find_files("*", "~/Projects/acme-site")\n'
            '  | sizes = [mine.file_info(f)["size"] for f in files]\n'
            '! more than 12 mine calls in one block; do less per block '
            '(line 2)\n'
            '~ retrying: step 2, try 2, temperature 0.55\n'
            'A broken block is not progress. It is retried inside the same '
            'step, and the model only sees its latest mistake.',
        20,
      ),
      StepSpec(
        'modelCall',
        'Step 2: the model rewrites the block',
        '. thinking (step 2, try 2)\n'
            'window ~1,780 tokens, temperature 0.55',
        16500,
      ),
      StepSpec(
        'toolCall',
        'List the four biggest-looking folders',
        '> code\n'
            '  | for d in ["backups", "assets/video", "logs", "build"]:\n'
            '  |     print(d, mine.list_dir("~/Projects/acme-site/" + d))\n'
            '< output\n'
            "  | backups ['db-2025-12-01.sql', 'db-2025-06-01.sql.gz']\n"
            "  | assets/video ['hero-4k.mov', 'hero-1080p.mp4']\n"
            "  | logs ['access.log', 'error.log']\n"
            "  | build ['app.bundle.js', 'app.bundle.js.map', "
            "'fonts-unused.zip']\n"
            'calls: list_dir x4',
        420,
      ),
      StepSpec(
        'modelCall',
        'Step 3: the model writes a block',
        '. thinking (step 3, try 1)\n'
            'window ~2,140 tokens, temperature 0.2',
        17000,
      ),
      StepSpec(
        'toolCall',
        'Size the candidates and keep the top 5',
        '> code\n'
            '  | base = "~/Projects/acme-site/"\n'
            '  | paths = ["backups/db-2025-12-01.sql", '
            '"backups/db-2025-06-01.sql.gz",\n'
            '  |   "assets/video/hero-4k.mov", "assets/video/hero-1080p.mp4", '
            '"logs/access.log",\n'
            '  |   "logs/error.log", "build/app.bundle.js", '
            '"build/app.bundle.js.map", "build/fonts-unused.zip"]\n'
            '  | info = sorted((mine.file_info(base + p) for p in paths),\n'
            '  |               key=lambda i: i["size"], reverse=True)\n'
            '  | for i in info[:5]:\n'
            '  |     print(i["size_text"], i["modified"], i["path"])\n'
            '  | mine.note("top5: " + ", ".join(i["path"] for i in info[:5]))\n'
            '< output\n'
            '  | 412.6 MB 2025-12-01 02:00 ~/Projects/acme-site/backups/'
            'db-2025-12-01.sql\n'
            '  | 188.0 MB 2025-09-14 16:21 ~/Projects/acme-site/assets/video/'
            'hero-4k.mov\n'
            '  | 96.3 MB 2026-11-21 23:59 ~/Projects/acme-site/logs/access.log\n'
            '  | 41.8 MB 2026-11-20 18:05 ~/Projects/acme-site/build/'
            'app.bundle.js.map\n'
            '  | 22.5 MB 2025-03-02 11:40 ~/Projects/acme-site/build/'
            'fonts-unused.zip\n'
            'calls: file_info x9, note (10 of 12 allowed)',
        890,
      ),
      StepSpec(
        'modelCall',
        'Step 4: the model writes a block',
        '. thinking (step 4, try 1)\n'
            'window ~2,560 tokens, temperature 0.2',
        14300,
      ),
      StepSpec(
        'error',
        'Refused: the dump is too big to read',
        '> code\n'
            '  | print(mine.read_file("~/Projects/acme-site/backups/'
            'db-2025-12-01.sql", 400))\n'
            '! ~/Projects/acme-site/backups/db-2025-12-01.sql is larger than '
            '2 MB; it is not read whole (line 1)\n'
            '~ retrying: step 4, try 2, temperature 0.55',
        30,
      ),
      StepSpec(
        'modelCall',
        'Step 4: the model rewrites the block',
        '. thinking (step 4, try 2)\n'
            'window ~2,690 tokens, temperature 0.55',
        15900,
      ),
      StepSpec(
        'toolCall',
        'Read the README to learn what the files are for',
        '> code\n'
            '  | print(mine.read_file("~/Projects/acme-site/README.md", 1200))\n'
            '< output\n'
            '  | # acme-site\n'
            '  | Marketing site. `npm run build` writes build/. The hero video '
            'is served from\n'
            '  | assets/video/hero-1080p.mp4. Nightly DB backups go to the NAS '
            '(see ops/backup.md);\n'
            '  | backups/ only holds manual dumps. Logs rotate weekly via '
            'logrotate.\n'
            'calls: read_file',
        260,
      ),
      StepSpec(
        'modelCall',
        'Step 5: drafting the cleanup report',
        '. thinking (step 5, try 1)\n'
            'window ~3,180 tokens, temperature 0.2\n'
            'The reply builds the report text from the pinned note and the README:\n'
            '  1. db-2025-12-01.sql, 412.6 MB: manual dump; nightly backups '
            'are on the NAS. Archive, then remove.\n'
            '  2. hero-4k.mov, 188.0 MB: source video; the site serves the '
            '1080p copy. Move to shared storage.\n'
            '  3. access.log, 96.3 MB: logrotate is not running (still '
            'growing). Fix rotation.\n'
            '  4. app.bundle.js.map, 41.8 MB: build output, regenerated by '
            'npm run build.\n'
            '  5. fonts-unused.zip, 22.5 MB: not in the README, untouched '
            'since March 2025.\n'
            'Saving it will use mine.write_file, which stops for your OK.',
        26400,
      ),
    ],
  ),

  // b) AWAITING_APPROVAL: paused at the real y/N prompt before a file write.
  SessionSpec(
    task: "Summarise this week's meeting notes in ~/Documents/meetings into "
        '~/Documents/weekly-summary.md',
    status: 'awaitingApproval',
    route: 'TASK 0.50 via rules',
    startedMinutesAgo: 11,
    steps: [
      StepSpec(
        'plan',
        'Routed to the local model',
        '> route  TASK 0.50 via rules\n'
            'The request names a folder and a file, so it goes to tier 2.\n'
            'mode: tools',
        30,
      ),
      StepSpec(
        'modelCall',
        'Step 1: the model writes a block',
        '. thinking (step 1, try 1)\n'
            'window ~1,380 tokens, temperature 0.2',
        12100,
      ),
      StepSpec(
        'toolCall',
        "Find this week's notes",
        '> code\n'
            '  | notes = mine.find_files("*.md", "~/Documents/meetings")\n'
            '  | print(notes)\n'
            '< output\n'
            "  | ['~/Documents/meetings/2026-11-16-standup.md', "
            "'~/Documents/meetings/2026-11-18-client-review.md', "
            "'~/Documents/meetings/2026-11-20-planning.md']\n"
            'calls: find_files',
        240,
      ),
      StepSpec(
        'modelCall',
        'Step 2: the model writes a block',
        '. thinking (step 2, try 1)\n'
            'window ~1,560 tokens, temperature 0.2',
        16800,
      ),
      StepSpec(
        'toolCall',
        'Read the three notes',
        '> code\n'
            '  | texts = [mine.read_file(n, 1500) for n in notes]\n'
            '  | for n, t in zip(notes, texts):\n'
            '  |     print(n, len(t))\n'
            '< output\n'
            '  | ~/Documents/meetings/2026-11-16-standup.md 812\n'
            '  | ~/Documents/meetings/2026-11-18-client-review.md 1342\n'
            '  | ~/Documents/meetings/2026-11-20-planning.md 1164\n'
            'calls: read_file x3',
        390,
      ),
      StepSpec(
        'modelCall',
        'Step 3: the model writes the summary',
        '. thinking (step 3, try 1)\n'
            'window ~2,840 tokens, temperature 0.2',
        24600,
      ),
      StepSpec(
        'approvalRequest',
        'Wants to create ~/Documents/weekly-summary.md',
        'The assistant wants to: create ~/Documents/weekly-summary.md\n'
            '        > # Week of 16 Nov 2026\n'
            '        > - Standup: release moved to 2 Dec; QA owns the '
            'regression pass.\n'
            '        > - Client review: Acme approved the... (1,284 chars)\n'
            '  Allow this? [y/N]\n'
            'calls: write_file (gated: nothing is written until you say y)',
        0,
      ),
    ],
  ),

  // c) DONE: a completed request with its final answer.
  SessionSpec(
    task: 'Find my PDF files in Downloads and tell me the biggest',
    status: 'done',
    route: 'TASK 0.50 via rules',
    outcome: 'answered',
    answer: 'The biggest is ~/Downloads/vendor-contract-2026.pdf (18.4 MB). '
        'You have 9 PDFs in Downloads, 41.7 MB in total.',
    startedMinutesAgo: 38,
    steps: [
      StepSpec(
        'plan',
        'Routed to the local model',
        '> route  TASK 0.50 via rules\n'
            'The request names a folder, so it goes to tier 2.\n'
            'mode: tools',
        30,
      ),
      StepSpec(
        'modelCall',
        'Step 1: the model writes a block',
        '. thinking (step 1, try 1)\n'
            'window ~1,350 tokens, temperature 0.2',
        14900,
      ),
      StepSpec(
        'toolCall',
        'Find and size the PDFs',
        '> code\n'
            '  | files = mine.find_files("*.pdf", "downloads")\n'
            '  | info = [mine.file_info(f) for f in files]\n'
            '  | info.sort(key=lambda i: i["size"], reverse=True)\n'
            '  | print(len(files), sum(i["size"] for i in info))\n'
            '  | print(info[0]["path"], info[0]["size_text"])\n'
            '< output\n'
            '  | 9 43726118\n'
            '  | ~/Downloads/vendor-contract-2026.pdf 18.4 MB\n'
            'calls: find_files, file_info x9',
        610,
      ),
      StepSpec(
        'modelCall',
        'Step 2: the model answers',
        '. thinking (step 2, try 1)\n'
            'window ~1,520 tokens, temperature 0.2',
        9800,
      ),
      StepSpec(
        'result',
        'Answered',
        'The biggest is ~/Downloads/vendor-contract-2026.pdf (18.4 MB). You '
            'have 9 PDFs in Downloads, 41.7 MB in total.\n'
            'outcome: answered, mode: tools, 1 step, 2 model calls, '
            'peak ~1,520 tokens, 25.4 s\n'
            'logged to ~/.local/state/mineos/runs/2026-11-22.jsonl',
        0,
      ),
    ],
  ),

  // d) FAILED: the agent never runs anything as root, and stops when stuck.
  SessionSpec(
    task: 'Install the latest Docker on this machine',
    status: 'failed',
    route: 'TASK 0.50 via rules',
    outcome: 'stuck',
    answer: 'I kept hitting the same problem, so I stopped: the agent does '
        'not run anything as root; ask the user to run it themselves '
        '(line 1).',
    startedMinutesAgo: 87,
    steps: [
      StepSpec(
        'plan',
        'Routed to the local model',
        '> route  TASK 0.50 via rules\nmode: tools',
        30,
      ),
      StepSpec(
        'modelCall',
        'Step 1: the model writes a block',
        '. thinking (step 1, try 1)\n'
            'window ~1,330 tokens, temperature 0.2',
        11200,
      ),
      StepSpec(
        'error',
        'Refused: sudo',
        '> code\n'
            '  | print(mine.run("sudo apt install -y docker.io"))\n'
            '! the agent does not run anything as root; ask the user to run '
            'it themselves (line 1)\n'
            '~ retrying: step 1, try 2, temperature 0.55',
        15,
      ),
      StepSpec(
        'modelCall',
        'Step 1: the model tries again',
        '. thinking (step 1, try 2)\n'
            'window ~1,410 tokens, temperature 0.55',
        11900,
      ),
      StepSpec(
        'error',
        'Refused again: sudo',
        '> code\n'
            '  | print(mine.run("sudo apt-get install docker.io"))\n'
            '! the agent does not run anything as root; ask the user to run '
            'it themselves (line 1)\n'
            '~ retrying: step 1, try 3, temperature 0.90',
        15,
      ),
      StepSpec(
        'modelCall',
        'Step 1: last try',
        '. thinking (step 1, try 3)\n'
            'window ~1,450 tokens, temperature 0.90',
        12400,
      ),
      StepSpec(
        'error',
        'Refused a third time',
        '> code\n'
            '  | print(mine.run("sudo snap install docker"))\n'
            '! the agent does not run anything as root; ask the user to run '
            'it themselves (line 1)\n'
            'The same error came back on every try, so the turn ends as '
            'STUCK.',
        15,
      ),
      StepSpec(
        'result',
        'Stopped: stuck',
        'I kept hitting the same problem, so I stopped: the agent does not '
            'run anything as root; ask the user to run it themselves '
            '(line 1).\n'
            'outcome: stuck, mode: tools, 0 steps, 3 model calls, 35.6 s\n'
            'Nothing was changed on the machine.',
        0,
      ),
    ],
  ),
];
