const roundSelect = document.getElementById('roundSelect');
const playBtn = document.getElementById('playBtn');
const pauseBtn = document.getElementById('pauseBtn');
const tickSampleInput = document.getElementById('tickSample');
const demoList = document.getElementById('demoList');
const loadDemoBtn = document.getElementById('loadDemoBtn');
const statusMsg = document.getElementById('statusMsg');
const loadingSpinner = document.getElementById('loadingSpinner');
const progressWrap = document.getElementById('progressWrap');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');

function setStatus(msg) {
  if (statusMsg) statusMsg.textContent = msg || '';
}

// Loading timer + spinner helpers (re-added)
let loadingTimer = null;
let loadingStart = 0;
function startLoading(messagePrefix) {
  // clear any previous timer first
  stopLoading();
  setStatus(messagePrefix + ' 0.0s');
  if (loadingSpinner) loadingSpinner.style.display = 'inline-block';
  loadingStart = Date.now();
  loadingTimer = setInterval(() => {
    const secs = ((Date.now() - loadingStart) / 1000).toFixed(1);
    setStatus(messagePrefix + ' ' + secs + 's');
  }, 100);
}

function stopLoading(finalMessage) {
  if (loadingTimer) { clearInterval(loadingTimer); loadingTimer = null; }
  if (loadingSpinner) loadingSpinner.style.display = 'none';
  if (finalMessage !== undefined) setStatus(finalMessage);
}

// Populate demos list from backend on load
function fetchDemos() {
  startLoading('A obter lista de demos...');
  fetch('/api/demos')
    .then(r => {
      if (!r.ok) throw new Error('Falha a obter lista de demos');
      return r.json();
    })
    .then(json => {
      demoList.innerHTML = '';
      if (!json.demos || !json.demos.length) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = 'Sem demos no servidor';
        demoList.appendChild(opt);
        stopLoading('Sem demos no servidor.');
        return;
      }
      json.demos.forEach(name => {
        const opt = document.createElement('option');
        opt.value = name; opt.textContent = name; demoList.appendChild(opt);
      });
      stopLoading('');
    })
    .catch(err => {
      console.error(err);
      stopLoading('Falha a obter demos. Verifica o servidor.');
      alert('Não foi possível obter a lista de demos. Verifica se o servidor está a correr.');
    });
}

let currentJob = null;
let progressPoll = null;

function showProgressUI(show) {
  if (progressWrap) progressWrap.style.display = show ? 'flex' : 'none';
}

function setProgress(pct, text) {
  if (progressFill) progressFill.style.width = Math.max(0, Math.min(100, pct)) + '%';
  if (progressText) progressText.textContent = text || '';
}

