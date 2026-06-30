from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


SERVE_DIRECTION = {
    "0": "unknown_direction",
    "4": "out_wide",
    "5": "body",
    "6": "down_the_T",
}

SHOT_DIRECTION = {
    "0": "unknown_direction",
    "1": "forehand_side",
    "2": "center",
    "3": "backhand_side",
}

SERVE_OUTCOMES = {
    "*": "ace",
    "#": "forced_error",
    "@": "unforced_error",
}

SERVE_RETURN_DEPTH = {
    "0": "unknown_depth",
    "7": "short",
    "8": "mid",
    "9": "deep",
}

RALLY_SEQUENCE = {
    "f": "forehand_groundstroke",
    "b": "backhand_groundstroke",
    "r": "forehand_slice",
    "s": "backhand_slice",
    "v": "forehand_volley",
    "z": "backhand_volley",
    "o": "standard_overhead",
    "p": "backhand_overhead",
    "u": "forehand_drop_shot",
    "y": "backhand_drop_shot",
    "l": "forehand_lob",
    "m": "backhand_lob",
    "h": "forehand_half_volley",
    "i": "backhand_half_volley",
    "j": "forehand_swinging_volley",
    "k": "backhand_swinging_volley",
    "t": "trickshots",
    "q": "unknown_shots",
}

FAULT_TYPE = {
    "n": "net",
    "w": "wide",
    "d": "deep",
    "x": "wide_and_deep",
    "g": "foot_fault",
    "!": "shank",
    "e": "unknown_fault",
    "c": "let",
    "V": "time_violation",
}

MODIFIERS = {
    "+": "approach_shot",
    "-": "under_the_net",
    "=": "baseline",
    ";": "net_cord",
    "^": "stop_volley",
}


@dataclass
class ParsedServe:
    raw: str
    direction_code: str | None = None
    direction: str | None = None
    modifiers: list[str] = field(default_factory=list)
    modifier_labels: list[str] = field(default_factory=list)
    outcome_code: str | None = None
    outcome: str | None = None
    fault_code: str | None = None
    fault: str | None = None
    is_fault: bool = False


@dataclass
class ParsedShot:
    raw: str
    shot_index: int
    actor: str
    is_return: bool
    shot_code: str | None = None
    shot_type: str | None = None
    direction_code: str | None = None
    direction: str | None = None
    depth_code: str | None = None
    depth: str | None = None
    modifiers: list[str] = field(default_factory=list)
    modifier_labels: list[str] = field(default_factory=list)
    outcome_code: str | None = None
    outcome: str | None = None
    fault_code: str | None = None
    fault: str | None = None


@dataclass
class ParsedPoint:
    raw: str
    serve_number: int
    serve: ParsedServe
    rally: list[ParsedShot]
    terminal_actor: str | None = None
    terminal_shot_type: str | None = None
    terminal_outcome: str | None = None
    warnings: list[str] = field(default_factory=list)


def _modifier_labels(tokens: list[str]) -> list[str]:
    return [MODIFIERS[token] for token in tokens if token in MODIFIERS]


def _read_modifiers(code: str, idx: int) -> tuple[list[str], int]:
    modifiers: list[str] = []
    while idx < len(code) and code[idx] in MODIFIERS:
        modifiers.append(code[idx])
        idx += 1
    return modifiers, idx


