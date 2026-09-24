"""Check primitive bridge action effects from a terminal result and fresh readback.

An achieved verdict here establishes only the action's measured effect. It
cannot establish a factory milestone or that a free-text model hypothesis was
correct. Those need goal-specific and visible-game evidence.
"""

import math

from .experiment_runner import Verification


def _position(value):
    if not isinstance(value, dict):
        return None
    coordinates = [value.get(axis) for axis in ("x", "y", "z")]
    if any(isinstance(number, bool) or not isinstance(number, (int, float))
           or not math.isfinite(number) for number in coordinates):
        return None
    return coordinates


def _distance(first, second):
    left, right = _position(first), _position(second)
    if left is None or right is None:
        return None
    return math.dist(left, right)


def _count(inventory, item_id):
    if not isinstance(inventory, dict) or inventory.get("complete") is not True:
        return None
    items = inventory.get("items")
    if not isinstance(items, list):
        return None
    values = [entry.get("count") for entry in items
              if isinstance(entry, dict) and entry.get("item_id") == item_id]
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values):
        return None
    return sum(values)


def _vein_amount(nearby, vein_id):
    if not isinstance(nearby, dict) or not isinstance(nearby.get("veins"), list):
        return None
    for entry in nearby["veins"]:
        if isinstance(entry, dict) and entry.get("id") == vein_id:
            amount = entry.get("amount")
            return amount if isinstance(amount, int) and not isinstance(amount, bool) and amount >= 0 else None
    return None


def verify_bridge_action(before, after, planned, result):
    """Return a primitive effect verdict, never a strategic goal verdict."""
    kind = planned.action["kind"]
    if result.get("status") == "rejected":
        return Verification("failed", "bridge rejected action: " + str(result.get("reason")),
                            after.evidence_ref)
    if result.get("status") == "partial":
        return Verification("partial", "bridge reported partial action: " + str(result.get("reason")))
    if result.get("status") != "completed":
        return Verification("unknown", "action has no terminal result")
    if kind == "inspect":
        return Verification("achieved", "fresh read-only bridge observation was recorded",
                            after.evidence_ref)
    if kind == "inspect_entity":
        entity = result.get("entity")
        entity_id = planned.action["args"].get("entity_id")
        evidence_ref = result.get("evidence_ref")
        if (result.get("action") != "inspect_entity" or result.get("session_id") != after.session_id
                or result.get("entity_id") != entity_id or not isinstance(entity, dict)
                or not isinstance(evidence_ref, str) or not evidence_ref):
            return Verification("unknown", "exact entity evidence is incomplete")
        proto_id = entity.get("proto_id")
        if isinstance(proto_id, bool) or not isinstance(proto_id, int) or proto_id <= 0:
            return Verification("unknown", "exact entity prototype is incomplete")
        assembler = entity.get("assembler")
        if isinstance(assembler, dict):
            recipe = assembler.get("recipe_id")
            cycles = assembler.get("cycle_count")
            details = f"; recipe_id={recipe}, cycle_count={cycles}"
        else:
            details = "; assembler detail unavailable"
        return Verification("achieved", f"exact entity {entity_id} proto_id={proto_id} read recorded" + details,
                            evidence_ref)
    if result.get("session_id") != after.session_id or result.get("planet_id") != after.facts.get("planet", {}).get("id"):
        return Verification("unknown", "operation identity and fresh planet do not match")
    if kind == "move":
        displacement = _distance(before.facts.get("mecha_position"), after.facts.get("mecha_position"))
        target_distance = _distance(after.facts.get("mecha_position"), result.get("target_position"))
        if displacement is None or target_distance is None:
            return Verification("unknown", "movement position readback is incomplete")
        if displacement > 0.5 and target_distance <= 3:
            return Verification("achieved", "mecha moved near the requested vein", after.evidence_ref)
        return Verification("unknown", "completed movement lacks matching position readback")
    if kind == "mine":
        item_id = planned.action["args"]["item_id"]
        vein_id = planned.action["args"]["vein_id"]
        count = planned.action["args"]["count"]
        start_inventory = result.get("inventory_before")
        now_inventory = result.get("inventory_now")
        start_vein = result.get("vein_amount_before")
        now_vein = result.get("vein_amount_now")
        numbers = (start_inventory, now_inventory, start_vein, now_vein)
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in numbers):
            return Verification("unknown", "mining counters are incomplete")
        observed_inventory = _count(after.facts.get("inventory"), item_id)
        observed_vein = _vein_amount(after.facts.get("nearby_veins"), vein_id)
        if (now_inventory - start_inventory >= count and start_vein - now_vein >= count
                and observed_inventory is not None and observed_inventory >= now_inventory
                and observed_vein is not None and observed_vein <= now_vein):
            return Verification("achieved", "inventory gain and vein depletion match the mining order",
                                after.evidence_ref)
        return Verification("unknown", "completed mining lacks matching fresh inventory and vein readback")
    return Verification("unknown", "no primitive verifier for action")
