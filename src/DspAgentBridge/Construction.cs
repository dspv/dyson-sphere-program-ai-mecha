using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEngine;

namespace DspAgentBridge
{
    // HTTP threads only enqueue. The game-owned preview is checked and consumed in Tick.
    internal sealed class Construction
    {
        private const int MaxOperations = 16;
        private const int SupportedItemId = 2302; // Arc Smelter only for the first live trial.
        private readonly object gate = new object();
        private readonly Dictionary<string, BuildOperation> operations = new Dictionary<string, BuildOperation>();
        private BuildOperation pending;

        private sealed class BuildOperation
        {
            public string Id;
            public string SessionId;
            public int ItemId;
            public Vector3 Expected;
            public string Status = "pending";
            public string Reason;
            public int PlanetId;
            public long Tick;
            public int PrebuildId;
        }

        internal string Enqueue(string operationId, string sessionId, int itemId, Vector3 expected)
        {
            lock (gate)
            {
                BuildOperation existing;
                if (operations.TryGetValue(operationId, out existing))
                {
                    if (existing.SessionId != sessionId || existing.ItemId != itemId ||
                        Vector3.Distance(existing.Expected, expected) > 0.0001f)
                        return Movement.Error("operation_conflict");
                    return Snapshot(existing);
                }
                if (pending != null) return Movement.Error("operation_in_progress");
                if (operations.Count >= MaxOperations) return Movement.Error("operation_limit");
                var operation = new BuildOperation { Id = operationId, SessionId = sessionId,
                    ItemId = itemId, Expected = expected };
                operations.Add(operationId, operation);
                pending = operation;
                return Snapshot(operation);
            }
        }

        internal string Get(string operationId)
        {
            lock (gate)
            {
                BuildOperation operation;
                return operations.TryGetValue(operationId, out operation) ? Snapshot(operation) : Movement.Error("unknown_operation");
            }
        }

        internal void Tick(string currentSessionId, bool movementBusy)
        {
            lock (gate)
            {
                var operation = pending;
                if (operation == null) return;
                try { Execute(operation, currentSessionId, movementBusy); }
                catch (Exception)
                {
                    // The game call may have mutated the world before an exception.
                    operation.Status = "partial";
                    operation.Reason = "build_readback_unknown";
                }
                finally { pending = null; }
            }
        }

        private static void Execute(BuildOperation operation, string currentSessionId, bool movementBusy)
        {
            if (!Observer.IsReady() || currentSessionId == null || currentSessionId != operation.SessionId)
            {
                Reject(operation, "session_mismatch");
                return;
            }
            if (GameMain.isPaused || movementBusy)
            {
                Reject(operation, GameMain.isPaused ? "game_paused" : "movement_in_progress");
                return;
            }
            var player = GameMain.mainPlayer;
            var planet = GameMain.localPlanet;
            var factory = planet.factory;
            var action = player.controller != null ? player.controller.actionBuild : null;
            var click = action != null ? action.clickTool : null;
            if (operation.ItemId != SupportedItemId || factory == null || player.currentOrder != null ||
                click == null || !click.active || action.activeTool != click ||
                click.buildPreviews == null || click.buildPreviews.Count != 1)
            {
                Reject(operation, "build_preview_unavailable");
                return;
            }
            var preview = click.buildPreviews[0];
            if (preview == null || preview.item == null || preview.item.ID != operation.ItemId ||
                preview.condition != EBuildCondition.Ok || preview.coverObjId != 0 || preview.isConnNode ||
                Vector3.Distance(preview.lpos, operation.Expected) > 0.15f)
            {
                Reject(operation, "stale_or_invalid_preview");
                return;
            }
            var inventoryBefore = CountItem(player.package, operation.ItemId) +
                (player.inhandItemId == operation.ItemId ? player.inhandItemCount : 0);
            if (inventoryBefore < 1 || !click.CheckBuildConditions() ||
                click.buildPreviews.Count != 1 || preview.condition != EBuildCondition.Ok ||
                Vector3.Distance(preview.lpos, operation.Expected) > 0.15f)
            {
                Reject(operation, "build_conditions_changed");
                return;
            }
            operation.PlanetId = planet.id;
            operation.Tick = GameMain.gameTick;
            var nextPrebuild = factory.prebuildCursor;
            click.CreatePrebuilds();
            var inventoryAfter = CountItem(player.package, operation.ItemId) +
                (player.inhandItemId == operation.ItemId ? player.inhandItemCount : 0);
            if (factory.prebuildCursor == nextPrebuild + 1 && inventoryBefore - inventoryAfter == 1 &&
                nextPrebuild < factory.prebuildPool.Length &&
                factory.prebuildPool[nextPrebuild].id == nextPrebuild &&
                factory.prebuildPool[nextPrebuild].protoId == operation.ItemId)
            {
                operation.Status = "completed";
                operation.PrebuildId = nextPrebuild;
            }
            else
            {
                operation.Status = "partial";
                operation.Reason = "build_readback_unknown";
            }
        }

        private static void Reject(BuildOperation operation, string reason)
        {
            operation.Status = "rejected";
            operation.Reason = reason;
        }

        private static int CountItem(StorageComponent package, int itemId)
        {
            if (package == null || package.grids == null) return 0;
            var count = 0;
            for (var i = 0; i < package.size && i < package.grids.Length && i < 256; i++)
                if (package.grids[i].itemId == itemId) count += package.grids[i].count;
            return count;
        }

        private static string Snapshot(BuildOperation operation)
        {
            var json = new StringBuilder(320);
            json.Append("{\"protocol_version\":1,\"operation_id\":\"").Append(operation.Id);
            json.Append("\",\"session_id\":\"").Append(operation.SessionId);
            json.Append("\",\"action\":\"confirm_build\",\"status\":\"").Append(operation.Status);
            json.Append("\",\"item_id\":").Append(operation.ItemId);
            json.Append(",\"expected_position\":{");
            json.Append("\"x\":").Append(operation.Expected.x.ToString("R", CultureInfo.InvariantCulture));
            json.Append(",\"y\":").Append(operation.Expected.y.ToString("R", CultureInfo.InvariantCulture));
            json.Append(",\"z\":").Append(operation.Expected.z.ToString("R", CultureInfo.InvariantCulture)).Append('}');
            json.Append(",\"planet_id\":").Append(operation.PlanetId > 0 ? operation.PlanetId.ToString() : "null");
            json.Append(",\"game_tick\":").Append(operation.Tick > 0 ? operation.Tick.ToString() : "null");
            json.Append(",\"prebuild_id\":").Append(operation.PrebuildId > 0 ? operation.PrebuildId.ToString() : "null");
            json.Append(",\"reason\":");
            if (operation.Reason == null) json.Append("null");
            else json.Append('"').Append(operation.Reason).Append('"');
            return json.Append('}').ToString();
        }
    }
}
