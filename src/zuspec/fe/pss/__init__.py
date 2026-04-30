import os
import re
from dataclasses import dataclass, field as _dc_field
from typing import List, Optional, Union
from pssparser import Parser as _PssParser, ParseException
from .ast_to_ir import AstToIrTranslator, AstToIrContext
from .ir_to_runtime import IrToRuntimeBuilder, ClassRegistry


# ---------------------------------------------------------------------------
# PSS source text-transformation helpers
# ---------------------------------------------------------------------------

def _is_word_char(c: str) -> bool:
    return c.isalnum() or c == '_'


def _scan_comment_or_string(text: str, i: int) -> int:
    """Return end index after a comment or string at i, or -1 if not at one."""
    n = len(text)
    if text[i:i+2] == '//':
        end = text.find('\n', i)
        return n if end == -1 else end + 1
    if text[i:i+2] == '/*':
        end = text.find('*/', i + 2)
        return n if end == -1 else end + 2
    if text[i] == '"':
        j = i + 1
        while j < n and text[j] != '"':
            if text[j] == '\\':
                j += 1
            j += 1
        return min(j + 1, n)
    return -1


def _find_matching_brace(text: str, start: int) -> int:
    """Given text[start] == '{', return index of matching '}'. Returns -1 if not found."""
    n = len(text)
    depth = 0
    i = start
    while i < n:
        end = _scan_comment_or_string(text, i)
        if end != -1:
            i = end
            continue
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _transform_forall_foreach(text: str, stub_body: bool) -> str:
    """Rename the PSS 'forall' keyword to 'foreach' throughout text.

    If stub_body is True, also replace each renamed block's body with
    '{ 0 == 0; }' so the pssparser linker doesn't fail on p.x references.
    If stub_body is False, only rename the keyword (for pass-1 annotation capture).
    """
    result = []
    i = 0
    n = len(text)
    while i < n:
        end = _scan_comment_or_string(text, i)
        if end != -1:
            result.append(text[i:end])
            i = end
            continue

        if (text[i:i+6] == 'forall'
                and (i == 0 or not _is_word_char(text[i-1]))
                and (i+6 >= n or not _is_word_char(text[i+6]))):
            result.append('foreach')
            i += 6

            if stub_body:
                # Copy whitespace before '('
                while i < n and text[i] in ' \t\n\r':
                    result.append(text[i]); i += 1
                # Copy '(...)' verbatim, tracking depth through comments/strings
                if i < n and text[i] == '(':
                    depth = 0
                    while i < n:
                        end2 = _scan_comment_or_string(text, i)
                        if end2 != -1:
                            result.append(text[i:end2]); i = end2; continue
                        c = text[i]
                        result.append(c); i += 1
                        if c == '(':
                            depth += 1
                        elif c == ')':
                            depth -= 1
                            if depth == 0:
                                break
                # Copy whitespace before '{'
                while i < n and text[i] in ' \t\n\r':
                    result.append(text[i]); i += 1
                # Replace body block with trivially-true stub
                if i < n and text[i] == '{':
                    end3 = _find_matching_brace(text, i)
                    if end3 != -1:
                        result.append('{ 0 == 0; }')
                        i = end3 + 1
                    else:
                        result.append(text[i]); i += 1
            continue

        result.append(text[i])
        i += 1
    return ''.join(result)


