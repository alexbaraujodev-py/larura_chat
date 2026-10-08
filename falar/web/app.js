const listenButton = document.querySelector('#listen-button');
const listenLabel = document.querySelector('#listen-label');
const progressStatus = document.querySelector('#progress-status');
const processLog = document.querySelector('#process-log');
const clearLogButton = document.querySelector('#clear-log');
let recognition;
let lastSpoken = '';
let voiceInteractionActive = false;
let taskStarted = false;
let lastPhase = 'idle';
let logLines = [];
let voicePromptTimer;
let renderedOutputCount = 0;
let speechFinishTimer;
let latestOutputCount = 0;
let currentRunId = null;
const dancers = document.querySelectorAll('.floating-dancer');

function getDancerObstacles() {
  return [...document.querySelectorAll(
    '.eyes, button, output, input, textarea, select, [role="button"], .log-panel',
  )]
    .filter(element => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== 'none'
        && style.visibility !== 'hidden'
        && rect.width > 0
        && rect.height > 0;
    })
    .map(element => element.getBoundingClientRect());
}

function findSafeDancerPosition(width, height, obstacles) {
  const margin = 16;
  const maxLeft = Math.max(margin, window.innerWidth - width - margin);
  const maxTop = Math.max(margin, window.innerHeight - height - margin);
  for (let attempt = 0; attempt < 60; attempt += 1) {
    const left = margin + Math.random() * Math.max(0, maxLeft - margin);
    const top = margin + Math.random() * Math.max(0, maxTop - margin);
    const overlapsElement = obstacles.some(rect => (
      left < rect.right + margin
      && left + width > rect.left - margin
      && top < rect.bottom + margin
      && top + height > rect.top - margin
    ));
    if (!overlapsElement) return { left, top };
  }
  return null;
}

function showDancer() {
  if (!dancers.length) return;
  const obstacles = getDancerObstacles();
  const selected = [...dancers]
    .sort(() => Math.random() - 0.5)
    .slice(0, 1 + Math.floor(Math.random() * dancers.length));
  selected.forEach(dancer => {
    const dancerSize = dancer.getBoundingClientRect();
    const position = findSafeDancerPosition(
      dancerSize.width,
      dancerSize.height,
      obstacles,
    );
    dancer.style.animation = 'none';
    void dancer.offsetWidth;
    if (position) {
      dancer.style.left = `${position.left}px`;
      dancer.style.top = `${position.top}px`;
      dancer.style.animation = 'dancer-appear 5s ease-in-out forwards';
    }
  });
}

function scheduleNextDancer() {
  showDancer();
  window.setTimeout(scheduleNextDancer, 5000);
}
let availableVoices = [];
let speechSequence = 0;

function log(message) {
  logLines.push(`${new Date().toLocaleTimeString('pt-BR')}  ${message}`);
  logLines = logLines.slice(-500);
  processLog.textContent = logLines.join('\n');
  processLog.style.height = 'auto';
  processLog.style.height = `${Math.min(processLog.scrollHeight, 680)}px`;
}

function clearLog() {
  logLines = [];
  renderedOutputCount = latestOutputCount;
  processLog.textContent = '';
  processLog.style.height = '420px';
}

clearLogButton.addEventListener('click', clearLog);

function refreshVoices() {
  availableVoices = window.speechSynthesis?.getVoices() || [];
}

function selectPortugueseVoice() {
  const portuguese = availableVoices.filter(voice => /^pt[-_]br$/i.test(voice.lang));
  const candidates = [
    /microsoft.*francisca/i,
    /microsoft.*brasil/i,
    /google.*portugu/i,
    /google.*brazil/i,
    /luciana|helena|francisca|fernanda|maria/i,
  ];
  return candidates.reduce((selected, pattern) => (
    selected || portuguese.find(voice => pattern.test(voice.name))
  ), null) || portuguese[0]
    || availableVoices.find(voice => /^pt[-_]/i.test(voice.lang))
    || null;
}

function speechParts(text) {
  return text
    .replace(/\s+/g, ' ')
    .trim()
    .match(/[^.!?]+[.!?]+|[^.!?]+$/g)
    ?.map(part => part.trim())
    .filter(Boolean) || [];
}

function speak(text, onEnd) {
  if (!('speechSynthesis' in window) || text === lastSpoken) {
    onEnd?.();
    return;
  }
  lastSpoken = text;
  const sequence = ++speechSequence;
  window.speechSynthesis.cancel();
  refreshVoices();
  const parts = speechParts(text);
  const voice = selectPortugueseVoice();
  let index = 0;
  const speakNext = () => {
    if (sequence !== speechSequence || index >= parts.length) {
      if (index >= parts.length) onEnd?.();
      return;
    }
    const utterance = new SpeechSynthesisUtterance(parts[index++]);
    utterance.lang = 'pt-BR';
    utterance.rate = 1.08;
    utterance.pitch = 1.04;
    utterance.volume = 0.96;
    utterance.voice = voice;
    utterance.onend = () => setTimeout(speakNext, 90);
    utterance.onerror = () => onEnd?.();
    window.speechSynthesis.speak(utterance);
  };
  speakNext();
}

function buildTaskSummary(state) {
  const lines = (state.output || [])
    .map(line => line.replace(/^\s*\d{1,2}:\d{2}:\d{2}\s+/, '').trim())
    .filter(line => line && !/^Hermes iniciou a tarefa\.?$/i.test(line));
  const summary = lines.slice(-3).join('. ').replace(/\s+/g, ' ').trim();
  if (!summary) return 'A tarefa foi concluída sem detalhes adicionais.';
  return summary.length > 420 ? `${summary.slice(0, 417).trimEnd()}...` : summary;
}

