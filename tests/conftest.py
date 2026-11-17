"""Alat bantu tes: Google Sheets PALSU di memori.

Tes di folder ini TIDAK nyentuh Google Sheets asli, Telegram, atau bot yang
lagi jalan. Semua data dibuat & dibuang di memori tiap tes.
Cara jalanin (dari folder repo):  pip install -r requirements-dev.txt && pytest
"""
import os
import re
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sheets_client as sc  # noqa: E402


def _cell(v):
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return "" if v is None else str(v)


def _a1(a1):
    m = re.fullmatch(r"([A-Z]+)(\d+)", a1)
    col = 0
    for ch in m.group(1):
        col = col * 26 + (ord(ch) - 64)
    return int(m.group(2)), col


class FakeWorksheet:
    """Tiruan gspread.Worksheet: cuma method yang dipakai sheets_client."""

    def __init__(self, title, headers):
        self.title = title
        self.rows = [list(headers)]

    def get_all_values(self, *a, **kw):
        lebar = max(len(r) for r in self.rows)
        return [list(r) + [""] * (lebar - len(r)) for r in self.rows]

    def row_values(self, n, *a, **kw):
        return list(self.rows[n - 1]) if n <= len(self.rows) else []

    def append_row(self, row, **kw):
        self.rows.append([_cell(v) for v in row])

    def append_rows(self, rows, **kw):
        for r in rows:
            self.append_row(r)

    def _set(self, r, c, v):
        while len(self.rows) < r:
            self.rows.append([])
        row = self.rows[r - 1]
        row.extend([""] * (c - len(row)))
        row[c - 1] = _cell(v)

    def update_cell(self, r, c, v):
        self._set(r, c, v)

    def batch_update(self, data, **kw):
        for d in data:
            r0, c0 = _a1(d["range"].split(":")[0])
            for i, vals in enumerate(d["values"]):
                for j, v in enumerate(vals):
                    self._set(r0 + i, c0 + j, v)

    def delete_rows(self, start, end=None):
        del self.rows[start - 1:(end or start)]


class FakeSpreadsheet:
    def __init__(self):
        self.tabs = {name: FakeWorksheet(name, headers) for name, headers in sc.SCHEMA.items()}

    def worksheet(self, name):
        return self.tabs[name]


@pytest.fixture
def sheets():
    """SheetsClient yang nyambung ke spreadsheet palsu (kosong, cuma header)."""
    c = sc.SheetsClient.__new__(sc.SheetsClient)
    c.sh = FakeSpreadsheet()
    c._lock = threading.Lock()
    c._ws_objs = {}
    c._data_cache = {}
    c._cache_lock = threading.Lock()
    return c


@pytest.fixture
def tab(sheets):
    """tab('Kas') -> list dict isi tab itu sekarang."""
    def _tab(name):
        return sheets._records(sheets._ws(name))
    return _tab