def _remove_covergroup_blocks(text: str) -> str:
    """Remove PSS 'covergroup { ... } name;' blocks, replacing with '// @ZSP_COV: name'.

    This prevents parse errors from 'cross' declarations, which the pssparser
    grammar does not support. Covergroup metadata is captured separately from
    the original source text by _extract_covergroup_annotations.
    """
    result = []
    i = 0
    n = len(text)
    KW = 'covergroup'
    klen = len(KW)
    while i < n:
        end = _scan_comment_or_string(text, i)
        if end != -1:
            result.append(text[i:end])
            i = end
            continue

        if (text[i:i+klen] == KW
                and (i == 0 or not _is_word_char(text[i-1]))
                and (i+klen >= n or not _is_word_char(text[i+klen]))):
            j = i + klen
            while j < n and text[j] != '{':
                j += 1
            if j >= n:
                result.append(text[i]); i += 1; continue

            end_brace = _find_matching_brace(text, j)
            if end_brace == -1:
                result.append(text[i]); i += 1; continue

            k = end_brace + 1
            while k < n and text[k] in ' \t\n\r':
                k += 1
            name_start = k
            while k < n and _is_word_char(text[k]):
                k += 1
            instance_name = text[name_start:k].strip() or 'cg'
            while k < n and text[k] in ' \t\n\r':
                k += 1
            if k < n and text[k] == ';':
                k += 1

            result.append(f'// @ZSP_COV: {instance_name}\n')
            i = k
            continue

        result.append(text[i])
        i += 1
    return ''.join(result)


def _strip_activity_with_constraints(text: str) -> str:
    """Remove 'with { ... }' inline constraints from PSS activity do-statements.

    The current pssparser grammar does not accept ``do action with { ... }``
    inline constraint syntax in activity bodies.  This pass strips the
    ``with { ... }`` portion so the parser can proceed; the inline constraints
    are silently dropped (a known limitation of the pssparser-based front-end).
    """
    WS = ' \t\n\r'
    result = []
    i = 0
    n = len(text)
    while i < n:
        end = _scan_comment_or_string(text, i)
        if end != -1:
            result.append(text[i:end])
            i = end
            continue

        if (text[i:i+2] == 'do'
                and (i == 0 or not _is_word_char(text[i-1]))
                and (i+2 < n and not _is_word_char(text[i+2]))):
            result.append('do')
            i += 2
            # Copy whitespace and the traversal-target (handles qualified names: a::b::c)
            while i < n and text[i] in WS:
                result.append(text[i]); i += 1
            while i < n:
                if _is_word_char(text[i]):
                    result.append(text[i]); i += 1
                elif text[i:i+2] == '::':
                    result.append('::'); i += 2
                else:
                    break
            # Peek ahead for optional 'with { ... }'
            j = i
            while j < n and text[j] in WS:
                j += 1
            if (text[j:j+4] == 'with'
                    and (j+4 >= n or not _is_word_char(text[j+4]))):
                k = j + 4
                while k < n and text[k] in WS:
                    k += 1
                if k < n and text[k] == '{':
                    end_brace = _find_matching_brace(text, k)
                    if end_brace != -1:
                        # Drop everything from current i up to end of '}'
                        i = end_brace + 1
                        continue
            # No 'with' or couldn't strip — leave pointer at i (after identifier)
            continue

        result.append(text[i])
        i += 1
    return ''.join(result)


def _normalize_fill_blocks(text: str) -> str:
    """Rewrite PSS 'fill { do action ...; }' blocks to plain 'do action;'.

    The current pssparser grammar does not recognise 'do' inside a fill block.
    This pass extracts the action name from the first traversal inside each
    fill block and replaces the entire fill statement with 'do action_name;'.
    All inline constraints and FILL markers are dropped (known limitation).
    """
    WS = ' \t\n\r'
    result = []
    i = 0
    n = len(text)
    KW = 'fill'
    klen = len(KW)

    while i < n:
        end = _scan_comment_or_string(text, i)
        if end != -1:
            result.append(text[i:end])
            i = end
            continue

        # Detect 'fill' keyword
        if (text[i:i+klen] == KW
                and (i == 0 or not _is_word_char(text[i-1]))
                and (i+klen < n and not _is_word_char(text[i+klen]))):
            j = i + klen
            while j < n and text[j] in WS:
                j += 1
            if j < n and text[j] == '{':
                end_brace = _find_matching_brace(text, j)
                if end_brace != -1:
                    body = text[j+1:end_brace]
                    # Extract the first 'do <identifier>' inside the body
                    action_name = _extract_first_do_target(body)
                    if action_name:
                        result.append(f'do {action_name};')
                    # Skip optional trailing ';' after '}'
                    k = end_brace + 1
                    while k < n and text[k] in WS:
                        k += 1
                    if k < n and text[k] == ';':
                        k += 1
                    i = k
                    continue
        result.append(text[i])
        i += 1
    return ''.join(result)


