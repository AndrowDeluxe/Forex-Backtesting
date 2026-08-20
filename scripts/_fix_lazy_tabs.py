"""One-off migration script (2026-08-20, Streamlit Cloud memory-limit
incident): converts `st.tabs()` pages from "all tabs render every rerun" to
lazy rendering via `on_change="rerun"` + `.open` guards, matching the fix
already hand-applied to app_pages/portfolio_construction.py. Static-checks
each tab body for cross-tab variable dependencies (a name loaded in one
tab's body that's only ever assigned inside a DIFFERENT tab's body) before
transforming - those would break silently once tabs stop unconditionally
co-executing. Files that fail the check, or whose st.tabs() usage doesn't
match the plain "sequential `with tab_x:` blocks at column 0" shape, are
left untouched and reported for manual handling.

Usage: python scripts/_fix_lazy_tabs.py [--apply]
Without --apply: dry-run, reports per-file safety verdict only.
"""

import ast
import builtins
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP_PAGES = REPO / "app_pages"
BUILTIN_NAMES = set(dir(builtins))


def find_tabs_calls(tree: ast.Module):
    """Yields (assign_node, call_node, target_kind, names) for each
    top-level `... = st.tabs(...)` assignment. target_kind is 'names' for
    `a, b = st.tabs(...)` or 'single' for `tabs = st.tabs(...)`."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        call = node.value
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and call.func.attr == "tabs" and isinstance(call.func.value, ast.Name)
                and call.func.value.id == "st"):
            continue
        if len(node.targets) != 1:
            continue
        tgt = node.targets[0]
        if isinstance(tgt, ast.Tuple) and all(isinstance(e, ast.Name) for e in tgt.elts):
            yield node, call, "names", [e.id for e in tgt.elts]
        elif isinstance(tgt, ast.Name):
            yield node, call, "single", [tgt.id]


def module_level_names(tree: ast.Module) -> set[str]:
    """Names bound by TOP-LEVEL module statements only (not descending into
    any `with`/`for`/`if`/function body) - imports, plain assignments
    (includes the tab variables themselves, e.g. `tab_x, tab_y = st.tabs(...)`
    is an ordinary top-level Assign like any other), top-level for-loop
    targets, and function defs. This is everything a `with tab_x:` block
    could legitimately have relied on regardless of tab order, since it's
    set once before any tab body runs - as opposed to a name first assigned
    INSIDE some other tab's body, which only a coincidence of top-to-bottom
    execution order made visible in the original flat script."""
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        names.add(n.id)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    names.add(n.id)
        elif isinstance(node, ast.With):
            for item in node.items:
                if item.optional_vars is not None:
                    for n in ast.walk(item.optional_vars):
                        if isinstance(n, ast.Name):
                            names.add(n.id)
    return names


def locally_bound_names(wnode: ast.With) -> set[str]:
    """Names bound WITHIN this tab's body via any mechanism other than a
    plain `Name(ctx=Store)` - comprehension/lambda/def parameters, `except
    ... as e`, `with ... as x` - so they aren't mistaken for cross-tab
    references to another tab's body."""
    bound = set()
    for n in ast.walk(wnode):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            args = n.args
            for group in (args.posonlyargs, args.args, args.kwonlyargs):
                bound.update(a.arg for a in group)
            if args.vararg:
                bound.add(args.vararg.arg)
            if args.kwarg:
                bound.add(args.kwarg.arg)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                bound.add(n.name)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            bound.add(n.name)
        elif isinstance(n, ast.comprehension):
            for t in ast.walk(n.target):
                if isinstance(t, ast.Name):
                    bound.add(t.id)
        elif isinstance(n, ast.withitem) and n.optional_vars is not None:
            for t in ast.walk(n.optional_vars):
                if isinstance(t, ast.Name):
                    bound.add(t.id)
    return bound


