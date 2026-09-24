using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEngine;

namespace DspAgentBridge
{
    // HTTP threads only enqueue and read snapshots. All game state is accessed in Tick.
    internal sealed class Movement
    {
        private const float MaxTargetDistance = 25f;
        private const long MaxTicks = 900;
        private const int MaxOperations = 16;
        private readonly object gate = new object();
        private readonly Dictionary<string, MoveOperation> operations = new Dictionary<string, MoveOperation>();
        private MoveOperation active;

        private sealed class MoveOperation
        {
            public string Id;
            public string SessionId;
            public int VeinId;
            public string Kind = "move";
            public int RequestedCount;
            public int StartInventory;
            public int CurrentInventory;
            public int StartVeinAmount;
            public int CurrentVeinAmount;
            public string Status = "pending";
            public string Reason;
            public int PlanetId;
            public long StartedTick;
            public long LastTick;
            public Vector3 Start;
            public Vector3 Target;
            public Vector3 Current;
            public OrderNode Order;
        }

        internal string Enqueue(string operationId, string sessionId, int veinId)
        {
            return EnqueueAction(operationId, sessionId, veinId, "move", 0);
        }

        internal string EnqueueMine(string operationId, string sessionId, int veinId, int count)
        {
            return EnqueueAction(operationId, sessionId, veinId, "mine", count);
        }

        private string EnqueueAction(string operationId, string sessionId, int veinId, string kind, int count)
        {
            lock (gate)
            {
                MoveOperation existing;
                if (operations.TryGetValue(operationId, out existing))
                {
                    if (existing.SessionId != sessionId || existing.VeinId != veinId ||
                        existing.Kind != kind || existing.RequestedCount != count)
                        return Error("operation_conflict");
                    return Snapshot(existing);
                }
                if (active != null) return Error("operation_in_progress");
                if (operations.Count >= MaxOperations) return Error("operation_limit");
                var operation = new MoveOperation { Id = operationId, SessionId = sessionId, VeinId = veinId,
                    Kind = kind, RequestedCount = count };
                operations.Add(operationId, operation);
                active = operation;
                return Snapshot(operation);
            }
        }

        internal string Get(string operationId)
        {
            lock (gate)
            {
                MoveOperation operation;
                return operations.TryGetValue(operationId, out operation) ? Snapshot(operation) : Error("unknown_operation");
            }
        }

        internal void Tick(string currentSessionId)
        {
            lock (gate)
            {
                var operation = active;
                if (operation == null) return;
                if (operation.Status == "pending")
                {
                    Start(operation, currentSessionId);
                    return;
                }
                if (operation.Status != "running") return;
                if (currentSessionId == null || currentSessionId != operation.SessionId || !Observer.IsReady())
                {
                    Finish(operation, "partial", "session_changed");
                    return;
                }
                var player = GameMain.mainPlayer;
                operation.Current = player.position;
                operation.LastTick = GameMain.gameTick;
                if (operation.Kind == "mine")
                {
                    var factory = GameMain.localPlanet.factory;
                    operation.CurrentInventory = CountItem(player.package, 1001);
                    operation.CurrentVeinAmount = factory != null && factory.veinPool != null &&
                        operation.VeinId < factory.veinPool.Length && factory.veinPool[operation.VeinId].id == operation.VeinId
                        ? factory.veinPool[operation.VeinId].amount : 0;
                    if (operation.CurrentInventory - operation.StartInventory >= operation.RequestedCount &&
                        operation.StartVeinAmount - operation.CurrentVeinAmount >= operation.RequestedCount)
                    {
                        if (player.currentOrder == operation.Order) player.AbortOrder();
                        Finish(operation, "completed", null);
                        return;
                    }
                }
                if (operation.Kind == "move" && operation.Order.targetReached)
                {
                    Finish(operation, "completed", null);
                    return;
                }
                if (GameMain.isPaused || player.currentOrder != operation.Order ||
                    GameMain.gameTick - operation.StartedTick > MaxTicks)
                {
                    var reason = GameMain.isPaused ? "paused" :
                        player.currentOrder != operation.Order ? "order_interrupted" : "action_timeout";
                    if (player.currentOrder == operation.Order) player.AbortOrder();
                    Finish(operation, "partial", reason);
                }
            }
        }

        internal void FailActive()
        {
            lock (gate)
            {
                if (active != null) Finish(active, "partial", "bridge_error");
            }
        }