def _extract_first_do_target(body: str) -> str:
    """Return the first action name from 'do <action_name> ...' in body."""
    WS = ' \t\n\r'
    i = 0
    n = len(body)
    while i < n:
        end = _scan_comment_or_string(body, i)
        if end != -1:
            i = end
            continue
        if (body[i:i+2] == 'do'
                and (i == 0 or not _is_word_char(body[i-1]))
                and (i+2 < n and not _is_word_char(body[i+2]))):
            j = i + 2
            while j < n and body[j] in WS:
                j += 1
            start = j
            while j < n and _is_word_char(body[j]):
                j += 1
            name = body[start:j]
            if name:
                return name
        i += 1
    return ''


def _strip_exec_file_blocks(text: str) -> str:
    # Remove PSS exec-file blocks: exec file "name" = triple-quoted-string ;
    # These are non-standard tool-specific blocks pssparser does not recognise.
    import re
    tq = chr(34) * 3  # triple-double-quote
    pattern = r'exec' + r'\s+file\s+"[^"]*"' + r'\s*=\s*' + tq + r'.*?' + tq + r'\s*;'
    return re.sub(pattern, '// @ZSP_STRIPPED: exec_file\n', text, flags=re.DOTALL)


def _preprocess_pss_inject_builtins(text: str) -> str:
    """Inject 'bool initial;' into state bodies and 'int instance_id;' into resource bodies."""
    result = []
    i = 0
    n = len(text)

    while i < n:
        if text[i:i+2] == '//':
            end = text.find('\n', i)
            end = n if end == -1 else end + 1
            result.append(text[i:end])
            i = end
            continue
        if text[i:i+2] == '/*':
            end = text.find('*/', i+2)
            end = n if end == -1 else end + 2
            result.append(text[i:end])
            i = end
            continue
        if text[i] == '"':
            j = i + 1
            while j < n and text[j] != '"':
                if text[j] == '\\': j += 1
                j += 1
            j = min(j + 1, n)
            result.append(text[i:j])
            i = j
            continue

        if text[i] in ('s', 'r'):
            prev = text[i - 1] if i > 0 else '\n'
            if not (prev.isalnum() or prev == '_'):
                for kw, field_decl, field_name in (
                    ('state',    'bool initial;',    'initial'),
                    ('resource', 'int instance_id;', 'instance_id'),
                ):
                    if text[i:i+len(kw)] != kw:
                        continue
                    nxt = text[i+len(kw)] if i+len(kw) < n else ' '
                    if nxt.isalnum() or nxt == '_':
                        continue
                    k = i + len(kw)
                    segment = [kw]
                    while k < n and text[k] != '{':
                        if text[k:k+2] == '//':
                            end = text.find('\n', k)
                            end = n if end == -1 else end + 1
                            segment.append(text[k:end]); k = end
                        elif text[k:k+2] == '/*':
                            end = text.find('*/', k+2)
                            end = n if end == -1 else end + 2
                            segment.append(text[k:end]); k = end
                        else:
                            segment.append(text[k]); k += 1
                    if k >= n:
                        result.append(''.join(segment)); i = k; break
                    body_preview = text[k+1:k+500]
                    already = bool(re.search(
                        r'\b' + re.escape(field_name) + r'\s*;',
                        body_preview,
                    ))
                    segment.append('{')
                    if not already:
                        segment.append('\n    ' + field_decl)
                    result.append(''.join(segment))
                    i = k + 1
                    break
                else:
                    result.append(text[i]); i += 1
                continue

        result.append(text[i])
        i += 1

    return ''.join(result)


