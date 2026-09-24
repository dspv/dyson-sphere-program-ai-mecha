using System;
using System.Collections.Generic;
using System.Globalization;
using System.Net;
using System.Text;
using System.Threading;
using BepInEx;
using UnityEngine;

namespace DspAgentBridge
{
    [BepInPlugin("cc.cybrix.dsp-agent-bridge", "DSP Agent Bridge", "0.6.0")]
    public sealed class Plugin : BaseUnityPlugin
    {
        private HttpListener listener;
        private Thread listenerThread;
        private volatile bool stopping;
        private readonly Queue<ObservationRequest> observationQueue = new Queue<ObservationRequest>();
        private GameData currentData;
        private bool currentReady;
        private string sessionId;
        private readonly Movement movement = new Movement();
        private readonly Construction construction = new Construction();

        private sealed class ObservationRequest
        {
            public readonly ManualResetEventSlim Done = new ManualResetEventSlim(false);
            public string Json;
            public int EntityId;
            public bool BuildPreview;
        }

        private void Awake()
        {
            try
            {
                listener = new HttpListener();
                listener.Prefixes.Add("http://127.0.0.1:38741/");
                listener.Start();
                listenerThread = new Thread(ListenLoop) { IsBackground = true, Name = "DspAgentBridge.Http" };
                listenerThread.Start();
                Logger.LogInfo("DSP Agent Bridge listener started on loopback");
            }
            catch (Exception error)
            {
                Logger.LogError("Bridge listener failed: " + error);
                if (listener != null) listener.Close();
                listener = null;
            }
        }

        private void ListenLoop()
        {
            while (!stopping && listener != null && listener.IsListening)
            {
                HttpListenerContext context;
                try { context = listener.GetContext(); }
                catch (HttpListenerException) { break; }
                catch (ObjectDisposedException) { break; }

                try { Respond(context); }
                catch (Exception error) { Logger.LogError("Bridge request failed: " + error); }
            }
        }

        private void Update()
        {
            var ready = Observer.IsReady();
            if (!ReferenceEquals(currentData, GameMain.data) || currentReady != ready)
            {
                currentData = GameMain.data;
                currentReady = ready;
                sessionId = ready ? Guid.NewGuid().ToString("N") : null;
            }

            try { movement.Tick(sessionId); }
            catch (Exception error)
            {
                movement.FailActive();
                Logger.LogError("Movement update failed: " + error);
            }
            construction.Tick(sessionId, movement.Busy);

            ObservationRequest request = null;
            lock (observationQueue)
            {
                if (observationQueue.Count > 0) request = observationQueue.Dequeue();
            }
            if (request == null) return;
            try
            {
                request.Json = request.BuildPreview ? Observer.CaptureBuildPreview(sessionId) :
                    request.EntityId > 0 ? Observer.CaptureEntity(sessionId, request.EntityId) : Observer.Capture(sessionId);
            }
            catch (Exception error)
            {
                Logger.LogError("Observation failed: " + error);
                request.Json = "{\"protocol_version\":1,\"status\":\"error\",\"error\":\"observation_failed\"}";
            }
            finally { request.Done.Set(); }
        }

