using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEngine;

namespace DspAgentBridge
{
    // Called only from Plugin.Update on Unity's game thread.
    internal static class Observer
    {
        private const int MaxInventorySlots = 256;
        private const int MaxEntityScan = 4096;
        private const int MaxNearbyEntities = 64;
        private const int MaxVeinScan = 4096;
        private const int MaxNearbyVeins = 64;
        private const float NearbyRadius = 25f;

        internal static bool IsReady()
        {
            var planet = GameMain.localPlanet;
            var player = GameMain.mainPlayer;
            return GameMain.isRunning && GameMain.gameTick > 0 && GameMain.data != null &&
                   !DSPGame.IsMenuDemo && (GameMain.instance == null || !GameMain.instance.isMenuDemo) &&
                   planet != null && player != null && player.planetId == planet.id;
        }

        internal static string Capture(string sessionId)
        {
            var json = new StringBuilder(4096);
            json.Append("{\"protocol_version\":1,\"status\":");
            var loaded = IsReady();
            String(json, loaded ? "ok" : "not_loaded");
            json.Append(",\"game_version\":");
            String(json, GameConfig.gameVersion.ToString());
            json.Append(",\"game_build\":");
            if (GameConfig.build > 0) json.Append(GameConfig.build);
            else json.Append("null");
            json.Append(",\"session_id\":");
            NullableString(json, loaded ? sessionId : null);
            if (!loaded) return json.Append('}').ToString();

            var player = GameMain.mainPlayer;
            json.Append(",\"embedded_save_name\":");
            String(json, GameMain.gameName);
            json.Append(",\"loaded_file_name\":null");
            json.Append(",\"game_tick\":").Append(GameMain.gameTick);
            json.Append(",\"paused\":").Append(GameMain.isPaused ? "true" : "false");
            var planet = GameMain.localPlanet;
            json.Append(",\"planet\":");
            if (planet == null) json.Append("null");
            else
            {
                json.Append("{\"id\":").Append(planet.id).Append(",\"name\":");
                String(json, planet.displayName);
                json.Append('}');
            }
            json.Append(",\"mecha_position\":");
            if (planet == null || player.planetId != planet.id) json.Append("null");
            else Vector(json, player.position);
            json.Append(",\"mecha_geo\":");
            if (planet == null || player.planetId != planet.id) json.Append("null");
            else Geo(json, player.position);
            Inventory(json, player.package);
            NearbyEntities(json, planet, player);
            NearbyVeins(json, planet, player);
            ProductionTotals(json, planet);
            return json.Append('}').ToString();
        }

        private static void Geo(StringBuilder json, Vector3 position)
        {
            int latDegrees, latMinutes, lonDegrees, lonMinutes;
            bool north, south, west, east;
            Maths.GetLatitudeLongitude(position, out latDegrees, out latMinutes, out lonDegrees, out lonMinutes,
                out north, out south, out west, out east);
            json.Append("{\"latitude_degrees\":").Append(latDegrees);
            json.Append(",\"latitude_minutes\":").Append(latMinutes);
            json.Append(",\"latitude_hemisphere\":");
            String(json, north ? "N" : south ? "S" : "equator");
            json.Append(",\"longitude_degrees\":").Append(lonDegrees);
            json.Append(",\"longitude_minutes\":").Append(lonMinutes);
            json.Append(",\"longitude_hemisphere\":");
            String(json, east ? "E" : west ? "W" : "meridian");
            json.Append('}');
        }

        private static void Inventory(StringBuilder json, StorageComponent package)
        {
            json.Append(",\"inventory\":");
            if (package == null || package.grids == null)
            {
                json.Append("null");
                return;
            }
            var slots = Math.Min(Math.Min(package.size, package.grids.Length), MaxInventorySlots);
            var counts = new SortedDictionary<int, long>();
            for (var i = 0; i < slots; i++)
            {
                var grid = package.grids[i];
                if (grid.itemId <= 0 || grid.count <= 0) continue;
                long previous;
                counts.TryGetValue(grid.itemId, out previous);
                counts[grid.itemId] = previous + grid.count;
            }
            json.Append("{\"slots_scanned\":").Append(slots);
            json.Append(",\"complete\":").Append(slots >= package.size ? "true" : "false");
            json.Append(",\"items\":[");
            var first = true;
            foreach (var item in counts)
            {
                if (!first) json.Append(',');
                first = false;
                json.Append("{\"item_id\":").Append(item.Key).Append(",\"count\":").Append(item.Value).Append('}');
            }
            json.Append("]}");
        }

