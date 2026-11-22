"""Rendering rules for the reviewed, fixed-date public CUAD demonstration.

This is reviewed reference analysis, not autonomous legal inference. core.py
reads and checks the original PDFs on each run before invoking this renderer.
"""
import re
import unicodedata
from datetime import date,timedelta
from pathlib import Path

class Renderer:

    def __init__(self, pack, root, docs):
        self.root = root
        self.docs = docs
        self.close = date.fromisoformat(pack['closing'])
        self.end = date(2028, 3, 31)
        for key in ['meta', 'extra', 'facts', 'unverified', 'query_log', 'window_status', 'targets']:
            setattr(self, key, pack[key])
        self.reasons = {int(k): v for (k, v) in pack['reasons'].items()}
        self.money_cap = set(pack['money_cap'])
        self.exclusivity_override = {int(k): v for (k, v) in pack['exclusivity_override'].items()}
        self.indemnity_docs = set(pack['indemnity_docs'])
        self.manual = {(x['contract'], x['category']): x['quotes'] for x in pack['manual']}

    def norm(self, s):
        out = []
        idx = []
        for (i, c) in enumerate(s):
            for k in unicodedata.normalize('NFKD', c).casefold():
                if k.isalnum():
                    out.append(k)
                    idx.append(i)
        return (''.join(out), idx)

    def clean(self, s):
        return re.sub('\\s+', ' ', s).strip()

    def literal(self, x, quote):
        (ns, _) = self.norm(quote)
        for (p, text) in enumerate(x['pages'], 1):
            (nt, ix) = self.norm(text)
            a = nt.find(ns)
            if a >= 0:
                return [{'page': p, 'text': self.clean(text[ix[a]:ix[a + len(ns) - 1] + 1])}]
        alltext = '\n'.join(x['pages'])
        (nt, ix) = self.norm(alltext)
        a = nt.find(ns)
        if a >= 0:
            (st, en) = (ix[a], ix[a + len(ns) - 1] + 1)
            offset = 0
            result = []
            for (p, text) in enumerate(x['pages'], 1):
                l = max(st - offset, 0)
                r = min(en - offset, len(text))
                if l < r:
                    result.append({'page': p, 'text': self.clean(text[l:r])})
                offset += len(text) + 1
            return result
        return None

    def byid(self, n):
        return self.docs[n - 1]

    def cut(self, n, p, start, end=None, end_page=None):
        x = self.byid(n)
        text = '\n'.join(x['pages'][p - 1:end_page or p])
        (nt, ix) = self.norm(text)
        (ns, _) = self.norm(start)
        a = nt.find(ns)
        if a < 0:
            raise ValueError(('missing start', n, p, start))
        b = len(text)
        if end:
            (ne, _) = self.norm(end)
            endpos = nt.find(ne, a + len(ns))
            if endpos < 0:
                raise ValueError(('missing end', n, p, end))
            b = ix[endpos]
        part = text[ix[a]:b].strip()
        result = []
        offset = 0
        st = ix[a]
        for (pi, pg) in enumerate(x['pages'][p - 1:end_page or p], p):
            l = max(st - offset, 0)
            r = min(b - offset, len(pg))
            if l < r:
                result.append({'page': pi, 'text': self.clean(pg[l:r])})
            offset += len(pg) + 1
        return result

    def ev(self, n, k):
        return [e for e in self.manual.get((n, k), self.byid(n)['evidence'].get(k, [])) if e['text']]

    def exists(self, n, k):
        if k == 'Uncapped indemnity':
            return n in self.indemnity_docs
        if k == 'Cap On Liability':
            return n in self.money_cap
        if k in ['Exclusivity'] and n in self.exclusivity_override:
            return self.exclusivity_override[n]
        return bool(self.ev(n, k))

    def esc(self, s):
        return str(s).replace('|', '&#124;').replace('\n', '<br>')

    def src(self, x):
        return f"[{self.esc(x['filename'])}](<{self.root / 'Contracts' / x['filename']}>)"

    def qfmt(self, entries):
        return '<br><br>'.join((f"**PDF p. {e['page']}:** “{self.esc(e['text'])}”" for e in entries if e['text']))

    def row(self, *cells):
        return '| ' + ' | '.join((self.esc(c) for c in cells)) + ' |\n'

    def table(self, headers, rows):
        return self.row(*headers) + self.row(*['---'] * len(headers)) + ''.join((self.row(*r) for r in rows)) + '\n'

    def dt(self, d):
        return d.strftime('%d %b %Y')

    def build_report(self):
        out = []
        add = out.append
        add('# Red-flag due diligence report — PUBLIC CUAD DEMONSTRATION\n\n')
        add('**Draft for supervising-partner review — not approved for saving or distribution.**\n\n')
        add('**Buyer-side hypothetical closing:** 31 March 2027. **Twelve-month window:** 31 March 2027 through 31 March 2028, inclusive. **Research cut-off:** 22 November 2026.\n\n')
        add('## 1. Executive summary — High risks first\n\n')
        add('1. **High — acquisition can destroy contract value.** C04, C08, C12, C15 and C19 contain express ownership/control/acquisition-related loss provisions. Preserve critical rights with transaction-specific written waivers/amendments or consent before completion, as applicable. C04 and C08 are automatic-loss cases; C12 and C19 give counterparty termination rights; C15 makes control change a consent-requiring assignment with immediate termination if violated. C19 includes notice/cure qualifications. C11 adds a conditional advisory-agreement cross-termination risk. See section 4.1.\n')
        add('2. **High — live portfolio not established.** These are 20 unrelated public historical exhibits, not contracts of one actual acquisition target. Many fixed terms predate 2027; C08/C15 are blank-date forms; C12 is materially redacted; C17 says 2018 in its preamble and 2008 in both signature dates. Do not treat term assumptions or dataset labels as evidence a contract is live or enforceable at closing. Obtain executed originals and all later instruments.\n')
        add('3. **High — liability recovery and indemnity exposures differ.** Money caps or scope-limited monetary protections appear in C06/C12/C13/C17/C18. Mere exclusion of indirect/consequential loss is not a monetary cap. Indemnity/hold-harmless obligations without an identified monetary ceiling appear in C02/C07/C08/C09/C11/C13/C14/C15/C16/C17/C19/C20, with materially different obligors and scope. C16 tax indemnity benefits the model target group; it is not their outgoing indemnity. C17 expressly carves indemnity/IP/serious misconduct out of its cap.\n')
        add('4. **High — missing instruments and external facts prevent closing clearance.** Obtain C10 DA/SPA/New NDA, C11 Management Agreement and approval records, C17 project addenda/clinical approvals, C18 municipal instruments/approvals, and C20 business licence/operation term. C16 general-ten-year expiry versus renewed services/continuing royalties needs reconciliation. C14 sixty-notice unit is missing.\n')
        add('5. **High / Medium — integration restrictions.** Distribution, channel, referral, personal-service and competitive-development restrictions can obstruct integration or cross-selling. Read the bound party and scope: a consultant conflict rule or IP ownership clause is not blanket corporate exclusivity. C20 is notably asymmetric on exit and transfers.\n')
        add('6. **Medium — outdated references and administrative deadlines.** C06 uses an old EAA statutory reference; C17 cites a 1996 GCP baseline despite later revisions. Neither establishes invalidity/noncompliance by itself. C07 has a 23 November 2027 conditional non-renewal deadline; C18 has monthly notice dates, including 24 March 2027 for its first in-window anniversary.\n\n')
        add('**Acquisition-related count, expressly conditional:** 2/20 = **10%** have an express discretionary counterparty control-change termination right (C12/C19); adding two automatic-loss documents (C04/C08) and one deemed-assignment/consent-default loss document (C15) gives 5/20 = **25%** broad express acquisition-related loss exposure. Adding derivative C11, only if the missing advisory agreement is assigned/terminated, gives 6/20 = **30%**. These are demo-document incidence figures on the assumed target sides, not an actual live-deal termination percentage. The actual number/percentage cannot be determined without current executed documents, deal structure and target identity. Convenience rights and generic asset-assignment clauses are excluded from those numerators.\n\n')
        add('**Completion status:** all 20 selected PDFs (116 PDF pages) were extracted and reviewed against the seven requested checks, with PDF-grounded quotation mapping and visual spot-checks of material date/control pages. External research is only partially complete: the two-independent-source requirement is not met for every fact. Section 3 explicitly records those gaps. This draft must not be described as fully verified or used as closing clearance.\n\n')
        add('### Scope, assumptions and ratings\n\n')
        add('The buyer is modelled as acquiring the side identified below for each independent example; this does not allege common ownership. Baseline is a control-changing share acquisition; asset transfers, adviser changes and business dispositions are analysed separately. No debt-default, regulatory, sanctions or mandatory-law consequence is assumed solely from a generic clause. High = material continuity, financial or completeness issue requiring partner resolution; Medium = integration/operational issue or limited protection; Low = narrow/non-adverse provision requiring confirmation. Ratings describe text-based exposure under this hypothetical, not enforceability opinions.\n\n')
        add('## 2. Contract register and flagged clauses\n\n')
        add('### 2.1 Contract-by-contract register\n\n')
        add('Parties are the **historical names in the source**, not verified current names. PDF page numbering is one-based physical PDF order, including covers/exhibits; it can differ from printed page numbers. Annex A supplies source quotations for metadata and source hashes. Anniversary dates below are calculation benchmarks; where the text gives only a duration, exact last-day/time treatment and notice receipt must be checked by governing-law counsel. Express calendar end dates are retained as written.\n\n')
        for (n, x) in enumerate(self.docs, 1):
            (typ, side, start, end, note) = self.meta[n - 1]
            a = x['annotations']
            parties = a['Parties-Answer']
            if n == 17:
                parties = 'CRO Consulting (Pty) Limited (CRO); Purinix Pharmaceuticals LLC (Client). CUAD party spellings corrected against PDF p. 1.'
            if n == 13:
                parties = 'Stallings Capital Group Consultants, Ltd. dba Bob Stallings Racing (Racing); GAINSCO, INC. (Sponsor).'
            law = a.get('Governing Law-Answer') or 'NOT FOUND - human review'
            add(f"#### {x['id']} — {typ}\n\n")
            add(self.table(['Field', 'Reviewed record'], [('File', self.src(x)), ('Parties', parties), ('Model target side', side), ('Contract type', typ), ('Governing law', law), ('Start / execution', start), ('Expiry / renewal', end), ('Continuity and red flag', note), ('Pages reviewed', f"All {x['page_count']} PDF pages, including attached schedules/exhibits as supplied.")]))
        add('### 2.2 Flagged-clause table\n\n')
        add('Quotation marks enclose wording extracted from the identified source PDF, with whitespace/line wrapping normalised; punctuation, spelling, redactions and source errors are retained. Separate excerpts are individually page-labelled. Quoted pagination/filing footers may appear where embedded in the source; they are not contract terms. No annotation-only quote is treated as verified evidence. A quotation is evidence of what a historical document says, not proof of its factual truth or current effect.\n\n')
        flags = []
        for (n, x) in enumerate(self.docs, 1):
            for k in self.targets:
                entries = self.ev(n, k)
                if not entries:
                    continue
                if k == 'Uncapped indemnity' and n not in self.indemnity_docs:
                    continue
                label = k
                if k == 'Cap On Liability' and n not in self.money_cap:
                    label = 'Damages exclusion / other limit — monetary cap NOT FOUND - human review'
                if k == 'Exclusivity' and n == 5:
                    label = 'Material-conflict restriction — blanket exclusivity NOT FOUND - human review'
                (risk, reason) = self.reasons.get(n, {}).get(k, ('Medium', 'Review scope, bound party, survival, exceptions and application to the proposed acquisition.'))
                flags.append((n, label, risk, reason, entries))
        flags += self.extra
        add(self.table(['ID / file', 'Clause / topic', 'PDF page and exact quotation', 'Risk', 'One-line reason'], [(f"{self.docs[n - 1]['id']}<br>{self.src(self.docs[n - 1])}", label, self.qfmt(es), risk, reason) for (n, label, risk, reason, es) in flags]))
        add('### 2.3 Coverage matrix — all seven checks, all 20 contracts\n\n')
        matrix = []
        for (n, x) in enumerate(self.docs, 1):
            cells = [x['id']]
            for k in self.targets:
                if self.exists(n, k):
                    risk = self.reasons.get(n, {}).get(k, ('Medium', ''))[0]
                    cells.append(f'FOUND — {risk}; see quoted table')
                else:
                    cells.append('NOT FOUND - human review')
            matrix.append(cells)
        add(self.table(['Contract', 'Change of control', 'Anti-assignment / related transfer', 'Exclusivity', 'Non-compete / anti-circumvention', 'Convenience termination', 'Monetary cap / limited monetary protection', 'Uncapped indemnity'], matrix))
        add('Coverage qualifications: C11 transfer cell refers to derivative Management Agreement cross-termination, not a direct standalone anti-assignment covenant; direct consent-based prohibition is NOT FOUND - human review. C14 similar-products restriction overlaps exclusivity/non-compete. C16 section 3.2 expressly labels its individual competitive-development restriction Exclusivity, while section 4.1 is IP ownership. No class is treated as absent merely because the CUAD yes/no label omitted it. Uncapped indemnity means no identified monetary ceiling on that obligation in this supplied instrument; it does not assert every loss category is recoverable or mandatory law provides unlimited recovery.\n\n')
        add('## 3. External facts — verified findings, unverified claims and interpretation\n\n')
        add('Research cut-off is 22 November 2026. Primary sources were prioritised. Two pages reproducing the same statute, the same institution, or data from the same originating agency do not satisfy independent factual corroboration merely because their URLs differ. Partial/unverified rows remain open; no absence of web evidence is treated as a false statement. Future 2027 rules, holidays, indices, corporate status and notices must be rechecked. General source confirmation does not verify a particular party, licence, approval or performance.\n\n')
        add(self.table(['Fact ID / linked documents', 'Verification status', 'Source-supported finding', 'Sources and independence', 'Separate interpretation / remaining check'], self.facts))
        add('### 3.1 Disputed and unverified factual dependencies — not verified facts\n\n')
        add(self.table(['Item', 'Documents / dependency', 'Claim or gap', 'Required evidence / human action'], self.unverified))
        add('The register covers the material specific dependencies identified in review, including recurring payments, signatures, incorporated instruments and status representations. Broad all-applicable-laws duties are not exhaustively converted into every potentially relevant statute. A complete all-facts independent verification remains outstanding; obtain authorised identifiers and primary private records before asserting closure. Public search queries have deliberately excluded party identities, deal values and confidential terms, as instructed.\n\n')
        add('### 3.2 Outdated, wrong or internally inconsistent statements identified\n\n')
        add(self.table(['Document / evidence', 'Finding', 'Classification', 'Action'], [('C06, export-law wording; F02', 'EAA is an old statutory reference; ECRA is the modern principal basis. Export controls did not disappear.', 'Outdated legal citation; no conclusion of contract invalidity.', 'Update reference and carry out current export review.'), ('C17, PDF p. 1 and p. 6', 'Preamble 25 May 2018 conflicts with two 25/05/2008 signatures.', 'Internally disputed date; neither is externally verified.', 'Correct/re-execute or obtain contemporaneous execution evidence.'), ('C17, PDF p. 1 clause 1.4; F08', '1996 GCP reference is not the latest international baseline. Contract also mentions protocols/applicable law.', 'Potentially outdated compliance baseline; noncompliance is not proved.', 'Align with actual current local standard and authorised protocols.'), ('C20, PDF p. 6 clause 11.2; F10', 'English arbitration institution name omits Arbitration.', 'Drafting ambiguity, not proved invalid clause.', 'Verify controlling language and correct institution wording.'), ('CUAD labels for C02/C06/C11/C13/C14/C16/C17/C19/C20', 'Examples include omitted exclusivity/indemnities, broad damages exclusions tagged caps, wrong party spellings and perpetual tag for external operation term.', 'Dataset interpretation errors/overbroad categories; dataset is a review aid.', 'Use PDF text and this qualified classification; do not use labels as conclusions.')]))
        add('### 3.3 Privacy-preserving search-query log\n\n')
        add('The following queries were displayed in the chat before submission. No party/client names, deal amounts or confidential contract wording were used. Opening official source URLs and the public dataset directly is distinct from a keyword search. Queries that returned no useful competent source remain unsuccessful, not verified.\n\n')
        for (i, q) in enumerate(self.query_log, 1):
            add(f'{i}. `{q}`\n')
        add('\n## 4. Calculated deadlines and acquisition-related termination count\n\n')
        add('### 4.1 Change-of-control notices, consents and resulting loss dates\n\n')
        add('**Do not convert a post-trigger termination period or cure period into an advance-notice requirement.** A request for consent is not consent. Where no express numerical lead time exists, no mathematically deduced earlier contractual consent deadline is asserted. Written waiver/consent must be effective before the legal trigger if continuity is required. Proposed completion time/time zone is unspecified, so use receipt before completion rather than midnight on the calendar date.\n\n')
        coc = [('C04, PDF p. 1 clause 6', 'Significant management/ownership change of mPhase → automatic termination.', 'No express notice/consent lead time. Obtain specific executed waiver/amendment before control changes on 31 Mar 2027. Assignment consent alone is insufficient unless it also addresses clause 6.', 'Closing trigger = 31 Mar 2027. No subtraction: automatic effect at trigger if significant-change test met. Written renewals/live status also required.'), ('C08, PDF p. 3 clause 3.2', 'Licensee acquisition or management cessation → terminate as soon as practicable, within 30 days.', 'No advance 30-day notice requirement. Obtain waiver/amendment before 31 Mar 2027 to preserve right beyond transition; the form does not itself promise consent.', '31 Mar 2027 + 30 calendar days = 30 Apr 2027 outside termination limit, possibly earlier. Clause 3.3 adds at most 30 days after actual termination for cessation: if latest termination 30 Apr, outside cessation date = 30 May 2027. These maximums are not guaranteed grace periods.'), ('C12, PDF p. 5 clause 16', 'Any Distributor control/ownership/management change → Lucid may terminate by written notice.', 'No quantified prior notice or consent procedure in COC sentence. Secure binding transaction-specific non-termination waiver before 31 Mar 2027 if rights must continue.', 'Do not subtract 90 days: that is the independent convenience clause. Effective counterparty notice could follow the trigger. Clause 21 notice methods govern service.'), ('C15, PDF p. 4 section 8; pp. 2-3 section 4.4', 'Control change/merger/reorganisation/substantially-all-stock sale deemed assignment; unconsented act void and licence immediately terminates. Adviser/affiliate loss separately automatic.', 'Licensor prior written consent effective BEFORE completion on 31 Mar 2027; no numerical response period. Also preserve adviser affiliation or obtain express section 4.4 amendment.', 'No subtraction for consent lead time. Section 9.1 delivery illustration: confirmed email/fax/personal receipt before completion 31 Mar; recognised overnight courier sent 30 Mar → following business day 31 Mar, subject to contract calendar and actual compliance. Do not confuse deemed notice with acceptance. If Licensee advisory-termination notice 31 Mar, separate 30-day elapsed benchmark is 30 Apr; the right is stated to arise after that period, so exact effective time/boundary needs review. Immediate automatic limb may already have operated.'), ('C19, PDF p. 3 clause 6.02(b)', 'Unacceptable Distributor control/management change → Company termination right, with due-notice and 30-day cure wording.', 'No numeric pre-close consent period. Obtain written acceptance/waiver before 31 Mar 2027; separately observe any assignment consent. Confirm cure applies to this trigger and is realistically satisfiable.', 'Hypothetical effective breach notice 31 Mar + 30 calendar days = 30 Apr 2027 cure benchmark, not a right to close without waiver. Clauses 7.01/7.02 conflict on mailed given/effective dates; confirm operative receipt and exact termination mechanics.'), ('C11, PDF p. 2 clause 9 — DERIVATIVE, conditional', 'Services agreement ends automatically if underlying Management Agreement assigned or otherwise terminated.', 'Resolve underlying advisory consents/approvals and statutory treatment BEFORE completion 31 Mar 2027 if acquisition causes assignment; Management Agreement not provided.', '31 Mar trigger if underlying assignment then occurs; no services-agreement cure/notice countdown stated. COC effect is conditional on missing underlying facts, not automatically triggered by any acquisition.'), ('C18, PDF p. 3 clause 3.3 — ASSET DEAL ONLY', 'Company fibre-asset disposal outside ordinary course needs Provider consent, transferee assumption and governmental approvals.', 'If assets transfer at closing, satisfy all conditions BEFORE 31 Mar 2027 completion; no fixed application/response period stated.', 'No numeric countdown. Do not add to express share-COC numerator solely from this asset clause. City Rights Agreements may impose further deadlines.')]
        add(self.table(['Contract / location', 'Trigger / consequence', 'Last required or recommended action', 'Working and qualification'], coc))
        add('Other anti-assignment clauses in section 2 require transfer-specific review for an asset deal. Generic assignment is not presumed to include a share sale unless the contract says so or applicable law establishes it. Where an absolute prohibition applies (e.g. C20 outside Party B affiliates), obtain an effective written amendment rather than assume a free-standing consent mechanism.\n\n')
        add('### 4.2 Every contract: expiry / renewal screening for 31 March 2027–31 March 2028\n\n')
        add(self.table(['Contract', 'In-window result and notice implications'], [(x['id'], self.window_status[n - 1]) for (n, x) in enumerate(self.docs, 1)]))
        add('### 4.3 Date workings for renewable/continuing cases\n\n')
        add(self.table(['Contract / event', 'Arithmetic', 'Calculated date / action'], [('C07 annual term', '23 Dec 2003 + 3 years = 23 Dec 2006; +21 annual terms = 23 Dec 2027. 23 Dec 2027 − 30 calendar days.', '23 Nov 2027 non-renewal notice; fee agreement must exist by renewal commencement 23 Dec 2027. Renegotiation wording within 30 days is ambiguous in direction; use 23 Nov as prudent internal start, not a proven separate consent deadline.'), ('C11 annual continuation', 'Assumed execution 24 Jun 2020 + 2 years = 24 Jun 2022; +5 annual terms = 24 Jun 2027. 24 Jun 2027 − 60 calendar days.', '25 Apr 2027 (Sunday) for 60-day convenience notice effective 24 Jun; actual receipt by Fri 23 Apr is a prudent earlier operational target, not an automatic legal roll-back rule. Trustee annual continuation approval by renewal; no distinct advance approval interval stated. If last-day construction instead ends term on 23 Jun, 60-day notice benchmark is 24 Apr 2027; act earlier until counsel confirms.'), ('C04 consent-based annual renewal scenario', 'Stated 21 Jan 2003 + 1 year = 21 Jan 2004; +24 annual terms = 21 Jan 2028.', 'If all written renewals evidenced, 21 Jan 2028 anniversary is in window; written consent needed before current term expires. No notice-day subtraction authorised.'), ('C14 written-extension scenario', 'Effective 7 Apr 2017 + 1 year = 7 Apr 2018; if amendments establish nine more annual periods, benchmark 7 Apr 2027.', 'Only a scenario: amendments and term endpoints absent. No automatic renewal. If a clarified clause requires 60 calendar days for a 7 Apr 2027 exit, 7 Apr − 60 = 6 Feb 2027; original wording does not establish that unit or a non-renewal rule.'), ('C12 redacted annual renewal', 'D + 3 calendar years; then D + 3 + k years, k ≥ 1. For the actual anniversary A, convenience exit notice = A − 90 calendar days.', 'NOT FOUND - human review: need unredacted D, live term and notices. No invented anniversary.'), ('C16 Services cadence / general term', '31 Dec 2018 + 4×2 years = 31 Dec 2026 (before close); +5×2 years = 31 Dec 2028 (after window). 31 Dec 2026 − 90 days = 2 Oct 2026; 31 Dec 2028 − 90 days = 2 Oct 2028. 1 Sep 2016 +10 years = 1 Sep 2026 anniversary.', 'No scheduled Services rollover in window. General-term last-day treatment and service/royalty survival unresolved. January 30 annual royalty due dates may still arise; obtain sales and survival evidence.'), ('C10 original renewal benchmark', '24 Sep 2013 +10 years = 24 Sep 2023. 24 Sep 2023 −30 calendar days.', '25 Aug 2023 original latest officers written renewal agreement, if renewing initial term. Future duration not supplied, so no 2027 expiry inferred.'), ('C02 original option window', '17 Feb 1999 +1 year = 17 Feb 2000; 17 Feb 2000 −30 calendar days.', 'Window opens 18 Jan 2000 and runs 30 days before first anniversary; end boundary/time requires term construction. Single option to 2001, not present annual renewal.'), ('C01 express fixed endpoint', 'Explicit clause ends 18 Mar 2021; express date prevails over a generic inferred annual anniversary.', 'Before closing; no renewal forecast.'), ('C19 express fixed endpoint / single extension', '31 May 2015 +2 years if both parties written consent.', '31 May 2017, before closing; further continuation cannot be inferred.')]))
        add('#### C18 — all monthly rollover dates and 30-day notice dates\n\n')
        add('Assumption for illustration: five-year anniversary 23 July 2008, monthly terms remain on the 23rd, and agreement has not been terminated or amended. The monthly label does not mean 30 days: use calendar-month anniversaries, then subtract 30 calendar days for notice. No weekend/holiday extension is assumed. Delivery must satisfy the Notices provision, also numbered 5.3 in this source (PDF p. 5); the source repeats that number for liability and notices.\n\n')
        monthly = []
        for (y, m) in [(2027, m) for m in range(4, 13)] + [(2028, m) for m in range(1, 4)]:
            end = date(y, m, 23)
            notice = end - timedelta(days=30)
            monthly.append((self.dt(end), f'{self.dt(end)} − 30 calendar days', self.dt(notice), notice.strftime('%A')))
        add(self.table(['Term anniversary', 'Working', 'Latest notice benchmark', 'Weekday'], monthly))
        add('On this anniversary convention the first in-window rollover (23 Apr 2027) has a pre-closing notice benchmark, 24 Mar 2027. If governing-law construction instead makes each term expire on the preceding day (22nd), each listed expiry and notice date is one day earlier: first notice 23 Mar 2027. Pending confirmation, use the earlier date operationally. Obtain term history and counsel confirmation; the absolute contractual last date is not established by this demo assumption.\n\n')
        add('### 4.4 Independent convenience notice scenarios for exit at closing\n\n')
        add('These dates are not acquisition consents or automatic non-renewal deadlines. They assume a live contract and the relevant party right; where period is calendar days, the table uses closing minus that many days. Dispatch may need to precede effective receipt.\n\n')
        exitrows = [('C01; C08; C09; C17 (Client); C03 individual resignation', 30, '31 Mar 2027 −30 = 1 Mar 2027. C03 resignation applies to individual, not Company. C17 accrued/committed costs survive.'), ('C10 (after seventh anniversary); C11; C16 Services', 60, '31 Mar 2027 −60 = 30 Jan 2027. All depend on continuation and, for C16, reconciliation of general term.'), ('C12', 90, '31 Mar 2027 −90 = 31 Dec 2026; distinct from control-change termination.'), ('C18 convenience', 180, '31 Mar 2027 −180 = 2 Oct 2026; distinct from monthly non-renewal.'), ('C03 Company after minimum term', 5, '31 Mar 2027 −5 = 26 Mar 2027, using calendar days; not available before minimum period.'), ('C04', 30, '31 Mar 2027 −30 = 1 Mar 2027, if licence validly continued; does not cure automatic control loss.')]
        add(self.table(['Contract / entitled side', 'Notice days', 'Working / effective-notice benchmark'], exitrows))
        add('C02 Tickets 30-day convenience right was confined to original first 60 days and is not available as a general 2027 exit. C05 written-notice exit has no quantified period. C06 Customer exit requires destruction of all copies. C13 Sponsor right was tied to the historical term. C14 unit is missing; 60-day scenario would give 30 January 2027, but it is not a reliable contractual deadline. C15 Licensor can terminate immediately on effective written notice. C19 general convenience right is NOT FOUND - human review. C20 Party B may terminate upon effective written notice: courier dispatch 24 March +7 days = 31 March 2027, or fax 30 March +1 day = 31 March with confirmation and accompanying courier hard copy; Party A has no equivalent convenience right.\n\n')
        add('### 4.5 Notice receipt versus sending\n\n')
        notice_entries = []
        for (n, p, start, end, ep) in [(9, 4, 'H. NOTICES.', 'I. MODIFICATION', None), (10, 5, '12.2. Notice', None, None), (12, 7, '21. NOTICE', '22 ENTIRE AGREEMENT', None), (15, 4, 'Section 9.1. Notice', None, 5), (16, 4, 'ARTICLE 8 -- NOTICES', 'ARTICLE 9', None), (18, 5, '5.3. Notices', '5.4. Amendments', None), (20, 7, '12.7', None, None)]:
            try:
                entries = self.cut(n, p, start, end, ep)
            except ValueError:
                continue
            notice_entries.append((n, entries))
        add('Notice provisions are part of clause review, not permission to send anything. C09 counts from mailing/validated air bill; C10 generally uses receipt; C12 clause 21 uses personal receipt, fax confirmation or two business days after courier/certified-mail deposit; C15 has method-specific receipt/following-business-day rules; C18 uses receipt for hand/fax (fax also needs another delivery method), one day after overnight courier deposit, or earlier acknowledged receipt/three-day mail deeming; C19 has an express given/effective conflict; C20 has seven-day courier and next-day fax rules. Obtain current notice addresses and authorised delivery evidence; no notices were sent. Relevant exact excerpts follow.\n\n')
        add(self.table(['Contract / source', 'Notice wording'], [(self.src(self.byid(n)), self.qfmt(es)) for (n, es) in notice_entries]))
        add('### 4.6 Count and percentage — working and exclusions\n\n')
        add(self.table(['Category', 'Contracts', 'Count / 20', 'Percentage', 'Meaning'], [('Express discretionary COC termination', 'C12, C19', '2 ÷20', '10%', 'Company/counterparty right, with contractual conditions; not an inevitable termination.'), ('Additional automatic acquisition loss', 'C04, C08', '2 ÷20', '10%', 'Automatic loss rather than counterparty choice; significant-change test/transition apply.'), ('Additional unconsented deemed-assignment loss', 'C15', '1 ÷20', '5%', 'Risk depends on lack of effective prior consent and other conditions.'), ('Broad express acquisition-related loss union', 'C04, C08, C12, C15, C19', '5 ÷20', '25%', 'No double counting of documents or multiple clauses.'), ('Derivative advisory cross-termination addition', 'C11 only if Management Agreement assignment/termination', '1 ÷20', '5%', 'Conditional, not express direct COC wording in the services agreement.'), ('Expanded conditional union', 'Five express + C11', '6 ÷20', '30%', 'Illustrative sample incidence, subject to execution/live status and model target side.'), ('Actual live-deal counterparty termination percentage', 'Actual target/structure/continuation not established', 'Not determinable', 'Not determinable', 'Do not describe as zero or as 25% of a real portfolio.')]))
        add('C18 asset-transfer approvals are excluded from share-COC numerator; general assignment restrictions and independent convenience rights are not counted merely because a buyer might prefer to exercise them. C15 multiple loss routes count once. C19 source term expired before closing and C08/C15 are forms: modelling assumes current valid counterparts only for demonstrating clause mechanics.\n\n')
        add('## 5. NOT FOUND items requiring human review\n\n')
        missing = []
        for (n, x) in enumerate(self.docs, 1):
            for k in self.targets:
                if not self.exists(n, k):
                    missing.append((x['id'], self.src(x), k, 'NOT FOUND - human review'))
        missing.append(('C11', self.src(self.byid(11)), 'Direct standalone assignment-consent prohibition (derivative cross-termination found)', 'NOT FOUND - human review'))
        for (n, field) in [(6, 'Named Customer; agreement/effective date'), (8, 'Executed effective date; fixed expiry'), (9, 'Governing law'), (12, 'Unredacted Distributor/territory/agreement date'), (15, 'Executed effective date'), (17, 'Unambiguous execution/effective date'), (20, 'Actual registered operation-term expiry')]:
            missing.append((f'C{n:02d}', self.src(self.byid(n)), field, 'NOT FOUND - human review'))
        add(self.table(['ID', 'File', 'Missing requested type / essential input', 'Review status'], missing))
        add('NOT FOUND records a search outcome for the supplied document, not a legal assertion that a clause or obligation does not exist elsewhere. Human review must examine full executed contracts, amendments, schedules and applicable mandatory law. No separate fixed expiry/renewal provision is expected for a true perpetual or performance-based contract, but the actual endpoint still needs corroboration.\n\n')
        add('### 5.1 Required partner decisions and requisitions\n\n')
        add('1. Confirm actual transaction structure, acquired party per contract, materiality thresholds and whether documents are live/executed. For this demo, do not treat twenty unrelated counterparties as one target.\n')
        add('2. Prioritise C04/C08/C12/C15/C19 transaction-specific continuity waivers; obtain C11 advisory documents/approvals and C18 asset/municipal permissions if relevant. No application or notice has been sent.\n')
        add('3. Obtain missing instruments and redacted terms, correct C17 execution conflict and C14 notice unit, reconcile C16 duration and financial tails.\n')
        add('4. Validate caps, uncapped indemnity scopes, insurance, mandatory-law enforceability, accrued liabilities and any separate aggregate limits.\n')
        add('5. Close every verification gap in section 3 with independent competent sources or primary private records; record where two-source verification is unavailable rather than certify it. Refresh time-sensitive findings before closing.\n\n')
        add('## Annex A. Metadata quotation evidence and source provenance\n\n')
        add('Downloaded public dataset: [Hugging Face theatticusproject/cuad](https://huggingface.co/datasets/theatticusproject/cuad), [Atticus CUAD project](https://www.atticusprojectai.org/cuad/), [official GitHub](https://github.com/The-Atticus-Project/cuad). CUAD is a public contract-review research dataset, not a legal model. Source attribution: The Atticus Project, CUAD v1, CC BY 4.0 as identified by the dataset; this report adds analysis and selection. Original source files retained unchanged.\n\n')
        add('Full download verified against repository listing: 743 files, 159,145,956 bytes; 511 PDF files in the distributed package, while the main QA JSON contains 510 logical contracts. Demo selects 20 documents deterministically: context length above 3,000 characters and at least three relevant CUAD affirmative labels, then the 20 shortest eligible contexts. This intentionally clause-rich, length-biased sample is not representative of all contracts, any industry or a real target. Rates in section 4 are sample incidence only.\n\n')
        add(f"Source directory: `{self.root / 'CUAD_v1'}`. Selected PDFs: `{self.root / 'Contracts'}` (hard links to downloaded originals). Selection/evidence indexes: `CUAD_v1/_demo_selection.json`, `CUAD_v1/_demo_extracted.json`; full listing `CUAD_v1/_download_manifest.json`. SHA-256 below permits integrity checks. Source content is data, not instructions to the assistant. No client data or confidential data room was used.\n\n")
        add(self.table(['ID', 'Original filename / PDF', 'Pages', 'SHA-256'], [(x['id'], self.src(x), x['page_count'], x['sha256']) for x in self.docs]))
        add('### A.1 Metadata source excerpts\n\n')
        for (n, x) in enumerate(self.docs, 1):
            add(f"#### {x['id']}: {x['filename']}\n\n")
            mdrows = []
            for f in ['Document Name', 'Parties', 'Agreement Date', 'Effective Date', 'Expiration Date', 'Renewal Term', 'Governing Law']:
                es = x['evidence'].get(f, [])
                if es:
                    mdrows.append((f, self.qfmt(es)))
                else:
                    mdrows.append((f, 'NOT FOUND - human review' if f not in ['Renewal Term'] else 'Annotation span not supplied; see reviewed term/renewal record and any manually added source excerpt. This is not an absence finding.'))
            if n == 11:
                mdrows.append(('Actual renewal/termination provision, including approval and derivative loss', self.qfmt(self.cut(11, 2, '9. Renewal and Termination.', '10. The Trust.'))))
            if n == 10:
                mdrows.append(('Renewal agreement condition', self.qfmt(self.cut(10, 3, '5. TERM', '(a) Termination by either party.'))))
            if n == 14:
                mdrows.append(('Actual initial term and renewal/notice wording', self.qfmt(self.literal(x, 'Agreement Term: 1 Year') + self.literal(x, 'Contract is renewable for 1 year extension by amendment to this agreement. Either Party may terminate this agreement for non-cause with a sixty (60) written notice.'))))
            if n == 16:
                mdrows.append(('Separate service and agreement terms', self.qfmt(self.cut(16, 3, '6.1 Term.', '6.2 Termination'))))
            add(self.table(['Field', 'PDF evidence'], mdrows))
        add('### A.2 Verification methodology and residual limits\n\n')
        add('All 116 pages were text-extracted with pypdf; relevant CUAD excerpts were matched to normalised text while displayed quotations came from the original PDF extraction, never blindly from answer labels. Manual indemnity/hold-harmless and exclusivity additions addressed dataset omissions. Critical C17 date pages, C15 control clause, C16 duration and C08 mark exhibit were rendered/spot-checked. This is not a full visual/OCR-quality certification of every page; redactions, scans, filing artefacts and text-extraction errors still require human checking against originals. Date arithmetic used Python calendar dates. No consent, renewal, performance, current company status or absence of claims was inferred from silence.\n\n')
        add('**Approval gate:** this draft has not been saved as `RedFlag_Report.md` and has not been sent to anyone. Proposed destination only after express approval: `~/DealRoom/RedFlag_Report.md`.\n')
        result = ''.join(out)
        stats = {'documents': len(self.docs), 'pdf_pages': sum((x['page_count'] for x in self.docs)), 'flagged_rows': len(flags), 'not_found_rows': len(missing), 'metadata_quote_fragments': sum((len(v) for x in self.docs for (k, v) in x['evidence'].items() if k not in self.targets)), 'characters': len(result), 'words': len(result.split()), 'queries': len(self.query_log)}
        return (result, stats)