        private void Respond(HttpListenerContext context)
        {
            var response = context.Response;
            response.ContentType = "application/json; charset=utf-8";
            response.Headers.Add("Cache-Control", "no-store");
            if (context.Request.HttpMethod == "GET" && context.Request.Url.AbsolutePath == "/v1/health")
            {
                Write(response, 200, "{\"protocol_version\":1,\"bridge_version\":\"0.6.0\",\"status\":\"stage_c_experimental\"}");
                return;
            }
            if (context.Request.HttpMethod == "GET" && context.Request.Url.AbsolutePath == "/v1/observe")
            {
                var request = new ObservationRequest();
                WriteObservation(response, request);
                return;
            }
            if (context.Request.HttpMethod == "GET" && context.Request.Url.AbsolutePath == "/v1/entity")
            {
                int entityId;
                if (context.Request.RawUrl.Length > 128 || context.Request.QueryString.Count != 1 ||
                    !int.TryParse(context.Request.QueryString["entity_id"], out entityId) || entityId <= 0)
                {
                    Write(response, 400, Movement.Error("invalid_entity_id"));
                    return;
                }
                WriteObservation(response, new ObservationRequest { EntityId = entityId });
                return;
            }
            if (context.Request.HttpMethod == "GET" && context.Request.Url.AbsolutePath == "/v1/build-preview")
            {
                if (context.Request.RawUrl.Length > 128 || context.Request.QueryString.Count != 0)
                {
                    Write(response, 400, Movement.Error("invalid_request"));
                    return;
                }
                WriteObservation(response, new ObservationRequest { BuildPreview = true });
                return;
            }
            if (context.Request.HttpMethod == "POST" &&
                (context.Request.Url.AbsolutePath == "/v1/move-to-vein" || context.Request.Url.AbsolutePath == "/v1/mine-vein"))
            {
                var mining = context.Request.Url.AbsolutePath == "/v1/mine-vein";
                string operationId = context.Request.QueryString["operation_id"];
                string requiredSession = context.Request.QueryString["session_id"];
                string rawVein = context.Request.QueryString["vein_id"];
                Guid parsedOperation, parsedSession;
                int veinId, count = 0, itemId = 1001;
                var rawItemId = context.Request.QueryString["item_id"];
                if (context.Request.RawUrl.Length > 256 ||
                    context.Request.QueryString.Count != (mining ? (rawItemId == null ? 4 : 5) : 3) ||
                    context.Request.ContentLength64 != 0 ||
                    !Guid.TryParseExact(operationId, "N", out parsedOperation) ||
                    !Guid.TryParseExact(requiredSession, "N", out parsedSession) ||
                    !int.TryParse(rawVein, out veinId) || veinId <= 0 ||
                    (mining && (!int.TryParse(context.Request.QueryString["count"], out count) || count < 1 || count > 5)) ||
                    (mining && rawItemId != null && (!int.TryParse(rawItemId, out itemId) ||
                                                     (itemId != 1001 && itemId != 1002))))
                {
                    Write(response, 400, Movement.Error("invalid_request"));
                    return;
                }
                var result = mining ? movement.EnqueueMine(operationId, requiredSession, veinId, count, itemId) :
                    movement.Enqueue(operationId, requiredSession, veinId);
                Write(response, result.Contains("\"status\":\"error\"") ? 409 : 202, result);
                return;
            }
            if (context.Request.HttpMethod == "POST" && context.Request.Url.AbsolutePath == "/v1/confirm-build")
            {
                var query = context.Request.QueryString;
                var operationId = query["operation_id"];
                var requiredSession = query["session_id"];
                Guid parsedOperation, parsedSession;
                int itemId;
                float x, y, z;
                if (context.Request.RawUrl.Length > 320 || query.Count != 6 || context.Request.ContentLength64 != 0 ||
                    !Guid.TryParseExact(operationId, "N", out parsedOperation) ||
                    !Guid.TryParseExact(requiredSession, "N", out parsedSession) ||
                    !int.TryParse(query["item_id"], out itemId) || itemId != 2302 ||
                    !float.TryParse(query["x"], NumberStyles.Float, CultureInfo.InvariantCulture, out x) ||
                    !float.TryParse(query["y"], NumberStyles.Float, CultureInfo.InvariantCulture, out y) ||
                    !float.TryParse(query["z"], NumberStyles.Float, CultureInfo.InvariantCulture, out z) ||
                    float.IsNaN(x) || float.IsNaN(y) || float.IsNaN(z) ||
                    float.IsInfinity(x) || float.IsInfinity(y) || float.IsInfinity(z))
                {
                    Write(response, 400, Movement.Error("invalid_request"));
                    return;
                }
                var result = construction.Enqueue(operationId, requiredSession, itemId, new Vector3(x, y, z));
                Write(response, result.Contains("\"status\":\"error\"") ? 409 : 202, result);
                return;
            }
            if (context.Request.HttpMethod == "GET" && context.Request.Url.AbsolutePath == "/v1/build-operation")
            {
                var operationId = context.Request.QueryString["operation_id"];
                Guid parsedOperation;
                if (context.Request.RawUrl.Length > 128 || context.Request.QueryString.Count != 1 ||
                    !Guid.TryParseExact(operationId, "N", out parsedOperation))
                {
                    Write(response, 400, Movement.Error("invalid_operation_id"));
                    return;
                }
                var result = construction.Get(operationId);
                Write(response, result.Contains("\"status\":\"error\"") ? 404 : 200, result);
                return;
            }
            if (context.Request.HttpMethod == "GET" && context.Request.Url.AbsolutePath == "/v1/operation")
            {
                string operationId = context.Request.QueryString["operation_id"];
                Guid parsedOperation;
                if (!Guid.TryParseExact(operationId, "N", out parsedOperation))
                {
                    Write(response, 400, Movement.Error("invalid_operation_id"));
                    return;
                }
                var result = movement.Get(operationId);
                Write(response, result.Contains("\"status\":\"error\"") ? 404 : 200, result);
                return;
            }
            Write(response, 404, "{\"protocol_version\":1,\"status\":\"error\",\"error\":\"unknown_action\"}");
        }

        private void WriteObservation(HttpListenerResponse response, ObservationRequest request)
        {
            lock (observationQueue)
            {
                if (observationQueue.Count >= 8)
                {
                    Write(response, 503, "{\"protocol_version\":1,\"status\":\"error\",\"error\":\"busy\"}");
                    return;
                }
                observationQueue.Enqueue(request);
            }
            if (!request.Done.Wait(2000))
            {
                Write(response, 503, "{\"protocol_version\":1,\"status\":\"error\",\"error\":\"game_thread_timeout\"}");
                return;
            }
            Write(response, 200, request.Json);
        }

        private static void Write(HttpListenerResponse response, int status, string json)
        {
            var bytes = Encoding.UTF8.GetBytes(json);
            response.StatusCode = status;
            response.ContentLength64 = bytes.Length;
            try { using (var stream = response.OutputStream) stream.Write(bytes, 0, bytes.Length); }
            finally { response.Close(); }
        }

        private void OnDestroy()
        {
            stopping = true;
            lock (observationQueue)
            {
                while (observationQueue.Count > 0)
                {
                    var request = observationQueue.Dequeue();
                    request.Json = "{\"protocol_version\":1,\"status\":\"error\",\"error\":\"stopping\"}";
                    request.Done.Set();
                }
            }
            if (listener != null) listener.Close();
            if (listenerThread != null && listenerThread.IsAlive) listenerThread.Join(1000);
        }
    }
}