def parse_point_code(code: str | None, serve_number: int = 1) -> ParsedPoint | None:
    """Parse a raw Match Charting Project point code into a structured point."""
    if code is None:
        return None

    raw = str(code).strip()
    if not raw or raw.lower() == "nan":
        return None

    idx = 0
    warnings: list[str] = []

    serve = ParsedServe(raw="")
    if raw[idx] in SERVE_DIRECTION:
        serve.direction_code = raw[idx]
        serve.direction = SERVE_DIRECTION[raw[idx]]
        serve.raw += raw[idx]
        idx += 1
    else:
        warnings.append(f"Unknown serve direction at position 0: {raw[idx]!r}")

    modifiers, idx = _read_modifiers(raw, idx)
    serve.modifiers = modifiers
    serve.modifier_labels = _modifier_labels(modifiers)
    serve.raw += "".join(modifiers)

    if idx < len(raw) and raw[idx] in FAULT_TYPE:
        fault_code = raw[idx]
        # A let ('c') is not a fault if it is followed by other characters:
        # it means the ball touched the net tape, stayed in play, and the
        # point continued normally.
        if fault_code == "c" and idx + 1 < len(raw):
            serve.raw += fault_code
            idx += 1  # skip the 'c' and continue parsing the rally
            warnings.append("Serve let (c): the point was replayed and is not counted as a fault")
        else:
            serve.fault_code = fault_code
            serve.fault = FAULT_TYPE[fault_code]
            serve.is_fault = True
            serve.raw += fault_code
            idx += 1

    elif idx < len(raw) and raw[idx] in SERVE_OUTCOMES:
        serve.outcome_code = raw[idx]
        serve.outcome = SERVE_OUTCOMES[raw[idx]]
        serve.raw += raw[idx]
        idx += 1

    rally: list[ParsedShot] = []
    shot_index = 0
    while idx < len(raw):
        token = raw[idx]

        if token not in RALLY_SEQUENCE:
            warnings.append(f"Unparsed token at position {idx}: {token!r}")
            idx += 1
            continue

        actor = "returner" if shot_index % 2 == 0 else "server"
        is_return = shot_index == 0
        shot = ParsedShot(
            raw=token,
            shot_index=shot_index,
            actor=actor,
            is_return=is_return,
            shot_code=token,
            shot_type=RALLY_SEQUENCE[token],
        )
        idx += 1

        modifiers, idx = _read_modifiers(raw, idx)
        shot.modifiers = modifiers
        shot.modifier_labels = _modifier_labels(modifiers)
        shot.raw += "".join(modifiers)

        if idx < len(raw) and raw[idx] in SHOT_DIRECTION:
            shot.direction_code = raw[idx]
            shot.direction = SHOT_DIRECTION[raw[idx]]
            shot.raw += raw[idx]
            idx += 1

        if is_return and idx < len(raw) and raw[idx] in SERVE_RETURN_DEPTH:
            shot.depth_code = raw[idx]
            shot.depth = SERVE_RETURN_DEPTH[raw[idx]]
            shot.raw += raw[idx]
            idx += 1

        if idx < len(raw) and raw[idx] in FAULT_TYPE:
            shot.fault_code = raw[idx]
            shot.fault = FAULT_TYPE[raw[idx]]
            shot.raw += raw[idx]
            idx += 1

        if idx < len(raw) and raw[idx] in SERVE_OUTCOMES:
            shot.outcome_code = raw[idx]
            shot.outcome = SERVE_OUTCOMES[raw[idx]]
            shot.raw += raw[idx]
            idx += 1

        rally.append(shot)
        shot_index += 1

    terminal_actor = None
    terminal_shot_type = None
    terminal_outcome = None

    if rally:
        terminal_actor = rally[-1].actor
        terminal_shot_type = rally[-1].shot_type
        terminal_outcome = rally[-1].outcome or rally[-1].fault
    elif serve.outcome or serve.fault:
        terminal_actor = "server"
        terminal_shot_type = "serve"
        terminal_outcome = serve.outcome or serve.fault

    return ParsedPoint(
        raw=raw,
        serve_number=serve_number,
        serve=serve,
        rally=rally,
        terminal_actor=terminal_actor,
        terminal_shot_type=terminal_shot_type,
        terminal_outcome=terminal_outcome,
        warnings=warnings,
    )


def parse_point_row(
    row: dict[str, Any],
    first_col: str = "1st",
    second_col: str = "2nd",
) -> dict[str, Any]:
    """Parse both serves for a row and return a dashboard-friendly record."""
    first_point = parse_point_code(row.get(first_col), serve_number=1)
    second_point = parse_point_code(row.get(second_col), serve_number=2)

    # Prefer the second serve when it exists, otherwise fall back to the first.
    active_point = second_point if second_point else first_point
    double_fault = bool(
        first_point
        and second_point
        and first_point.serve.is_fault
        and second_point.serve.is_fault
    )

    # Determine the point winner from the "PtWinner" column (1 or 2).
    pt_winner = str(row.get("PtWinner", "")).strip()
    server    = str(row.get("Svr", "")).strip()

    # Break point: the Sackmann "Pts" column contains "BP" on break points.
    pts_flag      = str(row.get("Pts", "")).strip()
    is_break_point = "BP" in pts_flag

    all_warnings = []
    if first_point:
        all_warnings += first_point.warnings
    if second_point:
        all_warnings += second_point.warnings

    return {
        "first_serve":  asdict(first_point)  if first_point  else None,
        "second_serve": asdict(second_point) if second_point else None,
        "active_point": asdict(active_point) if active_point else None,
        "derived":      derive_point_features(first_point, second_point),
        "flags": {
            "has_second_serve":  second_point is not None,
            "first_serve_fault": bool(first_point and first_point.serve.is_fault),
            "double_fault":      double_fault,
        },
        "meta": {
            "server":         str(row.get("Svr", "")).strip(),
            "point_winner":   str(row.get("PtWinner", "")).strip(),
            "set": int(row.get("Set1", 0)) + int(row.get("Set2", 0)) + 1,
            "is_break_point": "BP" in str(row.get("Pts", "")),
            "is_tiebreak": bool(row.get("TbSet", False)),
            "warnings":       all_warnings,
        }
    }


