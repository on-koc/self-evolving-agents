"""``sea discovery`` commands: run, grade and report the DiscoveryWorld memory experiment."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


def _options(pairs: list[str] | None) -> dict[str, Any]:
    from ..llm import parse_options

    try:
        return parse_options(pairs)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None


def cmd_run(args: argparse.Namespace) -> int:
    from .experiment import load_protocol, run_protocol

    try:
        protocol = load_protocol(args.protocol)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    statuses = run_protocol(
        protocol,
        args.out,
        llm=args.llm,
        llm_options=_options(args.llm_option),
        arms=args.arms.split(",") if args.arms else None,
        repeats=args.repeats,
    )
    print(f"Runs written to {args.out}/. Next: sea discovery grade {args.out} --grader <model>")
    return 2 if any(s for runs in statuses.values() for s in runs) else 0


def cmd_grade(args: argparse.Namespace) -> int:
    from .experiment import grade_protocol

    path = grade_protocol(
        args.out,
        grader=args.grader,
        grader_options=_options(args.grader_option),
        code=not args.no_code,
    )
    print(f"Grades: {path}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from .report import build_report

    build_report(args.out)
    print((Path(args.out) / "report.md").read_text())
    return 0


def cmd_code_sample(args: argparse.Namespace) -> int:
    """Export a random sample of episodes for people to code, without the arm."""
    from .behaviours import BEHAVIOUR_DEFINITIONS, coding_record
    from .experiment import episodes

    chosen = [e for e in episodes(args.out) if e["trajectory"] is not None]
    random.Random(args.seed).shuffle(chosen)
    chosen = chosen[: args.n]
    target = Path(args.sample)
    key = target.with_name(target.stem + ".key.json")
    with target.open("w") as fh:
        for i, episode in enumerate(chosen):
            fh.write(
                json.dumps(
                    {
                        "sample_id": i,
                        "record": coding_record(episode["trajectory"]),
                        "definitions": BEHAVIOUR_DEFINITIONS,
                        "labels": {name: None for name in BEHAVIOUR_DEFINITIONS},
                    }
                )
                + "\n"
            )
    key.write_text(json.dumps({str(i): e["key"] for i, e in enumerate(chosen)}, indent=1))
    print(f"wrote {len(chosen)} records to {target}; the key to the episodes is in {key}")
    return 0


def cmd_agreement(args: argparse.Namespace) -> int:
    """Cohen's kappa between people's labels and the model coder's, per behaviour."""
    from .behaviours import BEHAVIOUR_DEFINITIONS, cohen_kappa

    labels = [
        json.loads(line) for line in Path(args.labels).read_text().splitlines() if line.strip()
    ]
    key = json.loads(Path(args.labels).with_name(Path(args.labels).stem + ".key.json").read_text())
    grades = {}
    for line in (Path(args.out) / "grades.jsonl").read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            grades[row["key"]] = row
    result = {}
    for name in BEHAVIOUR_DEFINITIONS:
        people, model = [], []
        for item in labels:
            episode = key.get(str(item["sample_id"]))
            codes = ((grades.get(episode) or {}).get("behaviour_codes") or {}).get("codes") or {}
            people.append(item["labels"].get(name))
            model.append((codes.get(name) or {}).get("present"))
        usable = sum(
            1 for a, b in zip(people, model, strict=True) if a is not None and b is not None
        )
        result[name] = {"kappa": cohen_kappa(people, model), "pairs": usable}
    print(json.dumps(result, indent=2))
    (Path(args.out) / "coder_agreement.json").write_text(json.dumps(result, indent=2))
    return 0


def add_discovery_commands(sub: Any) -> None:
    discovery = sub.add_parser(
        "discovery", help="the DiscoveryWorld memory experiment"
    ).add_subparsers(dest="discovery_command", required=True)

    run = discovery.add_parser("run", help="run every arm and phase of a protocol")
    run.add_argument("--protocol", required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--llm", help="model for every arm (overrides the protocol)")
    run.add_argument("--llm-option", action="append", metavar="NAME=VALUE")
    run.add_argument("--arms", help="comma-separated subset of the arms")
    run.add_argument("--repeats", type=int)
    run.set_defaults(func=cmd_run)

    grade = discovery.add_parser("grade", help="knowledge scores and behaviour codes")
    grade.add_argument("out")
    grade.add_argument("--grader", required=True, help="the grading model, e.g. openai:gpt-4o")
    grade.add_argument("--grader-option", action="append", metavar="NAME=VALUE")
    grade.add_argument("--no-code", action="store_true", help="skip the behaviour coding")
    grade.set_defaults(func=cmd_grade)

    report = discovery.add_parser("report", help="tables of every measure")
    report.add_argument("out")
    report.set_defaults(func=cmd_report)

    sample = discovery.add_parser("code-sample", help="export episodes for people to code")
    sample.add_argument("out")
    sample.add_argument("--sample", required=True, help="JSONL file to write")
    sample.add_argument("--n", type=int, default=50)
    sample.add_argument("--seed", type=int, default=0)
    sample.set_defaults(func=cmd_code_sample)

    agreement = discovery.add_parser("agreement", help="agreement of the model coder with people")
    agreement.add_argument("out")
    agreement.add_argument("--labels", required=True, help="the coded sample (code-sample's file)")
    agreement.set_defaults(func=cmd_agreement)