def _preprocess_pss(text: str) -> str:
    """Full PSS source pre-processing pipeline (for pass 2 / link pass).

    1. Inject 'bool initial;' / 'int instance_id;' built-in fields.
    2. Remove 'covergroup { ... } name;' blocks.
    3. Rename 'forall' -> 'foreach' and stub bodies with '{ 0 == 0; }'.
    4. Strip unsupported 'do ... with { }' inline activity constraints.
    """
    text = _preprocess_pss_inject_builtins(text)
    text = _strip_exec_file_blocks(text)
    text = _remove_covergroup_blocks(text)
    text = _normalize_fill_blocks(text)
    text = _transform_forall_foreach(text, stub_body=True)
    text = _strip_activity_with_constraints(text)
    return text


def _preprocess_pss_pass1(text: str) -> str:
    """Minimal pre-processing for pass 1 (annotation capture, no link).

    Removes covergroup blocks (to avoid cross parse errors) and renames
    'forall' -> 'foreach' without body stubbing, so the pre-link AST
    preserves the real constraint body nodes.  Also strips unsupported
    'do ... with { }' inline activity constraints.
    """
    text = _strip_exec_file_blocks(text)
    text = _remove_covergroup_blocks(text)
    text = _normalize_fill_blocks(text)
    text = _transform_forall_foreach(text, stub_body=False)
    text = _strip_activity_with_constraints(text)
    return text


# ---------------------------------------------------------------------------
# PssAnnotation side-channel
# ---------------------------------------------------------------------------


def _extract_fill_annotations(text_files) -> 'List[PssAnnotation]':
    """Scan raw PSS source texts for fill activity blocks and return annotations.

    Finds ``fill { do action_name ...; }`` patterns, recording the enclosing
    type chain and traversal target so that ``ActivityFill`` IR nodes can be
    injected during AST-to-IR translation.
    """
    annotations: List[PssAnnotation] = []
    for _fname, text in text_files:
        _scan_text_for_fills(text, annotations)
    return annotations


def _scan_text_for_fills(text: str, annotations: list):
    """State-machine scanner: find fill blocks, track enclosing action names."""
    n = len(text)
    i = 0
    type_stack: list = []   # (keyword, name, brace_depth_at_open)
    brace_depth = 0
    TYPE_KWS = ('component', 'action', 'struct')
    FILL_KW = 'fill'
    fill_klen = len(FILL_KW)

    while i < n:
        end = _scan_comment_or_string(text, i)
        if end != -1:
            i = end
            continue

        c = text[i]
        if c == '{':
            brace_depth += 1
            i += 1
            continue
        if c == '}':
            brace_depth -= 1
            while type_stack and type_stack[-1][2] >= brace_depth:
                type_stack.pop()
            i += 1
            continue

        matched = False
        for kw in TYPE_KWS:
            klen = len(kw)
            if (text[i:i+klen] == kw
                    and (i == 0 or not _is_word_char(text[i-1]))
                    and (i+klen < n and not _is_word_char(text[i+klen]))):
                j = i + klen
                while j < n and text[j] in ' \t\n\r':
                    j += 1
                name_start = j
                while j < n and _is_word_char(text[j]):
                    j += 1
                name = text[name_start:j]
                if name:
                    type_stack.append((kw, name, brace_depth))
                i = j
                matched = True
                break
        if matched:
            continue

        # Check for 'fill' keyword
        if (text[i:i+fill_klen] == FILL_KW
                and (i == 0 or not _is_word_char(text[i-1]))
                and (i+fill_klen < n and not _is_word_char(text[i+fill_klen]))):
            j = i + fill_klen
            while j < n and text[j] in ' \t\n\r':
                j += 1
            if j < n and text[j] == '{':
                end_brace = _find_matching_brace(text, j)
                if end_brace != -1:
                    body_text = text[j+1:end_brace]
                    action_name = _extract_first_do_target(body_text)
                    if action_name:
                        type_chain = [entry[1] for entry in type_stack]
                        annotations.append(PssAnnotation(
                            kind='fill',
                            type_chain=type_chain,
                            data={
                                'action_name': action_name,
                                'max_iters': 1000,
                            },
                        ))
                    i = end_brace + 1
                    continue
        i += 1


