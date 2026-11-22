"""Small native GTK review window. Draft content stays in RAM until Save."""
import subprocess
import threading
from pathlib import Path

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GLib, Gtk, Pango

from .core import Cancelled, generate, pack_data, save
from .intent import DEFAULT_PROMPT, validate

CSS = b'''
window {background:#111820;color:#e7eff6;font-family:Inter,sans-serif;font-size:16px;}
headerbar {background:#18232e;color:#f1f6fa;border:0;box-shadow:none;}
label.title {font-size:26px;font-weight:700;} label.muted {color:#9fb0be;}
label.section {color:#77dbbc;font-size:12px;font-weight:700;}
label.metric {font-size:30px;font-weight:700;color:#edf9f6;}
.card {background:#1a2733;border-radius:12px;padding:16px;}
.sidebar {background:#15202a;padding:20px;border-radius:12px;}
button {background:#223343;color:#e7eff6;border:1px solid #3a4d5e;border-radius:7px;padding:8px 15px;box-shadow:none;text-shadow:none;}
button.suggested-action {background:#78dfbb;color:#0d2822;border-color:#78dfbb;font-weight:700;}
button:disabled {opacity:0.42;} textview,textview text {background:#17232e;color:#e6eef5;}
textview {padding:12px;font-size:14px;} notebook header {background:#111820;}
notebook tab {padding:10px 18px;} treeview {background:#17232e;color:#e7eff6;font-size:13px;}
treeview:selected {background:#2d4a59;color:white;} progressbar trough {background:#263b48;border:0;min-height:7px;border-radius:5px;}
progressbar progress {background:#78dfbb;min-height:7px;border-radius:5px;}
'''