        private void Start(MoveOperation operation, string currentSessionId)
        {
            if (currentSessionId == null || currentSessionId != operation.SessionId || !Observer.IsReady())
            {
                Finish(operation, "rejected", "session_mismatch");
                return;
            }
            if (GameMain.isPaused)
            {
                Finish(operation, "rejected", "game_paused");
                return;
            }
            var player = GameMain.mainPlayer;
            var planet = GameMain.localPlanet;
            if (player.movementState != EMovementState.Walk || player.currentOrder != null)
            {
                Finish(operation, "rejected", "player_busy");
                return;
            }
            var factory = planet.factory;
            if (factory == null || factory.veinPool == null || operation.VeinId <= 0 ||
                operation.VeinId >= factory.veinCursor || operation.VeinId >= factory.veinPool.Length)
            {
                Finish(operation, "rejected", "invalid_vein");
                return;
            }
            var vein = factory.veinPool[operation.VeinId];
            if (vein.id != operation.VeinId || vein.amount <= 0)
            {
                Finish(operation, "rejected", "invalid_vein");
                return;
            }
            var distance = Vector3.Distance(player.position, vein.pos);
            if ((operation.Kind == "move" && distance < 2f) || distance > MaxTargetDistance)
            {
                Finish(operation, "rejected", "target_out_of_range");
                return;
            }
            if (operation.Kind == "mine" && (vein.type != EVeinType.Iron || vein.productId != 1001 ||
                GameMain.data.gameDesc.isInfiniteResource || !HasEmptySlot(player.package)))
            {
                Finish(operation, "rejected", "invalid_mining_target_or_inventory");
                return;
            }
            if (operation.Kind == "mine")
            {
                var veinProto = LDB.veins.Select((int)vein.type);
                if (veinProto == null || player.mecha.miningSpeed > veinProto.MiningTime)
                {
                    Finish(operation, "rejected", "mining_rate_unbounded");
                    return;
                }
            }
            operation.PlanetId = planet.id;
            operation.StartedTick = GameMain.gameTick;
            operation.LastTick = GameMain.gameTick;
            operation.Start = player.position;
            operation.Current = player.position;
            operation.Target = vein.pos;
            if (operation.Kind == "mine")
            {
                operation.StartInventory = CountItem(player.package, 1001);
                operation.CurrentInventory = operation.StartInventory;
                operation.StartVeinAmount = vein.amount;
                operation.CurrentVeinAmount = vein.amount;
                var direction = (vein.pos - player.position).normalized;
                var target = (vein.pos - direction * 1.5f).normalized * vein.pos.magnitude;
                operation.Target = target;
                operation.Order = OrderNode.MineTarget(target, EObjectType.Vein, vein.id, vein.pos);
            }
            else operation.Order = OrderNode.MoveTo(vein.pos);
            operation.Status = "running";
            player.Order(operation.Order, false);
        }

        private static int CountItem(StorageComponent package, int itemId)
        {
            if (package == null || package.grids == null) return 0;
            var count = 0;
            for (var i = 0; i < package.size && i < package.grids.Length && i < 256; i++)
                if (package.grids[i].itemId == itemId) count += package.grids[i].count;
            return count;
        }

        private static bool HasEmptySlot(StorageComponent package)
        {
            if (package == null || package.grids == null || package.size > 256) return false;
            for (var i = 0; i < package.size && i < package.grids.Length; i++)
                if (package.grids[i].itemId == 0 || package.grids[i].count <= 0) return true;
            return false;
        }

        private void Finish(MoveOperation operation, string status, string reason)
        {
            operation.Status = status;
            operation.Reason = reason;
            active = null;
        }

        internal static string Error(string reason)
        {
            return "{\"protocol_version\":1,\"status\":\"error\",\"error\":\"" + reason + "\"}";
        }

        private static string Snapshot(MoveOperation operation)
        {
            var json = new StringBuilder(512);
            json.Append("{\"protocol_version\":1,\"operation_id\":\"").Append(operation.Id);
            json.Append("\",\"status\":\"").Append(operation.Status);
            json.Append("\",\"session_id\":\"").Append(operation.SessionId);
            json.Append("\",\"vein_id\":").Append(operation.VeinId);
            json.Append(",\"action\":\"").Append(operation.Kind).Append('"');
            if (operation.Kind == "mine")
            {
                json.Append(",\"requested_count\":").Append(operation.RequestedCount);
                json.Append(",\"inventory_before\":").Append(operation.StartedTick > 0 ? operation.StartInventory.ToString() : "null");
                json.Append(",\"inventory_now\":").Append(operation.StartedTick > 0 ? operation.CurrentInventory.ToString() : "null");
                json.Append(",\"vein_amount_before\":").Append(operation.StartedTick > 0 ? operation.StartVeinAmount.ToString() : "null");
                json.Append(",\"vein_amount_now\":").Append(operation.StartedTick > 0 ? operation.CurrentVeinAmount.ToString() : "null");
            }
            json.Append(",\"planet_id\":").Append(operation.PlanetId > 0 ? operation.PlanetId.ToString() : "null");
            json.Append(",\"started_tick\":").Append(operation.StartedTick > 0 ? operation.StartedTick.ToString() : "null");
            json.Append(",\"last_tick\":").Append(operation.LastTick > 0 ? operation.LastTick.ToString() : "null");
            json.Append(",\"start_position\":");
            Position(json, operation.Start, operation.StartedTick > 0);
            json.Append(",\"target_position\":");
            Position(json, operation.Target, operation.StartedTick > 0);
            json.Append(",\"current_position\":");
            Position(json, operation.Current, operation.StartedTick > 0);
            json.Append(",\"reason\":");
            if (operation.Reason == null) json.Append("null");
            else json.Append('"').Append(operation.Reason).Append('"');
            return json.Append('}').ToString();
        }

        private static void Position(StringBuilder json, Vector3 position, bool known)
        {
            if (!known) { json.Append("null"); return; }
            json.Append("{\"x\":").Append(position.x.ToString("R", CultureInfo.InvariantCulture));
            json.Append(",\"y\":").Append(position.y.ToString("R", CultureInfo.InvariantCulture));
            json.Append(",\"z\":").Append(position.z.ToString("R", CultureInfo.InvariantCulture)).Append('}');
        }
    }
}