@dataclass
class PssAnnotation:
    """Pre-link information extracted alongside the linked AST.

    kind: "forall" or "covergroup"
    type_chain: enclosing type names from outermost inward, e.g. ["pss_top", "test"]

    Forall data keys: iterator (str), collection (list[str]), body_ast (list of AST nodes)
    Covergroup data keys: instance_name (str), coverpoints (list[dict]), crosses (list[dict])
    """
    kind: str
    type_chain: List[str]
    data: dict = _dc_field(default_factory=dict)


# ---------------------------------------------------------------------------
# Forall annotation extraction (pre-link AST walk)
# ---------------------------------------------------------------------------

def _extract_forall_annotations(pss_files) -> List[PssAnnotation]:
    """Walk pssparser pre-link _files to find ConstraintStmtForeach nodes.

    Must be called AFTER parse()/parses() but BEFORE link().
    """
    import pssparser.ast as pss_ast
    annotations: List[PssAnnotation] = []
    for scope in pss_files[1:]:   # skip stdlib at index 0
        _walk_scope_forall(scope, [], annotations, pss_ast)
    return annotations


def _walk_scope_forall(scope, type_chain, annotations, pss_ast):
    for child in scope.children():
        if isinstance(child, pss_ast.Component):
            name = _scope_name(child, pss_ast)
            _walk_scope_forall(child, type_chain + [name], annotations, pss_ast)
        elif isinstance(child, pss_ast.Action):
            name = _scope_name(child, pss_ast)
            _collect_forall_in_type(child, type_chain + [name], annotations, pss_ast)
        elif isinstance(child, pss_ast.Struct):
            name = _scope_name(child, pss_ast)
            _collect_forall_in_type(child, type_chain + [name], annotations, pss_ast)
        elif isinstance(child, pss_ast.PackageScope):
            parts = [child.getId(k).getId() for k in range(child.numId())]
            _walk_scope_forall(child, type_chain + ['::'.join(parts)], annotations, pss_ast)


def _collect_forall_in_type(type_node, type_chain, annotations, pss_ast):
    for child in type_node.children():
        if isinstance(child, pss_ast.ConstraintBlock):
            for idx in range(child.numConstraints()):
                stmt = child.getConstraint(idx)
                if isinstance(stmt, pss_ast.ConstraintStmtForeach):
                    _capture_foreach_annotation(stmt, type_chain, annotations, pss_ast)
        elif isinstance(child, pss_ast.Action):
            name = _scope_name(child, pss_ast)
            _collect_forall_in_type(child, type_chain + [name], annotations, pss_ast)


def _capture_foreach_annotation(stmt, type_chain, annotations, pss_ast):
    it_node = stmt.getIt()
    if it_node is None:
        return
    name_obj = it_node.getName()
    if name_obj is None:
        return
    iterator = name_obj.getId() if hasattr(name_obj, 'getId') else str(name_obj)
    coll_path = _refpath_to_names(stmt.getExpr(), pss_ast)
    body_ast = [stmt.getConstraint(j) for j in range(stmt.numConstraints())]
    annotations.append(PssAnnotation(
        kind='forall',
        type_chain=type_chain,
        data={'iterator': iterator, 'collection': coll_path, 'body_ast': body_ast},
    ))


def _scope_name(node, pss_ast) -> str:
    name_node = node.getName()
    if isinstance(name_node, pss_ast.ExprId):
        return name_node.getId()
    return str(name_node)


def _refpath_to_names(expr, pss_ast) -> List[str]:
    if expr is None:
        return []
    if isinstance(expr, pss_ast.ExprRefPathContext):
        hier_id = expr.getHier_id()
        if hier_id is None:
            return []
        result = []
        for k in range(hier_id.numElems()):
            elem = hier_id.getElem(k)
            if elem is None:
                continue
            id_obj = elem.getId()
            if isinstance(id_obj, pss_ast.ExprId):
                result.append(id_obj.getId())
            elif id_obj is not None:
                result.append(str(id_obj))
        return result
    return []