if ('speechSynthesis' in window) {
  refreshVoices();
  window.speechSynthesis.addEventListener('voiceschanged', refreshVoices);
}

function render(state) {
  if (state.run_id && state.run_id !== currentRunId) {
    currentRunId = state.run_id;
    logLines = [];
    renderedOutputCount = 0;
    latestOutputCount = 0;
    processLog.textContent = '';
    processLog.style.height = '420px';
  }
  if (!voiceInteractionActive) {
    progressStatus.textContent = state.error ? `Erro: ${state.error}` : state.status;
  }
  latestOutputCount = state.output?.length || 0;
  if (state.output?.length > renderedOutputCount) {
    state.output.slice(renderedOutputCount).forEach(line => log(line));
    renderedOutputCount = state.output.length;
  }
  if (state.phase !== lastPhase && taskStarted) {
    if (state.running) speak('Hermes está trabalhando.');
    if (state.phase === 'completed') {
      progressStatus.textContent = 'Tarefa concluída — resumo disponível';
      speak(`Tarefa concluída. Resumo do processo: ${buildTaskSummary(state)}`);
    }
    if (state.phase === 'error') speak('Ocorreu um erro durante a tarefa.');
  }
  lastPhase = state.phase;
}

async function refresh() {
  try {
    render(await (await fetch('/api/status')).json());
  } catch (_) {
    progressStatus.textContent = 'Servidor desconectado';
  }
}

async function sendPrompt(prompt) {
  taskStarted = true;
  lastPhase = 'idle';
  clearLog();
  currentRunId = null;
  log(`Voz reconhecida: ${prompt}`);
  progressStatus.textContent = 'Enviando para Hermes';
  const token = document.querySelector('meta[name="falar-token"]')?.content;
  const response = await fetch('/api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Falar-Token': token || '' },
    body: JSON.stringify({ prompt }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Não foi possível iniciar a tarefa.');
  log('Hermes iniciou a tarefa.');
  render(data);
}

function startListening() {
  if (!('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
    voiceInteractionActive = true;
    progressStatus.textContent = 'Reconhecimento de voz indisponível';
    speak('Seu navegador não oferece reconhecimento de voz.');
    return;
  }
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new Recognition();
  recognition.lang = 'pt-BR'; recognition.interimResults = false; recognition.maxAlternatives = 1;
  recognition.onstart = () => { listenButton.classList.remove('ready'); listenButton.classList.add('listening'); listenLabel.textContent = 'Ouvindo...'; progressStatus.textContent = 'Capturando voz — termine de falar'; log('Microfone ativo; aguardando você terminar.'); };
  recognition.onresult = event => {
    voiceInteractionActive = false;
    const prompt = event.results[0][0].transcript;
    if (!prompt.trim()) {
      progressStatus.textContent = 'Nenhuma fala detectada';
      log('Nenhuma fala detectada; tarefa não iniciada.');
      return;
    }
    progressStatus.textContent = 'Aguardando 2 segundos para confirmar o fim da fala';
    log('Fala detectada; aguardando 2 segundos de silêncio.');
    clearTimeout(speechFinishTimer);
    speechFinishTimer = setTimeout(() => {
      progressStatus.textContent = 'Enviando para Hermes';
      sendPrompt(prompt).catch(error => { progressStatus.textContent = error.message; log(`Erro: ${error.message}`); speak(error.message); });
    }, 2000);
  };
  recognition.onerror = event => {
    listenButton.classList.remove('listening');
    listenButton.classList.remove('ready');
    listenLabel.textContent = 'Escutar voz';
    progressStatus.textContent = `Falha no microfone: ${event.error}`;
    log(`Falha na captura: ${event.error}. Tarefa não iniciada.`);
    if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
      speak('Permita o acesso ao microfone para escutar sua voz.');
    }
  };
  recognition.onnomatch = () => { progressStatus.textContent = 'Não entendi a fala'; log('Nenhuma fala compreensível; tarefa não iniciada.'); };
  recognition.onend = () => {
    listenButton.classList.remove('listening');
    listenButton.classList.remove('ready');
    listenLabel.textContent = 'Escutar voz';
    if (!taskStarted && !progressStatus.textContent.startsWith('Falha') && !progressStatus.textContent.startsWith('Não foi')) {
      voiceInteractionActive = false;
      progressStatus.textContent = 'Pronto para ouvir';
    }
  };
  voiceInteractionActive = true;
  progressStatus.textContent = 'Solicitando acesso ao microfone';
  listenButton.disabled = true;
  listenLabel.textContent = 'Aguarde...';
  let promptFinished = false;
  const beginCapture = () => {
    if (promptFinished) return;
    promptFinished = true;
    clearTimeout(voicePromptTimer);
    listenButton.disabled = false;
    listenButton.classList.add('ready');
    listenLabel.textContent = 'Pode falar';
    progressStatus.textContent = 'Pode começar a falar';
    log('Orientação concluída; microfone liberado.');
    try {
      recognition.start();
    } catch (error) {
      voiceInteractionActive = false;
      progressStatus.textContent = `Não foi possível iniciar: ${error.message}`;
      log(`Erro ao iniciar captura: ${error.message}`);
    }
  };
  voicePromptTimer = setTimeout(beginCapture, 5000);
  speak('Fale Comigo!', beginCapture);
}
listenButton.addEventListener('click', startListening);
refresh();
setInterval(refresh, 1000);
setTimeout(scheduleNextDancer, 3500 + Math.random() * 2500);
