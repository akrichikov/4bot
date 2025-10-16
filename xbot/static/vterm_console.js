(() => {
  const qs = (id) => document.getElementById(id);
  const logEl = qs('log');
  const cmdEl = qs('cmd');
  const tokenEl = qs('token');
  const statusEl = qs('status');
  const connectBtn = qs('connect');
  const runBtn = qs('run');
  const writeBtn = qs('write');
  const clearBtn = qs('clear');

  let ws;
  let base = location.origin;

  function append(text, cls) {
    const span = document.createElement('div');
    if (cls) span.className = cls;
    span.textContent = text;
    logEl.appendChild(span);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function fmtPayload(obj) {
    try {
      if (obj.json_objects && obj.json_objects.length) {
        return JSON.stringify(obj.json_objects[0]);
      }
      if (obj.lines && obj.lines.length) {
        return obj.lines.join('\n');
      }
      if (obj.key_values) {
        return Object.entries(obj.key_values).map(([k,v]) => `${k}=${v}`).join(' ');
      }
      return obj.raw_text || '';
    } catch (e) {
      return '';
    }
  }

  async function api(path, method, body) {
    const headers = {'content-type':'application/json'};
    const tok = tokenEl.value.trim();
    if (tok) headers['X-VTerm-Token'] = tok;
    const res = await fetch(`${base}${path}`, {method, headers, body: body ? JSON.stringify(body) : undefined});
    return {status: res.status, json: await res.json()};
  }

  function connectWS() {
    if (ws) try { ws.close(); } catch {}
    const tok = tokenEl.value.trim();
    const url = new URL(`${base.replace('http','ws')}/ws`);
    if (tok) url.searchParams.set('token', tok);
    ws = new WebSocket(url.toString());
    ws.onopen = () => { statusEl.textContent = 'connected'; };
    ws.onclose = () => { statusEl.textContent = 'disconnected'; };
    ws.onerror = () => { statusEl.textContent = 'error'; };
    ws.onmessage = (ev) => {
      try {
        const obj = JSON.parse(ev.data);
        const txt = fmtPayload(obj);
        if (txt) append(txt);
      } catch {}
    };
  }

  connectBtn.onclick = connectWS;

  runBtn.onclick = async () => {
    const cmd = cmdEl.value.trim();
    if (!cmd) return;
    const r = await api('/run','POST',{cmd});
    if (r.status !== 200) append(`ERR ${r.status}: ${JSON.stringify(r.json)}`,'err');
  };

  writeBtn.onclick = async () => {
    const txt = cmdEl.value + (cmdEl.value.endsWith('\n') ? '' : '\n');
    const r = await api('/write','POST',{text: txt});
    if (r.status !== 200) append(`ERR ${r.status}: ${JSON.stringify(r.json)}`,'err');
  };

  clearBtn.onclick = () => { logEl.textContent=''; };

  cmdEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); runBtn.click(); }
  });
})();

