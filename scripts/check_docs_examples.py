#!/usr/bin/env python3
"""Run the python blocks of a Markdown page and compare each result with its comment.

A comment run directly under a ``print(...)`` call or a bare expression states
the output: the printed text, or the ``repr`` of the value, with or without
quotes. A trailing comment on the same line does the same. It may carry a note
after the output, set off by a dash with spaces around it or by two spaces and
an opening parenthesis. Blocks of one page share a namespace. Blocks fenced
``python`` or ``py`` run. Fence code that must not run as ``text``.

A page fails when a block does not parse, when a statement raises, or when a
comment states an output under a statement the script cannot compare (only
``print`` calls, bare expressions and ``for`` loops show output).

    python scripts/check_docs_examples.py README.md docs/quickstart.md
"""

from __future__ import annotations

import ast
import contextlib
import io
import re
import sys

BLOCK = re.compile(r"^```(?:python|py)\n(.*?)^```", re.S | re.M)


NOTE = re.compile(r"(?:\s+—\s|\s{2,}[-(]).*$", re.S)


def stated(lines: list[str], stmt: ast.stmt) -> str | None:
    """The output a statement's comments claim, or None when it claims none."""
    tail = lines[stmt.end_lineno - 1]
    if stmt.end_lineno == stmt.lineno and "  # " in tail:
        return NOTE.sub("", tail.split("  # ", 1)[1].strip())
    out = []
    for line in lines[stmt.end_lineno:]:
        text = line.strip()
        if not text.startswith("#"):
            break
        out.append(NOTE.sub("", text[1:].removeprefix(" ")))
    return "\n".join(out) if out else None


def check(path: str) -> tuple[int, int]:
    checked = failed = 0
    scope: dict = {"__name__": "__docs__"}
    with open(path, encoding="utf-8") as fh:
        page = fh.read()
    for block in BLOCK.findall(page):
        lines = block.splitlines()
        try:
            body = ast.parse(block).body
        except SyntaxError as err:
            checked += 1
            failed += 1
            print(f"{path}: block does not parse: {err}")
            continue
        for stmt in body:
            source = ast.Module([stmt], [])
            is_print = (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Call)
                and getattr(stmt.value.func, "id", "") == "print"
            )
            claim = stated(lines, stmt)
            if claim is not None and not isinstance(stmt, (ast.Expr, ast.For)):
                checked += 1
                failed += 1
                print(f"{path}:{stmt.lineno}: comment under a statement that shows no output")
                continue
            buf = io.StringIO()
            accepted: set[str] = set()
            try:
                with contextlib.redirect_stdout(buf):
                    if claim is not None and isinstance(stmt, ast.Expr) and not is_print:
                        value = eval(compile(ast.Expression(stmt.value), path, "eval"), scope)
                        accepted = {repr(value)}
                        if isinstance(value, str):
                            accepted |= {value, f'"{value}"'}
                    else:
                        exec(compile(source, path, "exec"), scope)
            except Exception as err:
                if claim is None:
                    checked += 1
                    failed += 1
                    print(f"{path}: {ast.unparse(stmt)[:70]!r} raised {type(err).__name__}: {err}")
                    continue
                accepted = {f"{type(err).__name__}: {err}"}
            if claim is None:
                continue
            checked += 1
            got = buf.getvalue().rstrip("\n")
            accepted.add(got)
            if "\n" not in got:
                accepted |= {repr(got), f'"{got}"'}
            if claim not in accepted:
                failed += 1
                print(f"{path}:{stmt.lineno}: {ast.unparse(stmt)[:70]!r} stated {claim!r}, got {got or sorted(accepted)[0]!r}")
    return checked, failed


def main() -> int:
    total = failed = 0
    for path in sys.argv[1:]:
        n, bad = check(path)
        print(f"{path}: {n} outputs checked, {bad} differ")
        total += n
        failed += bad
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