def derive_point_features(
    first_point: ParsedPoint | None,
    second_point: ParsedPoint | None,
) -> dict[str, Any]:
    """Derive the flattened features used by the charts from the parsed point."""
    point = second_point if second_point else first_point
    if point is None:
        return {}

    serve = point.serve
    rally = point.rally

    return {
        "serve_number_played": point.serve_number,
        "serve_direction": serve.direction,
        "serve_is_fault": serve.is_fault,
        "serve_outcome": serve.outcome,
        "rally_length": len(rally),
        "return_depth": rally[0].depth if rally else None,
        "return_direction": rally[0].direction if rally else None,
        "terminal_actor": point.terminal_actor,
        "terminal_shot_type": point.terminal_shot_type,
        "terminal_outcome": point.terminal_outcome,
        "server_finished_at_net": any("-" in shot.modifiers for shot in rally if shot.actor == "server"),
        "returner_finished_at_net": any("-" in shot.modifiers for shot in rally if shot.actor == "returner"),
        "contains_drop_shot": any(
            shot.shot_code in {"u", "y"} for shot in rally
        ),
        "contains_lob": any(shot.shot_code in {"l", "m"} for shot in rally),
        "contains_volley": any(
            shot.shot_code in {"v", "z", "h", "i", "j", "k", "o", "p"}
            for shot in rally
        ),
        "contains_approach": ("+" in serve.modifiers) or any("+" in shot.modifiers for shot in rally),
    }


def parse_csv(
    input_path: str | Path,
    first_col: str = "1st",
    second_col: str = "2nd",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Parse an entire CSV file and return a list of structured point records."""
    records: list[dict[str, Any]] = []
    with Path(input_path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            parsed = parse_point_row(row, first_col=first_col, second_col=second_col)
            parsed["row_index"] = index
            records.append(parsed)
            if limit is not None and len(records) >= limit:
                break
    return records


def flatten_points_for_dashboard(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten nested parser output into a chart-friendly row format."""
    flat_rows: list[dict[str, Any]] = []
    for record in records:
        active = record.get("active_point")
        derived = record.get("derived", {})
        if not active:
            continue

        serve = active["serve"]
        flat_rows.append(
            {
                "row_index": record.get("row_index"),
                "serve_number_played": derived.get("serve_number_played"),
                "serve_direction": serve.get("direction"),
                "serve_is_fault": serve.get("is_fault"),
                "serve_outcome": serve.get("outcome"),
                "rally_length": derived.get("rally_length"),
                "return_depth": derived.get("return_depth"),
                "return_direction": derived.get("return_direction"),
                "terminal_actor": derived.get("terminal_actor"),
                "terminal_shot_type": derived.get("terminal_shot_type"),
                "terminal_outcome": derived.get("terminal_outcome"),
                "contains_volley": derived.get("contains_volley"),
                "contains_drop_shot": derived.get("contains_drop_shot"),
                "contains_lob": derived.get("contains_lob"),
                "contains_approach": derived.get("contains_approach"),
            }
        )
    return flat_rows


def summarize_serve_patterns(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a compact summary of serve and return patterns for dashboards."""
    summary = {
        "points": 0,
        "first_serves_in": 0,
        "second_serves_played": 0,
        "double_faults": 0,
        "serve_directions": {},
        "return_depths": {},
    }

    for record in records:
        summary["points"] += 1
        flags = record.get("flags", {})
        derived = record.get("derived", {})

        if not flags.get("first_serve_fault"):
            summary["first_serves_in"] += 1
        if flags.get("has_second_serve"):
            summary["second_serves_played"] += 1
        if flags.get("double_fault"):
            summary["double_faults"] += 1

        serve_direction = derived.get("serve_direction")
        if serve_direction:
            summary["serve_directions"][serve_direction] = (
                summary["serve_directions"].get(serve_direction, 0) + 1
            )

        return_depth = derived.get("return_depth")
        if return_depth:
            summary["return_depths"][return_depth] = (
                summary["return_depths"].get(return_depth, 0) + 1
            )

    if summary["points"]:
        summary["first_serve_in_pct"] = round(summary["first_serves_in"] / summary["points"], 4)
        summary["double_fault_pct"] = round(summary["double_faults"] / summary["points"], 4)
    else:
        summary["first_serve_in_pct"] = None
        summary["double_fault_pct"] = None

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse Jeff Sackmann Match Charting Project `1st` / `2nd` point codes."
    )
    parser.add_argument("input_csv", nargs="?", help="CSV file to parse.")
    parser.add_argument("--first-col", default="1st", help="Name of the first-serve column.")
    parser.add_argument("--second-col", default="2nd", help="Name of the second-serve column.")
    parser.add_argument("--limit", type=int, default=None, help="Only parse the first N rows.")
    parser.add_argument(
        "--sample",
        nargs="*",
        help="Parse one or more raw point codes directly instead of reading a CSV.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit compact JSON instead of pretty-printed JSON.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="When parsing a CSV, emit a compact dashboard-oriented summary.",
    )
    args = parser.parse_args()

    if args.sample:
        payload = []
        for code in args.sample:
            parsed = parse_point_code(code)
            if parsed is not None:
                payload.append(asdict(parsed))
    elif args.input_csv:
        records = parse_csv(
            args.input_csv,
            first_col=args.first_col,
            second_col=args.second_col,
            limit=args.limit,
        )
        payload = (
            {
                "summary": summarize_serve_patterns(records),
                "points": flatten_points_for_dashboard(records),
            }
            if args.summary
            else records
        )
    else:
        parser.error("Provide either an input CSV path or one or more --sample codes.")
        return

    if args.compact:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()