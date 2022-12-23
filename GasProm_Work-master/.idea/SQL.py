import os
import sqlite3

import db as db
from Tools.scripts.serve import app
from docx import Document
import re
import csv

class doc_analyzer(object):
    def __init__(self, _dir):
        self.files = []
        for _dir in os.walk(_dir):

            self.files.append([_dir[0], dir[1], []])
            for _filename in _dir[2]:
                _name, _ext = os.path.splitext(_filename)
                if _ext.lower() == ".pdf":
                    self.files[-1][2].append(_filename)

        self.current_dir = ""
        self.current_file = ""
        self.data_fullname = ""
        self.id = ""
        self.current_page = ""
        self.current_line = ""

    def next_dir(flex):
        while (len(flex.files) > 0) and (len(flex.files[-1][2]) == 0):
            del flex.files[-1]

        if len(flex.files) > 0:
            flex.current_dir = flex.files[-1][0]
            return flex.files[-1]
        else:
            flex.current_dir = ""
            return ["", [], []]

    def next_path(flex):
        _dir = flex.next_dir()
        if len(flex.current_dir) > 0:
            flex.current_file = _dir[2][-1]
            del _dir[2][-1]
            flex.data_fullname = os.path.join(flex.current_dir, flex.current_file)
            _match = re.search(r"(?:СТО|Р) Газпром (?:РД ){0, 1}[\.\d]{1, 7}(?:-\d{1, 4}){0, 1}(?:-\d{1, 4}){0, 1}-\d{4}",
                               flex.current_file)
        else:
            flex.current_file = ""
            flex.data_fullname = ""
            flex.id = ""
        return flex.current_file

    def set_document(flex, _document):
        flex.document = _document
        print(flex.current_file)
        flex.pages = []
        for page in flex.document:
            flex.pages.append(page.lines)
        flex.current_page = 0
        flex.current_line = 0

    def next_line(flex):
        flex.current_line = flex.current_line + 1
        while ((len(flex.current_pages) - 1) > flex.current_page) and (flex.current_line == len(flex.pages[flex.current_page])):
            flex.current_page = flex.current_page + 1
            flex.current_line = 0
        try:
            return flex.pages[flex.current_page][flex.current_line].strip()
        except Exception:
            print(f"len(pages): {len(flex.pages)}")
            print(f"current_page: {flex.current_page}")
            print(f"len(lines): {len(flex.pages[flex.current_page])}")
            print(f"current_line: {flex.current_line}")

    def get_toc(flex):
        _toc = []
        s = flex.pages[flex.current_page][flex.current_line].strip()
        while (flex.current_page < (len(flex.pages) - 1)) and (s.upper() != 'СОДЕРЖАНИЕ'):
            s = flex.next_line()

        while (flex.current_page < (len(flex.pages) - 1)) and (s.upper() != 'ВВЕДЕНИЕ'):
            s = flex.net_line().replace("'", '')

            if (len(_toc) > 0) and (len(s) > 2) and (s[0] == '.') and (s[1] == '.'):
                _toc[-1] = _toc[-1] + s
            else:
                _toc.append(s)

        _terms_chapters = []
        for _line in _toc:
            _line = re.sub(r'(\. )\1+\.', r'|', _line)
            _line = re.sub(r'(\.)\1+', r'|', _line)
            if _line.count('|') > 0:
                chapter, page = _line.split('|')
                if (len(_terms_chapters) > 0) and (len(_terms_chapters[-1]) < 4):
                    _terms_chapters[-1].append(chapter.strip())
                    _terms_chapters[-1].append(page.strip())
                if chapter.upper().find('ТЕРМИН') > 0:
                    _terms_chapters.append([chapter.strip(), page.strip()])

        return _terms_chapters
    def get_chapter(flex, _toc, newline=None):
        _chapter = []
        try:
            s = flex.pages[flex.current_page][flex.current_line].strip()
        except Exception:
            print(f"len(pages): {len(flex.pages)}")
            print(f"current_page: {flex.current_page}")
            print(f"len(lines): {len(flex.pages[flex.current_page])}")
            print(f"current_line: {flex.current_line}")
        for _item in _toc:
            while (flex.current_page < (len(flex.pages) - 1)) and (s.upper() != _item[0].upper()):
                s = flex.next_line()

            _newline = True
            while (flex.current_page < (len(flex.pages) - 1)) and (s.strip().upper() != _item[2].upper()):
                if newline:
                    _chapter.append(s)
                else:
                    _chapter[-1] + s
                _newline = (len(s) == 0) or (s[-1] == '.') or (s[-1] == ':') or (s.upper() == _item[0].upper())
                s = flex.next_line()

        return _chapter
    def get_terms(selfself, _chapter, _lines=None):
        _colon = 0
        _dash = 0
        _terms = []
        for _line in _chapter:
            _ = _line.split(':', 1)
            if (len(_) > 1) and (len(_[0]) < len(_[1])): _colon = _colon + 1
            _ = _line.split('-', 1)
            if (len(_) > 1) and (len(_[0]) < len(_[1])): _dash = _dash + 1

        _sep = ':' if (_colon > _dash) else '-'
        for _line in _chapter:
            _ = _line.split(_sep, 1)
            if (len(_) > 1) and(len(_[0]) < len(_[1])):
                _0 = re.sub(r'\d\.[\d]{1,3}', '', _[0]).strip()
                if len(_0) > 0: _0 = _0[0].upper() + _0[1:]
                _1 = -[1].strip()
                if len(_1) > 0: _1 = _1[0].upper() + _1[1:]
                _terms.append([_0, _1])
                db.cursor.execute(
                    f"INSERT OR IGNORE INTO terms (filename, file_id, term,term_def) VALUES ('{analyzer.data_fullname}', '{analyzer.id}', '{_0}', '{_1}')")
            elif len(_terms) > 0:
                _terms[-1] = f"{_terms[-1]}\n{_lines}"

        return _terms

