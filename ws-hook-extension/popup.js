function refresh() {
  chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    chrome.scripting.executeScript({
      target: {tabId: tabs[0].id},
      func: () => ({
        rc: window.__recv ? window.__recv.length : 0,
        sc: window.__send ? window.__send.length : 0,
        rb: window.__recv ? window.__recv.reduce((s,p)=>s+p.d.length,0) : 0
      })
    }, function(r) {
      if (r && r[0]) {
        document.getElementById('rc').textContent = r[0].result.rc;
        document.getElementById('sc').textContent = r[0].result.sc;
        document.getElementById('rb').textContent = r[0].result.rb;
      }
    });
  });
}
function dump() {
  chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    chrome.scripting.executeScript({
      target: {tabId: tabs[0].id},
      func: () => {
        if (!window.__recv) return 'no recv';
        return window.__recv.slice(-10).map((p,i) => 
          '['+i+'] '+p.d.length+'B: '+p.d.slice(0,40).join(',')+(p.d.length>40?'...':'')
        ).join('\n');
      }
    }, function(r) {
      document.getElementById('out').textContent = r[0].result;
    });
  });
}
refresh();
setInterval(refresh, 2000);
