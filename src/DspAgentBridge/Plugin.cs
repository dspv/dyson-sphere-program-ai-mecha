using System;
using System.Collections.Generic;
using System.Net;
using System.Text;
using System.Threading;
using BepInEx;

namespace DspAgentBridge
{
    [BepInPlugin("cc.cybrix.dsp-agent-bridge", "DSP Agent Bridge", "0.3.0")]
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

        private sealed class ObservationRequest
        {
            public readonly ManualResetEventSlim Done = new ManualResetEventSlim(false);
            public string Json;
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

            ObservationRequest request = null;
            lock (observationQueue)
            {
                if (observationQueue.Count > 0) request = observationQueue.Dequeue();
            }
            if (request == null) return;
            try { request.Json = Observer.Capture(sessionId); }
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
                Write(response, 200, "{\"protocol_version\":1,\"bridge_version\":\"0.3.0\",\"status\":\"stage_b_unverified\"}");
                return;
            }
            if (context.Request.HttpMethod == "GET" && context.Request.Url.AbsolutePath == "/v1/observe")
            {
                var request = new ObservationRequest();
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
                return;
            }
            if (context.Request.HttpMethod == "POST" && context.Request.Url.AbsolutePath == "/v1/move-to-vein")
            {
                string operationId = context.Request.QueryString["operation_id"];
                string requiredSession = context.Request.QueryString["session_id"];
                string rawVein = context.Request.QueryString["vein_id"];
                Guid parsedOperation, parsedSession;
                int veinId;
                if (context.Request.RawUrl.Length > 256 || context.Request.QueryString.Count != 3 ||
                    context.Request.ContentLength64 != 0 ||
                    !Guid.TryParseExact(operationId, "N", out parsedOperation) ||
                    !Guid.TryParseExact(requiredSession, "N", out parsedSession) ||
                    !int.TryParse(rawVein, out veinId) || veinId <= 0)
                {
                    Write(response, 400, Movement.Error("invalid_request"));
                    return;
                }
                var result = movement.Enqueue(operationId, requiredSession, veinId);
                Write(response, result.Contains("\"status\":\"error\"") ? 409 : 202, result);
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