# ---------------------------------------------------------------------------
# Covergroup annotation extraction (raw text scan)
# ---------------------------------------------------------------------------

def _extract_covergroup_annotations(text_files) -> List[PssAnnotation]:
    """Scan raw PSS source texts for covergroup blocks."""
    annotations: List[PssAnnotation] = []
    for _fname, text in text_files:
        _scan_text_for_covergroups(text, annotations)
    return annotations


def _scan_text_for_covergroups(text: str, annotations: list):
    """Brace-depth state machine: find covergroup blocks, track enclosing types."""
    n = len(text)
    i = 0
    type_stack: list = []   # (keyword, name, brace_depth_at_open)
    brace_depth = 0
    TYPE_KWS = ('component', 'action', 'struct')
    COV_KW = 'covergroup'
    cov_klen = len(COV_KW)

    while i < n:
        end = _scan_comment_or_string(text, i)
        if end != -1:
            i = end
            continue

        c = text[i]
        if c == '{':
            brace_depth += 1
            i += 1
            continue
        if c == '}':
            brace_depth -= 1
            while type_stack and type_stack[-1][2] >= brace_depth:
                type_stack.pop()
            i += 1
            continue

        matched = False
        for kw in TYPE_KWS:
            klen = len(kw)
            if (text[i:i+klen] == kw
                    and (i == 0 or not _is_word_char(text[i-1]))
                    and (i+klen < n and not _is_word_char(text[i+klen]))):
                j = i + klen
                while j < n and text[j] in ' \t\n\r':
                    j += 1
                name_start = j
                while j < n and _is_word_char(text[j]):
                    j += 1
                name = text[name_start:j]
                if name:
                    type_stack.append((kw, name, brace_depth))
                i = j
                matched = True
                break
        if matched:
            continue

        if (text[i:i+cov_klen] == COV_KW
                and (i == 0 or not _is_word_char(text[i-1]))
                and (i+cov_klen >= n or not _is_word_char(text[i+cov_klen]))):
            j = i + cov_klen
            while j < n and text[j] != '{':
                j += 1
            if j >= n:
                i += 1; continue
            end_brace = _find_matching_brace(text, j)
            if end_brace == -1:
                i += 1; continue

            body_text = text[j+1:end_brace]
            k = end_brace + 1
            while k < n and text[k] in ' \t\n\r':
                k += 1
            name_start2 = k
            while k < n and _is_word_char(text[k]):
                k += 1
            instance_name = text[name_start2:k].strip() or 'cg'
            while k < n and text[k] in ' \t\n\r':
                k += 1
            if k < n and text[k] == ';':
                k += 1

            coverpoints, crosses = _parse_covergroup_body(body_text)
            type_chain = [entry[1] for entry in type_stack]
            annotations.append(PssAnnotation(
                kind='covergroup',
                type_chain=type_chain,
                data={
                    'instance_name': instance_name,
                    'coverpoints': coverpoints,
                    'crosses': crosses,
                },
            ))
            i = k
            continue

        i += 1


def _parse_covergroup_body(body: str) -> tuple:
    """Parse coverpoint and cross declarations from a covergroup body string."""
    clean = re.sub(r'//[^\n]*', '', body)
    clean = re.sub(r'/\*.*?\*/', '', clean, flags=re.DOTALL)

    coverpoints = []
    crosses = []

    cross_re = re.compile(
        r'(?:(\w+)\s*:\s*)?cross\s+([\w\s,]+?)(?:\s*\{[^{}]*\})?\s*;',
        re.DOTALL,
    )
    for m in cross_re.finditer(clean):
        name = (m.group(1) or 'cross').strip()
        cp_names = [cp.strip() for cp in re.split(r'\s*,\s*', m.group(2).strip()) if cp.strip()]
        crosses.append({'name': name, 'coverpoint_names': cp_names})

    cp_re = re.compile(
        r'(?:(\w+)\s*:\s*)?coverpoint\s+(\w+)(?:\s*\{[^{}]*\})?\s*;',
        re.DOTALL,
    )
    for m in cp_re.finditer(clean):
        cp_name = (m.group(1) or m.group(2)).strip()
        target = m.group(2).strip()
        coverpoints.append({'name': cp_name, 'target': target})

    return coverpoints, crosses



