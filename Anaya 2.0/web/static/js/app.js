/**
 * Anaya 2.0 • Living AI Companion Client Application
 * Handles real-time SSE streaming, voice synthesis, microphone dictation,
 * dynamic status synchronization, and drawer/modal management.
 */

class AnayaApp {
  constructor() {
    this.sessionId = this.getOrCreateSessionId();
    this.isStreaming = false;
    this.voiceEnabled = localStorage.getItem('anaya_voice_enabled') !== 'false';
    this.selectedVoice = localStorage.getItem('anaya_neural_voice') || 'en-IN-NeerjaExpressiveNeural';
    this.currentAudio = null;
    this.activeFilter = 'all';
    this.memoriesCache = [];
    this.recognition = null;
    this.isListening = false;

    // DOM Elements
    this.messagesContainer = document.getElementById('messages-container');
    this.inputField = document.getElementById('user-input-field');
    this.sendBtn = document.getElementById('btn-send');
    this.undoBtn = document.getElementById('btn-undo-turn');
    this.clearChatBtn = document.getElementById('btn-clear-chat');
    this.toastContainer = document.getElementById('toast-container');
    this.micBtn = document.getElementById('btn-mic');
    this.typingIndicator = document.getElementById('typing-indicator');
    this.welcomeHero = document.getElementById('welcome-hero');

    // Status Elements
    this.statusActivity = document.getElementById('status-activity-text');
    this.statusMood = document.getElementById('status-mood-text');
    this.statusMusic = document.getElementById('status-music-text');
    this.threadsBadge = document.getElementById('threads-badge');
    this.voiceBadge = document.getElementById('voice-badge');

    // Modals & Drawers
    this.drawerOverlay = document.getElementById('drawer-overlay');
    this.memoryDrawer = document.getElementById('memory-drawer');
    this.threadsDrawer = document.getElementById('threads-drawer');
    this.diaryModal = document.getElementById('diary-modal');
    this.settingsModal = document.getElementById('settings-modal');

    this.init();
  }

  getOrCreateSessionId() {
    let sid = localStorage.getItem('anaya_web_session_id');
    if (!sid) {
      sid = 'web_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
      localStorage.setItem('anaya_web_session_id', sid);
    }
    return sid;
  }

  init() {
    this.bindEvents();
    this.setupAudioUnlocker();
    this.setupSpeechRecognition();
    this.loadHistory();
    this.refreshStatus();
    this.updateVoiceBadge();

    // Poll status periodically to keep Anaya's living activity refreshed
    setInterval(() => this.refreshStatus(), 30000);
  }