function pollProgress(jobId) {
  if (progressPoll) { clearInterval(progressPoll); }
  progressPoll = setInterval(() => {
    fetch(`/api/progress?job=${encodeURIComponent(jobId)}`)
      .then(r => r.json())
      .then(j => {
        if (j.error) { throw new Error(j.error); }
        const total = j.total_rounds || 0;
        const proc = j.processed_rounds || 0;
        const pct = typeof j.percent === 'number' ? j.percent : (total ? Math.floor((proc/total)*100) : 0);
        setProgress(pct, `${proc}/${total || '?'} rondas · ${j.message || ''}`);
        const isDone = (j.status === 'done') || (pct >= 100 && String(j.message||'').toLowerCase().includes('concl'));
        if (isDone) {
          clearInterval(progressPoll); progressPoll = null;
          fetch(`/api/result?job=${encodeURIComponent(jobId)}`)
            .then(r => r.json())
            .then(json => {
              console.log('Parse result:', json);
              data = json;
              populateRounds();
              // If the job result contains a map name, attempt to show a background image.
              let mapName = null;
              if (json) {
                if (typeof json.map === 'string' && json.map.trim()) mapName = json.map.trim();
                // don't try to use `json.rounds.map` (that's Array.map function) — only accept explicit strings
                if (!mapName && json.rounds && typeof json.rounds.mapName === 'string' && json.rounds.mapName.trim()) mapName = json.rounds.mapName.trim();
              }
              if (typeof mapName === 'string' && mapName) setMapBackground(mapName);
              // Ensure controls are enabled and visible
              try { if (roundSelect) { roundSelect.disabled = false; roundSelect.style.display = 'inline-block'; } } catch(e){}
              try { if (playBtn) { playBtn.disabled = false; playBtn.style.display = 'inline-block'; } } catch(e){}
              try { if (timeSlider) { timeSlider.disabled = false; timeSlider.style.display = 'inline-block'; } } catch(e){}
              stopLoading('Demo processada.');
              showProgressUI(false);
              currentJob = null;
              // If there are rounds but none contain positions, notify the user
              const hasPos = data && Array.isArray(data.rounds) && data.rounds.some(r => Array.isArray(r.players) && r.players.some(p => Array.isArray(p.positions) && p.positions.length>0));
              if (!hasPos) {
                alert('A demo foi processada mas não foram encontradas posições. Tenta reduzir o valor de "every_n" para incluir mais ticks.');
              }
            })
            .catch(err => { console.error(err); stopLoading('Falha a obter resultado.'); showProgressUI(false); currentJob = null; });
        } else if (j.status === 'error') {
          clearInterval(progressPoll); progressPoll = null;
          stopLoading(j.message || 'Erro no processamento');
          showProgressUI(false);
          currentJob = null;
        }
      })
      .catch(err => { console.error(err); /* keep polling; transient errors */ });
  }, 500);
}

loadDemoBtn.addEventListener('click', () => {
  console.log('Processar Demo clicado');
  const name = demoList.value;
  if (!name) { alert('Seleciona uma demo na lista.'); return; }
  const everyN = Number(tickSampleInput && tickSampleInput.value ? tickSampleInput.value : 1) || 1;
  loadDemoBtn.disabled = true;
  showProgressUI(true);
  setProgress(0, '0/? rondas · A iniciar...');
  fetch('/api/start-parse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name, every_n: everyN })
  })
    .then(r => {
      if (!r.ok) return r.json().then(j => { throw new Error(j && j.error ? j.error : 'Erro no servidor'); });
      return r.json();
    })
    .then(resp => {
      if (!resp.job) throw new Error('Resposta inválida do servidor');
      currentJob = resp.job;
      pollProgress(currentJob);
    })
    .catch(err => { console.error(err); alert('Falha a iniciar processamento: ' + err.message); stopLoading('Falha a iniciar.'); showProgressUI(false); })
    .finally(() => { loadDemoBtn.disabled = false; });
});

// Initial attempt to fetch demos list
fetchDemos();
const timeSlider = document.getElementById('timeSlider');
const tickLabel = document.getElementById('tickLabel');
const canvas = document.getElementById('field');
const ctx = canvas.getContext('2d');

let data = null;
let currentRound = null;
let animating = false;
let currentTickIndex = 0;
let maxTickIndex = 0;
let lastFrameTime = 0;
let tickDurationMs = 30; // adjust speed

const fallbackColors = ['#ff5555','#55aaff','#ffaa00','#66dd66','#ff66cc','#cccc66','#66cccc','#aa66ff'];
let mapImage = null;
let mapImageName = null;
let mapImageUrl = '';

// file input removed; only server-side demos are supported

// sample button removed; using only server demos

function populateRounds() {
  roundSelect.innerHTML = '';
  if (!data?.rounds?.length) return;
  data.rounds.forEach(r => {
    const opt = document.createElement('option');
    opt.value = r.round;
    opt.textContent = 'Round ' + r.round;
    roundSelect.appendChild(opt);
  });
  // Prefer a non-empty round if available
  const nonEmpty = data.rounds.find(r => Array.isArray(r.players) && r.players.some(p => Array.isArray(p.positions) && p.positions.length > 0));
  const firstRound = nonEmpty ? nonEmpty.round : data.rounds[0].round;
  selectRound(firstRound);
}