class Parser(_PssParser):
    """pssparser.Parser wrapper with two-pass parsing and annotation extraction.

    Pass 1: minimal transform (covergroup removal + forall->foreach, no stub)
            -> parse without link -> capture forall pre-link body AST nodes.
    Pass 2: full _preprocess_pss (with body stub) -> parse for link().

    Covergroup annotations are extracted from the raw source text directly,
    since pssparser silently drops covergroup blocks and errors on 'cross'.
    """

    def __init__(self):
        super().__init__()
        self._pass1_parser: Optional[_PssParser] = None  # kept alive: prevents GC of pre-link AST nodes
        self._forall_annotations: List[PssAnnotation] = []
        self._cov_annotations: List[PssAnnotation] = []
        self._fill_annotations: List[PssAnnotation] = []

    @property
    def annotations(self) -> List[PssAnnotation]:
        """All extracted annotations (forall + covergroup)."""
        return self._forall_annotations + self._cov_annotations + self._fill_annotations

    def parse(self, files: List[str]) -> bool:
        """Read and parse PSS files with annotation extraction."""
        text_files = []
        for path in files:
            with open(path, 'r') as fh:
                src = fh.read()
            text_files.append((path, src))
        return self._two_pass_parse(text_files)

    def parses(self, text_files) -> bool:
        """Parse in-memory PSS texts with annotation extraction."""
        return self._two_pass_parse(list(text_files))

    def _two_pass_parse(self, text_files: List[tuple]) -> bool:
        # Covergroup and fill annotations from original text (before any transformation)
        self._cov_annotations = _extract_covergroup_annotations(text_files)
        self._fill_annotations = _extract_fill_annotations(text_files)

        # Pass 1: minimal transform, parse without link, capture forall bodies
        self._pass1_parser = _PssParser()
        pass1 = [(fname, _preprocess_pss_pass1(src)) for fname, src in text_files]
        self._pass1_parser.parses(pass1)
        self._forall_annotations = _extract_forall_annotations(self._pass1_parser._files)

        # Pass 2: full preprocessing, parse for subsequent link()
        pass2 = [(fname, _preprocess_pss(src)) for fname, src in text_files]
        return super().parses(pass2)


