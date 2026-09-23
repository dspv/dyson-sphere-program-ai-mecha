using System;
using System.Net;
using System.Text;
using System.Threading;
using BepInEx;

namespace DspAgentBridge
{
    // Bootstrap endpoint only. It does not read or mutate DSP state.
    [BepInPlugin("cc.cybrix.dsp-agent-bridge", "DSP Agent Bridge", "0.1.0")]
    public sealed class Plugin : BaseUnityPlugin
    {
        private HttpListener listener;
        private Thread listenerThread;
        private volatile bool stopping;

        private void Awake()
        {
            try
            {
                listener = new HttpListener();
                listener.Prefixes.Add("http://127.0.0.1:38741/");
                listener.Start();
                listenerThread = new Thread(ListenLoop) { IsBackground = true, Name = "DspAgentBridge.Http" };
                listenerThread.Start();
                Logger.LogInfo("DSP Agent Bridge bootstrap listener started on loopback");
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

        private static void Respond(HttpListenerContext context)
        {
            var response = context.Response;
            response.ContentType = "application/json; charset=utf-8";
            response.Headers.Add("Cache-Control", "no-store");
            if (context.Request.HttpMethod == "GET" && context.Request.Url.AbsolutePath == "/v1/health")
            {
                Write(response, 200, "{\"protocol_version\":1,\"bridge_version\":\"0.1.0\",\"status\":\"bootstrap_only\"}");
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
            if (listener != null) listener.Close();
            if (listenerThread != null && listenerThread.IsAlive) listenerThread.Join(1000);
        }
    }
}