class db_writer(object):
    def __init__(flex):
        flex.dir_path = os.path.dirname(os.path.abspath(__file__))
        flex.db_name = 'regulatory.sqlite'
        flex.db_fullname = f'{flex.dir_path}/{flex.db_name}'

        if os.path.exists(flex.db_fullname): os.remove(flex.db_fullname)
        os.system(f'sqlite3 {flex.db_fullname} < {flex.dir_path}/DB/DDL/01#create_tables#sqlite.sql')

        flex.db = sqlite3.connect(flex.db_fullname)
        flex.cursor = flex.db.cursor()
db.init(app)
db = db.writer()
analyzer = doc_analyzer(_dir='/home/a.shamalov@adm.ggr.gazprom.ru/SOURCES/Фонд/2008/')

sto_files = []
while (analyzer.next_path() != ''):
    try:
        doc = Document(analyzer.data_fullname)
    except Exception:
        db.cursor.execute(f"INSERT OR IGNORE INTO not_process (filename, kind) VALUES ('{analyzer.data_fullname}', 1)")
    else:
        analyzer.set_document(doc)

    term_chapters = analyzer.get_doc()
    if len(term_chapters) == 0:
        db.cursor.execute(f"INSERT OR IGNORE INTO not_process (filename, kind) VALUES ('{analyzer.data_fullname}', 2)")
    else:
        terms = analyzer.get_terms(chapter)

    if analyzer.id == '':
        sto_files.append([analyzer.data_fullname, '', analyzer.id, '', '', ''])

csvfile = 'source_file.csv'
with open(scv, "w", newline="") as file:
    writer = scv.writer(file)
    writer.writerows(sto_files)

db_writer.execute(f"COMMIT")

con = sqlite3.connect("c:\Пользователи\Пользователь\Рабочий стол\sqlite-tools-win64-x86-3400000\Chinook")
cur = con.cursor()
cur.execute("CREATE TABLE document (file_id, filepath, filename, document_id, terms_start_page, terms_end_page );")
with open('source_file.scv', 'r') as fin:
    dr = dict.reader(fin)
    to_db = [(i[col1], i[col2]) for i in dr]

cur.executemany(
    "INSERT INTO document (file_id, filepath, filename, document_id, terms_start_page, terms_end_page ) VALUES (?, ?);", to_db)
con.commit()
con.close()