roundSelect.addEventListener('change', () => selectRound(Number(roundSelect.value)));

function selectRound(roundNumber) {
  currentRound = data.rounds.find(r => r.round === roundNumber);
  if (!currentRound) return;
  // Determine max tick count
  let maxLen = 0;
  if (Array.isArray(currentRound.players)) {
    currentRound.players.forEach(p => {
      const l = (p.positions && p.positions.length) ? p.positions.length : 0;
      if (l > maxLen) maxLen = l;
    });
  }
  maxTickIndex = Math.max(0, maxLen - 1);
  timeSlider.max = maxTickIndex;
  timeSlider.value = 0;
  currentTickIndex = 0;
  updateTickLabel();
  drawCurrentTick();
}

playBtn.addEventListener('click', () => {
  if (!currentRound) return;
  animating = true;
  playBtn.disabled = true;
  pauseBtn.disabled = false;
  requestAnimationFrame(step);
});

pauseBtn.addEventListener('click', () => {
  animating = false;
  playBtn.disabled = false;
  pauseBtn.disabled = true;
});

timeSlider.addEventListener('input', () => {
  currentTickIndex = Number(timeSlider.value);
  updateTickLabel();
  drawCurrentTick();
});

function step(ts) {
  if (!animating) return;
  if (ts - lastFrameTime >= tickDurationMs) {
    advanceTick();
    lastFrameTime = ts;
  }
  requestAnimationFrame(step);
}

function advanceTick() {
  if (currentTickIndex < maxTickIndex) {
    currentTickIndex++;
    timeSlider.value = currentTickIndex;
    updateTickLabel();
    drawCurrentTick();
  } else {
    animating = false;
    playBtn.disabled = false;
    pauseBtn.disabled = true;
  }
}

function updateTickLabel() {
  tickLabel.textContent = 'Tick: ' + currentTickIndex;
}

function drawCurrentTick() {
  ctx.clearRect(0,0,canvas.width,canvas.height);
  const pad = 40;

  if (mapImage) {
    ctx.drawImage(mapImage, 0, 0, canvas.width, canvas.height);
  } else {
    ctx.strokeStyle = '#222';
    ctx.lineWidth = 1;
    for (let gx=0; gx<10; gx++) {
      const x = pad + gx*(canvas.width - pad*2)/10;
      ctx.beginPath(); ctx.moveTo(x, pad); ctx.lineTo(x, canvas.height - pad); ctx.stroke();
    }
    for (let gy=0; gy<10; gy++) {
      const y = pad + gy*(canvas.height - pad*2)/10;
      ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(canvas.width - pad, y); ctx.stroke();
    }
  }

  if (!currentRound) return;
  // Compute bounds from all positions once (cache)
  if (!currentRound._bounds) {
    let xs = [], ys = [];
    if (Array.isArray(currentRound.players)) {
      currentRound.players.forEach(p => Array.isArray(p.positions) && p.positions.forEach(pos => { xs.push(pos.x); ys.push(pos.y); }));
    }
    if (xs.length === 0 || ys.length === 0) return; // nothing to draw
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    currentRound._bounds = { minX, maxX, minY, maxY };
  }
  const { minX, maxX, minY, maxY } = currentRound._bounds;
  const pad = 40;
  const scaleX = (canvas.width - pad*2) / (maxX - minX || 1);
  const scaleY = (canvas.height - pad*2) / (maxY - minY || 1);

  // Draw background grid
  ctx.strokeStyle = '#222';
  ctx.lineWidth = 1;
  for (let gx=0; gx<10; gx++) {
    const x = pad + gx*(canvas.width - pad*2)/10;
    ctx.beginPath(); ctx.moveTo(x, pad); ctx.lineTo(x, canvas.height - pad); ctx.stroke();
  }
  for (let gy=0; gy<10; gy++) {
    const y = pad + gy*(canvas.height - pad*2)/10;
    ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(canvas.width - pad, y); ctx.stroke();
  }

  if (!Array.isArray(currentRound.players)) return;
  currentRound.players.forEach((player, idx) => {
    const pos = player.positions[Math.min(currentTickIndex, player.positions.length - 1)];
    const color = player.color || fallbackColors[idx % fallbackColors.length];
    const x = pad + (pos.x - minX) * scaleX;
    const y = pad + (pos.y - minY) * scaleY;
    // Trail
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    let first = true;
    for (let i=0; i<=currentTickIndex && i<player.positions.length; i++) {
      const tp = player.positions[i];
      const tx = pad + (tp.x - minX) * scaleX;
      const ty = pad + (tp.y - minY) * scaleY;
      if (first) { ctx.moveTo(tx, ty); first = false; } else ctx.lineTo(tx, ty);
    }
    ctx.stroke();
    // Player marker
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(x, y, 8, 0, Math.PI*2);
    ctx.fill();
    // Label
    ctx.fillStyle = '#fff';
    ctx.font = '10px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(player.name ?? player.id, x, y - 14);
  });
}

