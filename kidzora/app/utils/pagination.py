"""Lightweight pagination helper for Supabase PostgREST queries."""
from __future__ import annotations
from dataclasses import dataclass, field
from math import ceil
from flask import request


_DEFAULT_PER_PAGE = 20


@dataclass
class Pagination:
    """Holds a single page of results plus metadata for the template."""
    items:       list
    page:        int
    per_page:    int
    total:       int
    # computed
    pages:       int      = field(init=False)
    has_prev:    bool     = field(init=False)
    has_next:    bool     = field(init=False)
    prev_num:    int      = field(init=False)
    next_num:    int      = field(init=False)

    def __post_init__(self):
        self.pages    = ceil(self.total / self.per_page) if self.per_page else 1
        self.has_prev = self.page > 1
        self.has_next = self.page < self.pages
        self.prev_num = self.page - 1
        self.next_num = self.page + 1

    def iter_pages(self, left_edge=2, right_edge=2, left_current=2, right_current=2):
        """Yield page numbers (or None for ellipsis gaps) suitable for a page list."""
        last = 0
        for num in range(1, self.pages + 1):
            in_left    = num <= left_edge
            in_right   = num > self.pages - right_edge
            in_current = abs(num - self.page) <= max(left_current, right_current)
            if in_left or in_right or in_current:
                if last and num - last > 1:
                    yield None      # ellipsis
                yield num
                last = num


def paginate_list(items: list, per_page: int = _DEFAULT_PER_PAGE) -> Pagination:
    """Paginate a plain Python list (already fetched from DB).

    Reads ``page`` from the current request query-string (default 1).
    Use this when the full list is already in memory (small datasets, filtered
    in Python).  For large tables prefer ``paginate_query`` instead.
    """
    page = _get_page()
    total = len(items)
    start = (page - 1) * per_page
    return Pagination(
        items    = items[start : start + per_page],
        page     = page,
        per_page = per_page,
        total    = total,
    )


def paginate_query(query, per_page: int = _DEFAULT_PER_PAGE) -> Pagination:
    """Paginate a Supabase PostgREST query builder.

    Adds ``.count('exact')``, then fetches only the current page via
    ``.range(start, end)`` so the DB only returns *per_page* rows.

    Args:
        query:    A Supabase query builder (before ``.execute()``).
        per_page: Rows per page.

    Returns:
        A :class:`Pagination` object.
    """
    page  = _get_page()
    start = (page - 1) * per_page
    end   = start + per_page - 1          # PostgREST range is inclusive

    try:
        result = query.range(start, end).execute()
        items  = result.data or []
        # supabase-py exposes count when count='exact' was set on the query builder
        total  = result.count if result.count is not None else len(items)
    except Exception:
        items = []
        total = 0

    return Pagination(items=items, page=page, per_page=per_page, total=total)


# ── helpers ────────────────────────────────────────────────────────────────

def _get_page() -> int:
    try:
        p = int(request.args.get('page', 1))
        return max(p, 1)
    except (TypeError, ValueError):
        return 1