        private static void NearbyEntities(StringBuilder json, PlanetData planet, Player player)
        {
            json.Append(",\"nearby_entities\":");
            if (planet == null || player.planetId != planet.id || !planet.factoryLoaded || planet.factory == null || planet.factory.entityPool == null)
            {
                json.Append("null");
                return;
            }
            var factory = planet.factory;
            var scanEnd = Math.Min(Math.Min(factory.entityCursor, factory.entityPool.Length), MaxEntityScan);
            var radiusSquared = NearbyRadius * NearbyRadius;
            var center = player.position;
            json.Append("{\"radius\":").Append(Number(NearbyRadius));
            json.Append(",\"scanned\":").Append(Math.Max(0, scanEnd - 1));
            json.Append(",\"complete\":").Append(factory.entityCursor <= scanEnd ? "true" : "false");
            json.Append(",\"entities\":[");
            var found = 0;
            var first = true;
            for (var i = 1; i < scanEnd; i++)
            {
                var entity = factory.entityPool[i];
                if (entity.id != i || (entity.pos - center).sqrMagnitude > radiusSquared) continue;
                if (found == MaxNearbyEntities)
                {
                    // There are more nearby entities than the response cap.
                    json.Append("],\"result_truncated\":true}");
                    return;
                }
                if (!first) json.Append(',');
                first = false;
                json.Append("{\"id\":").Append(entity.id);
                json.Append(",\"proto_id\":").Append(entity.protoId);
                json.Append(",\"position\":");
                Vector(json, entity.pos);
                json.Append('}');
                found++;
            }
            json.Append("],\"result_truncated\":false}");
        }

        private static void NearbyVeins(StringBuilder json, PlanetData planet, Player player)
        {
            json.Append(",\"nearby_veins\":");
            if (planet == null || player.planetId != planet.id || !planet.factoryLoaded || planet.factory == null || planet.factory.veinPool == null)
            {
                json.Append("null");
                return;
            }
            var factory = planet.factory;
            var scanEnd = Math.Min(Math.Min(factory.veinCursor, factory.veinPool.Length), MaxVeinScan);
            var radiusSquared = NearbyRadius * NearbyRadius;
            var center = player.position;
            json.Append("{\"radius\":").Append(Number(NearbyRadius));
            json.Append(",\"scanned\":").Append(Math.Max(0, scanEnd - 1));
            json.Append(",\"scan_complete\":").Append(factory.veinCursor <= scanEnd ? "true" : "false");
            json.Append(",\"veins\":[");
            var found = 0;
            var first = true;
            for (var i = 1; i < scanEnd; i++)
            {
                var vein = factory.veinPool[i];
                if (vein.id != i || (vein.pos - center).sqrMagnitude > radiusSquared) continue;
                if (found == MaxNearbyVeins)
                {
                    json.Append("],\"result_truncated\":true}");
                    return;
                }
                if (!first) json.Append(',');
                first = false;
                json.Append("{\"id\":").Append(vein.id);
                json.Append(",\"type\":").Append((int)vein.type);
                json.Append(",\"product_id\":").Append(vein.productId);
                json.Append(",\"amount\":").Append(vein.amount);
                json.Append(",\"position\":");
                Vector(json, vein.pos);
                json.Append('}');
                found++;
            }
            json.Append("],\"result_truncated\":false}");
        }

        private static void ProductionTotals(StringBuilder json, PlanetData planet)
        {
            json.Append(",\"local_production\":");
            var statistics = GameMain.data.statistics;
            if (planet.factory == null || statistics == null || statistics.production == null ||
                statistics.production.factoryStatPool == null || planet.factory.index < 0 ||
                planet.factory.index >= statistics.production.factoryStatPool.Length)
            {
                json.Append("null");
                return;
            }
            var factoryStats = statistics.production.factoryStatPool[planet.factory.index];
            if (factoryStats == null || factoryStats.productIndices == null || factoryStats.productPool == null)
            {
                json.Append("null");
                return;
            }
            json.Append("{\"scope\":\"local_planet\",\"counter_kind\":\"all_time_produced\",\"items\":[");
            ProductTotal(json, factoryStats, 1001);
            json.Append(',');
            ProductTotal(json, factoryStats, 1101);
            json.Append("]}");
        }

        private static void ProductTotal(StringBuilder json, FactoryProductionStat stats, int itemId)
        {
            json.Append("{\"item_id\":").Append(itemId).Append(",\"count\":");
            if (itemId >= stats.productIndices.Length)
            {
                json.Append("null}");
                return;
            }
            var index = stats.productIndices[itemId];
            if (index <= 0) json.Append("null}");
            else if (index < stats.productPool.Length && stats.productPool[index] != null &&
                     stats.productPool[index].itemId == itemId && stats.productPool[index].total != null &&
                     stats.productPool[index].total.Length > 6)
                json.Append(stats.productPool[index].total[6]).Append('}');
            else json.Append("null}");
        }

        private static void Vector(StringBuilder json, Vector3 value)
        {
            json.Append("{\"x\":").Append(Number(value.x));
            json.Append(",\"y\":").Append(Number(value.y));
            json.Append(",\"z\":").Append(Number(value.z)).Append('}');
        }

        private static string Number(float value)
        {
            return float.IsNaN(value) || float.IsInfinity(value)
                ? "null"
                : value.ToString("R", CultureInfo.InvariantCulture);
        }

        private static void NullableString(StringBuilder json, string value)
        {
            if (value == null) json.Append("null");
            else String(json, value);
        }

        private static void String(StringBuilder json, string value)
        {
            json.Append('"');
            foreach (var character in value ?? string.Empty)
            {
                switch (character)
                {
                    case '"': json.Append("\\\""); break;
                    case '\\': json.Append("\\\\"); break;
                    case '\n': json.Append("\\n"); break;
                    case '\r': json.Append("\\r"); break;
                    case '\t': json.Append("\\t"); break;
                    default:
                        if (character < 0x20) json.Append("\\u").Append(((int)character).ToString("x4"));
                        else json.Append(character);
                        break;
                }
            }
            json.Append('"');
        }
    }
}