// Set map background by attempting to load common extensions (.jpg, .png)
function setMapBackground(mapName) {
  if (typeof mapName !== 'string') {
    console.warn('setMapBackground: ignored non-string mapName:', mapName);
    return;
  }
  const trimmed = mapName.trim();
  if (!trimmed) return;

  const safeName = trimmed.replace(/[\0<>:"\/\\|?*\x00-\x1F]/g, '').slice(0, 200);
  if (!safeName) return;

  const wrap = document.getElementById('mapWrap');
  if (mapImage && mapImageName === safeName) {
    if (wrap && mapImageUrl) wrap.style.backgroundImage = `url('${mapImageUrl}')`;
    drawCurrentTick();
    return;
  }

  mapImage = null;
  mapImageName = null;
  mapImageUrl = '';
  if (wrap) wrap.style.backgroundImage = '';

  const applyImage = (img, url) => {
    mapImage = img;
    mapImageName = safeName;
    mapImageUrl = url;
    if (wrap) wrap.style.backgroundImage = `url('${url}')`;
    drawCurrentTick();
  };

  const loadImage = (url, onError) => {
    const img = new Image();
    img.onload = () => applyImage(img, url);
    img.onerror = onError;
    img.src = url;
  };

  const tryFallback = () => {
    const tryDirs = ['/assets/maps', '/maps'];
    const tryExt = ['.png', '.jpg', '.webp'];
    const urls = [];
    for (const d of tryDirs) {
      for (const e of tryExt) {
        urls.push(`${d}/${encodeURIComponent(safeName)}${e}`);
      }
    }
    let idx = 0;
    const attempt = () => {
      if (idx >= urls.length) {
        console.warn('setMapBackground: map image not found for', safeName);
        return;
      }
      loadImage(urls[idx++], attempt);
    };
    attempt();
  };

  fetch(`/api/map?name=${encodeURIComponent(safeName)}`)
    .then(r => {
      if (!r.ok) throw new Error('Map not found');
      return r.json();
    })
    .then(j => {
      if (j && j.url) {
        loadImage(j.url, tryFallback);
      } else {
        throw new Error('Invalid map response');
      }
    })
    .catch(() => { tryFallback(); });
}

window.addEventListener('keydown', e => {
  if (e.code === 'Space') {
    if (animating) pauseBtn.click(); else playBtn.click();
    e.preventDefault();
  }
  if (e.code === 'ArrowRight') {
    currentTickIndex = Math.min(currentTickIndex + 1, maxTickIndex);
    timeSlider.value = currentTickIndex;
    updateTickLabel();
    drawCurrentTick();
  }
  if (e.code === 'ArrowLeft') {
    currentTickIndex = Math.max(currentTickIndex - 1, 0);
    timeSlider.value = currentTickIndex;
    updateTickLabel();
    drawCurrentTick();
  }
});

// Optional: expose a function to load data programmatically.
window.loadMovementData = (json) => { data = json; populateRounds(); };