class PssTranslationError(Exception):
    """Raised when PSS source cannot be fully translated to IR."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        joined = "\n  ".join(errors)
        super().__init__(f"PSS IR translation failed with {len(errors)} error(s):\n  {joined}")


def load_pss(pss_text: str) -> ClassRegistry:
    """Parse PSS source text and return a registry of randomizable Python classes.

    Each PSS ``struct`` becomes a plain Python dataclass whose fields can be
    randomized with ``zuspec.dataclasses.randomize()``.

    Example::

        from zuspec.fe.pss import load_pss
        from zuspec.dataclasses import randomize

        ns = load_pss(\"\"\"
            struct Packet {
                rand bit[8] addr;
                constraint addr % 4 == 0;
            }
        \"\"\")
        pkt = ns.Packet()
        randomize(pkt, seed=42)
        assert pkt.addr % 4 == 0
    """
    parser = Parser()
    parser.parses([('inline.pss', pss_text)])
    root = parser.link()
    ctx = AstToIrTranslator().translate(root, annotations=parser.annotations)
    if ctx.errors:
        raise PssTranslationError(ctx.errors)
    return IrToRuntimeBuilder(ctx).build()


def load_pss_files(paths: List[Union[str, os.PathLike]]) -> ClassRegistry:
    """Parse one or more ``.pss`` files and return a registry of Python classes.

    Files are parsed together so they can reference each other's types.

    Example::

        from zuspec.fe.pss import load_pss_files
        from zuspec.dataclasses import randomize

        ns = load_pss_files(['bus.pss', 'cpu.pss'])
        cmd = ns.WriteCmd()
        randomize(cmd, seed=1)
    """
    str_paths = [str(p) for p in paths]
    parser = Parser()
    parser.parse(str_paths)
    root = parser.link()
    ctx = AstToIrTranslator().translate(root, annotations=parser.annotations)
    if ctx.errors:
        raise PssTranslationError(ctx.errors)
    return IrToRuntimeBuilder(ctx).build()


def get_deps():
    return ["pssparser"]

def get_libs():
    return []

def get_libdirs():
    return []

def get_incdirs():
    return []


# ---------------------------------------------------------------------------
# PSS-to-SystemVerilog generation API
# ---------------------------------------------------------------------------

from pathlib import Path
import shutil


def _get_runtime_lib_path() -> Path:
    """Return the path to the bundled zsp_rt_pkg.sv runtime library."""
    return Path(__file__).parent / "share" / "sv" / "zsp_rt_pkg.sv"


def generate_sv(pss_text: str, output_dir: str, **options) -> List[Path]:
    """Parse PSS source text and generate SystemVerilog files."""
    parser = Parser()
    parser.parses([('inline.pss', pss_text)])
    root = parser.link()
    ir_ctx = AstToIrTranslator().translate(root, annotations=parser.annotations)
    if ir_ctx.errors:
        raise PssTranslationError(ir_ctx.errors)
    return _generate_sv_from_ctx(ir_ctx, output_dir, **options)


def generate_sv_files(paths: List[Union[str, os.PathLike]], output_dir: str, **options) -> List[Path]:
    """Parse PSS source files and generate SystemVerilog files."""
    str_paths = [str(p) for p in paths]
    parser = Parser()
    parser.parse(str_paths)
    root = parser.link()
    ir_ctx = AstToIrTranslator().translate(root, annotations=parser.annotations)
    if ir_ctx.errors:
        raise PssTranslationError(ir_ctx.errors)
    return _generate_sv_from_ctx(ir_ctx, output_dir, **options)


def _generate_sv_from_ctx(ir_ctx: AstToIrContext, output_dir: str, **options) -> List[Path]:
    """Internal: lower IR context and write SV output files."""
    from .sv.pss_to_sv import pss_to_sv
    from .sv.emit_files import emit_files
    from .sv.lower_top import generate_top_module

    multi_file = options.pop('multi_file', True)
    inference_mode = options.pop('inference_mode', 'static')
    sv_nodes = pss_to_sv(ir_ctx)
    rt_src = _get_runtime_lib_path()

    comp_type = options.pop('comp_type', None)
    root_action_type = options.pop('root_action_type', None)
    top_node = None
    if comp_type and root_action_type:
        top_node = generate_top_module(
            comp_type=comp_type,
            root_action_type=root_action_type,
            import_if_type=options.pop('import_if_type', None),
            import_if_driver=options.pop('import_if_driver', None),
            watchdog_ns=options.pop('watchdog_ns', 0),
        )

    if multi_file:
        return emit_files(
            nodes=sv_nodes,
            output_dir=output_dir,
            runtime_lib_path=rt_src if rt_src.exists() else None,
            top_module_node=top_node,
        )

    from zuspec.be.sv.ir.sv_emit import SVEmitter

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    emitter = SVEmitter()

    all_nodes = list(sv_nodes)
    if top_node is not None:
        all_nodes.append(top_node)

    sv_text = emitter.emit_all(all_nodes)
    written: List[Path] = []

    gen_path = out / 'zsp_pkg.sv'
    gen_path.write_text(sv_text + "\n")
    written.append(gen_path)

    if rt_src.exists():
        rt_dst = out / 'zsp_rt_pkg.sv'
        shutil.copy2(str(rt_src), str(rt_dst))
        written.append(rt_dst)

    return written
