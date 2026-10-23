#!/usr/bin/env python3
"""TMFP Vibe Day v0.4 — index observations of an eventset, not the eventset itself.

Python >=3.10, git; stdlib except optional huggingface_hub for publishing.
"""
from __future__ import annotations
import argparse
import contextlib
import fcntl
import datetime as dt
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid
from zoneinfo import ZoneInfo

VERSION = "0.4.0"
SCHEMA = "tmfp.day.v0.4"
FILESETS = ("day.json", "dataset.json", "events.jsonl", "pieces.jsonl", "relations.jsonl", "experiences.jsonl", "members.jsonl", "contexts.jsonl", "context_requests.jsonl", "obs/overlay.txt")
MAX_ATTACH = 5 * 1024 * 1024


def utcnow():
    return dt.datetime.now(dt.timezone.utc)


def iso(t=None):
    return (t or utcnow()).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write(path: Path, value: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".tmfp-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def jwrite(path: Path, obj):
    write(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def jread(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def append(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as out:
        out.write(dump(obj) + "\n")
        out.flush()
        os.fsync(out.fileno())


def rows(path: Path):
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def cmd(*argv, cwd=None):
    p = subprocess.run(list(argv), cwd=cwd, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(f"{' '.join(str(a) for a in argv)}: {p.stderr.strip() or p.stdout.strip()}")
    return p.stdout.strip()


def git(repo: Path, *args):
    return cmd("git", "-C", str(repo), *args)


def check_date(value):
    return dt.date.fromisoformat(value).isoformat()


def root_of(args):
    return Path(args.home).expanduser().resolve()


def conf(root):
    path = root / ".tmfp/config.json"
    if not path.exists():
        raise ValueError("Run `init` first")
    return jread(path)


def local_day(root, t=None):
    return (t or utcnow()).astimezone(ZoneInfo(conf(root)["timezone"])).date().isoformat()


def repo_of(root, date):
    return root / "days" / f"tmfp-{check_date(date)}"


def active_path(root):
    return root / ".tmfp/active.json"


def current_context(root):
    path = active_path(root)
    return jread(path) if path.is_file() else None


def new_id(prefix):
    return prefix + ":" + uuid.uuid4().hex


def manifest_root(day):
    p = day / "integrity/manifest.json"
    return jread(p)["root_sha256"] if p.exists() else None


def last_sealed_before(root, date):
    days = sorted((root / "days").glob("tmfp-????-??-??")) if (root / "days").exists() else []
    for prev in reversed(days):
        if prev.name < f"tmfp-{date}" and (prev / "integrity/manifest.json").is_file():
            return {"day_id": jread(prev / "day.json")["day_id"], "root_sha256": manifest_root(prev)}
    return None


SERIES = "Vibe-Inventing World Peace"


def dataset_meta(root, date):
    """Read primary v0.4 identity; interpret earlier v0.3 days without rewriting them."""
    repo = repo_of(root, date)
    day = jread(repo / "day.json")
    descriptor = repo / "dataset.json"
    if descriptor.is_file():
        return jread(descriptor)
    return {"schema": "tmfp.dataset.legacy", "dataset_id": f"tmfp:dataset:{date}",
            "day_id": day["day_id"], "date": date, "day_number": day.get("day_number"),
            "series": SERIES, "title": f"{SERIES} | Legacy day {date}",
            "entity_kind": "recorded_experience_dataset",
            "scope": "observer_defined_local_civil_day", "context": {"origin": "legacy v0.3 index"},
            "provenance": {"day_id": day["day_id"], "timezone": day["timezone"]}}


def next_day_number(root):
    numbers = []
    for repo in (root / "days").glob("tmfp-????-??-??"):
        if (repo / "day.json").is_file():
            old = jread(repo / "day.json")
            if isinstance(old.get("day_number"), int):
                numbers.append(old["day_number"])
    if numbers:
        return max(numbers) + 1
    return conf(root).get("first_day_number", 1)


def make_dataset_id(number, date):
    return f"tmfp:dataset:day:{number:04d}:{date}"


def ensure_day(root, date):
    repo = repo_of(root, date)
    if (repo / "day.json").exists():
        return repo
    if repo.exists() and any(repo.iterdir()):
        raise ValueError(f"Refusing to overwrite existing directory {repo}")
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "obs").mkdir()
    (repo / "objects").mkdir()
    (repo / "integrity").mkdir()
    number = next_day_number(root)
    dsid = make_dataset_id(number, date)
    title = f"{SERIES} | Day {number} of ???"
    jwrite(repo / "day.json", {
        "schema": SCHEMA, "day_id": f"tmfp:day:{date}", "date": date,
        "day_number": number, "dataset_id": dsid, "title": title,
        "timezone": conf(root)["timezone"], "created_at_utc": iso(),
        "scope": "observer_defined_local_civil_day", "observed_eventset": "physical_world",
        "previous_index_snapshot": last_sealed_before(root, date),
        "claim": "This index is a representation of events, not the events themselves."
    })
    jwrite(repo / "dataset.json", {
        "schema": "tmfp.dataset.v0.4", "dataset_id": dsid,
        "day_id": f"tmfp:day:{date}", "date": date, "day_number": number,
        "series": SERIES, "title": title,
        "entity_kind": "recorded_experience_dataset",
        "scope": "observer_defined_local_civil_day",
        "context": {"world": "not_exhaustively_recorded",
                    "format": "recursive_addressable_kv", "horizon": "???"},
        "provenance": {"recorded_by": "human_declared", "timezone": conf(root)["timezone"],
                       "created_at_utc": iso(), "previous_index_snapshot": last_sealed_before(root, date)},
        "parent_query": "tmfp:series:vibe-inventing-world-peace",
        "claim": "Dataset is an addressable representation of a day, not the world itself."
    })
    for name in ("events.jsonl", "pieces.jsonl", "relations.jsonl", "experiences.jsonl", "members.jsonl", "contexts.jsonl", "context_requests.jsonl"):
        (repo / name).touch()
    write(repo / ".gitignore", ".DS_Store\n.env\n.env.*\n*.pem\n*.key\n__pycache__/\n")
    write(repo / ".gitattributes", "* -text\n")
    write(repo / "README.md", "# TMFP daily slice: " + date + "\n\n"
          "An addressable daily experience dataset, **not** the physical eventset. "
          "See `dataset.json`, `day.json`, `members.jsonl`, `contexts.jsonl`, "
          "`events.jsonl`, `pieces.jsonl`, `relations.jsonl`, `experiences.jsonl`. "
          "Links are references; they do not attest to remote bytes.\n")
    write(repo / "obs/overlay.txt", "☮ TMFP | NOT LIVE\n")
    try:
        git(repo, "init", "-q", "-b", "main")
    except RuntimeError:
        git(repo, "init", "-q")
        git(repo, "checkout", "-q", "-b", "main")
    checkpoint(repo, "initialize daily index")
    return repo


def stage(repo):
    for folder in ("objects", "obs"):
        for f in (repo / folder).rglob("*"):
            if f.is_symlink():
                raise ValueError("Symlinks are not permitted in indexed payloads")
    managed = [".gitignore", ".gitattributes", "README.md", "day.json", "dataset.json",
               "events.jsonl", "pieces.jsonl", "relations.jsonl", "experiences.jsonl",
               "members.jsonl", "contexts.jsonl", "context_requests.jsonl", "obs", "objects", "integrity"]
    git(repo, "add", "-A", "--", *[name for name in managed if (repo / name).exists()])


def checkpoint(repo, label):
    stage(repo)
    if not git(repo, "diff", "--cached", "--name-only"):
        return git(repo, "rev-parse", "HEAD")
    cmd("git", "-C", str(repo), "-c", "user.name=TMFP Local Indexer",
        "-c", "user.email=tmfp@invalid.example", "commit", "-q", "-m", label)
    return git(repo, "rev-parse", "HEAD")


def text_overlay(root, repo, a):
    day = jread(repo / "day.json")
    label = a["session_id"] if a else "OFF_AIR"
    label_title = day.get("title") or f"{SERIES} | legacy {day['date']}"
    lines = ["☮ THE WILDER-NESS ADVENTURES", label_title, f"SLICE {day['day_id']}",
             f"SESSION {label}", f"MODE {a['mode'] if a else 'OFF_AIR'}",
             f"TO {a['address'] if a else '—'}", f"RE {a['focus'] if a else '—'}",
             f"TOPIC {a['topic'] if a else '—'}", f"UTC {iso()}"]
    value = "\n".join(lines) + "\n"
    write(repo / "obs/overlay.txt", value)
    write(root / "obs/current.txt", value)


def ensure_runtime_day(root, when=None):
    date = local_day(root, when)
    repo = ensure_day(root, date)
    a = current_context(root)
    if a and a.get("latest_day") != date:
        a["latest_day"] = date
        jwrite(active_path(root), a)
        emit(root, repo, a, "session_continued", "Session crosses an observer-defined day boundary")
    text_overlay(root, repo, a)
    return repo


def elapsed(a, when=None):
    if not a:
        return None
    start = dt.datetime.fromisoformat(a["started_at_utc"].replace("Z", "+00:00"))
    return max(0, int(((when or utcnow()) - start).total_seconds() * 1000))


def emit(root, repo, a, kind, description, piece_id="", detail=None):
    when = utcnow()
    entry = {"id": new_id("evt"), "day_id": jread(repo / "day.json")["day_id"],
        "utc": iso(when), "session_id": a["session_id"] if a else "",
        "elapsed_ms": elapsed(a, when), "kind": kind, "description": description,
        "speaker": "wilder" if a else "system", "address": a["address"] if a else "",
        "focus": a["focus"] if a else "", "piece_id": piece_id,
        "detail_json": dump(detail or {})}
    append(repo / "events.jsonl", entry)
    return entry


def parse_data(arg):
    if not arg:
        return {}
    obj = json.loads(arg)
    if not isinstance(obj, dict):
        raise ValueError("--data must be a JSON object")
    return obj


@contextlib.contextmanager
def local_lock(root):
    p = root / ".tmfp/.write.lock"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def do_init(args):
    root = root_of(args)
    ZoneInfo(args.timezone)
    if args.first_day_number < 1:
        raise ValueError("--first-day-number must be >= 1")
    path = root / ".tmfp/config.json"
    if path.exists():
        raise ValueError("Workspace already initialized")
    jwrite(path, {"timezone": args.timezone, "schema": SCHEMA, "first_day_number": args.first_day_number, "series": SERIES})
    write(root / "obs/current.txt", "☮ THE WILDER-NESS ADVENTURES | OFF_AIR\n")
    print(f"Initialized {root}; OBS source: {root / 'obs/current.txt'}")


def do_start(args):
    root = root_of(args)
    conf(root)
    if current_context(root):
        raise ValueError("Session is already active: use `stop` first")
    date = check_date(args.date) if args.date else local_day(root)
    repo = ensure_day(root, date)
    a = {"session_id": new_id("session"), "started_at_utc": iso(), "latest_day": date,
         "mode": args.mode, "address": args.address, "focus": "", "topic": args.topic}
    jwrite(active_path(root), a)
    emit(root, repo, a, "session_started", args.topic)
    text_overlay(root, repo, a)
    print(f"Started {a['session_id']} | {repo}")


def do_state(args):
    root = root_of(args)
    a = current_context(root)
    if not a:
        raise ValueError("No active session")
    for field in ("mode", "address", "focus", "topic"):
        v = getattr(args, field)
        if v is not None:
            a[field] = v
    jwrite(active_path(root), a)
    repo = ensure_runtime_day(root)
    emit(root, repo, a, "state_changed", "Live annotation state updated")
    text_overlay(root, repo, a)
    print(f"MODE={a['mode']} TO={a['address']} RE={a['focus']} TOPIC={a['topic']}")


def do_mark(args):
    root = root_of(args)
    a = current_context(root)
    if not a:
        raise ValueError("No active session")
    repo = ensure_runtime_day(root)
    pid = new_id("piece")
    record = {"id": pid, "day_id": jread(repo / "day.json")["day_id"],
        "utc": iso(), "kind": args.kind, "key": args.key,
        "description": args.text, "value_json": dump(parse_data(args.data)),
        "address": args.address if args.address is not None else a["address"],
        "focus": args.focus if args.focus is not None else a["focus"],
        "uri": "", "sha256": "", "evidence_status": "self_reported_live_annotation"}
    append(repo / "pieces.jsonl", record)
    emit(root, repo, a, "piece_annotated", args.text, pid)
    print(pid)


def do_add(args):
    root = root_of(args)
    repo = ensure_day(root, check_date(args.date) if args.date else local_day(root))
    if bool(args.file) == bool(args.uri):
        raise ValueError("Specify exactly one of --file and --uri")
    a = current_context(root)
    metadata = parse_data(args.data)
    if args.file:
        original = Path(args.file).expanduser().resolve()
        if not original.is_file() or original.is_symlink() or original.stat().st_size > MAX_ATTACH:
            raise ValueError("Local source must be a regular file <= 5 MiB (larger: use --uri)")
        data = original.read_bytes()
        metadata.setdefault("original_filename", original.name)
        metadata.setdefault("mime_type", mimetypes.guess_type(original.name)[0] or "application/octet-stream")
        metadata.setdefault("file_size", len(data))
        digest = hashlib.sha256(data).hexdigest()
        target = repo / "objects" / digest
        if not target.exists():
            target.write_bytes(data)
        uri = f"objects/{digest}"
        status = "local_bytes_hashed"
    else:
        if not args.uri.startswith(("https://", "http://", "hf://", "s3://")):
            raise ValueError("External reference must be a supported URI")
        uri, digest, status = args.uri, args.sha256 or "", "remote_reference_unverified"
        if digest and not (len(digest) == 64 and all(c in "0123456789abcdefABCDEF" for c in digest)):
            raise ValueError("--sha256 must be 64 hex characters")
    pid = new_id("piece")
    record = {"id": pid, "day_id": jread(repo / "day.json")["day_id"],
        "utc": iso(), "kind": args.kind, "key": args.key,
        "description": args.description, "value_json": dump(metadata),
        "address": a["address"] if a else "", "focus": a["focus"] if a else "",
        "uri": uri, "sha256": digest, "evidence_status": status}
    append(repo / "pieces.jsonl", record)
    emit(root, repo, a, "piece_registered", args.description, pid)
    print(f"{pid} {uri}")


def do_relate(args):
    root = root_of(args)
    repo = ensure_day(root, check_date(args.date) if args.date else local_day(root))
    rel = {"id": new_id("relation"), "day_id": jread(repo / "day.json")["day_id"],
        "utc": iso(), "subject_id": args.subject, "predicate": args.predicate,
        "object_id": args.object, "evidence_id": args.evidence or "",
        "assertion_status": "human_declared", "description": args.description or ""}
    append(repo / "relations.jsonl", rel)
    emit(root, repo, current_context(root), "relation_asserted", args.predicate, detail={"relation_id": rel["id"]})
    print(rel["id"])




def get_value(args):
    if args.value_json is not None:
        return json.loads(args.value_json)
    if args.value is not None:
        return args.value
    raise ValueError("Supply --value or --value-json")


def record_member(root, repo, *, key, value, kind="kv", subject=None, source_ref="",
                  description="", context=None, declared_at=None):
    """Generic addressable K:V; values can be any JSON type incl nested objects.

    No anticipation/ground-truth interpretation is imposed. A member can be
    queried as a value of the day dataset or as a parent entity itself.
    """
    meta = dataset_meta(root, jread(repo / "day.json")["date"])
    rec = {"id": new_id("member"), "dataset_id": meta["dataset_id"],
           "day_id": meta["day_id"], "utc": declared_at or iso(),
           "subject_id": subject or meta["dataset_id"], "key": key,
           "value_json": dump(value), "kind": kind, "description": description,
           "context_json": dump(context or {}), "source_ref": source_ref,
           "assertion_status": "human_declared", "evidence_status": "reference_unverified" if source_ref else "self_reported"}
    append(repo / "members.jsonl", rec)
    return rec


def do_member(args):
    root = root_of(args)
    repo = ensure_day(root, check_date(args.date) if args.date else local_day(root))
    rec = record_member(root, repo, key=args.key, value=get_value(args), kind=args.kind,
                        subject=args.subject, source_ref=args.source_ref or "",
                        description=args.description or "", context=parse_data(args.context))
    emit(root, repo, current_context(root), "member_recorded", args.key,
         detail={"member_id": rec["id"]})
    print(rec["id"])


def do_context(args):
    """Append, never silently rewrite, one contextual/provenance association."""
    root = root_of(args)
    repo = ensure_day(root, check_date(args.date) if args.date else local_day(root))
    meta = dataset_meta(root, jread(repo / "day.json")["date"])
    rec = {"id": new_id("context"), "dataset_id": meta["dataset_id"],
           "day_id": meta["day_id"], "utc": iso(),
           "subject_id": args.subject or meta["dataset_id"], "key": args.key,
           "value_json": dump(get_value(args)), "source_ref": args.source_ref or "",
           "description": args.description or "", "assertion_status": "human_declared",
           "evidence_status": "reference_unverified" if args.source_ref else "self_reported"}
    append(repo / "contexts.jsonl", rec)
    emit(root, repo, current_context(root), "context_attached", args.key,
         detail={"context_id": rec["id"]})
    print(rec["id"])


def all_context_requests(root):
    output = {}
    for repo in (root / "days").glob("tmfp-????-??-??"):
        for item in rows(repo / "context_requests.jsonl"):
            if item["phase"] == "request":
                if item["request_id"] in output:
                    raise ValueError("Duplicate context request")
                output[item["request_id"]] = item
    return output


def do_need(args):
    """A declared missing-context question for future human/agent research."""
    root = root_of(args)
    repo = ensure_day(root, check_date(args.date) if args.date else local_day(root))
    rid = new_id("need")
    meta = dataset_meta(root, jread(repo / "day.json")["date"])
    append(repo / "context_requests.jsonl", {
        "id": new_id("ctxevt"), "request_id": rid, "phase": "request",
        "dataset_id": meta["dataset_id"], "day_id": meta["day_id"],
        "subject_id": args.subject or meta["dataset_id"], "utc": iso(),
        "question": args.question, "source_hint": args.source_hint or ""})
    emit(root, repo, current_context(root), "context_requested", args.question,
         detail={"request_id": rid})
    print(rid)


def do_answer(args):
    root = root_of(args)
    prior = all_context_requests(root).get(args.request_id)
    if not prior:
        raise ValueError("Unknown context request ID")
    for repo in (root / "days").glob("tmfp-????-??-??"):
        for item in rows(repo / "context_requests.jsonl"):
            if item["request_id"] == args.request_id and item["phase"] == "answer":
                raise ValueError("Already answered; append further context as new contextual member")
    repo = ensure_day(root, check_date(args.date) if args.date else local_day(root))
    now = iso()
    append(repo / "context_requests.jsonl", {
        "id": new_id("ctxevt"), "request_id": args.request_id,
        "phase": "answer", "dataset_id": dataset_meta(root, jread(repo / "day.json")["date"])["dataset_id"],
        "day_id": jread(repo / "day.json")["day_id"], "utc": now,
        "subject_id": prior["subject_id"], "question": prior["question"],
        "value_json": dump(get_value(args)), "source_ref": args.source_ref or "",
        "evidence_status": "reference_unverified" if args.source_ref else "self_reported"})
    emit(root, repo, current_context(root), "context_answered", prior["question"],
         detail={"request_id": args.request_id})
    print(args.request_id)


def do_anchor(args):
    """A manually declared UTC-to-media-time alignment; not frame-accurate synchronization."""
    root = root_of(args)
    repo = ensure_day(root, check_date(args.date) if args.date else local_day(root))
    if args.media_time_ms < 0:
        raise ValueError("--media-time-ms must be nonnegative")
    try:
        anchor_time = dt.datetime.fromisoformat(args.utc.replace("Z", "+00:00")) if args.utc else utcnow()
    except ValueError as e:
        raise ValueError("--utc must be an ISO8601 date/time with offset") from e
    if anchor_time.tzinfo is None:
        raise ValueError("--utc requires timezone offset")
    rec = record_member(root, repo, key="media_time_anchor", kind="sync_anchor",
                        value={"recording_ref": args.recording, "media_time_ms": args.media_time_ms,
                               "utc": iso(anchor_time.astimezone(dt.timezone.utc)),
                               "method": "human_declared_alignment"},
                        description="Manually asserted media clock alignment", source_ref=args.recording)
    emit(root, repo, current_context(root), "media_anchor_recorded", args.recording,
         detail={"member_id": rec["id"]})
    print(rec["id"])


def experience_rows(root):
    """Derive Q/K -> V training projections from separately time-stamped events.

    Raw records are append-only. Training rows are regenerated, not treated as
    privileged descriptions of the world. Later-day outcomes remain supported.
    """
    starts, outcomes = {}, {}
    for repo in sorted((root / "days").glob("tmfp-????-??-??")):
        for item in rows(repo / "experiences.jsonl"):
            eid = item["experience_id"]
            if item["phase"] == "expectation":
                if eid in starts:
                    raise ValueError(f"Duplicate expectation: {eid}")
                starts[eid] = item
            elif item["phase"] == "outcome":
                if eid in outcomes:
                    raise ValueError(f"Duplicate outcome: {eid}")
                outcomes[eid] = item
    assembled = []
    for eid, result in outcomes.items():
        start = starts.get(eid)
        if not start:
            raise ValueError(f"Outcome without expectation: {eid}")
        if result["utc"] <= start["utc"]:
            raise ValueError(f"Outcome not later than expectation: {eid}")
        prompt = "WORLD MOMENT (Q):\n" + start["q"] + "\nEXPECTED (K):\n" + start["k"] + "\nACTUAL (V):\n"
        assembled.append({
            "experience_id": eid,
            "day_id": result["day_id"],  # dataset projection assigned to outcome day
            "expectation_day_id": start["day_id"],
            "expectation_utc": start["utc"],
            "outcome_utc": result["utc"],
            "q": start["q"], "k": start["k"], "v": result["v"],
            "prompt": prompt, "completion": result["v"],
            "design_declared": start["design_declared"],
            "mark_ref": start["mark_ref"],
            "referent": start["referent"],
            "address": start["address"],
            "outcome_evidence_ref": result["evidence_ref"],
            "evidence_status": "reference_unverified" if result["evidence_ref"] else "self_reported",
            "causal_status": "not_established",
        })
    return sorted(assembled, key=lambda item: (item["outcome_utc"], item["experience_id"]))


def do_expect(args):
    root = root_of(args)
    repo = ensure_day(root, check_date(args.date) if args.date else local_day(root))
    a = current_context(root)
    eid = new_id("experience")
    record = {"experience_id": eid, "phase": "expectation", "day_id": jread(repo / "day.json")["day_id"],
              "utc": iso(), "q": args.q, "k": args.k, "design_declared": args.design,
              "mark_ref": args.mark or "", "referent": args.referent or "",
              "address": a["address"] if a else ""}
    append(repo / "experiences.jsonl", record)
    emit(root, repo, a, "qkv_expectation_recorded", "Q/K recorded before outcome", detail={"experience_id": eid})
    print(eid)


def do_resolve(args):
    root = root_of(args)
    originals = {}
    resolved = set()
    for repo in (root / "days").glob("tmfp-????-??-??"):
        for item in rows(repo / "experiences.jsonl"):
            if item["phase"] == "expectation":
                originals[item["experience_id"]] = item
            elif item["phase"] == "outcome":
                resolved.add(item["experience_id"])
    if args.experience_id not in originals:
        raise ValueError("Unknown experience ID")
    if args.experience_id in resolved:
        raise ValueError("Experience already resolved; historical outcome is append-only")
    original = originals[args.experience_id]
    when = iso()
    if when <= original["utc"]:
        raise ValueError("Outcome must be recorded after the expectation")
    repo = ensure_day(root, check_date(args.date) if args.date else local_day(root))
    a = current_context(root)
    entry = {"experience_id": args.experience_id, "phase": "outcome",
             "day_id": jread(repo / "day.json")["day_id"],
             "utc": when, "v": args.v, "evidence_ref": args.evidence or ""}
    append(repo / "experiences.jsonl", entry)
    emit(root, repo, a, "qkv_outcome_recorded", "V observed/declared after Q/K", detail={"experience_id": args.experience_id})
    print(args.experience_id)

def do_stop(args):
    root = root_of(args)
    a = current_context(root)
    if not a:
        raise ValueError("No active session")
    repo = ensure_runtime_day(root)
    emit(root, repo, a, "session_ended", "Session ended")
    active_path(root).unlink()
    text_overlay(root, repo, None)
    print(f"Stopped {a['session_id']}")


def snapshot_hashes(repo):
    paths = [p for p in git(repo, "ls-files", "-z").split("\0") if p and p != "integrity/manifest.json"]
    hashes = []
    for rel in sorted(paths, key=lambda x: x.encode("utf-8")):
        full = repo / rel
        if full.is_symlink() or not full.is_file():
            raise ValueError(f"Missing or symbolic tracked file: {rel}")
        b = full.read_bytes()
        digest = hashlib.sha256(b).digest()
        hashes.append({"path": rel, "sha256": digest.hex(), "bytes": len(b)})
    return hashes


def merkle(entries):
    leafs = [hashlib.sha256(b"\x00" + e["path"].encode("utf-8") + b"\x00" + bytes.fromhex(e["sha256"])).digest() for e in entries]
    if not leafs:
        return hashlib.sha256(b"\x02").hexdigest()
    while len(leafs) > 1:
        if len(leafs) % 2:
            leafs.append(leafs[-1])
        leafs = [hashlib.sha256(b"\x01" + leafs[i] + leafs[i+1]).digest() for i in range(0, len(leafs), 2)]
    return leafs[0].hex()


def do_checkpoint(args):
    root = root_of(args)
    repo = repo_of(root, check_date(args.date) if args.date else local_day(root))
    if not (repo / "day.json").exists():
        raise ValueError("Daily index not initialized")
    revision = checkpoint(repo, args.message)
    print(f"Checkpoint {revision}; seal separately to refresh integrity manifest")


def do_seal(args):
    root = root_of(args)
    date = check_date(args.date) if args.date else local_day(root)
    repo = repo_of(root, date)
    if not (repo / "day.json").exists():
        raise ValueError(f"No daily index for {date}")
    stage(repo)
    entries = snapshot_hashes(repo)
    root_hash = merkle(entries)
    manifest = {"schema": "tmfp.merkle.v0", "day_id": jread(repo / "day.json")["day_id"],
                "root_sha256": root_hash, "files": entries, "sealed_at_utc": iso(),
                "excludes": ["integrity/manifest.json"],
                "claim": "Integrity of indexed local bytes only; not the physical world or remote media."}
    jwrite(repo / "integrity/manifest.json", manifest)
    revision = checkpoint(repo, "seal daily index " + date)
    print(f"Day {date} sealed | root={root_hash} | git={revision}")


def verify(repo, require_clean=True):
    manifest_file = repo / "integrity/manifest.json"
    if not manifest_file.exists():
        raise ValueError("Not sealed")
    m = jread(manifest_file)
    actual = snapshot_hashes(repo)
    if actual != m["files"] or merkle(actual) != m["root_sha256"]:
        raise ValueError("Sealed files changed; root mismatch")
    if require_clean and git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Uncommitted/untracked files exist")
    return m


def do_verify(args):
    root = root_of(args)
    repo = repo_of(root, check_date(args.date) if args.date else local_day(root))
    m = verify(repo)
    ref = jread(repo / "day.json").get("previous_index_snapshot")
    if args.ancestors and ref:
        prev_date = ref["day_id"].split(":")[-1]
        prev = repo_of(root, prev_date)
        if not prev.exists() or verify(prev)["root_sha256"] != ref["root_sha256"]:
            raise ValueError("Previous indexed snapshot no longer matches")
    print(f"VERIFIED {m['day_id']} | {m['root_sha256']}")


def day_records(root, repo):
    """Make one searchable view of *all* addressable relations, not only predictions."""
    date = jread(repo / "day.json")["date"]
    meta = dataset_meta(root, date)
    dsid = meta["dataset_id"]
    result = []
    def push(kind, row, key, value, subject=None, provenance=None):
        result.append({"id": row["id"], "dataset_id": dsid,
                       "day_id": meta["day_id"], "utc": row.get("utc", ""),
                       "kind": kind, "subject_id": subject or dsid, "key": key,
                       "value_json": dump(value), "provenance_json": dump(provenance or {}),
                       "source_id": row["id"]})
    for r in rows(repo / "members.jsonl"):
        push(r["kind"], r, r["key"], json.loads(r["value_json"]),
             r.get("subject_id"), {"source_ref": r.get("source_ref", ""),
                                    "context_json": r.get("context_json", "{}"),
                                    "assertion_status": r.get("assertion_status", "")})
    for r in rows(repo / "contexts.jsonl"):
        push("context", r, r["key"], json.loads(r["value_json"]),
             r.get("subject_id"), {"source_ref": r.get("source_ref", ""),
                                    "assertion_status": r["assertion_status"]})
    for r in rows(repo / "pieces.jsonl"):
        push("piece", r, r["key"], {"description": r["description"],
             "value": json.loads(r["value_json"]), "uri": r["uri"],
             "sha256": r["sha256"]}, provenance={"evidence_status": r["evidence_status"],
             "address": r["address"], "focus": r["focus"]})
    for r in rows(repo / "events.jsonl"):
        push("event", r, r["kind"], {"description": r["description"],
             "detail": json.loads(r["detail_json"]), "elapsed_ms": r["elapsed_ms"]},
             provenance={"speaker": r["speaker"], "session_id": r["session_id"],
                         "address": r["address"], "focus": r["focus"], "piece_id": r["piece_id"]})
    for r in rows(repo / "relations.jsonl"):
        push("relation", r, r["predicate"], {"object_id": r["object_id"],
             "description": r["description"]}, subject=r["subject_id"],
             provenance={"assertion_status": r["assertion_status"],
                         "evidence_id": r["evidence_id"]})
    for r in rows(repo / "experiences.jsonl"):
        push("legacy_experience_journal", {**r, "id": f"journal:{r['experience_id']}:{r['phase']}"},
             r["phase"], r, subject=r["experience_id"],
             provenance={"note": "Legacy expectation/outcome is an optional task, not generic K:V semantics"})
    for r in rows(repo / "context_requests.jsonl"):
        push("context_research", r, r["phase"], r, subject=r["subject_id"],
             provenance={"request_id": r["request_id"]})
    return sorted(result, key=lambda r: (r["utc"], r["id"]))


def lm_chunks(meta, entries, max_chars=24000):
    """Portable self-supervised text. Each row is a complete JSON object with context.

    Does not invent training targets, or pretend each row is one whole experience.
    Chunks preserve member boundaries unless a single member exceeds max_chars.
    """
    if max_chars < 1000:
        raise ValueError("max_chars must be >= 1000")
    # Keep stable, canonical JSON within each chunk, preserving parent dataset identity.
    result, batch, size = [], [], 0
    def flush():
        nonlocal batch, size
        if not batch:
            return
        obj = {"query_entity": meta, "members": batch,
               "note": "Contextualized source representation, not verified physical ground truth"}
        result.append({"dataset_id": meta["dataset_id"],
                       "chunk_index": len(result), "text": dump(obj),
                       "first_member_id": batch[0]["id"],
                       "last_member_id": batch[-1]["id"], "member_count": len(batch)})
        batch, size = [], 0
    for rec in entries:
        cost = len(dump(rec)) + 1
        if batch and size + cost > max_chars:
            flush()
        batch.append(rec)
        size += cost
    flush()
    if not result:
        result.append({"dataset_id": meta["dataset_id"], "chunk_index": 0,
                       "text": dump({"query_entity": meta, "members": [],
                                     "note": "Empty recorded day; metadata only"}),
                       "first_member_id": "", "last_member_id": "", "member_count": 0})
    for rec in result:
        rec["chunk_count"] = len(result)
    return result


def write_hf_configs(export, groups, *, default="datasets", title="TMFP Dataset"):
    if not groups.get(default):
        raise ValueError("Default HF dataset config must contain records")
    (export / "data").mkdir(parents=True, exist_ok=True)
    configs = []
    for name, records in groups.items():
        if not records:
            continue
        write(export / "data" / f"{name}.jsonl", "".join(dump(x) + "\n" for x in records))
        configs.extend([f"  - config_name: {name}",
                        *(["    default: true"] if name == default else []),
                        "    data_files:", "      - split: full", f"        path: data/{name}.jsonl"])
    return ("---\n" + "pretty_name: " + json.dumps(title, ensure_ascii=False)
            + "\ntags:\n  - longitudinal\n  - provenance\n  - experiential-data\nconfigs:\n"
            + "\n".join(configs) + "\n---\n")


def hf_export(repo, root):
    m = verify(repo)
    day = jread(repo / "day.json")
    meta = dataset_meta(root, day["date"])
    export = root / "exports" / day["date"]
    if export.exists():
        if export.is_symlink():
            raise ValueError("Export path must not be a symlink")
        shutil.rmtree(export)
    (export / "data").mkdir(parents=True)
    if (repo / "objects").is_dir():
        shutil.copytree(repo / "objects", export / "objects")
    members = day_records(root, repo)
    pointer = {"dataset_id": meta["dataset_id"], "day_id": day["day_id"],
               "day_number": meta["day_number"] or 0, "title": meta["title"],
               "date": day["date"], "timezone": day["timezone"],
               "query_json": dump(meta), "context_json": dump(meta.get("context", {})),
               "provenance_json": dump(meta.get("provenance", {})),
               "member_refs_json": dump([r["id"] for r in members]),
               "member_count": len(members), "git_revision": git(repo, "rev-parse", "HEAD"),
               "merkle_root": m["root_sha256"],
               "previous_snapshot_json": dump(day.get("previous_index_snapshot"))}
    # Cross-day Q/K-before-V examples are a *derived* optional task, never ontology.
    sealed_ids = set()
    for other in (root / "days").glob("tmfp-????-??-??"):
        if (other / "integrity/manifest.json").is_file():
            try:
                verify(other)
                sealed_ids.add(jread(other / "day.json")["day_id"])
            except ValueError:
                pass
    qkv = [r for r in experience_rows(root) if r["day_id"] == day["day_id"]
           and r["expectation_day_id"] in sealed_ids]
    groups = {
        "datasets": [pointer],
        "members": members,
        "lm_chunks": lm_chunks(meta, members),
        "days": [{"day_id": day["day_id"], "date": day["date"],
                  "timezone": day["timezone"], "scope": day["scope"],
                  "dataset_id": meta["dataset_id"], "day_number": meta["day_number"] or 0,
                  "title": meta["title"],
                  "git_revision": pointer["git_revision"], "merkle_root": m["root_sha256"],
                  "previous_snapshot_json": pointer["previous_snapshot_json"],
                  "piece_count": len(rows(repo / "pieces.jsonl")),
                  "event_count": len(rows(repo / "events.jsonl")),
                  "relation_count": len(rows(repo / "relations.jsonl"))}],
        "pieces": rows(repo / "pieces.jsonl"),
        "events": rows(repo / "events.jsonl"),
        "relations": rows(repo / "relations.jsonl"),
        "kv": rows(repo / "members.jsonl"),
        "contexts": rows(repo / "contexts.jsonl"),
        "context_requests": rows(repo / "context_requests.jsonl"),
        "experiences": rows(repo / "experiences.jsonl"),
        "qkv_predictions": qkv,
        "qkv": qkv,  # v0.3 compatibility alias; not native transformer attention keys
    }
    header = write_hf_configs(export, groups, title=meta["title"])
    doc = (f"# {meta['title']}\n\n"
           "**One daily dataset. One addressable query-entity representing a bounded, recorded experience.**\n\n"
           "This is not the physical world or its complete experience. `datasets` contains the day as one "
           "query/index row; `members` contains recursively addressable K:V records and other "
           "time-stamped source relationships; `lm_chunks` contains context-aware serialized JSON "
           "for ordinary next-token modeling. **Chunks are storage/training conveniences, "
           "not new physical days or independent experiences.**\n\n"
           "`kv` is generic structured member data; `contexts` is declared provenance/context; "
           "`context_requests` records missing contextual research needs and later answers. "
           "`pieces`, `events`, `relations`, and `experiences` preserve raw journals. "
           "`qkv_predictions` is an optional, derived expectation/outcome task; its Q/K/V "
           "labels do **not** define generic relational QKV and are **not** attention tensors.\n\n"
           "All datasets expose an unsplit `full` view; this is not an independent ML evaluation split. "
           "Text was not automatically adjudicated for truth, completeness, or causal validity.\n\n"
           "## Evidence and publication\n\n"
           "A declared reference does not verify remote content. Source hashes attest local bytes only. "
           "Check consent, personal information, rights, secrets, and source licenses before "
           "making this dataset public or reusing it for model training.\n\n"
           f"Source Git revision: `{pointer['git_revision']}`. "
           f"Source Merkle root: `{m['root_sha256']}`.\n")
    write(export / "README.md", header + doc)
    jwrite(export / "integrity.json", {"source_manifest": m, "day": day, "dataset": meta,
                                        "projection_schema": "tmfp.hf-projection.v0.4",
                                        "note": "Export is a verified projection, not a Git clone"})
    print(f"Exported {meta['title']} | {export} | members={len(members)}, LM chunks={len(groups['lm_chunks'])}")
    return export


def corpus_export(root):
    """Longitudinal index of independently verified daily dataset entities."""
    conf(root)
    export = root / "exports" / "corpus"
    day_rows, relations, contexts, reqs, datasets = [], [], [], [], []
    for repo in sorted((root / "days").glob("tmfp-????-??-??")):
        if not (repo / "integrity/manifest.json").exists():
            continue
        manifest = verify(repo)
        day = jread(repo / "day.json")
        meta = dataset_meta(root, day["date"])
        remote = git(repo, "remote", "get-url", "origin") if "origin" in git(repo, "remote").splitlines() else ""
        dsrow = {"dataset_id": meta["dataset_id"], "title": meta["title"],
                 "day_id": day["day_id"], "date": day["date"],
                 "day_number": meta["day_number"] or 0, "merkle_root": manifest["root_sha256"],
                 "git_revision": git(repo, "rev-parse", "HEAD"), "github_remote": remote,
                 "day_dataset_name": repo.name, "query_json": dump(meta)}
        datasets.append(dsrow)
        day_rows.append({"day_id": day["day_id"], "date": day["date"],
                         "timezone": day["timezone"], "scope": day["scope"],
                         "merkle_root": manifest["root_sha256"],
                         "git_revision": dsrow["git_revision"], "github_remote": remote,
                         "preceding_snapshot_json": dump(day.get("previous_index_snapshot")),
                         "piece_count": len(rows(repo / "pieces.jsonl")),
                         "event_count": len(rows(repo / "events.jsonl")),
                         "relation_count": len(rows(repo / "relations.jsonl")),
                         "day_dataset_name": repo.name, "dataset_id": meta["dataset_id"],
                         "day_number": meta["day_number"] or 0, "title": meta["title"]})
        relations.extend(rows(repo / "relations.jsonl"))
        contexts.extend(rows(repo / "contexts.jsonl"))
        reqs.extend(rows(repo / "context_requests.jsonl"))
    if not day_rows:
        raise ValueError("No sealed daily datasets exist")
    if export.exists():
        if export.is_symlink():
            raise ValueError("Export path must not be a symlink")
        shutil.rmtree(export)
    (export / "data").mkdir(parents=True)
    sealed_ids = {r["day_id"] for r in day_rows}
    qkv = [r for r in experience_rows(root)
           if r["day_id"] in sealed_ids and r["expectation_day_id"] in sealed_ids]
    series_members = [{"id": "series-member:" + r["dataset_id"],
                       "subject_id": "tmfp:series:vibe-inventing-world-peace",
                       "key": f"day-{r['day_number']:04d}",
                       "value_json": dump({"dataset_id": r["dataset_id"],
                                           "date": r["date"], "title": r["title"],
                                           "merkle_root": r["merkle_root"]}),
                       "dataset_id": r["dataset_id"],
                       "relation": "is_member_of_series"} for r in datasets]
    groups = {"datasets": datasets, "series_members": series_members,
              "days": day_rows, "relations": relations,
              "contexts": contexts, "context_requests": reqs,
              "qkv_predictions": qkv, "qkv": qkv}
    header = write_hf_configs(export, groups, title=f"{SERIES} | Longitudinal dataset index")
    write(export / "README.md", header + "# Vibe-Inventing World Peace — longitudinal index\n\n"
          "One *addressable dataset entity* per observer-defined day. This index lists their verified "
          "Git snapshots and links. Daily datasets carry the actual member records and contextualized "
          "self-supervised training views. No independent evaluation split or permission for model training "
          "is implied. A day boundary is not a causal or experiential boundary.\n")
    print(f"Corpus exported: {export} | days={len(day_rows)} relations={len(relations)}")
    return export


def do_export_corpus(args):
    corpus_export(root_of(args))


def do_export(args):
    root = root_of(args)
    repo = repo_of(root, check_date(args.date) if args.date else local_day(root))
    hf_export(repo, root)


def do_github(args):
    root = root_of(args)
    repo = repo_of(root, check_date(args.date) if args.date else local_day(root))
    verify(repo)
    if args.public and not args.reviewed:
        raise ValueError("Public release requires --reviewed after manual privacy/consent/rights review")
    if not shutil.which("gh"):
        raise ValueError("Install and authenticate GitHub CLI: gh auth login")
    name = f"{args.owner}/{repo.name}"
    remotes = git(repo, "remote").splitlines()
    if "origin" not in remotes:
        cmd("gh", "repo", "create", name, "--source", str(repo), "--remote", "origin",
            "--public" if args.public else "--private", "--push")
    else:
        # An existing public repository is public even without --public.
        try:
            visibility = cmd("gh", "repo", "view", "--json", "visibility", "--jq", ".visibility", cwd=repo).upper()
        except RuntimeError as exc:
            raise ValueError("Could not establish GitHub remote visibility; refusing to push") from exc
        if visibility != "PRIVATE" and not args.reviewed:
            raise ValueError("Existing remote may be public; pass --reviewed after manual rights/consent review")
        git(repo, "push", "origin", "HEAD")
    print(f"GitHub publish attempted: https://github.com/{name} (visibility of existing remote is unchanged)")


def do_hf_publish(args):
    root = root_of(args)
    repo = repo_of(root, check_date(args.date) if args.date else local_day(root))
    if args.public and not args.reviewed:
        raise ValueError("Public release requires --reviewed after manual privacy/consent/rights review")
    folder = corpus_export(root) if args.corpus else hf_export(repo, root)
    try:
        from huggingface_hub import HfApi
    except ImportError:
        raise ValueError("For publishing: python3 -m pip install huggingface_hub")
    api = HfApi()
    api.create_repo(repo_id=args.repo, repo_type="dataset", private=not args.public, exist_ok=True)
    # Existing Hub repositories retain prior visibility; check it before upload.
    remote_info = api.repo_info(repo_id=args.repo, repo_type="dataset")
    if not remote_info.private and not args.reviewed:
        raise ValueError("Existing dataset repository is public; --reviewed is required before upload")
    api.upload_folder(repo_id=args.repo, repo_type="dataset", folder_path=str(folder))
    print(f"Published dataset: https://huggingface.co/datasets/{args.repo} (existing visibility unchanged)")


def do_status(args):
    root = root_of(args)
    conf(root)
    date = check_date(args.date) if args.date else local_day(root)
    repo = repo_of(root, date)
    info = {"date": date, "repo": str(repo), "session": current_context(root),
            "merkle_root": manifest_root(repo) if repo.exists() else None}
    if (repo / "day.json").exists():
        meta = dataset_meta(root, date)
        info.update({"title": meta["title"], "dataset_id": meta["dataset_id"], "day_number": meta["day_number"]})
    if repo.exists():
        info.update({"pieces": len(rows(repo / "pieces.jsonl")),
                     "events": len(rows(repo / "events.jsonl")),
                     "relations": len(rows(repo / "relations.jsonl")),
                     "members": len(rows(repo / "members.jsonl")),
                     "context_items": len(rows(repo / "contexts.jsonl")),
                     "context_requests": len(rows(repo / "context_requests.jsonl"))})
    print(json.dumps(info, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description="TMFP Vibe Day: one queryable experience dataset per livestream day")
    parser.add_argument("--version", action="version", version=f"TMFP Vibe Day {VERSION}")
    parser.add_argument("--home", default="~/tmfp-vibe", help="Workspace root (default: ~/tmfp-vibe)")
    sub = parser.add_subparsers(dest="operation", required=True)
    def add(name, func, dated=False):
        p = sub.add_parser(name)
        if dated:
            p.add_argument("--date", help="Observer's local day YYYY-MM-DD")
        p.set_defaults(fn=func)
        return p
    p=add("init", do_init)
    p.add_argument("--timezone", default="America/Anchorage")
    p.add_argument("--first-day-number", type=int, default=1)
    p=add("start", do_start, dated=True)
    p.add_argument("--mode", default="JUST_CHATTING")
    p.add_argument("--address", default="aurora-future,wilder-present")
    p.add_argument("--topic", default="Vibe-inventing world peace")
    p=add("state", do_state)
    for x in ("mode", "address", "focus", "topic"):
        p.add_argument("--" + x)
    p=add("mark", do_mark)
    p.add_argument("text")
    p.add_argument("--kind", default="spoken_marginalia")
    p.add_argument("--key", default="annotation")
    p.add_argument("--data", default="{}")
    p.add_argument("--address")
    p.add_argument("--focus")
    p=add("add", do_add, dated=True)
    p.add_argument("--kind", default="artifact")
    p.add_argument("--key", default="object")
    p.add_argument("--description", required=True)
    p.add_argument("--data", default="{}")
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument("--file")
    source.add_argument("--uri")
    p.add_argument("--sha256", help="Claimed remote checksum (not verified by tool)")
    p=add("relate", do_relate, dated=True)
    p.add_argument("subject")
    p.add_argument("predicate")
    p.add_argument("object")
    p.add_argument("--description")
    p.add_argument("--evidence")
    p=add("member", do_member, dated=True)
    p.add_argument("--key", required=True)
    vp=p.add_mutually_exclusive_group(required=True)
    vp.add_argument("--value")
    vp.add_argument("--value-json", help="Any JSON value; objects/arrays supported")
    p.add_argument("--kind", default="kv")
    p.add_argument("--subject", help="Entity this K:V belongs to (default: day dataset)")
    p.add_argument("--context", default="{}", help="Structured local context JSON object")
    p.add_argument("--source-ref", help="Evidence or provenance pointer (not independently verified)")
    p.add_argument("--description")
    p=add("context", do_context, dated=True)
    p.add_argument("--key", required=True)
    vp=p.add_mutually_exclusive_group(required=True)
    vp.add_argument("--value")
    vp.add_argument("--value-json")
    p.add_argument("--subject")
    p.add_argument("--source-ref")
    p.add_argument("--description")
    p=add("need", do_need, dated=True)
    p.add_argument("question")
    p.add_argument("--subject")
    p.add_argument("--source-hint")
    p=add("answer", do_answer, dated=True)
    p.add_argument("request_id")
    vp=p.add_mutually_exclusive_group(required=True)
    vp.add_argument("--value")
    vp.add_argument("--value-json")
    p.add_argument("--source-ref")
    p=add("anchor", do_anchor, dated=True)
    p.add_argument("--recording", required=True, help="URI/piece ID for recording")
    p.add_argument("--media-time-ms", type=int, required=True)
    p.add_argument("--utc", help="Observed UTC/media anchor as ISO8601 with offset; default now")
    p=add("expect", do_expect, dated=True)
    p.add_argument("--q", required=True, help="World moment (Q), expressed or referenced")
    p.add_argument("--k", required=True, help="Expectation/prediction (K), declared before outcome")
    p.add_argument("--design", default="observational", choices=["observational", "intentional_intervention", "simulation"])
    p.add_argument("--mark", help="Optional reference to a deliberately introduced mark/perturbation")
    p.add_argument("--referent", help="Optional OXI/piece URI or persistent identifier")
    p=add("resolve", do_resolve, dated=True)
    p.add_argument("experience_id", help="ID printed by expect")
    p.add_argument("--v", required=True, help="Observed continuation / outcome (V)")
    p.add_argument("--evidence", help="Optional evidence pointer; NOT independently verified")
    add("stop", do_stop)
    add("tick", lambda args: print(ensure_runtime_day(root_of(args))))
    add("status", do_status, dated=True)
    p=add("checkpoint", do_checkpoint, dated=True)
    p.add_argument("message")
    add("seal", do_seal, dated=True)
    p=add("verify", do_verify, dated=True)
    p.add_argument("--ancestors", action="store_true", help="Also verify linked preceding snapshot")
    add("export-hf", do_export, dated=True)
    add("export-corpus", do_export_corpus)
    p=add("publish-github", do_github, dated=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--public", action="store_true", help="Default private; no change to existing remote visibility")
    p.add_argument("--reviewed", action="store_true", help="Affirm you reviewed privacy, rights and consent for public publication")
    p=add("publish-hf", do_hf_publish, dated=True)
    p.add_argument("--repo", required=True, help="namespace/dataset-name")
    p.add_argument("--public", action="store_true", help="Default private; existing remote visibility unchanged")
    p.add_argument("--reviewed", action="store_true", help="Affirm you reviewed privacy, rights and consent for public publication")
    p.add_argument("--corpus", action="store_true", help="Publish longitudinal index instead of one day")
    args=parser.parse_args(argv)
    try:
        if args.operation in {"init", "start", "state", "mark", "add", "relate", "member", "context", "need", "answer", "anchor", "expect", "resolve", "stop", "tick", "checkpoint", "seal"}:
            with local_lock(root_of(args)):
                args.fn(args)
        else:
            args.fn(args)
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as error:
        print(f"TMFP: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