class ReviewWindow(Gtk.Window):
    def __init__(self, root, prompt, autorun=False):
        super().__init__(title='Mino · Deal Review')
        self.set_default_size(1120, 820)
        self.set_size_request(900, 650)
        self.root = root
        self.draft = None
        self.saved = None
        self.busy = False
        self.closed = False
        self.cancel = threading.Event()
        self.connect('destroy', self.on_close)
        provider = Gtk.CssProvider();provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER+1)
        self.provider = provider
        header = Gtk.HeaderBar(title='Mino Deal Review', subtitle='Public CUAD demo');header.set_show_close_button(False)
        self.set_titlebar(header)
        close_button=Gtk.Button(label='×');close_button.set_tooltip_text('Close')
        close_button.connect('clicked',lambda *_: self.destroy());header.pack_end(close_button)
        self.view_button = Gtk.Button(label='View saved report');self.view_button.set_sensitive(False)
        self.view_button.connect('clicked', lambda *_: self.open_path(self.saved[1]) if self.saved else None)
        header.pack_end(self.view_button)
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24, margin=24)
        self.add(outer)
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        side.get_style_context().add_class('sidebar');side.set_size_request(230, -1);outer.pack_start(side,False,False,0)
        self.label(side, 'PUBLIC CUAD DEMO', 'section')
        self.label(side, '20 contracts\nOne review.', 'title')
        self.label(side, 'Buyer-side acquisition\nClosing 31 March 2027', 'muted')
        self.stage_labels=[]
        for title in ['1  Read original PDFs', '2  Check reviewed clauses', '3  Calculate deadlines', '4  Preview and save']:
            self.stage_labels.append(self.label(side,title,'muted'))
        self.label(side,'Reviewed public-source analysis.\nRuns locally without an API key.','muted')
        self.label(side,'Research snapshot\n22 November 2026','muted')
        self.folder = self.label(side,str(root),'muted');self.folder.set_line_wrap(True);self.folder.set_max_width_chars(25)
        folder_button=Gtk.Button(label='Open DealRoom');folder_button.connect('clicked',lambda *_: self.open_path(root))
        side.pack_end(folder_button,False,False,0)
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14);outer.pack_start(main,True,True,0)
        self.label(main,'Contract due diligence','title')
        self.label(main,'Exact source quotations, risk flags and transparent deadline calculations.','muted')
        prompt_scroll=Gtk.ScrolledWindow();prompt_scroll.set_min_content_height(115)
        self.prompt=Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.prompt.get_buffer().set_text(prompt or DEFAULT_PROMPT);prompt_scroll.add(self.prompt);main.pack_start(prompt_scroll,False,False,0)
        controls=Gtk.Box(spacing=10);main.pack_start(controls,False,False,0)
        self.run_button=Gtk.Button(label='Generate review');self.run_button.get_style_context().add_class('suggested-action')
        self.run_button.connect('clicked',self.start);controls.pack_start(self.run_button,False,False,0)
        self.stop_button=Gtk.Button(label='Stop');self.stop_button.set_sensitive(False)
        self.stop_button.connect('clicked',lambda *_: self.cancel.set());controls.pack_start(self.stop_button,False,False,0)
        self.save_button=Gtk.Button(label='Save report…');self.save_button.set_sensitive(False)
        self.save_button.set_tooltip_text('Approve saving Markdown and HTML reports to DealRoom')
        self.save_button.connect('clicked',self.save_report);controls.pack_end(self.save_button,False,False,0)
        self.progress=Gtk.ProgressBar(show_text=True);self.progress.set_text('Ready · 20 public contracts');main.pack_start(self.progress,False,False,0)
        metrics=Gtk.Box(spacing=12);main.pack_start(metrics,False,False,0);self.metrics=[]
        for title in ['Contracts checked','Pages reviewed','Flagged entries']:
            card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=3);card.get_style_context().add_class('card')
            metric=self.label(card,'—','metric');self.label(card,title,'muted');self.metrics.append(metric);metrics.pack_start(card,True,True,0)
        self.tabs=Gtk.Notebook();main.pack_start(self.tabs,True,True,0)
        self.summary=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14,margin=14)
        summary_scroll=Gtk.ScrolledWindow();summary_scroll.add(self.summary)
        self.label(self.summary,'Generate a review to see the priority findings.','muted')
        self.tabs.append_page(summary_scroll,Gtk.Label(label='Summary'))
        self.model=Gtk.ListStore(str,str,str,str)
        for doc in pack_data()['docs']:self.model.append([doc['id'],doc['filename'],str(doc['page_count']),'Waiting'])
        self.tree=Gtk.TreeView(model=self.model);self.tree.set_tooltip_column(1)
        for i,title in enumerate(['ID','Contract','Pages','Status']):
            cell=Gtk.CellRendererText()
            if i==1:cell.set_property('ellipsize',Pango.EllipsizeMode.MIDDLE)
            column=Gtk.TreeViewColumn(title,cell,text=i);column.set_expand(i==1)
            if i==1:column.set_min_width(250)
            self.tree.append_column(column)
        self.tree.connect('row-activated',self.open_contract)
        scroll=Gtk.ScrolledWindow();scroll.add(self.tree);self.tabs.append_page(scroll,Gtk.Label(label='Contracts'))
        report_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
        self.search=Gtk.SearchEntry(placeholder_text='Find in draft…');self.search.connect('activate',self.find_text)
        report_box.pack_start(self.search,False,False,0)
        self.report=Gtk.TextView(editable=False,cursor_visible=True,wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.report.set_left_margin(14);self.report.set_right_margin(14)
        report_scroll=Gtk.ScrolledWindow();report_scroll.add(self.report);report_box.pack_start(report_scroll,True,True,0)
        self.tabs.append_page(report_box,Gtk.Label(label='Full draft'))
        self.status=self.label(main,'No report is saved until you choose Save report.','muted')
        self.status.set_line_wrap(True)
        self.prompt.get_buffer().connect('changed',self.request_changed)
        self.show_all()
        if autorun:GLib.idle_add(self.start)

    def request_changed(self,*_):
        if not self.busy and self.draft:
            self.draft=None
            self.save_button.set_sensitive(False)
            self.progress.set_text('Request changed · generate a new review')
            self.status.set_text('The previous preview is kept for reference. Generate the updated request before saving.')

    def label(self,box,text,style):
        label=Gtk.Label(label=text,xalign=0);label.get_style_context().add_class(style)
        box.pack_start(label,False,False,0);return label

    def open_path(self,path):
        try:subprocess.Popen(['xdg-open',str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except OSError as error:self.status.set_text(str(error))

    def open_contract(self,_tree,path,_column):
        self.open_path(self.root/'Contracts'/self.model[path][1])

    def start(self,*_):
        if self.busy or self.closed:return False
        buf=self.prompt.get_buffer();text=buf.get_text(buf.get_start_iter(),buf.get_end_iter(),True)
        try:validate(text)
        except ValueError as error:self.status.set_text(str(error));return False
        self.busy=True;self.cancel.clear();self.draft=None;self.saved=None
        self.run_button.set_sensitive(False);self.stop_button.set_sensitive(True)
        self.save_button.set_sensitive(False);self.view_button.set_sensitive(False);self.prompt.set_editable(False)
        self.report.get_buffer().set_text('');self.tabs.set_current_page(1)
        for row in self.model:row[3]='Waiting'
        for metric in self.metrics:metric.set_text('0')
        self.status.set_text('Reading public PDFs and checking reviewed source evidence locally…')
        def worker():
            try:
                draft=generate(self.root,lambda event:GLib.idle_add(self.update,event),self.cancel)
                GLib.idle_add(self.finished,draft,None)
            except Exception as error:GLib.idle_add(self.finished,None,str(error))
        threading.Thread(target=worker,daemon=True).start();return False

    def update(self,event):
        if self.closed:return False
        stage=event['stage']
        if stage in ('reading','reviewed'):
            index=event['index'];self.model[index-1][3]='Reading…' if stage=='reading' else 'Checked ✓'
            path=Gtk.TreePath.new_from_indices([index-1])
            self.tree.get_selection().select_path(path);self.tree.scroll_to_cell(path)
            self.progress.set_fraction((index-1 if stage=='reading' else index)/22)
            self.progress.set_text(f'{index}/20 · {event["id"]} · '+('Reading PDF' if stage=='reading' else 'Source evidence checked'))
            if stage=='reviewed':
                self.metrics[0].set_text(str(index));pages=sum(int(row[2]) for row in list(self.model)[:index]);self.metrics[1].set_text(str(pages))
            self.stage_labels[0].set_text('1  Reading original PDFs')
            self.stage_labels[1].set_text('2  Checking reviewed clauses')
        elif stage=='deadlines':
            self.stage_labels[0].set_text('1  Original PDFs checked ✓');self.stage_labels[1].set_text('2  Source clauses checked ✓')
            self.stage_labels[2].set_text('3  Calculating deadlines…');self.progress.set_fraction(0.95)
        return False

    def finished(self,draft,error):
        if self.closed:return False
        self.busy=False;self.run_button.set_sensitive(True);self.stop_button.set_sensitive(False);self.prompt.set_editable(True)
        if error:
            self.progress.set_text('Stopped' if self.cancel.is_set() else 'Review needs attention')
            self.status.set_text(error);return False
        self.draft=draft;self.save_button.set_sensitive(True);self.progress.set_fraction(1);self.progress.set_text('Draft ready · review before saving')
        for label,title in zip(self.stage_labels,['1  Original PDFs checked ✓','2  Source clauses checked ✓','3  Deadlines calculated ✓','4  Preview ready']):label.set_text(title)
        self.metrics[2].set_text(str(draft.stats['flagged_rows']));self.report.get_buffer().set_text(draft.markdown)
        self.show_summary()
        self.tabs.set_current_page(0)
        self.status.set_text(f'{draft.stats["quote_checks"]} source checks · {draft.stats["not_found_rows"]} NOT FOUND items · {draft.stats["seconds"]:.1f}s. '
                             'External verification gaps are marked. Save creates Markdown + HTML in DealRoom.')
        return False

    def show_summary(self):
        for child in self.summary.get_children():child.destroy()
        label=self.label(self.summary,'High priority · acquisition continuity','section')
        label=self.label(self.summary,'5 of 20 documents contain express acquisition-related loss clauses. '
            'This is conditional demo incidence; current execution and live status remain unverified.','muted')
        label.set_line_wrap(True);label.set_max_width_chars(75)
        pack=pack_data()
        for n,category in [(4,'Change Of Control'),(8,'Change Of Control'),(12,'Change Of Control'),
                           (15,'Change Of Control'),(19,'Change Of Control'),(11,'Anti-Assignment')]:
            card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
            card.get_style_context().add_class('card')
            self.label(card,f'C{n:02d} · '+('Related advisory agreement' if n==11 else 'Control-change clause'),'section')
            reason=pack['reasons'][str(n)][category][1]
            label=self.label(card,reason,'muted');label.set_line_wrap(True);label.set_max_width_chars(70)
            self.summary.pack_start(card,False,False,0)
        label=self.label(self.summary,'Also resolve: C17 conflicting execution dates; C16 agreement/service duration; '
            'C14 missing notice unit. The full draft contains every flagged entry, quotation and deadline.','muted')
        label.set_line_wrap(True);label.set_max_width_chars(75)
        self.summary.show_all()

    def find_text(self,*_):
        term=self.search.get_text()
        if not term:return
        buffer=self.report.get_buffer();start=buffer.get_iter_at_mark(buffer.get_insert())
        found=start.forward_search(term,Gtk.TextSearchFlags.CASE_INSENSITIVE,None)
        if not found:found=buffer.get_start_iter().forward_search(term,Gtk.TextSearchFlags.CASE_INSENSITIVE,None)
        if found:
            begin,end=found;buffer.select_range(begin,end);self.report.scroll_to_iter(begin,0.15,False,0,0)

    def save_report(self,*_):
        if not self.draft or self.busy:return
        exists=any((self.root/name).exists() for name in ['RedFlag_Report.md','RedFlag_Report.html'])
        if exists:
            dialog=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.NONE,text='Replace the existing demo reports?')
            dialog.format_secondary_text('This saves the reviewed Markdown and HTML draft in DealRoom. Source PDFs stay in place.')
            dialog.add_buttons('Cancel',Gtk.ResponseType.CANCEL,'Replace reports',Gtk.ResponseType.OK)
            yes=dialog.run()==Gtk.ResponseType.OK;dialog.destroy()
            if not yes:return
        try:self.saved=save(self.draft,approved=True,overwrite=exists)
        except Exception as error:self.status.set_text(f'Could not save: {error}');return
        self.view_button.set_sensitive(True)
        self.status.set_text('Saved to '+str(self.saved[0])+'. View saved report opens the readable HTML version.')

    def on_close(self,*_):
        self.closed=True;self.cancel.set()
        Gtk.StyleContext.remove_provider_for_screen(self.get_screen(),self.provider)
        Gtk.main_quit()


def main(root:Path,prompt:str='',autorun:bool=False):
    ReviewWindow(root,prompt,autorun);Gtk.main();return 0
