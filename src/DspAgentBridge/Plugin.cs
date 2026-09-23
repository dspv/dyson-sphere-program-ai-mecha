using System;
using System.Collections.Generic;
using System.Net;
using System.Text;
using System.Threading;
using BepInEx;

namespace DspAgentBridge
{
    // Observation is read-only; positive factory entities still need live UI verification.
    [BepInPlugin("cc.cybrix.dsp-agent-bridge", "DSP Agent Bridge", "0.2.0")]
    public sealed class Plugin : BaseUnityPlugin
    {
        private HttpListener listener;
        private Thread listenerThread;
        private volatile bool stopping;
        private readonly Queue<ObservationRequest> observationQueue = new Queue<ObservationRequest>();
        private GameData currentData;
        private bool currentReady;
        private string sessionId;

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
                Logger.LogInfo("DSP Agent Bridge read-only listener started on loopback");
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
                Write(response, 200, "{\"protocol_version\":1,\"bridge_version\":\"0.2.0\",\"status\":\"observer_unverified\"}");
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
            // There is intentionally no mutation route before game-version validation.
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