def analyze_file(path: Path):
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    calls = list(find_tabs_calls(tree))
    if not calls:
        return None
    if len(calls) > 1:
        return {"path": path, "ok": False, "reason": f"{len(calls)} separate st.tabs() calls - needs manual review"}
    assign_node, call_node, kind, names = calls[0]

    with_blocks = []  # (label, with_node) in source order, column-0 only
    if kind == "names":
        wanted = set(names)
        for node in tree.body:
            if isinstance(node, ast.With) and node.col_offset == 0 and len(node.items) == 1:
                ctx = node.items[0].context_expr
                if isinstance(ctx, ast.Name) and ctx.id in wanted:
                    with_blocks.append((ctx.id, node))
    else:  # single name, expect `with tabs[i]:`
        base = names[0]
        for node in tree.body:
            if isinstance(node, ast.With) and node.col_offset == 0 and len(node.items) == 1:
                ctx = node.items[0].context_expr
                if (isinstance(ctx, ast.Subscript) and isinstance(ctx.value, ast.Name)
                        and ctx.value.id == base and isinstance(ctx.slice, ast.Constant)):
                    with_blocks.append((f"{base}[{ctx.slice.value}]", node))

    if len(with_blocks) < 2:
        return {"path": path, "ok": False, "reason": f"found {len(with_blocks)} matching `with` blocks (expected >=2) - needs manual review"}

    mod_names = module_level_names(tree)

    problems = []
    for label, wnode in with_blocks:
        assigned, loaded = set(), set()
        for n in ast.walk(wnode):
            if isinstance(n, ast.Name):
                if isinstance(n.ctx, ast.Store):
                    assigned.add(n.id)
                elif isinstance(n.ctx, ast.Load):
                    loaded.add(n.id)
        assigned |= locally_bound_names(wnode)
        unresolved = loaded - assigned - mod_names - BUILTIN_NAMES
        if unresolved:
            problems.append((label, sorted(unresolved)))

    return {
        "path": path, "ok": not problems, "reason": problems if problems else "safe",
        "assign_node": assign_node, "call_node": call_node, "kind": kind,
        "names": names, "with_blocks": with_blocks, "src": src,
    }


def transform(info: dict) -> str:
    src = info["src"]
    lines = src.splitlines(keepends=True)
    call = info["call_node"]

    # Insert on_change="rerun" right before the call's closing paren.
    end_l, end_c = call.end_lineno - 1, call.end_col_offset
    line = lines[end_l]
    insert_at = end_c - 1  # position of the closing ')'
    lines[end_l] = line[:insert_at] + ', on_change="rerun"' + line[insert_at:]

    # Replace each `with <ctx>:` line with `def _render_tab_<label>():`.
    render_names = {}
    for label, wnode in info["with_blocks"]:
        safe = "".join(c if c.isalnum() or c == "_" else "_" for c in label)
        fname = f"_render_tab_{safe}"
        render_names[label] = fname
        l = wnode.lineno - 1
        indent = " " * wnode.col_offset
        lines[l] = f"{indent}def {fname}():\n"

    src2 = "".join(lines)

    # Dispatch block appended at end of file.
    if info["kind"] == "names":
        pairs = ", ".join(f"({n}, {render_names[n]})" for n in info["names"])
    else:
        base = info["names"][0]
        pairs = ", ".join(f"({base}[{lbl.split('[')[1][:-1]}], {render_names[lbl]})" for lbl in render_names)

    dispatch = (
        "\n\n"
        "# ============================================================ Lazy dispatch\n"
        "# st.tabs() renders ALL tab bodies on every rerun by default, even hidden ones.\n"
        '# on_change="rerun" above makes tab.open reflect the actually-selected tab; only\n'
        "# that one's render function runs now (2026-08-20 Streamlit Cloud memory-limit fix,\n"
        "# see app_pages/portfolio_construction.py for the original instance of this fix).\n"
        f"for _tab, _render in [{pairs}]:\n"
        "    if _tab.open:\n"
        "        with _tab:\n"
        "            _render()\n"
    )
    if not src2.endswith("\n"):
        src2 += "\n"
    return src2 + dispatch


def main():
    apply = "--apply" in sys.argv
    results = []
    for path in sorted(APP_PAGES.glob("*.py")):
        info = analyze_file(path)
        if info is None:
            continue
        results.append(info)

    for info in results:
        rel = info["path"].relative_to(REPO)
        if info["ok"]:
            print(f"OK    {rel}")
        else:
            print(f"SKIP  {rel}: {info['reason']}")

    if not apply:
        print("\nDry run only - pass --apply to write changes.")
        return

    for info in results:
        if not info["ok"]:
            continue
        new_src = transform(info)
        ast.parse(new_src)  # fail loud before writing anything
        info["path"].write_text(new_src, encoding="utf-8")
        print(f"WROTE {info['path'].relative_to(REPO)}")


if __name__ == "__main__":
    main()
