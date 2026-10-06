(() => {
  if (window.__fh) return;
  window.__fh = 1;
  var q = [];
  var post = function(p){ try { fetch('http://127.0.0.1:18899', {method:'POST', body: JSON.stringify(p)}); } catch(e){} };
  setInterval(function(){ if(!q.length) return; post({ws_raw: q.splice(0, q.length), t: Date.now()}); }, 800);
  var b = function(d){
    if (typeof d === 'string') { try { return btoa(unescape(encodeURIComponent(d))); } catch(e) { return d; } }
    var u = d instanceof ArrayBuffer ? new Uint8Array(d) : (d && d.buffer ? new Uint8Array(d.buffer) : null);
    if (!u) return '';
    var s = ''; var CH = 8192;
    for (var i=0;i<u.length;i+=CH){ s += String.fromCharCode.apply(null, u.subarray(i, i+CH)); }
    return btoa(s);
  };
  var os = WebSocket.prototype.send;
  WebSocket.prototype.send = function(d){ try { if (this.url.indexOf('m28')>=0 || this.url.indexOf('ws')>=0) q.push({d:'s',p:b(d),t:Date.now()}); } catch(e){} return os.apply(this, arguments); };
  var om = WebSocket.prototype.addEventListener;
  WebSocket.prototype.addEventListener = function(t,f,o){
    if (t === 'message') {
      var w = function(ev){ try { if (ev.data) q.push({d:'r',p:b(ev.data),t:Date.now()}); } catch(e){} return f.apply(this, arguments); };
      return om.call(this, t, w, o);
    }
    return om.apply(this, arguments);
  };
  console.log('FH-OK');
  post({hook:'installed4'});
})();
