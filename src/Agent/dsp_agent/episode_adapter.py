"""Turn attributed game snapshots into reward proofs; never infer production from inventory."""

import json
from dataclasses import asdict
from pathlib import Path

from .evidence import EvidenceError, ProductionSample, ProductionVerifier
from .reward import EpisodeResult, ProductionWindow, SignalProof, WhiteThroughput


def iron_sample_from_entity(payload, *, save_copy_id, checkpoint_sha256, game_version):
    """Read the UI-checked one-ingot-per-cycle counter for this installed recipe."""
    if (not isinstance(payload, dict) or payload.get("protocol_version") != 1
            or payload.get("status") != "ok"
            or game_version not in ("0.10.35.29057", "0.10.35.29088")):
        raise EvidenceError("loaded entity observation is required")
    entity = payload.get("entity")
    assembler = entity.get("assembler") if isinstance(entity, dict) else None
    inputs = assembler.get("inputs") if isinstance(assembler, dict) else None
    outputs = assembler.get("outputs") if isinstance(assembler, dict) else None
    if (not isinstance(entity, dict) or entity.get("proto_id") != 2302
            or not isinstance(assembler, dict) or assembler.get("recipe_id") != 1
            or assembler.get("extra_cycle_count") != 0
            or not isinstance(inputs, list) or len(inputs) != 1
            or not isinstance(inputs[0], dict)
            or inputs[0].get("item_id") != 1001 or inputs[0].get("per_cycle") != 1
            or not isinstance(outputs, list) or len(outputs) != 1
            or not isinstance(outputs[0], dict)
            or outputs[0].get("item_id") != 1101 or outputs[0].get("per_cycle") != 1):
        raise EvidenceError("entity does not match the verified iron-smelting recipe")
    count = assembler.get("cycle_count")
    tick = payload.get("game_tick")
    planet_id = payload.get("planet_id")
    entity_id = payload.get("entity_id")
    if (any(isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in (count, tick, planet_id, entity_id))
            or any(isinstance(slot.get("buffered"), bool)
                   or not isinstance(slot.get("buffered"), int)
                   or slot["buffered"] < 0 for slot in (inputs[0], outputs[0]))):
        raise EvidenceError("invalid assembler cycle counter")
    sample = ProductionSample(session_id=payload.get("session_id"),
                              save_copy_id=save_copy_id,
                              checkpoint_sha256=checkpoint_sha256,
                              game_version=game_version,
                              planet_id=planet_id, entity_id=entity_id, item_id=1101,
                              recipe_id=1, game_tick=tick,
                              produced_total=count, source="game_production_counter")
    sample.validate()
    return sample


def proof_from_windows(signal_name, evidence_id, samples, ui_refs, *, window_ticks,
                       required_windows=2):
    """Return no proof for a stalled line, missing UI comparisons, or manual mining."""
    if not isinstance(samples, (tuple, list)) or not samples:
        return None
    if not isinstance(ui_refs, (tuple, list)):
        raise EvidenceError("window UI references are required")
    verifier = ProductionVerifier(window_ticks, required_windows)
    for sample in samples:
        verifier.observe(sample)
    status = verifier.status()
    if not status["confirmed"]:
        return None
    windows = status["windows"][-required_windows:]
    if (len(ui_refs) != len(status["windows"]) or
            any(not isinstance(ref, str) or not ref for ref in ui_refs[-required_windows:])):
        raise EvidenceError("each confirmed window needs a visible UI reference")
    proof = SignalProof(signal_name, "entity_counter", evidence_id,
                        tuple(ProductionWindow(window["end_tick"] - window["start_tick"],
                                               window["produced"]) for window in windows))
    proof.validate()
    return proof


def episode_from_record(record):
    """Scoreable episode metadata stays tied to its private, exact-copy samples."""
    if not isinstance(record, dict):
        raise EvidenceError("episode record must be an object")
    try:
        samples = tuple(ProductionSample(**entry) for entry in record["samples"])
        first = samples[0]
        identity = (first.save_copy_id, first.checkpoint_sha256, first.session_id,
                    first.game_version, first.planet_id, first.entity_id, first.item_id)
        expected = tuple(record[key] for key in ("save_copy_id", "checkpoint_sha256",
                    "session_id", "game_version", "planet_id", "entity_id", "item_id"))
        if identity != expected:
            raise EvidenceError("episode and sample identity differ")
        signal_name = record["signal_name"]
        if signal_name not in ("iron_ingot_output_sustained", "white_matrix_output_sustained"):
            raise EvidenceError("signal has no audited game item mapping")
        if signal_name == "iron_ingot_output_sustained" and (
                first.item_id != 1101 or first.recipe_id != 1):
            raise EvidenceError("iron signal does not match the iron-ingot recipe")
        if signal_name == "iron_ingot_output_sustained" and (
                not isinstance(record.get("automated_input_ui_refs"), (list, tuple))
                or len(record["automated_input_ui_refs"]) != record.get("required_windows", 2)
                or any(not isinstance(ref, str) or not ref
                       for ref in record["automated_input_ui_refs"])):
            raise EvidenceError("each iron window needs observed automated ore input")
        if signal_name == "white_matrix_output_sustained" and not record.get("item_mapping_ui_ref"):
            raise EvidenceError("white-matrix item mapping needs a verified game reference")
        evidence_id = record["evidence_id"]
        if not isinstance(evidence_id, str) or not evidence_id:
            raise EvidenceError("private evidence ID is required")
        proof = proof_from_windows(signal_name, evidence_id, samples,
                                   record["window_ui_refs"], window_ticks=record["window_ticks"],
                                   required_windows=record.get("required_windows", 2))
        end_proofs = (proof,) if proof is not None else ()
        white = (WhiteThroughput(proof.source, proof.evidence_id, proof.windows)
                 if proof is not None and proof.name == "white_matrix_output_sustained" else None)
        return EpisodeResult(record["episode_id"], record["strategy_id"],
                             record["trial_key"], record["game_version"],
                             record["ordinary_mode"], record["elapsed_ticks"],
                             (), end_proofs, white)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise EvidenceError("invalid private episode record") from exc


def append_private_episode(path, record):
    """Append a raw JSON record to a caller-chosen ignored/private location."""
    episode_from_record(record)
    location = Path(path)
    location.parent.mkdir(parents=True, exist_ok=True)
    with location.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def sample_record(sample):
    return asdict(sample)
