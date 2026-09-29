// content.js - 在 MAIN world document_start 直接 hook
window.__recv = [];
window.__send = [];
var OrigWS = window.WebSocket;
function HookedWS(url, protocols) {
  var ws = protocols ? new OrigWS(url, protocols) : new OrigWS(url);
  ws.binaryType = 'arraybuffer';
  ws.addEventListener('message', function(e) {
    if (e.data instanceof ArrayBuffer) {
      window.__recv.push({ t: Date.now(), d: Array.from(new Uint8Array(e.data)) });
    }
  });
  var origSend = ws.send.bind(ws);
  ws.send = function(data) {
    try {
      if (data instanceof ArrayBuffer) {
        window.__send.push({ t: Date.now(), d: Array.from(new Uint8Array(data)) });
      }
    } catch(e) {}
    return origSend(data);
  };
  return ws;
}
HookedWS.prototype = OrigWS.prototype;
window.WebSocket = HookedWS;
console.log('[WS-HOOK] hooked at document_start');