  setupAudioUnlocker() {
    this.audioUnlocked = false;
    const unlock = () => {
      if (this.audioUnlocked) return;
      try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
          const ctx = new AudioContext();
          ctx.resume().then(() => {
            this.audioUnlocked = true;
          });
        }
      } catch (e) {}
      window.removeEventListener('click', unlock);
      window.removeEventListener('keydown', unlock);
      window.removeEventListener('touchstart', unlock);
    };
    window.addEventListener('click', unlock, { passive: true });
    window.addEventListener('keydown', unlock, { passive: true });
    window.addEventListener('touchstart', unlock, { passive: true });
  }

  bindEvents() {
    // Input handling
    this.sendBtn.addEventListener('click', () => this.sendMessage());
    this.inputField.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    // Auto-expand textarea
    this.inputField.addEventListener('input', () => {
      this.inputField.style.height = 'auto';
      this.inputField.style.height = Math.min(this.inputField.scrollHeight, 120) + 'px';
    });

    // Quick suggestion chips
    document.querySelectorAll('.chip-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const msg = btn.getAttribute('data-msg');
        if (msg) {
          this.inputField.value = msg;
          this.sendMessage();
        }
      });
    });

    // Undo turn
    if (this.undoBtn) {
      this.undoBtn.addEventListener('click', () => this.undoLastTurn());
    }

    // Clear chat
    if (this.clearChatBtn) {
      this.clearChatBtn.addEventListener('click', () => this.clearChat());
    }

    // Mic button
    this.micBtn.addEventListener('click', () => this.toggleMicrophone());

    // Voice toggle
    document.getElementById('btn-voice-toggle').addEventListener('click', () => {
      this.toggleVoiceMode();
    });

    // Voice setting controls in settings modal
    const voiceSelect = document.getElementById('voice-select');
    if (voiceSelect) {
      voiceSelect.value = this.selectedVoice;
      voiceSelect.addEventListener('change', (e) => {
        this.selectedVoice = e.target.value;
        localStorage.setItem('anaya_neural_voice', this.selectedVoice);
      });
    }

    const voiceModeBtn = document.getElementById('btn-toggle-voice-mode');
    if (voiceModeBtn) {
      voiceModeBtn.addEventListener('click', () => {
        this.toggleVoiceMode();
      });
    }

    // Drawer toggles
    document.getElementById('btn-open-memory').addEventListener('click', () => this.openMemoryDrawer());
    document.getElementById('btn-close-memory').addEventListener('click', () => this.closeDrawers());

    document.getElementById('btn-open-threads').addEventListener('click', () => this.openThreadsDrawer());
    document.getElementById('btn-close-threads').addEventListener('click', () => this.closeDrawers());

    document.getElementById('btn-open-diary').addEventListener('click', () => this.openDiaryModal());
    document.getElementById('btn-close-diary').addEventListener('click', () => this.diaryModal.close());
    document.getElementById('btn-refresh-diary').addEventListener('click', () => this.fetchDiary(true));

    document.getElementById('btn-open-settings').addEventListener('click', () => this.openSettingsModal());
    document.getElementById('btn-close-settings').addEventListener('click', () => this.settingsModal.close());

    this.drawerOverlay.addEventListener('click', () => this.closeDrawers());

    // Living pill click -> opens settings / mood
    document.getElementById('living-pill').addEventListener('click', () => this.openSettingsModal());

    // Memory filter buttons
    document.querySelectorAll('.filter-pill').forEach((pill) => {
      pill.addEventListener('click', (e) => {
        document.querySelectorAll('.filter-pill').forEach((p) => p.classList.remove('active'));
        pill.classList.add('active');
        this.activeFilter = pill.getAttribute('data-filter');
        this.renderMemoriesList();
      });
    });

    // Save memory form
    document.getElementById('btn-save-memory').addEventListener('click', () => this.saveNewMemory());

    // Settings model select
    document.getElementById('model-select').addEventListener('change', (e) => {
      this.changeModel(e.target.value);
    });

    // Mood buttons
    document.querySelectorAll('.mood-opt-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const mood = btn.getAttribute('data-mood');
        this.changeMood(mood);
      });
    });

    // Clear history in settings
    const wipeBtn = document.getElementById('btn-wipe-history');
    if (wipeBtn) {
      wipeBtn.addEventListener('click', () => this.clearChat());
    }
  }

  toggleVoiceMode() {
    this.voiceEnabled = !this.voiceEnabled;
    localStorage.setItem('anaya_voice_enabled', this.voiceEnabled);
    this.updateVoiceBadge();
    const stateLabel = this.voiceEnabled ? 'Enabled (Auto-play On)' : 'Disabled (Auto-play Off)';
    this.showToast(`Neural Voice Notes: ${stateLabel}`, this.voiceEnabled ? 'success' : 'info');
  }

  updateVoiceBadge() {
    if (this.voiceBadge) {
      this.voiceBadge.textContent = this.voiceEnabled ? 'On' : 'Off';
      this.voiceBadge.style.color = this.voiceEnabled ? 'var(--accent-green)' : 'var(--text-dim)';
      this.voiceBadge.style.borderColor = this.voiceEnabled ? 'var(--accent-green)' : 'var(--text-dim)';
    }
    const voiceModeBtn = document.getElementById('btn-toggle-voice-mode');
    if (voiceModeBtn) {
      voiceModeBtn.textContent = this.voiceEnabled ? 'Auto-play On' : 'Auto-play Off';
      voiceModeBtn.style.color = this.voiceEnabled ? 'var(--accent-pink)' : 'var(--text-dim)';
    }
  }

  // =========================================================================
  // Status Synchronization
  // =========================================================================

  async refreshStatus() {
    try {
      const res = await fetch('/api/status');
      if (!res.ok) return;
      const data = await res.json();

      const living = data.living_state || {};
      if (this.statusActivity && living.activity) {
        this.statusActivity.textContent = living.activity;
      }
      if (this.statusMood && living.mood_name) {
        this.statusMood.textContent = living.mood_name;
      }
      if (this.statusMusic && living.music) {
        this.statusMusic.textContent = living.music;
      }

      // Update hero vibe
      const heroVibe = document.getElementById('hero-vibe-val');
      if (heroVibe && living.vibe) {
        heroVibe.textContent = `${living.activity} (${living.vibe})`;
      }

      // Update threads badge
      const openThreads = data.open_threads_count || 0;
      if (this.threadsBadge) {
        this.threadsBadge.textContent = openThreads;
        this.threadsBadge.style.display = openThreads > 0 ? 'inline-block' : 'none';
      }

      // Update settings stats
      const stats = data.stats || {};
      const totalMsgs = document.getElementById('stat-total-msgs');
      const daysKnown = document.getElementById('stat-days-known');
      const memCount = document.getElementById('stat-memories-count');

      if (totalMsgs) totalMsgs.textContent = stats.total_messages || 0;
      if (daysKnown) daysKnown.textContent = stats.days_known || 1;
      if (memCount) memCount.textContent = stats.total_memories || 0;

      // Update model dropdown selection
      const modelSelect = document.getElementById('model-select');
      if (modelSelect && data.active_model) {
        modelSelect.value = data.active_model;
      }
    } catch (e) {
      console.warn('Status refresh error:', e);
    }
  }

  // =========================================================================
  // Conversation History
  // =========================================================================

  async loadHistory() {
    try {
      const res = await fetch('/api/history?limit=30');
      if (!res.ok) return;
      const data = await res.json();
      const messages = data.messages || [];

      if (messages.length > 0 && this.welcomeHero) {
        this.welcomeHero.style.display = 'none';
      }

      messages.forEach((m) => {
        this.appendMessageBubble(m.role, m.content, m.timestamp);
      });

      this.scrollToBottom();
    } catch (e) {
      console.warn('History load error:', e);
    }
  }

  // =========================================================================
  // Send & Real-time Streaming with Burst Messaging & Typing Physics
  // =========================================================================

  async sendMessage() {
    const text = this.inputField.value.trim();
    if (!text || this.isStreaming) return;

    // Handle slash commands immediately
    if (text.startsWith('/')) {
      this.inputField.value = '';
      this.inputField.style.height = 'auto';
      await this.handleSlashCommand(text);
      return;
    }

    this.isStreaming = true;
    this.inputField.value = '';
    this.inputField.style.height = 'auto';

    if (this.welcomeHero) {
      this.welcomeHero.style.display = 'none';
    }

    // Append user message
    this.appendMessageBubble('user', text, new Date().toISOString());
    this.scrollToBottom();

    // Show initial typing indicator
    this.typingIndicator.style.display = 'inline-flex';

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: this.sessionId,
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      this.typingIndicator.style.display = 'none';

      // Setup Anaya message row with a burst cluster container
      const row = document.createElement('div');
      row.className = 'message-row anaya-row';

      const avatar = document.createElement('img');
      avatar.src = '/static/images/anaya_avatar.jpg';
      avatar.alt = 'Anaya';
      avatar.className = 'msg-avatar';
      row.appendChild(avatar);

      const cluster = document.createElement('div');
      cluster.className = 'burst-cluster';
      row.appendChild(cluster);

      this.messagesContainer.appendChild(row);

      // Active live bubble inside cluster
      let activeWrapper = document.createElement('div');
      let activeBubble = document.createElement('div');
      activeBubble.className = 'message-bubble anaya-bubble burst-bubble';
      activeWrapper.appendChild(activeBubble);
      cluster.appendChild(activeWrapper);
      this.scrollToBottom();

      let accumulatedText = '';
      let currentBurstText = '';

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.replace('data: ', '').trim();
            if (!jsonStr) continue;
            try {
              const data = JSON.parse(jsonStr);
              if (data.token) {
                accumulatedText += data.token;

                // Handle burst delimiter '|||'
                if (data.token.includes('|||') || currentBurstText.includes('|||')) {
                  const parts = currentBurstText.split('|||');
                  const finishedText = parts[0].trim();
                  activeBubble.textContent = finishedText;

                  // Add Listen button to the finished bubble
                  if (finishedText && !activeWrapper.querySelector('.btn-audio-listen')) {
                    const listenBtn = this.createListenButton(finishedText, activeWrapper);
                    activeWrapper.appendChild(listenBtn);
                  }

                  // Spawn new bubble for next burst
                  activeWrapper = document.createElement('div');
                  activeBubble = document.createElement('div');
                  activeBubble.className = 'message-bubble anaya-bubble burst-bubble';
                  activeWrapper.appendChild(activeBubble);
                  cluster.appendChild(activeWrapper);

                  currentBurstText = parts[1] || '';
                  activeBubble.textContent = currentBurstText;
                } else {
                  currentBurstText += data.token;
                  activeBubble.textContent = currentBurstText.replace('|||', '').trim();
                }
                this.scrollToBottom();
              }

              if (data.done) {
                accumulatedText = data.full_response || accumulatedText;
                const finalBursts = accumulatedText.split('|||').map((s) => s.trim()).filter(Boolean);

                // Re-render cluster cleanly with timestamp and voice controls
                cluster.innerHTML = '';
                const timeNow = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                finalBursts.forEach((bText, idx) => {
                  const bWrapper = document.createElement('div');
                  const bBubble = document.createElement('div');
                  bBubble.className = 'message-bubble anaya-bubble burst-bubble';
                  bBubble.textContent = bText;

                  const listenBtn = this.createListenButton(bText, bWrapper);

                  const meta = document.createElement('div');
                  meta.className = 'msg-meta';
                  meta.innerHTML = `<span class="msg-time">${timeNow}</span>`;

                  bWrapper.appendChild(bBubble);
                  bWrapper.appendChild(listenBtn);
                  bWrapper.appendChild(meta);
                  cluster.appendChild(bWrapper);
                });

                this.scrollToBottom();

                // If voice auto-play is enabled: play Neural Voice Note for the message
                if (this.voiceEnabled && finalBursts.length > 0) {
                  const firstWrapper = cluster.querySelector('div');
                  const firstListenBtn = firstWrapper ? firstWrapper.querySelector('.btn-audio-listen') : null;
                  const speechTarget = finalBursts.join(' ');
                  this.playNeuralVoiceNote(speechTarget, firstWrapper, firstListenBtn, true);
                }
              }
            } catch (err) {
              console.error('Error parsing SSE json:', err);
            }
          }
        }
      }

      // Refresh living status after chat
      this.refreshStatus();
    } catch (err) {
      this.typingIndicator.style.display = 'none';
      this.appendMessageBubble('assistant', `[Could not connect to Anaya: ${err.message}]`);
    } finally {
      this.isStreaming = false;
    }
  }

  appendMessageBubble(role, content, timestamp) {
    const isUser = role === 'user';
    const row = document.createElement('div');
    row.className = `message-row ${isUser ? 'user-row' : 'anaya-row'}`;

    if (!isUser) {
      const avatar = document.createElement('img');
      avatar.src = '/static/images/anaya_avatar.jpg';
      avatar.alt = 'Anaya';
      avatar.className = 'msg-avatar';
      row.appendChild(avatar);
    }

    const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Now';

    if (isUser) {
      const bubbleWrapper = document.createElement('div');
      const bubble = document.createElement('div');
      bubble.className = 'message-bubble user-bubble';
      bubble.textContent = content;

      const meta = document.createElement('div');
      meta.className = 'msg-meta';
      meta.innerHTML = `<span class="msg-time">${timeStr}</span>`;

      bubbleWrapper.appendChild(bubble);
      bubbleWrapper.appendChild(meta);
      row.appendChild(bubbleWrapper);
    } else {
      // Split content into bursts if delimiter present
      const bursts = content.split('|||').map((s) => s.trim()).filter(Boolean);
      const cluster = document.createElement('div');
      cluster.className = 'burst-cluster';

      bursts.forEach((burstText) => {
        const bubbleWrapper = document.createElement('div');
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble anaya-bubble burst-bubble';
        bubble.textContent = burstText;

        const listenBtn = this.createListenButton(burstText, bubbleWrapper);

        const meta = document.createElement('div');
        meta.className = 'msg-meta';
        meta.innerHTML = `<span class="msg-time">${timeStr}</span>`;

        bubbleWrapper.appendChild(bubble);
        bubbleWrapper.appendChild(listenBtn);
        bubbleWrapper.appendChild(meta);
        cluster.appendChild(bubbleWrapper);
      });

      row.appendChild(cluster);
    }

    this.messagesContainer.appendChild(row);
  }

  createListenButton(text, container) {
    const btn = document.createElement('button');
    btn.className = 'btn-audio-listen';
    btn.innerHTML = `
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
        <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
      </svg>
      <span>Voice Note</span>
    `;
    btn.addEventListener('click', () => {
      this.playNeuralVoiceNote(text, container, btn, true);
    });
    return btn;
  }

  scrollToBottom() {
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  // =========================================================================
  // High-Definition Neural Voice Note Engine (edge-tts)
  // =========================================================================

  async playNeuralVoiceNote(text, parentContainer, triggerBtn, autoPlay = true) {
    if (!text || !parentContainer) return;

    // If player is already rendered inside parentContainer, toggle it
    const existingPlayer = parentContainer.querySelector('.voice-note-player');
    if (existingPlayer) {
      const playBtn = existingPlayer.querySelector('.vn-play-btn');
      if (playBtn) playBtn.click();
      return;
    }

    // Set loading indicator
    if (triggerBtn) {
      triggerBtn.classList.add('loading');
      triggerBtn.innerHTML = '<span>Synthesizing...</span>';
    }

    try {
      const res = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text,
          voice: this.selectedVoice,
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const audioUrl = data.audio_url;

      if (triggerBtn) {
        triggerBtn.classList.remove('loading');
        triggerBtn.style.display = 'none';
      }

      const playIconSvg = '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="6 3 20 12 6 21 6 3"></polygon></svg>';
      const pauseIconSvg = '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>';

      // Stop any active audio
      if (this.currentAudio) {
        this.currentAudio.pause();
        document.querySelectorAll('.voice-note-player.playing').forEach((p) => p.classList.remove('playing'));
        document.querySelectorAll('.vn-play-btn').forEach((b) => (b.innerHTML = playIconSvg));
      }

      // Build WhatsApp / Telegram style Audio Note Card
      const player = document.createElement('div');
      player.className = 'voice-note-player';

      const playBtn = document.createElement('button');
      playBtn.className = 'vn-play-btn';
      playBtn.title = 'Play / Pause';
      playBtn.innerHTML = playIconSvg;

      const body = document.createElement('div');
      body.className = 'vn-body';

      const waveform = document.createElement('div');
      waveform.className = 'vn-waveform';

      const barHeights = [8, 14, 18, 10, 22, 16, 12, 20, 24, 16, 14, 22, 18, 10, 16, 20, 14, 18, 12, 22, 16, 10, 14, 8];
      const bars = [];
      barHeights.forEach((h) => {
        const bar = document.createElement('div');
        bar.className = 'vn-bar';
        bar.style.height = `${h}px`;
        waveform.appendChild(bar);
        bars.push(bar);
      });

      const meta = document.createElement('div');
      meta.className = 'vn-meta';

      const timeSpan = document.createElement('span');
      timeSpan.className = 'vn-time';
      timeSpan.textContent = '0:00';

      const voiceLabel = document.createElement('span');
      voiceLabel.className = 'vn-voice-label';
      voiceLabel.textContent = 'Anaya Voice';

      meta.appendChild(timeSpan);
      meta.appendChild(voiceLabel);

      body.appendChild(waveform);
      body.appendChild(meta);

      player.appendChild(playBtn);
      player.appendChild(body);

      parentContainer.appendChild(player);

      const audio = document.createElement('audio');
      audio.preload = 'metadata';
      audio.src = audioUrl;
      audio.style.display = 'none';
      player.appendChild(audio);

      const formatTime = (secs) => {
        if (isNaN(secs) || !isFinite(secs)) return '0:00';
        const m = Math.floor(secs / 60);
        const s = Math.floor(secs % 60);
        return `${m}:${s < 10 ? '0' : ''}${s}`;
      };

      audio.addEventListener('loadedmetadata', () => {
        timeSpan.textContent = formatTime(audio.duration);
      });

      audio.addEventListener('timeupdate', () => {
        if (audio.duration && isFinite(audio.duration)) {
          timeSpan.textContent = `${formatTime(audio.currentTime)} / ${formatTime(audio.duration)}`;
          const progress = audio.currentTime / audio.duration;
          const activeIndex = Math.floor(progress * bars.length);
          bars.forEach((b, idx) => {
            if (idx <= activeIndex) {
              b.classList.add('active');
            } else {
              b.classList.remove('active');
            }
          });
        }
      });

      audio.addEventListener('play', () => {
        player.classList.add('playing');
        playBtn.innerHTML = pauseIconSvg;
      });

      audio.addEventListener('pause', () => {
        player.classList.remove('playing');
        playBtn.innerHTML = playIconSvg;
      });

      audio.addEventListener('ended', () => {
        player.classList.remove('playing');
        playBtn.innerHTML = playIconSvg;
        bars.forEach((b) => b.classList.remove('active'));
        timeSpan.textContent = formatTime(audio.duration);
      });

      audio.addEventListener('error', () => {
        const err = audio.error;
        if (!err || err.code === 1) return;

        console.warn(`Audio element error (code ${err.code}): ${err.message || 'Media load error'}`);
        // Transparently play synthesized neural audio via Web Audio API decode engine
        this.playViaWebAudio(audioUrl, text, player, playBtn, bars, timeSpan);
      });

      playBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (audio.paused) {
          if (this.currentAudio && this.currentAudio !== audio) {
            this.currentAudio.pause();
          }
          if (this.currentSourceNode) {
            try { this.currentSourceNode.stop(); } catch (stopErr) {}
          }
          this.currentAudio = audio;
          try {
            await audio.play();
          } catch (playErr) {
            if (playErr.name === 'AbortError') {
              return; // Pause/interruption during promise is normal
            }
            console.warn('Audio playback error:', playErr);
            if (playErr.name === 'NotAllowedError') {
              this.showToast('Tap the play button again to start audio.', 'info');
            } else {
              // Try decoding and playing neural audio via Web Audio API
              this.playViaWebAudio(audioUrl, text, player, playBtn, bars, timeSpan);
            }
          }
        } else {
          audio.pause();
        }
      });

      waveform.addEventListener('click', (e) => {
        const rect = waveform.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const ratio = Math.max(0, Math.min(1, clickX / rect.width));
        if (audio.duration && isFinite(audio.duration)) {
          audio.currentTime = ratio * audio.duration;
        }
      });

      if (autoPlay) {
        this.currentAudio = audio;
        audio.play().then(() => {
          player.classList.add('playing');
          playBtn.innerHTML = pauseIconSvg;
        }).catch((e) => {
          console.log('Autoplay deferred by browser policy:', e.name);
          this.showToast('Voice Note ready • Click play on the bubble to listen', 'info', 4000);
        });
      }
    } catch (err) {
      console.error('Voice note generation error:', err);
      if (triggerBtn) {
        triggerBtn.classList.remove('loading');
        triggerBtn.style.display = 'inline-flex';
        triggerBtn.innerHTML = `
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
          </svg>
          <span>Speak (Browser TTS)</span>
        `;
        triggerBtn.onclick = () => this.speakWithWebSpeechFallback(text);
      }
    }
  }

  async playViaWebAudio(audioUrl, fallbackText, player, playBtn, bars, timeSpan) {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) {
        this.speakWithWebSpeechFallback(fallbackText);
        return;
      }
      if (!this.webAudioCtx) {
        this.webAudioCtx = new AudioCtx();
      }
      if (this.webAudioCtx.state === 'suspended') {
        await this.webAudioCtx.resume();
      }

      const res = await fetch(audioUrl);
      const arrayBuffer = await res.arrayBuffer();
      const audioBuffer = await this.webAudioCtx.decodeAudioData(arrayBuffer);

      if (this.currentSourceNode) {
        try { this.currentSourceNode.stop(); } catch (e) {}
      }

      const source = this.webAudioCtx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.webAudioCtx.destination);

      const pauseIconSvg = '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>';
      const playIconSvg = '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="6 3 20 12 6 21 6 3"></polygon></svg>';

      player.classList.add('playing');
      playBtn.innerHTML = pauseIconSvg;

      const duration = audioBuffer.duration;
      const startTime = this.webAudioCtx.currentTime;

      const animInterval = setInterval(() => {
        const elapsed = this.webAudioCtx.currentTime - startTime;
        if (elapsed >= duration) {
          clearInterval(animInterval);
          player.classList.remove('playing');
          playBtn.innerHTML = playIconSvg;
          bars.forEach((b) => b.classList.remove('active'));
          return;
        }
        const progress = elapsed / duration;
        const activeIndex = Math.floor(progress * bars.length);
        bars.forEach((b, idx) => {
          if (idx <= activeIndex) b.classList.add('active');
          else b.classList.remove('active');
        });
        const m = Math.floor(elapsed / 60);
        const s = Math.floor(elapsed % 60);
        timeSpan.textContent = `${m}:${s < 10 ? '0' : ''}${s}`;
      }, 100);

      source.onended = () => {
        clearInterval(animInterval);
        player.classList.remove('playing');
        playBtn.innerHTML = playIconSvg;
        bars.forEach((b) => b.classList.remove('active'));
      };

      source.start(0);
      this.currentSourceNode = source;
    } catch (webaudioErr) {
      console.warn('Web Audio API playback failed:', webaudioErr);
      this.speakWithWebSpeechFallback(fallbackText);
    }
  }

  speakWithWebSpeechFallback(text) {
    if (!('speechSynthesis' in window)) {
      this.showToast('Speech synthesis not supported in this browser.', 'warning');
      return;
    }
    try {
      window.speechSynthesis.cancel();
      const cleanText = text
        .replace(/\|\|\|/g, '. ')
        .replace(/\*[^*]+\*/g, '')
        .replace(/https?:\/\/\S+/g, '')
        .replace(/[#`_~>]/g, '')
        .trim();

      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.lang = 'en-IN';
      utterance.rate = 1.0;
      utterance.pitch = 1.05;

      const voices = window.speechSynthesis.getVoices();
      const matchVoice = voices.find(
        (v) => v.lang === 'en-IN' || (v.lang.startsWith('en') && v.name.toLowerCase().includes('india')) || v.lang === 'hi-IN'
      );
      if (matchVoice) {
        utterance.voice = matchVoice;
      }
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn('SpeechSynthesis error:', e);
    }
  }

  speakText(text) {
    // Delegated to high-fidelity Neural Voice Engine
    this.playNeuralVoiceNote(text, this.messagesContainer.lastElementChild, null, true);
  }

  // =========================================================================
  // Speech Recognition (Microphone Voice Input)
  // =========================================================================

  setupSpeechRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      if (this.micBtn) {
        this.micBtn.title = 'Speech-to-text not supported in this browser';
        this.micBtn.addEventListener('click', () => {
          this.showToast('Speech recognition is not supported in this browser. Please use Chrome or Edge.', 'warning');
        });
      }
      return;
    }

    this.recognition = new SpeechRec();
    this.recognition.continuous = false;
    this.recognition.interimResults = true;
    this.recognition.lang = 'en-IN';

    this.recognition.onstart = () => {
      this.isListening = true;
      this.micBtn.classList.add('listening');
      this.showToast('Listening... Speak into your microphone', 'info', 3000);
    };

    this.recognition.onresult = (event) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      this.inputField.value = transcript;
    };

    this.recognition.onend = () => {
      this.isListening = false;
      this.micBtn.classList.remove('listening');
    };

    this.recognition.onerror = (event) => {
      this.isListening = false;
      this.micBtn.classList.remove('listening');
      if (event.error === 'not-allowed') {
        this.showToast('Microphone access blocked. Please allow microphone in browser settings.', 'danger', 5000);
      } else if (event.error !== 'no-speech') {
        this.showToast(`Microphone error: ${event.error}`, 'warning', 3000);
      }
    };
  }

  toggleMicrophone() {
    if (!this.recognition) return;
    if (this.isListening) {
      this.recognition.stop();
    } else {
      try {
        this.recognition.start();
      } catch (e) {
        console.warn('Recognition start error:', e);
      }
    }
  }

  // =========================================================================
  // Undo, Clear Chat & Slash Command Execution
  // =========================================================================

  async handleSlashCommand(cmdStr) {
    const parts = cmdStr.trim().split(/\s+/);
    const cmd = parts[0].toLowerCase();
    const arg = parts[1];

    if (cmd === '/undo' || cmd === '/delturn') {
      const turns = parseInt(arg, 10) || 1;
      await this.undoLastTurn(turns);
      return;
    }

    if (cmd === '/clear' || cmd === '/reset') {
      await this.clearChat();
      return;
    }

    if (cmd === '/diary' || cmd === '/journal') {
      this.openDiaryModal();
      return;
    }

    if (cmd === '/memory' || cmd === '/memories') {
      this.openMemoryDrawer();
      return;
    }

    if (cmd === '/settings') {
      this.openSettingsModal();
      return;
    }

    if (cmd === '/help') {
      this.showToast('Available commands: /undo [n], /clear, /diary, /memories, /settings', 'info', 4000);
      return;
    }

    this.showToast(`Unknown command '${cmd}'. Type /help for options.`, 'warning');
  }

  async undoLastTurn(turns = 1) {
    try {
      const res = await fetch('/api/delete-last', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'turn', count: turns }),
      });
      const data = await res.json();
      if (data.deleted_count > 0) {
        // Remove the corresponding message rows from DOM
        // In a turn there is 1 user row and 1 assistant row
        const removeCount = data.deleted_count;
        const rows = Array.from(this.messagesContainer.querySelectorAll('.message-row'));
        const toRemove = rows.slice(-removeCount);
        toRemove.forEach((r) => r.remove());

        // If no message rows remain, restore the welcome hero!
        const remainingRows = this.messagesContainer.querySelectorAll('.message-row');
        if (remainingRows.length === 0 && this.welcomeHero) {
          this.welcomeHero.style.display = 'flex';
        }

        const turnLabel = turns > 1 ? `${turns} turns` : 'last turn';
        this.showToast(`Undid ${turnLabel} (${data.deleted_count} messages removed)`, 'success');
        this.refreshStatus();
      } else {
        this.showToast('No conversation turns to undo.', 'warning');
      }
    } catch (e) {
      this.showToast('Failed to undo turn: ' + e.message, 'danger');
    }
  }

  async clearChat() {
    try {
      const res = await fetch('/api/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: this.sessionId, all_sessions: true }),
      });
      const data = await res.json();
      if (data.success) {
        // Remove all message rows from DOM
        const rows = this.messagesContainer.querySelectorAll('.message-row');
        rows.forEach((r) => r.remove());

        // Restore welcome hero
        if (this.welcomeHero) {
          this.welcomeHero.style.display = 'flex';
        }

        // Generate fresh session ID
        this.sessionId = 'web_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
        localStorage.setItem('anaya_web_session_id', this.sessionId);

        if (this.settingsModal && this.settingsModal.open) {
          this.settingsModal.close();
        }

        this.showToast('Conversation cleared. Started a fresh session.', 'success');
        this.refreshStatus();
      } else {
        this.showToast('Could not clear conversation.', 'warning');
      }
    } catch (e) {
      this.showToast('Failed to clear chat: ' + e.message, 'danger');
    }
  }

  showToast(message, type = 'info', duration = 3000) {
    if (!this.toastContainer) {
      this.toastContainer = document.getElementById('toast-container');
    }
    if (!this.toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconSvg = '';
    if (type === 'success') {
      iconSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#34d399" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>';
    } else if (type === 'warning') {
      iconSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>';
    } else if (type === 'danger') {
      iconSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
    } else {
      iconSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';
    }

    toast.innerHTML = `${iconSvg}<span>${message}</span>`;
    this.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('toast-exit');
      setTimeout(() => toast.remove(), 250);
    }, duration);
  }

  // =========================================================================
  // Memory Bank Drawer
  // =========================================================================

  async openMemoryDrawer() {
    this.drawerOverlay.classList.add('active');
    this.memoryDrawer.classList.add('active');
    await this.fetchMemories();
  }

  async fetchMemories() {
    const listEl = document.getElementById('memories-list');
    listEl.innerHTML = '<div class="loading-state">Loading memories...</div>';

    try {
      const res = await fetch('/api/memories');
      const data = await res.json();
      this.memoriesCache = data.memories || [];
      this.renderMemoriesList();
    } catch (e) {
      listEl.innerHTML = '<div class="loading-state">Error loading memories</div>';
    }
  }

  renderMemoriesList() {
    const listEl = document.getElementById('memories-list');
    listEl.innerHTML = '';

    const filtered =
      this.activeFilter === 'all'
        ? this.memoriesCache
        : this.memoriesCache.filter((m) => m.category === this.activeFilter);

    if (filtered.length === 0) {
      listEl.innerHTML = '<div class="loading-state">No memories in this category yet.</div>';
      return;
    }

    filtered.forEach((m) => {
      const card = document.createElement('div');
      card.className = 'memory-card';

      card.innerHTML = `
        <div class="card-top-row">
          <span class="cat-badge">${m.category || 'general'}</span>
          <button class="delete-item-btn" title="Delete memory">&times;</button>
        </div>
        <div class="card-key">${m.key}</div>
        <div class="card-val">${m.value}</div>
      `;

      card.querySelector('.delete-item-btn').addEventListener('click', () => {
        this.deleteMemory(m.key);
      });

      listEl.appendChild(card);
    });
  }

  async saveNewMemory() {
    const key = document.getElementById('new-mem-key').value.trim();
    const val = document.getElementById('new-mem-val').value.trim();
    const cat = document.getElementById('new-mem-cat').value;

    if (!key || !val) {
      alert('Please provide both memory title and details.');
      return;
    }

    try {
      const res = await fetch('/api/memories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value: val, category: cat }),
      });
      if (res.ok) {
        document.getElementById('new-mem-key').value = '';
        document.getElementById('new-mem-val').value = '';
        await this.fetchMemories();
      }
    } catch (e) {
      alert('Error saving memory');
    }
  }

  async deleteMemory(key) {
    if (!confirm(`Delete memory "${key}"?`)) return;
    try {
      await fetch(`/api/memories/${encodeURIComponent(key)}`, { method: 'DELETE' });
      await this.fetchMemories();
    } catch (e) {
      alert('Error deleting memory');
    }
  }

  // =========================================================================
  // Life Threads Drawer
  // =========================================================================

  async openThreadsDrawer() {
    this.drawerOverlay.classList.add('active');
    this.threadsDrawer.classList.add('active');
    await this.fetchThreads();
  }

  async fetchThreads() {
    const listEl = document.getElementById('threads-list');
    listEl.innerHTML = '<div class="loading-state">Loading active threads...</div>';

    try {
      const res = await fetch('/api/threads');
      const data = await res.json();
      const threads = data.threads || [];
      listEl.innerHTML = '';

      if (threads.length === 0) {
        listEl.innerHTML = '<div class="loading-state">No active life threads right now. Mention an upcoming event to Anaya!</div>';
        return;
      }

      threads.forEach((t) => {
        const card = document.createElement('div');
        card.className = 'thread-card';
        card.innerHTML = `
          <div class="card-top-row">
            <span class="cat-badge">Upcoming Event</span>
            <button class="primary-btn" style="padding: 3px 8px; font-size: 0.72rem;">Mark Done</button>
          </div>
          <div class="card-key">${t.topic}</div>
          <div class="card-val">${t.context}</div>
          ${t.follow_up_hint ? `<div class="card-val" style="color: var(--accent-pink); font-style: italic; margin-top: 4px;">Follow-up: "${t.follow_up_hint}"</div>` : ''}
        `;

        card.querySelector('button').addEventListener('click', async () => {
          await fetch('/api/threads/resolve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: t.topic }),
          });
          await this.fetchThreads();
          this.refreshStatus();
        });

        listEl.appendChild(card);
      });
    } catch (e) {
      listEl.innerHTML = '<div class="loading-state">Error loading threads</div>';
    }
  }

  // =========================================================================
  // Secret Diary Modal
  // =========================================================================

  async openDiaryModal() {
    this.diaryModal.showModal();
    await this.fetchDiary(false);
  }

  async fetchDiary(forceRefresh = false) {
    const bodyEl = document.getElementById('diary-content-body');
    bodyEl.innerHTML = '<p class="diary-loading">Anaya is writing in her personal journal...</p>';

    try {
      const res = await fetch('/api/diary');
      const data = await res.json();
      bodyEl.innerHTML = `<p>${(data.diary_entry || '').replace(/\n/g, '<br>')}</p>`;
    } catch (e) {
      bodyEl.innerHTML = '<p>Could not open Anaya’s diary right now.</p>';
    }
  }

  // =========================================================================
  // Settings & Mood Modal
  // =========================================================================

  openSettingsModal() {
    const voiceSelect = document.getElementById('voice-select');
    if (voiceSelect) {
      voiceSelect.value = this.selectedVoice;
    }
    const voiceModeBtn = document.getElementById('btn-toggle-voice-mode');
    if (voiceModeBtn) {
      voiceModeBtn.textContent = this.voiceEnabled ? 'Auto-play On' : 'Auto-play Off';
      voiceModeBtn.style.color = this.voiceEnabled ? 'var(--accent-pink)' : 'var(--text-dim)';
    }
    this.settingsModal.showModal();
  }

  async changeModel(model) {
    try {
      const res = await fetch('/api/model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model }),
      });
      const data = await res.json();
      if (data.success) {
        this.refreshStatus();
      }
    } catch (e) {
      alert('Error switching model');
    }
  }

  async changeMood(moodKey) {
    try {
      const res = await fetch('/api/mood', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mood_key: moodKey }),
      });
      const data = await res.json();
      if (data.success) {
        this.refreshStatus();
        this.settingsModal.close();
      }
    } catch (e) {
      alert('Error changing mood');
    }
  }

  closeDrawers() {
    this.drawerOverlay.classList.remove('active');
    this.memoryDrawer.classList.remove('active');
    this.threadsDrawer.classList.remove('active');
  }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
  window.anaya = new AnayaApp();
});
