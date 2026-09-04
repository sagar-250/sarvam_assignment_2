"""Apply "intervene" decisions to the token stream, producing the final
memory-aware string. Preserves all original whitespace/punctuation exactly
(by copying the source text between token spans verbatim) and reattaches any
possessive suffix ('s / 's) that was stripped for matching.
"""
from backend.decision import Decision
from backend.tokenizer import Token


def apply_decisions(original_text: str, tokens: list[Token], decisions: list[Decision]) -> str:
    to_apply = sorted(
        [d for d in decisions if d.kind == "intervene"], key=lambda d: d.start_idx
    )

    output: list[str] = []
    cursor = 0
    i = 0
    di = 0
    n = len(tokens)

    while i < n:
        if di < len(to_apply) and to_apply[di].start_idx == i:
            d = to_apply[di]
            start_tok = tokens[d.start_idx]
            end_tok = tokens[d.end_idx - 1]

            output.append(original_text[cursor:start_tok.start])
            replacement = d.canonical_form
            if end_tok.is_possessive:
                replacement = replacement + end_tok.possessive_suffix
            output.append(replacement)

            cursor = end_tok.end
            i = d.end_idx
            di += 1
        else:
            i += 1

    output.append(original_text[cursor:])
    return "".join(output)
