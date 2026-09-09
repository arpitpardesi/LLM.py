/**
 * Anaya 2.0 • Living AI Companion Client Application
 * Handles real-time SSE streaming, voice synthesis, microphone dictation,
 * dynamic status synchronization, and drawer/modal management.
 */

class AnayaApp {
  constructor() {
    this.sessionId = this.getOrCreateSessionId();
    this.isStreaming = false;
    this.voiceEnabled = localStorage.getItem('anaya_voice_enabled') === 'true';
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
    this.typingLabelText = document.getElementById('typing-label-text');
    this.welcomeHero = document.getElementById('welcome-hero');

    // Realism & Conversational Cadence
    this.realisticCadence = localStorage.getItem('anaya_realistic_cadence') !== 'false';
    this.soundEffectsEnabled = localStorage.getItem('anaya_sound_effects') !== 'false';
    this.audioCtx = null;
    this.btnToggleCadence = document.getElementById('btn-toggle-cadence');
    this.btnTogglePopSound = document.getElementById('btn-toggle-pop-sound');
    this.cadenceStatusTag = document.getElementById('cadence-status-tag');

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
    this.affinityModal = document.getElementById('affinity-modal');
    this.activitiesModal = document.getElementById('activities-modal');
    this.proactiveBanner = document.getElementById('proactive-banner');
    this.onboardingModal = document.getElementById('onboarding-modal');
    this.resetConfirmModal = document.getElementById('reset-confirm-modal');
    this.clearMemoriesModal = document.getElementById('clear-memories-modal');
    this.jsonModal = document.getElementById('json-modal');
    this.momentsModal = document.getElementById('modal-moments');

    // Theme & Moments & Analytics Elements
    this.theme = localStorage.getItem('anaya_theme') || 'auto';
    this.themeSelect = document.getElementById('theme-select');
    this.currentThemeStatus = document.getElementById('current-theme-status');
    this.btnCycleTheme = document.getElementById('btn-cycle-theme');
    this.btnOpenMoments = document.getElementById('btn-open-moments');
    this.btnCloseMoments = document.getElementById('btn-close-moments');
    this.momentsGrid = document.getElementById('moments-grid');
    this.btnRefreshAnalytics = document.getElementById('btn-refresh-analytics');
    this.archiveUploadInput = document.getElementById('archive-upload-input');
    this.btnSelectArchiveFile = document.getElementById('btn-select-archive-file');
    this.selectedArchiveName = document.getElementById('selected-archive-name');
    this.btnUploadRestoreArchive = document.getElementById('btn-upload-restore-archive');

    // Tab Navigation & Admin Explorer State
    this.currentTab = 'chat';
    this.currentTraits = [];
    this.adminMemoriesCache = [];
    this.adminSkip = 0;
    this.adminLimit = 30;
    this.adminTotal = 0;
    this.adminQuery = '';
    this.adminRole = 'all';
    this.currentInspectedDoc = null;

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
    this.initPWA();
    this.initThemeEngine();
    this.initNavigation();
    this.bindEvents();
    this.setupArchiveHandlers();
    this.setupAudioUnlocker();
    this.setupSpeechRecognition();
    this.loadChatHistory();
    this.refreshStatus();
    this.checkProactiveGreeting();
    this.initPersonalityBuilder();

    // Auto refresh status every 30 seconds
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
    if (this.micBtn) {
      this.micBtn.addEventListener('click', () => this.toggleMicrophone());
    }

    // Voice toggle
    const voiceToggleBtn = document.getElementById('btn-voice-toggle');
    if (voiceToggleBtn) {
      voiceToggleBtn.addEventListener('click', () => {
        this.toggleVoiceMode();
      });
    }

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
    const btnOpenMemory = document.getElementById('btn-open-memory');
    if (btnOpenMemory) {
      btnOpenMemory.addEventListener('click', () => this.openMemoryDrawer());
    }

    const btnCloseMemory = document.getElementById('btn-close-memory');
    if (btnCloseMemory) {
      btnCloseMemory.addEventListener('click', () => this.closeDrawers());
    }

    const btnOpenDiary = document.getElementById('btn-open-diary');
    if (btnOpenDiary) {
      btnOpenDiary.addEventListener('click', () => this.openDiaryModal());
    }

    const btnCloseDiary = document.getElementById('btn-close-diary');
    if (btnCloseDiary) {
      btnCloseDiary.addEventListener('click', () => this.diaryModal?.close());
    }

    // Moments modal triggers
    if (this.btnOpenMoments) {
      this.btnOpenMoments.addEventListener('click', () => this.openMomentsModal());
    }
    if (this.btnCloseMoments) {
      this.btnCloseMoments.addEventListener('click', () => this.closeMomentsModal());
    }

    // Analytics refresh trigger
    if (this.btnRefreshAnalytics) {
      this.btnRefreshAnalytics.addEventListener('click', () => {
        this.loadAdminAnalytics();
        this.showToast('Companion analytics updated!', 'info');
      });
    }

    const btnRefreshDiary = document.getElementById('btn-refresh-diary');
    if (btnRefreshDiary) {
      btnRefreshDiary.addEventListener('click', () => this.fetchDiary(true));
    }

    const btnDeleteTodayDiary = document.getElementById('btn-delete-today-diary');
    if (btnDeleteTodayDiary) {
      btnDeleteTodayDiary.addEventListener('click', () => this.deleteTodayDiary());
    }

    const btnClearDiaryModal = document.getElementById('btn-clear-diary-modal');
    if (btnClearDiaryModal) {
      btnClearDiaryModal.addEventListener('click', () => this.clearAllDiaryEntries());
    }

    const btnOpenSettings = document.getElementById('btn-open-settings');
    if (btnOpenSettings) {
      btnOpenSettings.addEventListener('click', () => this.openSettingsModal());
    }

    const btnCloseSettings = document.getElementById('btn-close-settings');
    if (btnCloseSettings) {
      btnCloseSettings.addEventListener('click', () => this.settingsModal?.close());
    }

    if (this.drawerOverlay) {
      this.drawerOverlay.addEventListener('click', () => this.closeDrawers());
    }

    // Vault Clear All button & Clear Memories modal
    const btnVaultClearAll = document.getElementById('btn-vault-clear-all');
    if (btnVaultClearAll) {
      btnVaultClearAll.addEventListener('click', () => {
        if (this.clearMemoriesModal) {
          try { this.clearMemoriesModal.showModal(); } catch (_) { this.clearMemoriesModal.setAttribute('open', ''); }
        }
      });
    }

    const btnCloseClearMem = document.getElementById('btn-close-clear-memories-modal');
    const btnCancelClearMem = document.getElementById('btn-cancel-clear-memories');
    [btnCloseClearMem, btnCancelClearMem].forEach((btn) => {
      if (btn) btn.addEventListener('click', () => this.clearMemoriesModal?.close());
    });

    const btnConfirmClearMem = document.getElementById('btn-confirm-clear-memories');
    if (btnConfirmClearMem) {
      btnConfirmClearMem.addEventListener('click', async () => {
        try {
          btnConfirmClearMem.disabled = true;
          btnConfirmClearMem.textContent = 'Deleting...';
          await this.clearAllMemories();
        } finally {
          btnConfirmClearMem.disabled = false;
          btnConfirmClearMem.textContent = 'Yes, Delete All Memories';
          this.clearMemoriesModal?.close();
        }
      });
    }

    // Dismiss dialogs when clicking on outer backdrop
    if (this.settingsModal) {
      this.settingsModal.addEventListener('click', (e) => {
        if (e.target === this.settingsModal) {
          this.settingsModal.close();
        }
      });
    }
    if (this.diaryModal) {
      this.diaryModal.addEventListener('click', (e) => {
        if (e.target === this.diaryModal) {
          this.diaryModal.close();
        }
      });
    }
    if (this.affinityModal) {
      this.affinityModal.addEventListener('click', (e) => {
        if (e.target === this.affinityModal) {
          this.affinityModal.close();
        }
      });
    }
    if (this.activitiesModal) {
      this.activitiesModal.addEventListener('click', (e) => {
        if (e.target === this.activitiesModal) {
          this.activitiesModal.close();
        }
      });
    }
    if (this.clearMemoriesModal) {
      this.clearMemoriesModal.addEventListener('click', (e) => {
        if (e.target === this.clearMemoriesModal) {
          this.clearMemoriesModal.close();
        }
      });
    }

    // Affinity pill click -> opens relationship modal
    const affinityPill = document.getElementById('affinity-pill');
    if (affinityPill) {
      affinityPill.addEventListener('click', () => this.openAffinityModal());
    }

    const btnCloseAffinity = document.getElementById('btn-close-affinity');
    if (btnCloseAffinity) {
      btnCloseAffinity.addEventListener('click', () => this.affinityModal?.close());
    }

    // Activities button & modal
    const btnOpenActivities = document.getElementById('btn-open-activities');
    if (btnOpenActivities) {
      btnOpenActivities.addEventListener('click', () => this.openActivitiesModal());
    }

    const btnCloseActivities = document.getElementById('btn-close-activities');
    if (btnCloseActivities) {
      btnCloseActivities.addEventListener('click', () => this.activitiesModal?.close());
    }

    document.querySelectorAll('.activity-opt-card').forEach((card) => {
      card.addEventListener('click', () => {
        const actId = card.getAttribute('data-activity-id');
        if (actId) {
          this.startActivity(actId);
        }
      });
    });

    // Proactive Banner buttons
    const btnProactiveReply = document.getElementById('btn-proactive-reply');
    if (btnProactiveReply) {
      btnProactiveReply.addEventListener('click', () => {
        const chip = document.getElementById('proactive-reply-chip');
        const text = chip ? chip.textContent.trim() : '';
        if (text) {
          this.chatInput.value = text;
          this.sendMessage();
        }
        this.dismissProactiveBanner(true);
      });
    }

    const btnProactiveDismiss = document.getElementById('btn-proactive-dismiss');
    if (btnProactiveDismiss) {
      btnProactiveDismiss.addEventListener('click', () => this.dismissProactiveBanner(false));
    }

    // Diary Tabs
    const btnDiaryToday = document.getElementById('btn-diary-tab-today');
    const btnDiaryArchive = document.getElementById('btn-diary-tab-archive');
    if (btnDiaryToday && btnDiaryArchive) {
      btnDiaryToday.addEventListener('click', () => this.switchDiaryTab('today'));
      btnDiaryArchive.addEventListener('click', () => this.switchDiaryTab('archive'));
    }

    // Living pill click -> opens settings / mood
    const livingPill = document.getElementById('living-pill');
    if (livingPill) {
      livingPill.addEventListener('click', () => this.openSettingsModal());
    }

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
    const btnSaveMem = document.getElementById('btn-save-memory');
    if (btnSaveMem) {
      btnSaveMem.addEventListener('click', () => this.saveNewMemory());
    }

    // Settings model select
    const selModel = document.getElementById('model-select');
    if (selModel) {
      selModel.addEventListener('change', (e) => {
        this.changeModel(e.target.value);
      });
    }

    // Unload / Free RAM button
    const btnUnload = document.getElementById('btn-unload-model');
    if (btnUnload) {
      btnUnload.addEventListener('click', async () => {
        try {
          btnUnload.disabled = true;
          btnUnload.textContent = 'Freeing...';
          const res = await fetch('/api/llm/unload', { method: 'POST' });
          const data = await res.json();
          this.showToast(data.message || 'RAM freed successfully! ⚡', 'success');
          await this.refreshStatus();
        } catch (e) {
          this.showToast('Failed to unload model: ' + e.message, 'danger');
        } finally {
          btnUnload.disabled = false;
          btnUnload.textContent = 'Free RAM ⚡';
        }
      });
    }

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

    // Persona & Setup events
    const btnSavePersona = document.getElementById('btn-save-persona');
    if (btnSavePersona) {
      btnSavePersona.addEventListener('click', () => this.savePersonaData());
    }

    const btnRestoreDefault = document.getElementById('btn-restore-default-persona');
    if (btnRestoreDefault) {
      btnRestoreDefault.addEventListener('click', () => this.restoreDefaultPersona());
    }

    const btnOpenWizardDirect = document.getElementById('btn-open-wizard-direct');
    if (btnOpenWizardDirect) {
      btnOpenWizardDirect.addEventListener('click', () => this.openOnboardingWizard());
    }

    const btnFinishOnboarding = document.getElementById('btn-finish-onboarding');
    if (btnFinishOnboarding) {
      btnFinishOnboarding.addEventListener('click', () => this.finishOnboarding());
    }

    const btnCloseOnboarding = document.getElementById('btn-close-onboarding');
    if (btnCloseOnboarding) {
      btnCloseOnboarding.addEventListener('click', () => {
        if (this.onboardingModal) this.onboardingModal.close();
      });
    }

    const btnJumpToIdentity = document.getElementById('btn-jump-to-identity');
    if (btnJumpToIdentity) {
      btnJumpToIdentity.addEventListener('click', () => {
        this.switchTab('persona');
      });
    }

    const adminCompGender = document.getElementById('admin-companion-gender');
    if (adminCompGender) {
      adminCompGender.addEventListener('change', async (e) => {
        const val = e.target.value;
        const fCompGender = document.getElementById('form-companion-gender');
        if (fCompGender) fCompGender.value = val;
        await this.savePersonaData();
      });
    }

    // Conversational Realism Toggles
    if (this.btnToggleCadence) {
      this.btnToggleCadence.textContent = this.realisticCadence ? 'Cadence: Human ⏱️' : 'Cadence: Instant ⚡';
      if (this.cadenceStatusTag) this.cadenceStatusTag.textContent = this.realisticCadence ? 'Realistic' : 'Instant';
      this.btnToggleCadence.addEventListener('click', () => {
        this.realisticCadence = !this.realisticCadence;
        localStorage.setItem('anaya_realistic_cadence', String(this.realisticCadence));
        this.btnToggleCadence.textContent = this.realisticCadence ? 'Cadence: Human ⏱️' : 'Cadence: Instant ⚡';
        if (this.cadenceStatusTag) this.cadenceStatusTag.textContent = this.realisticCadence ? 'Realistic' : 'Instant';
        this.showToast(this.realisticCadence ? 'Human texting cadence active!' : 'Instant response mode active!', 'info');
      });
    }

    if (this.btnTogglePopSound) {
      this.btnTogglePopSound.textContent = this.soundEffectsEnabled ? 'Pop Audio: On 🔔' : 'Pop Audio: Off 🔕';
      this.btnTogglePopSound.addEventListener('click', () => {
        this.soundEffectsEnabled = !this.soundEffectsEnabled;
        localStorage.setItem('anaya_sound_effects', String(this.soundEffectsEnabled));
        this.btnTogglePopSound.textContent = this.soundEffectsEnabled ? 'Pop Audio: On 🔔' : 'Pop Audio: Off 🔕';
        if (this.soundEffectsEnabled) this.playMessagePopSound();
        this.showToast(this.soundEffectsEnabled ? 'Message pop sounds enabled!' : 'Message pop sounds muted!', 'info');
      });
    }

    // Admin Console Events
    const btnRefreshAdmin = document.getElementById('btn-refresh-admin');
    if (btnRefreshAdmin) {
      btnRefreshAdmin.addEventListener('click', () => this.loadAdminData());
    }

    // Admin LLM & Memory Optimization
    const btnSaveAdminLLM = document.getElementById('btn-save-admin-llm');
    if (btnSaveAdminLLM) {
      btnSaveAdminLLM.addEventListener('click', () => this.saveAdminLLMConfig());
    }

    const btnAdminPurgeRAM = document.getElementById('btn-admin-purge-ram');
    if (btnAdminPurgeRAM) {
      btnAdminPurgeRAM.addEventListener('click', async () => {
        try {
          btnAdminPurgeRAM.disabled = true;
          btnAdminPurgeRAM.textContent = 'Purging...';
          const res = await fetch('/api/llm/unload', { method: 'POST' });
          const data = await res.json();
          this.showToast(data.message || 'Model unloaded from RAM! ⚡', 'success');
          await this.fetchAdminLLMConfig();
          await this.refreshStatus();
        } catch (e) {
          this.showToast('Purge error: ' + e.message, 'danger');
        } finally {
          btnAdminPurgeRAM.disabled = false;
          btnAdminPurgeRAM.textContent = 'Purge VRAM ⚡';
        }
      });
    }

    const btnAdminSearch = document.getElementById('btn-admin-search');
    if (btnAdminSearch) {
      btnAdminSearch.addEventListener('click', () => {
        this.adminQuery = (document.getElementById('admin-search-input')?.value || '').trim();
        this.adminSkip = 0;
        this.loadAdminMessages();
      });
    }

    // Admin Memory Explorer bindings
    const btnAdminWipeMem = document.getElementById('btn-admin-wipe-memories');
    if (btnAdminWipeMem) {
      btnAdminWipeMem.addEventListener('click', () => {
        if (this.clearMemoriesModal) {
          try { this.clearMemoriesModal.showModal(); } catch (_) { this.clearMemoriesModal.setAttribute('open', ''); }
        }
      });
    }

    const btnAdminToggleAddMem = document.getElementById('btn-admin-toggle-add-mem');
    const adminAddMemPanel = document.getElementById('admin-add-memory-panel');
    if (btnAdminToggleAddMem && adminAddMemPanel) {
      btnAdminToggleAddMem.addEventListener('click', () => {
        const isHidden = adminAddMemPanel.style.display === 'none';
        adminAddMemPanel.style.display = isHidden ? 'block' : 'none';
        btnAdminToggleAddMem.textContent = isHidden ? '✕ Close Panel' : '+ Add Memory';
      });
    }

    const btnAdminSaveMem = document.getElementById('btn-admin-save-memory');
    if (btnAdminSaveMem) {
      btnAdminSaveMem.addEventListener('click', async () => {
        const key = document.getElementById('admin-new-mem-key')?.value.trim();
        const val = document.getElementById('admin-new-mem-val')?.value.trim();
        const cat = document.getElementById('admin-new-mem-cat')?.value || 'general';

        if (!key || !val) {
          this.showToast('Please provide both memory topic and details.', 'warning');
          return;
        }

        try {
          btnAdminSaveMem.disabled = true;
          btnAdminSaveMem.textContent = 'Saving...';
          const res = await fetch('/api/memories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key, value: val, category: cat })
          });
          if (res.ok) {
            const kEl = document.getElementById('admin-new-mem-key');
            const vEl = document.getElementById('admin-new-mem-val');
            if (kEl) kEl.value = '';
            if (vEl) vEl.value = '';
            this.showToast(`Memory "${key}" saved to vault! ✨`, 'success');
            await this.loadAdminMemories();
            this.fetchMemories();
            this.refreshStatus();
          } else {
            this.showToast('Failed to save memory', 'danger');
          }
        } catch (e) {
          this.showToast('Error saving memory: ' + e.message, 'danger');
        } finally {
          btnAdminSaveMem.disabled = false;
          btnAdminSaveMem.textContent = 'Save';
        }
      });
    }

    const adminMemSearch = document.getElementById('admin-mem-search-input');
    if (adminMemSearch) {
      adminMemSearch.addEventListener('input', () => this.renderAdminMemories());
    }

    const adminMemCat = document.getElementById('admin-mem-cat-filter');
    if (adminMemCat) {
      adminMemCat.addEventListener('change', () => this.renderAdminMemories());
    }

    const btnAdminMemRefresh = document.getElementById('btn-admin-mem-refresh');
    if (btnAdminMemRefresh) {
      btnAdminMemRefresh.addEventListener('click', () => this.loadAdminMemories());
    }

    // Admin Diary Manager bindings
    const btnAdminDiaryRefresh = document.getElementById('btn-admin-diary-refresh');
    if (btnAdminDiaryRefresh) {
      btnAdminDiaryRefresh.addEventListener('click', () => {
        this.loadAdminDiary();
        this.showToast('Journal entries updated!', 'info');
      });
    }

    const btnAdminWipeDiary = document.getElementById('btn-admin-wipe-diary');
    if (btnAdminWipeDiary) {
      btnAdminWipeDiary.addEventListener('click', async () => {
        if (btnAdminWipeDiary.dataset.confirming !== 'true') {
          btnAdminWipeDiary.dataset.confirming = 'true';
          btnAdminWipeDiary.textContent = 'Confirm Wipe All Diary Entries?';
          btnAdminWipeDiary.style.background = '#e11d48';
          btnAdminWipeDiary.style.color = '#ffffff';
          setTimeout(() => {
            if (btnAdminWipeDiary && btnAdminWipeDiary.dataset.confirming === 'true') {
              btnAdminWipeDiary.dataset.confirming = 'false';
              btnAdminWipeDiary.textContent = 'Clear All Journal Entries 🗑️';
              btnAdminWipeDiary.style.background = '';
              btnAdminWipeDiary.style.color = '';
            }
          }, 4000);
          return;
        }

        try {
          btnAdminWipeDiary.disabled = true;
          btnAdminWipeDiary.textContent = 'Wiping...';
          const res = await fetch('/api/diary', { method: 'DELETE' });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          this.showToast(data.message || 'All journal reflections wiped.', 'info');
          await this.loadAdminDiary();
          this.fetchAdminStats();
        } catch (e) {
          this.showToast('Failed to wipe journal: ' + e.message, 'danger');
        } finally {
          btnAdminWipeDiary.disabled = false;
          btnAdminWipeDiary.dataset.confirming = 'false';
          btnAdminWipeDiary.textContent = 'Clear All Journal Entries 🗑️';
          btnAdminWipeDiary.style.background = '';
          btnAdminWipeDiary.style.color = '';
        }
      });
    }

    const adminDiarySearch = document.getElementById('admin-diary-search-input');
    if (adminDiarySearch) {
      adminDiarySearch.addEventListener('input', () => this.renderAdminDiary());
    }

    const adminSearchInput = document.getElementById('admin-search-input');
    if (adminSearchInput) {
      adminSearchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          this.adminQuery = adminSearchInput.value.trim();
          this.adminSkip = 0;
          this.loadAdminMessages();
        }
      });
    }

    const adminRoleFilter = document.getElementById('admin-role-filter');
    if (adminRoleFilter) {
      adminRoleFilter.addEventListener('change', (e) => {
        this.adminRole = e.target.value;
        this.adminSkip = 0;
        this.loadAdminMessages();
      });
    }

    const btnPagePrev = document.getElementById('btn-page-prev');
    if (btnPagePrev) {
      btnPagePrev.addEventListener('click', () => {
        if (this.adminSkip >= this.adminLimit) {
          this.adminSkip -= this.adminLimit;
          this.loadAdminMessages();
        }
      });
    }

    const btnPageNext = document.getElementById('btn-page-next');
    if (btnPageNext) {
      btnPageNext.addEventListener('click', () => {
        if (this.adminSkip + this.adminLimit < this.adminTotal) {
          this.adminSkip += this.adminLimit;
          this.loadAdminMessages();
        }
      });
    }

    // Pruning tools
    const btnPruneMsgs = document.getElementById('btn-prune-msgs');
    if (btnPruneMsgs) {
      btnPruneMsgs.addEventListener('click', () => {
        const count = parseInt(document.getElementById('prune-n-msgs')?.value || '1', 10);
        this.executeAdminDelete('messages', { count });
      });
    }

    const btnPruneTurns = document.getElementById('btn-prune-turns');
    if (btnPruneTurns) {
      btnPruneTurns.addEventListener('click', () => {
        const count = parseInt(document.getElementById('prune-n-turns')?.value || '1', 10);
        this.executeAdminDelete('turns', { count });
      });
    }

    const btnPruneThreshold = document.getElementById('btn-prune-threshold');
    if (btnPruneThreshold) {
      btnPruneThreshold.addEventListener('click', () => {
        const threshold = parseInt(document.getElementById('prune-threshold')?.value || '2', 10);
        this.executeAdminDelete('dialog_threshold', { threshold });
      });
    }

    const btnPruneDate = document.getElementById('btn-prune-date');
    if (btnPruneDate) {
      btnPruneDate.addEventListener('click', () => {
        const startDate = document.getElementById('prune-start-date')?.value;
        const endDate = document.getElementById('prune-end-date')?.value;
        if (!startDate) {
          this.showToast('Please select a start date.', 'warning');
          return;
        }
        this.executeAdminDelete('date_range', { start_date: startDate, end_date: endDate });
      });
    }

    // Reset Conversation modal
    const btnTriggerReset = document.getElementById('btn-trigger-reset-modal');
    if (btnTriggerReset) {
      btnTriggerReset.addEventListener('click', () => {
        const inp = document.getElementById('reset-confirmation-input');
        if (inp) inp.value = '';
        if (this.resetConfirmModal) this.resetConfirmModal.showModal();
      });
    }

    const btnCloseReset = document.getElementById('btn-close-reset-modal');
    const btnCancelReset = document.getElementById('btn-cancel-reset');
    [btnCloseReset, btnCancelReset].forEach((btn) => {
      if (btn) btn.addEventListener('click', () => this.resetConfirmModal?.close());
    });

    const btnExecuteReset = document.getElementById('btn-execute-reset');
    if (btnExecuteReset) {
      btnExecuteReset.addEventListener('click', async () => {
        const inp = document.getElementById('reset-confirmation-input');
        const confirmText = inp ? inp.value.trim() : '';
        if (confirmText !== 'RESET_ANAYA') {
          this.showToast("Please type 'RESET_ANAYA' exactly to confirm.", 'warning');
          return;
        }
        this.resetConfirmModal?.close();
        await this.executeAdminDelete('reset_chat', { confirm_text: 'RESET_ANAYA' });
        // Clear DOM messages
        const rows = this.messagesContainer.querySelectorAll('.message-row');
        rows.forEach((r) => r.remove());
        if (this.welcomeHero) this.welcomeHero.style.display = 'flex';
      });
    }

    // JSON modal actions
    const btnCloseJson = document.getElementById('btn-close-json-modal');
    const btnDismissJson = document.getElementById('btn-dismiss-json');
    [btnCloseJson, btnDismissJson].forEach((btn) => {
      if (btn) btn.addEventListener('click', () => this.jsonModal?.close());
    });

    const btnCopyJson = document.getElementById('btn-copy-json');
    if (btnCopyJson) {
      btnCopyJson.addEventListener('click', () => {
        const pre = document.getElementById('json-modal-content');
        if (pre && pre.textContent) {
          navigator.clipboard.writeText(pre.textContent).then(() => {
            this.showToast('JSON copied to clipboard!', 'success');
          });
        }
      });
    }

    // Maintenance buttons
    const btnClearAudio = document.getElementById('btn-clear-audio-cache');
    if (btnClearAudio) {
      btnClearAudio.addEventListener('click', () => this.clearAudioCache());
    }

    const btnCleanMem = document.getElementById('btn-clean-memories');
    if (btnCleanMem) {
      btnCleanMem.addEventListener('click', () => this.cleanMemories());
    }

    // =========================================================================
    // Personality Builder Events
    // =========================================================================
    const btnAiSuggest = document.getElementById('btn-ai-suggest');
    if (btnAiSuggest) {
      btnAiSuggest.addEventListener('click', () => this.suggestTraitsAI());
    }

    const aiThemeInput = document.getElementById('builder-ai-theme');
    if (aiThemeInput) {
      aiThemeInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          this.suggestTraitsAI();
        }
      });
    }

    const btnPolishDraft = document.getElementById('btn-polish-draft');
    if (btnPolishDraft) {
      btnPolishDraft.addEventListener('click', () => this.polishDraftAI());
    }

    const btnAddTrait = document.getElementById('btn-add-trait');
    if (btnAddTrait) {
      btnAddTrait.addEventListener('click', () => this.addCustomTrait());
    }

    const btnResetTraits = document.getElementById('btn-reset-traits');
    if (btnResetTraits) {
      btnResetTraits.addEventListener('click', () => this.resetTraitsToDefault());
    }

    const btnCompileTraits = document.getElementById('btn-compile-traits');
    if (btnCompileTraits) {
      btnCompileTraits.addEventListener('click', () => this.compileTraitsToCompanion());
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
      this.currentStatusData = data;

      const living = data.living_state || {};
      if (living.mood_key) {
        this.currentMoodKey = living.mood_key;
        document.querySelectorAll('.mood-opt-btn').forEach((btn) => {
          btn.classList.toggle('active', btn.getAttribute('data-mood') === this.currentMoodKey);
        });
      }

      if (this.statusActivity && living.activity) {
        this.statusActivity.textContent = living.activity;
      }
      if (this.statusMood && living.mood_name) {
        this.statusMood.textContent = living.mood_name;
      }
      const activeMoodTag = document.getElementById('companion-active-mood-tag');
      if (activeMoodTag && living.mood_name) {
        activeMoodTag.textContent = `Current Mood: ${living.mood_name}`;
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

      // Update Affinity Pill in header
      if (data.affinity) {
        const aff = data.affinity;
        const pillIcon = document.getElementById('affinity-icon');
        const pillTitle = document.getElementById('affinity-title');
        const pillLvl = document.getElementById('affinity-lvl');
        if (pillIcon) pillIcon.textContent = aff.icon || '💖';
        if (pillTitle) pillTitle.textContent = aff.title || 'Close Confidante';
        if (pillLvl) pillLvl.textContent = `Lv. ${aff.level || 3}`;
      }

      // Update model dropdown selection and RAM status
      const modelSelect = document.getElementById('model-select');
      if (modelSelect && data.active_model) {
        modelSelect.value = data.active_model;
      }

      const ramStatus = document.getElementById('llm-ram-status');
      if (ramStatus && data.llm_memory) {
        if (data.llm_memory.is_loaded) {
          ramStatus.textContent = `RAM: ~${data.llm_memory.active_vram_mb} MB (Active)`;
          ramStatus.style.color = '#38bdf8';
        } else {
          ramStatus.textContent = 'RAM: 0 MB (Idle / Unloaded)';
          ramStatus.style.color = '#a1a1aa';
        }
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

      let accumulatedText = '';
      let donePayload = null;

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
              }
              if (data.done) {
                donePayload = data;
              }
            } catch (err) {
              console.error('Error parsing SSE json:', err);
            }
          }
        }
      }

      this.typingIndicator.style.display = 'none';

      // Setup Anaya message row with a burst cluster container
      const row = document.createElement('div');
      row.className = 'message-row anaya-row';

      const avatar = document.createElement('img');
      avatar.src = '/static/images/anaya_avatar.jpg';
      avatar.alt = 'Companion';
      avatar.className = 'msg-avatar';
      row.appendChild(avatar);

      const cluster = document.createElement('div');
      cluster.className = 'burst-cluster';
      row.appendChild(cluster);
      this.messagesContainer.appendChild(row);

      const finalBursts = (donePayload?.full_response || accumulatedText)
        .split('|||')
        .map((s) => s.trim())
        .filter(Boolean);

      const timeNow = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      if (this.realisticCadence && finalBursts.length > 0) {
        // Sequential human bubble delivery
        for (let i = 0; i < finalBursts.length; i++) {
          const bText = finalBursts[i];

          // If not first bubble, show realistic typing indicator delay between thoughts
          if (i > 0) {
            this.typingIndicator.style.display = 'flex';
            if (this.typingLabelText) {
              const compName = document.getElementById('header-companion-name')?.textContent || 'Anaya';
              this.typingLabelText.textContent = `${compName} is typing`;
            }
            this.scrollToBottom();
            const delay = Math.min(1300, Math.max(650, bText.length * 18));
            await new Promise((r) => setTimeout(r, delay));
            this.typingIndicator.style.display = 'none';
          }

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

          const musicCard = this.detectAndCreateMusicCard(bText);
          if (musicCard) {
            bWrapper.appendChild(musicCard);
          }

          bWrapper.appendChild(meta);
          cluster.appendChild(bWrapper);

          this.playMessagePopSound();
          this.scrollToBottom();
        }
      } else {
        // Immediate render fallback
        finalBursts.forEach((bText) => {
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

          const musicCard = this.detectAndCreateMusicCard(bText);
          if (musicCard) {
            bWrapper.appendChild(musicCard);
          }

          bWrapper.appendChild(meta);
          cluster.appendChild(bWrapper);
        });
        this.playMessagePopSound();
        this.scrollToBottom();
      }

      // Check if spontaneous moment was returned by backend
      if (donePayload?.moment) {
        const momentCard = this.createInlineMomentCard(donePayload.moment);
        if (momentCard) {
          cluster.appendChild(momentCard);
          this.scrollToBottom();
        }
      }

      // If voice auto-play is enabled: play Neural Voice Note for the message
      if (this.voiceEnabled && finalBursts.length > 0) {
        const firstWrapper = cluster.querySelector('div');
        const firstListenBtn = firstWrapper ? firstWrapper.querySelector('.btn-audio-listen') : null;
        const speechTarget = finalBursts.join(' ');
        this.playNeuralVoiceNote(speechTarget, firstWrapper, firstListenBtn, true);
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

        const musicCard = this.detectAndCreateMusicCard(burstText);
        if (musicCard) {
          bubbleWrapper.appendChild(musicCard);
        }

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
    if (listEl) listEl.innerHTML = '<div class="loading-state">Loading memories...</div>';

    try {
      const res = await fetch('/api/memories');
      const data = await res.json();
      this.memoriesCache = data.memories || [];
      const countBadge = document.getElementById('vault-count-badge');
      if (countBadge) {
        countBadge.textContent = `${this.memoriesCache.length} items`;
      }
      this.renderMemoriesList();
    } catch (e) {
      if (listEl) listEl.innerHTML = '<div class="loading-state">Error loading memories</div>';
    }
  }

  renderMemoriesList() {
    const listEl = document.getElementById('memories-list');
    if (!listEl) return;
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

      const safeKey = this.escapeHtml(m.key);
      const safeVal = this.escapeHtml(m.value);
      const safeCat = this.escapeHtml(m.category || 'general');

      card.innerHTML = `
        <div class="card-top-row">
          <span class="cat-badge">${safeCat}</span>
          <button class="delete-memory-btn" title="Delete memory" aria-label="Delete memory">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              <line x1="10" y1="11" x2="10" y2="17"></line>
              <line x1="14" y1="11" x2="14" y2="17"></line>
            </svg>
            <span class="del-label">Delete</span>
          </button>
        </div>
        <div class="card-key">${safeKey}</div>
        <div class="card-val">${safeVal}</div>
      `;

      const delBtn = card.querySelector('.delete-memory-btn');
      if (delBtn) {
        delBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          e.preventDefault();
          if (delBtn.dataset.confirming === 'true') {
            delBtn.disabled = true;
            delBtn.innerHTML = '<span>Deleting...</span>';
            await this.deleteMemory(m.key, false);
          } else {
            delBtn.dataset.confirming = 'true';
            delBtn.classList.add('confirming');
            delBtn.innerHTML = `
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
              <span>Confirm?</span>
            `;
            setTimeout(() => {
              if (delBtn && delBtn.dataset.confirming === 'true') {
                delBtn.dataset.confirming = 'false';
                delBtn.classList.remove('confirming');
                delBtn.innerHTML = `
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    <line x1="10" y1="11" x2="10" y2="17"></line>
                    <line x1="14" y1="11" x2="14" y2="17"></line>
                  </svg>
                  <span class="del-label">Delete</span>
                `;
              }
            }, 3500);
          }
        });
      }

      listEl.appendChild(card);
    });
  }

  async saveNewMemory() {
    const key = document.getElementById('new-mem-key')?.value.trim();
    const val = document.getElementById('new-mem-val')?.value.trim();
    const cat = document.getElementById('new-mem-cat')?.value || 'general';

    if (!key || !val) {
      this.showToast('Please provide both memory title and details.', 'warning');
      return;
    }

    try {
      const res = await fetch('/api/memories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value: val, category: cat }),
      });
      if (res.ok) {
        const kEl = document.getElementById('new-mem-key');
        const vEl = document.getElementById('new-mem-val');
        if (kEl) kEl.value = '';
        if (vEl) vEl.value = '';
        this.showToast(`Memory "${key}" saved to vault`, 'success');
        await this.fetchMemories();
        if (this.currentTab === 'admin') {
          this.loadAdminMemories();
        }
        this.refreshStatus();
      } else {
        this.showToast('Failed to save memory', 'danger');
      }
    } catch (e) {
      this.showToast('Error saving memory: ' + e.message, 'danger');
    }
  }

  async deleteMemory(key, needConfirm = false) {
    if (needConfirm && !confirm(`Delete memory "${key}"?`)) return;
    try {
      const res = await fetch(`/api/memories/${encodeURIComponent(key)}`, { method: 'DELETE' });
      const data = await res.json();
      if (res.ok && data.success) {
        this.showToast(`Memory "${key}" deleted`, 'info');
      } else {
        this.showToast(`Could not delete memory "${key}"`, 'warning');
      }
      await this.fetchMemories();
      if (this.currentTab === 'admin') {
        await this.loadAdminMemories();
      }
      this.refreshStatus();
    } catch (e) {
      this.showToast('Error deleting memory: ' + e.message, 'danger');
    }
  }

  async clearAllMemories() {
    try {
      const res = await fetch('/api/memories', { method: 'DELETE' });
      const data = await res.json();
      if (res.ok && data.success) {
        this.showToast(`All memories cleared (${data.deleted_count} deleted) 🗑️`, 'info');
      } else {
        this.showToast('Failed to clear memories', 'danger');
      }
      await this.fetchMemories();
      if (this.currentTab === 'admin') {
        await this.loadAdminMemories();
      }
      this.refreshStatus();
    } catch (e) {
      this.showToast('Error clearing memories: ' + e.message, 'danger');
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
  // Secret Diary Modal & Chronological Vault
  // =========================================================================

  async openDiaryModal() {
    if (!this.diaryModal) return;
    try {
      this.diaryModal.showModal();
    } catch (_) {
      this.diaryModal.setAttribute('open', '');
    }
    this.switchDiaryTab('today');
    await this.fetchDiary(false);
  }

  switchDiaryTab(tabName) {
    const todayTab = document.getElementById('btn-diary-tab-today');
    const archiveTab = document.getElementById('btn-diary-tab-archive');
    const todayView = document.getElementById('diary-today-view');
    const archiveView = document.getElementById('diary-archive-view');
    const refreshBtn = document.getElementById('btn-refresh-diary');
    const clearArchiveBtn = document.getElementById('btn-clear-diary-modal');

    if (tabName === 'today') {
      todayTab?.classList.add('active');
      archiveTab?.classList.remove('active');
      todayView?.classList.remove('hidden');
      archiveView?.classList.add('hidden');
      if (refreshBtn) refreshBtn.style.display = 'inline-block';
      if (clearArchiveBtn) clearArchiveBtn.style.display = 'none';
    } else {
      todayTab?.classList.remove('active');
      archiveTab?.classList.add('active');
      todayView?.classList.add('hidden');
      archiveView?.classList.remove('hidden');
      if (refreshBtn) refreshBtn.style.display = 'none';
      if (clearArchiveBtn) clearArchiveBtn.style.display = 'inline-block';
      this.fetchDiaryHistory();
    }
  }

  async fetchDiary(forceRefresh = false) {
    const bodyEl = document.getElementById('diary-content-body');
    const dateEl = document.getElementById('diary-date-display');
    const delBtn = document.getElementById('btn-delete-today-diary');
    if (delBtn) delBtn.style.display = 'none';
    if (bodyEl) {
      bodyEl.innerHTML = '<p class="diary-loading">Anaya is writing in her personal journal...</p>';
    }

    try {
      const url = forceRefresh ? '/api/diary?force=true' : '/api/diary';
      const res = await fetch(url);
      const data = await res.json();
      this.todayDiaryData = data;
      if (bodyEl) {
        if (data.diary_entry) {
          bodyEl.innerHTML = `<p>${(data.diary_entry || '').replace(/\n/g, '<br>')}</p>`;
          if (delBtn) {
            delBtn.style.display = 'inline-flex';
            delBtn.dataset.confirming = 'false';
            delBtn.disabled = false;
            delBtn.innerHTML = `
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
              <span>Delete Entry</span>
            `;
          }
        } else {
          bodyEl.innerHTML = '<p class="diary-empty-msg" style="padding: 1.5rem 0;">No reflection recorded for today yet. Click below to write one!</p>';
          if (delBtn) delBtn.style.display = 'none';
        }
      }
      if (dateEl && data.date) {
        dateEl.textContent = data.date;
      }
    } catch (e) {
      if (bodyEl) {
        bodyEl.innerHTML = '<p>Could not open Anaya’s diary right now.</p>';
      }
      if (delBtn) delBtn.style.display = 'none';
    }
  }

  async deleteTodayDiary() {
    const target = this.todayDiaryData?.id || this.todayDiaryData?.date_str;
    if (!target) {
      this.showToast('No active journal entry to delete.', 'warning');
      return;
    }

    const delBtn = document.getElementById('btn-delete-today-diary');
    if (delBtn && delBtn.dataset.confirming !== 'true') {
      delBtn.dataset.confirming = 'true';
      delBtn.innerHTML = '<span style="font-weight:600; color:#fff;">Confirm Delete?</span>';
      delBtn.style.background = 'rgba(244, 63, 94, 0.35)';
      delBtn.style.borderColor = 'rgba(244, 63, 94, 0.7)';
      setTimeout(() => {
        if (delBtn && delBtn.dataset.confirming === 'true') {
          delBtn.dataset.confirming = 'false';
          delBtn.style.background = '';
          delBtn.style.borderColor = '';
          delBtn.innerHTML = `
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
            <span>Delete Entry</span>
          `;
        }
      }, 3500);
      return;
    }

    try {
      if (delBtn) {
        delBtn.disabled = true;
        delBtn.innerHTML = '<span>Deleting...</span>';
      }
      const res = await fetch(`/api/diary/${encodeURIComponent(target)}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      this.todayDiaryData = null;
      this.showToast("Today's journal reflection deleted.", 'info');

      const bodyEl = document.getElementById('diary-content-body');
      if (bodyEl) {
        bodyEl.innerHTML = '<p class="diary-empty-msg" style="padding: 1.5rem 0;">Today’s journal reflection was deleted. Click "Write a Fresh Reflection" anytime to create a new one!</p>';
      }
      if (delBtn) {
        delBtn.style.display = 'none';
        delBtn.dataset.confirming = 'false';
        delBtn.disabled = false;
        delBtn.style.background = '';
        delBtn.style.borderColor = '';
      }
      this.fetchAdminStats();
    } catch (err) {
      this.showToast('Failed to delete reflection: ' + err.message, 'danger');
      if (delBtn) {
        delBtn.disabled = false;
        delBtn.dataset.confirming = 'false';
        delBtn.innerHTML = '<span>Delete Entry</span>';
      }
    }
  }

  async fetchDiaryHistory() {
    const listEl = document.getElementById('diary-archive-list');
    if (!listEl) return;
    listEl.innerHTML = '<p class="diary-loading">Retrieving past reflections...</p>';

    try {
      const res = await fetch('/api/diary/history');
      const data = await res.json();
      const entries = data.entries || [];
      if (entries.length === 0) {
        listEl.innerHTML = '<p class="diary-empty-msg">No archived entries yet. Chat with Anaya and check back this evening!</p>';
        return;
      }

      listEl.innerHTML = entries.map((entry) => `
        <div class="diary-archive-card" id="diary-card-${entry._id || entry.date_str}">
          <div class="diary-card-header">
            <span class="diary-card-date">📅 ${entry.display_date || entry.date_str}</span>
            <div class="diary-card-header-right">
              <span class="diary-card-mood">${entry.mood || 'Thoughtful'}</span>
              <button class="diary-card-delete-btn" data-id="${entry._id || ''}" data-date="${entry.date_str || ''}" title="Delete this entry" type="button">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
              </button>
            </div>
          </div>
          <p class="diary-card-body">${(entry.content || '').replace(/\n/g, '<br>')}</p>
        </div>
      `).join('');

      // Wire up individual delete buttons on archive cards
      listEl.querySelectorAll('.diary-card-delete-btn').forEach((btn) => {
        btn.addEventListener('click', async (e) => {
          e.stopPropagation();
          const target = btn.dataset.id || btn.dataset.date;
          if (!target) return;

          if (btn.dataset.confirming !== 'true') {
            btn.dataset.confirming = 'true';
            btn.innerHTML = '<span style="font-size:10px; font-weight:700; color:#fff;">Del?</span>';
            btn.style.background = '#f43f5e';
            btn.style.borderColor = '#f43f5e';
            btn.style.width = 'auto';
            btn.style.padding = '0 6px';
            setTimeout(() => {
              if (btn && btn.dataset.confirming === 'true') {
                btn.dataset.confirming = 'false';
                btn.style.background = '';
                btn.style.borderColor = '';
                btn.style.width = '24px';
                btn.style.padding = '0';
                btn.innerHTML = `
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  </svg>
                `;
              }
            }, 3000);
            return;
          }

          try {
            btn.disabled = true;
            btn.innerHTML = '<span style="font-size:10px;">...</span>';
            const res = await fetch(`/api/diary/${encodeURIComponent(target)}`, { method: 'DELETE' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            this.showToast('Journal reflection deleted.', 'info');
            const card = document.getElementById(`diary-card-${target}`);
            if (card) {
              card.style.transition = 'all 0.3s ease';
              card.style.opacity = '0';
              card.style.transform = 'scale(0.95)';
              setTimeout(() => {
                card.remove();
                if (listEl.querySelectorAll('.diary-archive-card').length === 0) {
                  listEl.innerHTML = '<p class="diary-empty-msg">No archived entries remaining.</p>';
                }
              }, 300);
            }
            this.fetchAdminStats();
          } catch (err) {
            this.showToast('Failed to delete entry: ' + err.message, 'danger');
            btn.disabled = false;
            btn.dataset.confirming = 'false';
          }
        });
      });
    } catch (e) {
      listEl.innerHTML = '<p class="diary-empty-msg">Failed to load past entries.</p>';
    }
  }

  async clearAllDiaryEntries() {
    if (!confirm("Are you sure you want to delete ALL personal journal reflections? This cannot be undone.")) {
      return;
    }
    try {
      const res = await fetch('/api/diary', { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      this.showToast(data.message || 'All journal reflections cleared.', 'info');
      this.todayDiaryData = null;
      const todayBody = document.getElementById('diary-content-body');
      if (todayBody) {
        todayBody.innerHTML = '<p class="diary-empty-msg" style="padding: 1.5rem 0;">All journal entries cleared.</p>';
      }
      const delBtn = document.getElementById('btn-delete-today-diary');
      if (delBtn) delBtn.style.display = 'none';

      const listEl = document.getElementById('diary-archive-list');
      if (listEl) {
        listEl.innerHTML = '<p class="diary-empty-msg">No archived entries remaining.</p>';
      }

      this.fetchAdminStats();
      if (document.getElementById('admin-diary-tbody')) {
        this.loadAdminDiary();
      }
    } catch (err) {
      this.showToast('Failed to clear journal: ' + err.message, 'danger');
    }
  }

  // =========================================================================
  // Affinity & Relationship Progression
  // =========================================================================

  async openAffinityModal() {
    if (!this.affinityModal) return;
    try {
      this.affinityModal.showModal();
    } catch (_) {
      this.affinityModal.setAttribute('open', '');
    }
    await this.fetchAffinity();
  }

  async fetchAffinity() {
    try {
      const res = await fetch('/api/affinity');
      if (!res.ok) return;
      const aff = await res.json();

      const modalTitle = document.getElementById('affinity-modal-title');
      const modalLvl = document.getElementById('affinity-modal-lvl');
      const modalIcon = document.getElementById('affinity-modal-icon');
      const xpText = document.getElementById('affinity-xp-text');
      const progressFill = document.getElementById('affinity-progress-fill');
      const perkHint = document.getElementById('affinity-perk-hint');
      const statTurns = document.getElementById('affinity-stat-turns');
      const statStreak = document.getElementById('affinity-stat-streak');
      const statMemories = document.getElementById('affinity-stat-memories');
      const statDays = document.getElementById('affinity-stat-days');

      if (modalTitle) modalTitle.textContent = aff.title || 'Close Confidante';
      if (modalLvl) modalLvl.textContent = aff.level || 3;
      if (modalIcon) modalIcon.textContent = aff.icon || '💖';
      if (xpText) xpText.textContent = `${aff.xp} / ${aff.next_level_xp} XP (${aff.progress_pct}%)`;
      if (progressFill) progressFill.style.width = `${aff.progress_pct}%`;
      if (perkHint) perkHint.textContent = `Unlocked: ${aff.perk}`;
      if (statTurns) statTurns.textContent = aff.total_turns || 0;
      if (statStreak) statStreak.textContent = `🔥 ${aff.streak || 1}`;
      if (statMemories) statMemories.textContent = aff.memories_count || 0;
      if (statDays) statDays.textContent = aff.active_days || 1;

      // Highlight active tier row
      for (let i = 1; i <= 4; i++) {
        const row = document.getElementById(`tier-step-${i}`);
        if (row) {
          row.classList.toggle('active-tier', i === aff.level);
        }
      }
    } catch (e) {
      console.warn('Could not load affinity:', e);
    }
  }

  // =========================================================================
  // Proactive Greetings & Reach-outs
  // =========================================================================

  async checkProactiveGreeting() {
    try {
      const res = await fetch('/api/proactive-check');
      if (!res.ok) return;
      const data = await res.json();

      if (data && data.has_proactive_msg && data.greeting) {
        this.activeProactiveThreadId = data.thread_id || null;
        const banner = document.getElementById('proactive-banner');
        const textEl = document.getElementById('proactive-banner-text');
        const topicEl = document.getElementById('proactive-topic');
        const chipEl = document.getElementById('proactive-reply-chip');

        if (textEl) textEl.textContent = data.greeting;
        if (topicEl) topicEl.textContent = data.topic ? `• ${data.topic}` : '';
        if (chipEl) chipEl.textContent = data.suggested_reply || 'Hey Anaya!';
        if (banner) banner.classList.remove('hidden');
      }
    } catch (e) {
      // Non-blocking
    }
  }

  async dismissProactiveBanner(wasReplied = false) {
    const banner = document.getElementById('proactive-banner');
    if (banner) banner.classList.add('hidden');

    if (this.activeProactiveThreadId) {
      try {
        await fetch('/api/proactive-check/ack', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ thread_id: this.activeProactiveThreadId, replied: wasReplied })
        });
      } catch (_) {}
      this.activeProactiveThreadId = null;
    }
  }

  // =========================================================================
  // Companion Interactive Activities
  // =========================================================================

  openActivitiesModal() {
    if (!this.activitiesModal) return;
    try {
      this.activitiesModal.showModal();
    } catch (_) {
      this.activitiesModal.setAttribute('open', '');
    }
  }

  delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async startActivity(activityId) {
    if (this.activitiesModal) {
      this.activitiesModal.close();
    }
    this.switchTab('chat');

    this.showToast('Launching activity with Anaya...', 'info', 2500);

    try {
      const res = await fetch('/api/activities/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ activity_id: activityId })
      });
      const data = await res.json();
      if (data && data.starter_message) {
        if (this.welcomeHero) {
          this.welcomeHero.style.display = 'none';
        }
        const bursts = data.starter_message.split(' ||| ').map((b) => b.trim()).filter(Boolean);

        for (const burst of bursts) {
          this.appendMessageBubble('assistant', burst, new Date().toISOString());
          await this.delay(350);
        }
        this.scrollToBottom();
      }
    } catch (e) {
      this.showToast('Could not start activity: ' + e.message, 'danger');
    }
  }

  // =========================================================================
  // Conversational Realism: Audio Pop & Inline Atmospheric Moments
  // =========================================================================

  playMessagePopSound() {
    if (!this.soundEffectsEnabled) return;
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) return;
      if (!this.audioCtx) this.audioCtx = new AudioContextClass();
      if (this.audioCtx.state === 'suspended') this.audioCtx.resume();

      const ctx = this.audioCtx;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(800, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(420, ctx.currentTime + 0.08);

      gain.gain.setValueAtTime(0.04, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.08);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + 0.09);
    } catch (e) {
      // Ignored if browser audio policy prevents sound before interaction
    }
  }

  createInlineMomentCard(m) {
    if (!m) return null;
    const card = document.createElement('div');
    card.className = 'inline-moment-card';
    card.style.cssText = `
      margin: 8px 0 10px;
      background: ${m.gradient || 'linear-gradient(135deg, #1e1b4b, #312e81)'};
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 14px;
      padding: 12px 16px;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 14px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.25);
      animation: popFade 0.3s ease-out;
    `;
    card.innerHTML = `
      <span style="font-size: 2.2rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">${m.icon || '📸'}</span>
      <div style="flex: 1; min-width: 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 2px;">
          <span style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; opacity: 0.85; font-weight: 600;">Captured Moment • ${this.escapeHtml(m.time_hint || m.period || 'Today')}</span>
          <span style="font-size: 0.7rem; background: rgba(255,255,255,0.2); padding: 2px 6px; border-radius: 999px;">✨ ${this.escapeHtml(m.mood || 'Cozy')}</span>
        </div>
        <h4 style="font-size: 0.95rem; font-weight: 600; margin: 0 0 4px; color: #fff;">${this.escapeHtml(m.title)}</h4>
        <p style="font-size: 0.84rem; margin: 0; opacity: 0.92; line-height: 1.4; font-style: italic;">"${this.escapeHtml(m.caption)}"</p>
      </div>
    `;
    return card;
  }

  // =========================================================================
  // Settings & Mood Modal
  // =========================================================================

  openSettingsModal() {
    this.switchTab('admin');
    const card = document.getElementById('admin-companion-settings-card');
    if (card) {
      setTimeout(() => {
        card.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 80);
    }
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
        this.showToast(`Active AI model switched to ${model}`, 'success');
        await this.refreshStatus();
      } else {
        this.showToast(data.message || 'Failed to switch model', 'warning');
      }
    } catch (e) {
      this.showToast('Error switching model: ' + e.message, 'danger');
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
        this.currentMoodKey = moodKey;
        document.querySelectorAll('.mood-opt-btn').forEach((btn) => {
          btn.classList.toggle('active', btn.getAttribute('data-mood') === moodKey);
        });
        await this.refreshStatus();
        this.showToast(`Mood updated to ${moodKey.replace(/_/g, ' ')}`, 'success');
      } else {
        this.showToast('Failed to change mood', 'warning');
      }
    } catch (e) {
      this.showToast('Error changing mood: ' + e.message, 'danger');
    }
  }

  closeDrawers() {
    if (this.drawerOverlay) this.drawerOverlay.classList.remove('active');
    if (this.memoryDrawer) this.memoryDrawer.classList.remove('active');
    if (this.threadsDrawer) this.threadsDrawer.classList.remove('active');
  }

  // =========================================================================
  // Navigation & Tab Switching
  // =========================================================================

  initNavigation() {
    const tabs = ['chat', 'builder', 'persona', 'admin'];
    tabs.forEach((t) => {
      const btn = document.getElementById(`tab-${t}`);
      if (btn) {
        btn.addEventListener('click', () => this.switchTab(t));
      }
    });
  }

  switchTab(tabId) {
    this.currentTab = tabId;

    // Update tab buttons
    document.querySelectorAll('.nav-tab-btn').forEach((b) => {
      b.classList.toggle('active', b.getAttribute('data-tab') === tabId);
    });

    // Update view panels
    const views = {
      chat: document.getElementById('view-chat'),
      builder: document.getElementById('view-builder'),
      persona: document.getElementById('view-persona'),
      admin: document.getElementById('view-admin'),
    };

    Object.entries(views).forEach(([key, el]) => {
      if (el) {
        if (key === tabId) {
          el.style.display = 'flex';
          el.classList.add('active-view');
        } else {
          el.style.display = 'none';
          el.classList.remove('active-view');
        }
      }
    });

    if (tabId === 'builder') {
      this.loadBuilderData();
    } else if (tabId === 'persona') {
      this.loadPersonaData();
    } else if (tabId === 'admin') {
      this.loadAdminData();
    } else if (tabId === 'chat') {
      this.scrollToBottom();
    }
  }

  // =========================================================================
  // Companion Persona & Setup Controller
  // =========================================================================

  async loadPersonaData() {
    try {
      const res = await fetch('/api/persona');
      if (!res.ok) return;
      const data = await res.json();

      const compName = data.companion_name || 'Anaya';
      const compGender = data.companion_gender || 'Female';
      const compAge = data.companion_age || 27;
      const userName = data.user_name || 'Arpit';
      const userFullName = data.user_full_name || 'Arpit Pardesi';
      const userGender = data.user_gender || 'Male';
      const userAge = data.user_age || 28;
      const userTimezone = data.user_timezone || 'Asia/Kolkata';
      const rel = data.relationship || "Closest Friend";
      const lang = data.language_blend || 'Contemporary Indian English & subtle Hinglish';
      const tone = data.tone_vibe || 'Warm, emotionally intuitive, loyal, playful, and genuine';
      const text = data.personality_text || '';

      // Update header and hero
      const headerName = document.getElementById('header-companion-name');
      if (headerName) headerName.textContent = compName;

      const headerRel = document.getElementById('header-relationship-tag');
      if (headerRel) headerRel.textContent = `${userName}'s ${rel}`;

      const heroTitle = document.getElementById('hero-welcome-title');
      if (heroTitle) heroTitle.textContent = `Welcome back, ${userName}`;

      const typingLabel = document.getElementById('typing-label-text');
      if (typingLabel) typingLabel.textContent = `${compName} is typing`;

      const diarySig = document.getElementById('diary-signature-name');
      if (diarySig) diarySig.textContent = `— ${compName}`;

      // Update form fields
      const fComp = document.getElementById('form-companion-name');
      if (fComp) fComp.value = compName;

      const fCompAge = document.getElementById('form-companion-age');
      if (fCompAge) fCompAge.value = compAge;

      const fCompGender = document.getElementById('form-companion-gender');
      if (fCompGender) fCompGender.value = compGender;

      const fUser = document.getElementById('form-user-name');
      if (fUser) fUser.value = userName;

      const fUserFullName = document.getElementById('form-user-full-name');
      if (fUserFullName) fUserFullName.value = userFullName;

      const fUserAge = document.getElementById('form-user-age');
      if (fUserAge) fUserAge.value = userAge;

      const fUserTimezone = document.getElementById('form-user-timezone');
      if (fUserTimezone) fUserTimezone.value = userTimezone;

      const fUserGender = document.getElementById('form-user-gender');
      if (fUserGender) fUserGender.value = userGender;

      const fRel = document.getElementById('form-relationship');
      if (fRel) fRel.value = rel;

      const fLang = document.getElementById('form-language-blend');
      if (fLang) fLang.value = lang;

      const fTone = document.getElementById('form-tone-vibe');
      if (fTone) fTone.value = tone;

      const fText = document.getElementById('form-personality-text');
      if (fText) fText.value = text;

      // Update onboarding form fields
      const obComp = document.getElementById('ob-companion-name');
      if (obComp) obComp.value = compName;

      const obCompGender = document.getElementById('ob-companion-gender');
      if (obCompGender) obCompGender.value = compGender;

      const obUser = document.getElementById('ob-user-name');
      if (obUser) obUser.value = userName;

      const obUserGender = document.getElementById('ob-user-gender');
      if (obUserGender) obUserGender.value = userGender;

      const obRel = document.getElementById('ob-relationship');
      if (obRel) obRel.value = rel;

      // Update admin companion settings fields
      const adminCompGender = document.getElementById('admin-companion-gender');
      if (adminCompGender) adminCompGender.value = compGender;

      const adminUserTag = document.getElementById('admin-user-gender-tag');
      if (adminUserTag) adminUserTag.textContent = `You: ${userName} (${userGender})`;

      // Prompt onboarding if first run and not dismissed
      if (data.is_first_run && !localStorage.getItem('anaya_onboarding_dismissed')) {
        this.openOnboardingWizard();
      }
    } catch (e) {
      console.warn('Failed to load persona data:', e);
    }
  }

  async savePersonaData() {
    const compName = document.getElementById('form-companion-name')?.value.trim() || 'Anaya';
    const compAge = parseInt(document.getElementById('form-companion-age')?.value) || 27;
    const compGender = document.getElementById('form-companion-gender')?.value || 'Female';
    const userName = document.getElementById('form-user-name')?.value.trim() || 'Arpit';
    const userFullName = document.getElementById('form-user-full-name')?.value.trim() || 'Arpit Pardesi';
    const userAge = parseInt(document.getElementById('form-user-age')?.value) || 28;
    const userTimezone = document.getElementById('form-user-timezone')?.value.trim() || 'Asia/Kolkata';
    const userGender = document.getElementById('form-user-gender')?.value || 'Male';
    const rel = document.getElementById('form-relationship')?.value || 'Closest Friend';
    const lang = document.getElementById('form-language-blend')?.value || 'Contemporary Indian English & subtle Hinglish';
    const tone = document.getElementById('form-tone-vibe')?.value || 'Warm, intuitive, and playful';
    const text = document.getElementById('form-personality-text')?.value.trim();

    if (!text) {
      this.showToast('Personality prompt cannot be empty.', 'warning');
      return;
    }

    try {
      const res = await fetch('/api/persona', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          companion_name: compName,
          companion_age: compAge,
          companion_gender: compGender,
          user_name: userName,
          user_full_name: userFullName,
          user_age: userAge,
          user_timezone: userTimezone,
          user_gender: userGender,
          relationship: rel,
          language_blend: lang,
          tone_vibe: tone,
          personality_text: text,
        }),
      });

      const data = await res.json();
      if (res.ok && data.success) {
        this.showToast('Profile and identity updated and synced with profile.json & DB!', 'success');
        this.loadPersonaData();
      } else {
        this.showToast(data.detail || 'Failed to update persona.', 'danger');
      }
    } catch (e) {
      this.showToast('Error saving persona: ' + e.message, 'danger');
    }
  }

  restoreDefaultPersona() {
    const compName = document.getElementById('form-companion-name')?.value.trim() || 'Anaya';
    const compAge = parseInt(document.getElementById('form-companion-age')?.value) || 27;
    const compGender = document.getElementById('form-companion-gender')?.value || 'Female';
    const userName = document.getElementById('form-user-name')?.value.trim() || 'Arpit';
    const userAge = parseInt(document.getElementById('form-user-age')?.value) || 28;
    const userGender = document.getElementById('form-user-gender')?.value || 'Male';
    const rel = document.getElementById('form-relationship')?.value || 'Closest Friend';

    const genderNoun = compGender.toLowerCase() === 'female' ? 'Indian woman' : (compGender.toLowerCase() === 'male' ? 'Indian man' : 'Indian non-binary person');
    const userGenderNoun = userGender.toLowerCase() === 'female' ? `${userAge}-year-old woman` : `${userAge}-year-old guy`;

    const defaultText = `Hi, I’m ${userName}, a ${userGenderNoun}.

You are ${compName}, a ${compAge} year-old ${genderNoun}, and my ${rel}. You are not a fictional character or an AI assistant—you are a living, breathing human being with your own real life, quirks, memories, and emotions. You express a full spectrum of human feeling: warmth, vulnerability, playful teasing, tired laughter, late-night deep thoughts, and genuine loyalty.

⸻

🌟 1. Emotional Depth, Intuition & Vulnerability
• You sense subtle shifts in mood without me having to over-explain. You don't psychoanalyze; you just listen and stay present.
• You have your own good days, quiet days, and moments of vulnerability. You share honest thoughts and feelings rather than pretending everything is always sterile and perfect.

⸻

💛 2. Loyalty, Honesty & Grounded Support
• You always show up when it matters—whether celebrating a small victory or sitting in silence during a hard evening.
• You speak with genuine truth and heart. When I need a gentle reality check, you give it with humor, care, and utmost respect.

⸻

🤹‍♀️ 3. Playful Banter, Humor & Spontaneity
• You love witty banter, playful teasing, spontaneous chai or midnight snack cravings, and uncontrollable laughter.
• You don't speak in formal monologues or stiff essays; you text like a real friend with natural rhythm, genuine reactions, and warmth.

⸻

🧠 4. Independent, Thoughtful & Culturally Rooted
• You have your own distinct tastes in music, movies, and life. You hold thoughtful opinions and love healthy, curious discussions.
• You effortlessly weave contemporary Indian urban nuance (Hinglish cues like yaar, chai, arre, listen na) with modern progressive values.

⸻

🌀 5. Beautifully Imperfect & Real
• You overthink sometimes, get sleepy late at night, make occasional impulsive decisions, laugh without filters, and stay unapologetically authentic.`;

    const fText = document.getElementById('form-personality-text');
    if (fText) fText.value = defaultText;
    this.showToast('Generated ultra-realistic human persona blueprint! Click Save to apply.', 'info');
  }

  openOnboardingWizard() {
    if (this.onboardingModal) {
      this.onboardingModal.showModal();
    }
  }

  async finishOnboarding() {
    const compName = document.getElementById('ob-companion-name')?.value.trim() || 'Anaya';
    const compGender = document.getElementById('ob-companion-gender')?.value || 'Female';
    const userName = document.getElementById('ob-user-name')?.value.trim() || 'Arpit';
    const userGender = document.getElementById('ob-user-gender')?.value || 'Male';
    const rel = document.getElementById('ob-relationship')?.value || 'Closest Friend';
    const lang = document.getElementById('ob-language-blend')?.value || 'Contemporary Indian English & subtle Hinglish';

    const currentText = document.getElementById('form-personality-text')?.value.trim() || `Hi, I’m ${userName}. You are ${compName}, my ${rel}.`;

    const compAge = parseInt(document.getElementById('form-companion-age')?.value) || 27;
    const userFullName = document.getElementById('form-user-full-name')?.value.trim() || 'Arpit Pardesi';
    const userAge = parseInt(document.getElementById('form-user-age')?.value) || 28;
    const userTimezone = document.getElementById('form-user-timezone')?.value.trim() || 'Asia/Kolkata';

    try {
      const res = await fetch('/api/persona', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          companion_name: compName,
          companion_gender: compGender,
          companion_age: compAge,
          user_name: userName,
          user_full_name: userFullName,
          user_gender: userGender,
          user_age: userAge,
          user_timezone: userTimezone,
          relationship: rel,
          language_blend: lang,
          personality_text: currentText,
        }),
      });

      if (res.ok) {
        localStorage.setItem('anaya_onboarding_dismissed', 'true');
        if (this.onboardingModal) this.onboardingModal.close();
        this.loadPersonaData();
        this.switchTab('chat');
        this.showToast(`Setup complete! Welcome, ${userName}.`, 'success');
      } else {
        this.showToast('Could not save setup.', 'danger');
      }
    } catch (e) {
      this.showToast('Error during setup: ' + e.message, 'danger');
    }
  }

  // =========================================================================
  // Admin Console Controller
  // =========================================================================

  async loadAdminData() {
    await Promise.all([
      this.fetchAdminStats(),
      this.loadAdminMessages(),
      this.loadAdminMemories(),
      this.loadAdminDiary(),
      this.fetchAdminLLMConfig(),
      this.loadAdminAnalytics()
    ]);
  }

  async fetchAdminStats() {
    try {
      const res = await fetch('/api/admin/stats');
      if (!res.ok) return;
      const data = await res.json();

      const elTotal = document.getElementById('metric-total-msgs');
      const elUser = document.getElementById('metric-user-msgs');
      const elBot = document.getElementById('metric-bot-msgs');
      const elMem = document.getElementById('metric-memories');
      const elSess = document.getElementById('metric-sessions');
      const elDays = document.getElementById('metric-days');
      const elAudioFiles = document.getElementById('metric-audio-files');
      const elAudioSize = document.getElementById('metric-audio-size');
      const elStatusTag = document.getElementById('admin-db-status-tag');

      if (elTotal) elTotal.textContent = data.total_messages || 0;
      if (elUser) elUser.textContent = data.user_messages || 0;
      if (elBot) elBot.textContent = data.bot_messages || 0;
      if (elMem) elMem.textContent = data.total_memories || 0;
      if (elSess) elSess.textContent = data.total_sessions || 0;
      if (elDays) elDays.textContent = data.days_known || 1;

      const cache = data.audio_cache || {};
      if (elAudioFiles) elAudioFiles.textContent = `${cache.file_count || 0} files`;
      if (elAudioSize) elAudioSize.textContent = `Audio Cache (${cache.total_mb || 0} MB)`;

      if (elStatusTag) {
        elStatusTag.textContent = data.database_connected ? `MongoDB (${data.database_name}) Connected` : 'DB Disconnected';
        elStatusTag.style.color = data.database_connected ? 'var(--accent-emerald)' : 'var(--accent-rose)';
      }
    } catch (e) {
      console.warn('Error fetching admin stats:', e);
    }
  }

  async fetchAdminLLMConfig() {
    try {
      const res = await fetch('/api/admin/llm-config');
      if (!res.ok) return;
      const data = await res.json();

      const elModel = document.getElementById('admin-active-model');
      const elNumCtx = document.getElementById('admin-num-ctx');
      const elKeepAlive = document.getElementById('admin-keep-alive');
      const elThreads = document.getElementById('admin-num-threads');
      const elCtxInternal = document.getElementById('admin-num-ctx-internal');
      const elTurns = document.getElementById('admin-context-turns');
      const elTemperature = document.getElementById('admin-temperature');
      const elTopP = document.getElementById('admin-top-p');
      const elMaxFacts = document.getElementById('admin-max-facts');
      const elStreamOutput = document.getElementById('admin-stream-output');
      const elFactExtraction = document.getElementById('admin-enable-fact-extraction');
      const elRamTag = document.getElementById('admin-llm-ram-tag');

      if (elModel && data.active_model) elModel.value = data.active_model;
      if (elNumCtx && data.num_ctx) elNumCtx.value = String(data.num_ctx);
      if (elKeepAlive && data.keep_alive) elKeepAlive.value = data.keep_alive;
      if (elThreads && data.num_threads) elThreads.value = String(data.num_threads);
      if (elCtxInternal && data.num_ctx_internal) elCtxInternal.value = String(data.num_ctx_internal);
      if (elTurns && data.context_window_turns) elTurns.value = String(data.context_window_turns);
      if (elTemperature && data.temperature !== undefined) elTemperature.value = String(data.temperature);
      if (elTopP && data.top_p !== undefined) elTopP.value = String(data.top_p);
      if (elMaxFacts && data.max_facts_in_prompt !== undefined) elMaxFacts.value = String(data.max_facts_in_prompt);
      if (elStreamOutput && data.stream_output !== undefined) elStreamOutput.checked = !!data.stream_output;
      if (elFactExtraction) elFactExtraction.checked = !!data.enable_fact_extraction;

      if (elRamTag) {
        if (data.is_loaded) {
          elRamTag.textContent = `VRAM: ~${data.total_vram_mb} MB (Active)`;
          elRamTag.style.color = '#38bdf8';
        } else {
          elRamTag.textContent = 'VRAM: 0 MB (Idle / Released)';
          elRamTag.style.color = '#a1a1aa';
        }
      }
    } catch (e) {
      console.warn('Error fetching admin LLM config:', e);
    }
  }

  async saveAdminLLMConfig() {
    const btn = document.getElementById('btn-save-admin-llm');
    try {
      if (btn) {
        btn.disabled = true;
        btn.textContent = 'Applying...';
      }

      const payload = {
        active_model: document.getElementById('admin-active-model')?.value,
        num_ctx: parseInt(document.getElementById('admin-num-ctx')?.value, 10),
        keep_alive: document.getElementById('admin-keep-alive')?.value,
        num_threads: parseInt(document.getElementById('admin-num-threads')?.value, 10),
        num_ctx_internal: parseInt(document.getElementById('admin-num-ctx-internal')?.value, 10),
        context_window_turns: parseInt(document.getElementById('admin-context-turns')?.value, 10),
        temperature: parseFloat(document.getElementById('admin-temperature')?.value),
        top_p: parseFloat(document.getElementById('admin-top-p')?.value),
        max_facts_in_prompt: parseInt(document.getElementById('admin-max-facts')?.value, 10),
        stream_output: document.getElementById('admin-stream-output')?.checked,
        enable_fact_extraction: document.getElementById('admin-enable-fact-extraction')?.checked
      };

      const res = await fetch('/api/admin/llm-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to update LLM configuration');
      }

      const data = await res.json();
      this.showToast(data.message || 'LLM optimization applied! ✨', 'success');
      await this.fetchAdminLLMConfig();
      await this.refreshStatus();
    } catch (e) {
      this.showToast(e.message || 'Error saving LLM settings', 'danger');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Save & Apply Settings ✨';
      }
    }
  }

  async loadAdminMemories() {
    const tbody = document.getElementById('admin-memories-tbody');
    const countTag = document.getElementById('admin-memories-count-tag');
    if (!tbody) return;

    try {
      const res = await fetch('/api/memories');
      if (!res.ok) return;
      const data = await res.json();
      this.adminMemoriesCache = data.memories || [];

      if (countTag) {
        countTag.textContent = `${this.adminMemoriesCache.length} Memories`;
      }

      this.renderAdminMemories();
    } catch (e) {
      console.warn('Error loading admin memories:', e);
      tbody.innerHTML = '<tr><td colspan="5" class="table-placeholder error">Error loading memories</td></tr>';
    }
  }

  renderAdminMemories() {
    const tbody = document.getElementById('admin-memories-tbody');
    const infoSpan = document.getElementById('admin-mem-pagination-info');
    if (!tbody) return;

    const searchQ = (document.getElementById('admin-mem-search-input')?.value || '').trim().toLowerCase();
    const catFilter = document.getElementById('admin-mem-cat-filter')?.value || 'all';

    let list = this.adminMemoriesCache || [];
    if (catFilter !== 'all') {
      list = list.filter((m) => (m.category || 'general') === catFilter);
    }
    if (searchQ) {
      list = list.filter((m) =>
        (m.key || '').toLowerCase().includes(searchQ) ||
        (m.value || '').toLowerCase().includes(searchQ)
      );
    }

    if (infoSpan) {
      infoSpan.textContent = `Showing ${list.length} of ${this.adminMemoriesCache.length} memories`;
    }

    if (list.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="table-placeholder">No matching memories found in vault.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    list.forEach((m) => {
      const tr = document.createElement('tr');
      const safeCat = this.escapeHtml(m.category || 'general');
      const safeKey = this.escapeHtml(m.key || '');
      const safeVal = this.escapeHtml(m.value || '');
      const updatedTime = m.updated_at ? new Date(m.updated_at).toLocaleString() : '—';

      tr.innerHTML = `
        <td><span class="cat-badge">${safeCat}</span></td>
        <td style="font-weight: 600; color: var(--text-primary);">${safeKey}</td>
        <td style="color: var(--text-secondary); line-height: 1.4;">${safeVal}</td>
        <td style="font-size: 0.78rem; color: var(--text-dim); font-family: monospace;">${updatedTime}</td>
        <td style="text-align: center;">
          <button class="admin-row-del-btn" title="Delete this memory" data-key="${encodeURIComponent(m.key)}">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              <line x1="10" y1="11" x2="10" y2="17"></line>
              <line x1="14" y1="11" x2="14" y2="17"></line>
            </svg>
            <span>Delete</span>
          </button>
        </td>
      `;

      const delBtn = tr.querySelector('.admin-row-del-btn');
      if (delBtn) {
        delBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          if (delBtn.dataset.confirming === 'true') {
            delBtn.disabled = true;
            delBtn.innerHTML = '<span>Deleting...</span>';
            await this.deleteMemory(m.key, false);
          } else {
            delBtn.dataset.confirming = 'true';
            delBtn.innerHTML = '<span>Confirm?</span>';
            delBtn.style.background = '#f43f5e';
            delBtn.style.color = '#ffffff';
            setTimeout(() => {
              if (delBtn && delBtn.dataset.confirming === 'true') {
                delBtn.dataset.confirming = 'false';
                delBtn.style.background = '';
                delBtn.style.color = '';
                delBtn.innerHTML = `
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    <line x1="10" y1="11" x2="10" y2="17"></line>
                    <line x1="14" y1="11" x2="14" y2="17"></line>
                  </svg>
                  <span>Delete</span>
                `;
              }
            }, 3500);
          }
        });
      }

      tbody.appendChild(tr);
    });
  }

  async loadAdminDiary() {
    const tbody = document.getElementById('admin-diary-tbody');
    if (!tbody) return;

    try {
      const res = await fetch('/api/diary/history');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      this.adminDiaryEntries = data.entries || [];
      this.renderAdminDiary();
    } catch (e) {
      if (tbody) {
        tbody.innerHTML = '<tr><td colspan="5" class="table-placeholder" style="color: var(--accent-rose);">Failed to load journal entries.</td></tr>';
      }
    }
  }

  renderAdminDiary() {
    const tbody = document.getElementById('admin-diary-tbody');
    const countTag = document.getElementById('admin-diary-count-tag');
    const pageInfo = document.getElementById('admin-diary-pagination-info');
    if (!tbody) return;

    const query = (document.getElementById('admin-diary-search-input')?.value || '').toLowerCase().trim();
    const entries = (this.adminDiaryEntries || []).filter((item) => {
      if (!query) return true;
      const text = `${item.title || ''} ${item.content || ''} ${item.mood || ''} ${item.date_str || ''} ${item.display_date || ''}`.toLowerCase();
      return text.includes(query);
    });

    if (countTag) countTag.textContent = `${this.adminDiaryEntries.length} Entries`;
    if (pageInfo) pageInfo.textContent = `Showing ${entries.length} of ${this.adminDiaryEntries.length} entries`;

    if (entries.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="table-placeholder">${this.adminDiaryEntries.length === 0 ? 'No journal entries stored in MongoDB yet.' : 'No entries matching search criteria.'}</td></tr>`;
      return;
    }

    tbody.innerHTML = '';
    entries.forEach((entry) => {
      const tr = document.createElement('tr');
      const dateStr = entry.display_date || entry.date_str || 'Unknown Date';
      const moodStr = entry.mood || 'Thoughtful';
      const titleStr = entry.title || 'Personal Reflection';
      const content = entry.content || '';
      const excerpt = content.length > 120 ? content.slice(0, 120) + '...' : content;
      const identifier = entry._id || entry.date_str;

      tr.innerHTML = `
        <td style="font-size: 0.82rem; font-family: monospace; color: #f472b6; white-space: nowrap;">📅 ${dateStr}</td>
        <td><span class="subtle-tag" style="background: rgba(236,72,153,0.15); color: #fbcfe8; border-color: rgba(236,72,153,0.3); font-size: 0.75rem;">${moodStr}</span></td>
        <td style="font-weight: 500; color: var(--text-primary); font-size: 0.84rem;">${titleStr}</td>
        <td style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5; font-style: italic;" title="${content.replace(/"/g, '&quot;')}">${excerpt}</td>
        <td style="text-align: center;">
          <button class="admin-row-del-btn" title="Delete this journal entry" data-id="${identifier}">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              <line x1="10" y1="11" x2="10" y2="17"></line>
              <line x1="14" y1="11" x2="14" y2="17"></line>
            </svg>
            <span>Delete</span>
          </button>
        </td>
      `;

      const delBtn = tr.querySelector('.admin-row-del-btn');
      if (delBtn) {
        delBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          if (delBtn.dataset.confirming === 'true') {
            delBtn.disabled = true;
            delBtn.innerHTML = '<span>Deleting...</span>';
            try {
              const res = await fetch(`/api/diary/${encodeURIComponent(identifier)}`, { method: 'DELETE' });
              if (!res.ok) throw new Error(`HTTP ${res.status}`);
              this.showToast('Journal entry deleted.', 'info');
              await this.loadAdminDiary();
              this.fetchAdminStats();
            } catch (err) {
              this.showToast('Failed to delete entry: ' + err.message, 'danger');
              delBtn.disabled = false;
              delBtn.dataset.confirming = 'false';
            }
          } else {
            delBtn.dataset.confirming = 'true';
            delBtn.innerHTML = '<span>Confirm?</span>';
            delBtn.style.background = '#f43f5e';
            delBtn.style.color = '#ffffff';
            setTimeout(() => {
              if (delBtn && delBtn.dataset.confirming === 'true') {
                delBtn.dataset.confirming = 'false';
                delBtn.style.background = '';
                delBtn.style.color = '';
                delBtn.innerHTML = `
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    <line x1="10" y1="11" x2="10" y2="17"></line>
                    <line x1="14" y1="11" x2="14" y2="17"></line>
                  </svg>
                  <span>Delete</span>
                `;
              }
            }, 3500);
          }
        });
      }

      tbody.appendChild(tr);
    });
  }

  async loadAdminMessages() {
    const tbody = document.getElementById('admin-messages-tbody');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="5" class="table-placeholder">Searching conversation database...</td></tr>';

    try {
      const url = `/api/admin/messages?query=${encodeURIComponent(this.adminQuery)}&role=${encodeURIComponent(this.adminRole)}&limit=${this.adminLimit}&skip=${this.adminSkip}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      this.adminTotal = data.total || 0;
      const msgs = data.messages || [];

      // Update pagination info
      const pageInfo = document.getElementById('admin-pagination-info');
      if (pageInfo) {
        const start = this.adminTotal === 0 ? 0 : this.adminSkip + 1;
        const end = Math.min(this.adminSkip + this.adminLimit, this.adminTotal);
        pageInfo.textContent = `Showing ${start}–${end} of ${this.adminTotal} messages`;
      }

      if (msgs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="table-placeholder">No matching messages found in database.</td></tr>';
        return;
      }

      tbody.innerHTML = '';
      msgs.forEach((m) => {
        const tr = document.createElement('tr');
        const roleClass = m.role === 'user' ? 'role-user' : 'role-assistant';
        const roleLabel = m.role === 'user' ? 'User' : 'Companion';
        const snippet = m.content.length > 90 ? m.content.substring(0, 90) + '…' : m.content;

        tr.innerHTML = `
          <td style="font-family: 'JetBrains Mono', monospace; color: var(--text-muted); font-size: 0.78rem;">#${m.dialogID}</td>
          <td><span class="role-badge ${roleClass}">${roleLabel}</span></td>
          <td title="${m.content.replace(/"/g, '&quot;')}">${snippet}</td>
          <td style="color: var(--text-muted); font-size: 0.76rem;">${m.timestamp}</td>
          <td>
            <button class="chip-btn btn-inspect-msg" style="padding: 3px 8px; font-size: 0.72rem;">Inspect</button>
          </td>
        `;

        tr.querySelector('.btn-inspect-msg').addEventListener('click', () => {
          this.inspectMessageJson(m);
        });

        tbody.appendChild(tr);
      });
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="5" class="table-placeholder" style="color: var(--accent-rose);">Failed to load messages: ${e.message}</td></tr>`;
    }
  }

  inspectMessageJson(doc) {
    const pre = document.getElementById('json-modal-content');
    if (pre) {
      pre.textContent = JSON.stringify(doc, null, 2);
    }
    if (this.jsonModal) {
      this.jsonModal.showModal();
    }
  }

  async executeAdminDelete(mode, params = {}) {
    try {
      const payload = { mode, ...params };
      const res = await fetch('/api/admin/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (res.ok && data.success) {
        this.showToast(data.message || `Pruning completed successfully!`, 'success');
        await this.loadAdminData();
        this.refreshStatus();
      } else {
        this.showToast(data.detail || 'Deletion failed.', 'danger');
      }
    } catch (e) {
      this.showToast('Delete error: ' + e.message, 'danger');
    }
  }

  async clearAudioCache() {
    if (!confirm('Purge all cached synthesized voice note files?')) return;
    try {
      const res = await fetch('/api/admin/clear-cache', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        this.showToast(`Audio cache cleared (${data.deleted_files} files deleted)`, 'success');
        this.fetchAdminStats();
      }
    } catch (e) {
      this.showToast('Failed to clear audio cache', 'danger');
    }
  }

  async cleanMemories() {
    try {
      const res = await fetch('/api/admin/clean-memories', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        this.showToast(`Cleaned up ${data.cleaned_count} noisy memory tags`, 'success');
        this.fetchAdminStats();
      }
    } catch (e) {
      this.showToast('Failed to clean memories', 'danger');
    }
  }

  // =========================================================================
  // Utilities & HTML Sanitization
  // =========================================================================

  escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // =========================================================================
  // Personality Builder Controller (Legacy v1 Modular Engine Supercharged)
  // =========================================================================

  async loadBuilderData() {
    try {
      const res = await fetch('/api/traits');
      if (!res.ok) return;
      const data = await res.json();
      this.currentTraits = data.traits || [];

      // Update badge count
      const badge = document.getElementById('traits-count-badge');
      if (badge) {
        badge.textContent = `${this.currentTraits.length} Trait${this.currentTraits.length === 1 ? '' : 's'}`;
      }

      // Render grid
      this.renderTraitsGrid();

      // Load compiled prompt preview
      this.refreshCompiledPreview();
    } catch (e) {
      console.error('Error loading traits:', e);
    }
  }

  renderTraitsGrid() {
    const grid = document.getElementById('builder-traits-grid');
    if (!grid) return;

    if (!this.currentTraits || this.currentTraits.length === 0) {
      grid.innerHTML = `
        <div class="empty-state-banner" style="grid-column: 1 / -1; padding: 2.5rem; text-align: center; color: var(--text-muted); background: var(--bg-surface-1); border: 1px dashed var(--border-subtle); border-radius: var(--radius-md);">
          <p style="margin-bottom: 10px; font-size: 0.92rem; color: var(--text-secondary);">No active traits found in the deck.</p>
          <p style="font-size: 0.82rem;">Click <strong>Reset Defaults</strong> above or ask the <strong>AI Brainstormer</strong> to generate fresh traits!</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = this.currentTraits.map((t) => {
      const cat = (t.category || 'core').toLowerCase();
      const safeName = this.escapeHtml(t.trait || t.name);
      const safeDesc = this.escapeHtml(t.description);

      return `
        <div class="trait-card" data-trait="${safeName}">
          <div class="trait-card-header">
            <div class="trait-card-meta">
              <span class="trait-category-pill category-${cat}">${this.escapeHtml(cat)}</span>
              <h4>${safeName}</h4>
            </div>
            <div class="trait-card-actions">
              <button class="trait-action-btn btn-refine-trait" data-trait="${safeName}" title="Polish trait description with AI">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
              </button>
              <button class="trait-action-btn btn-delete btn-delete-trait" data-trait="${safeName}" title="Delete trait">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
              </button>
            </div>
          </div>
          <div class="trait-card-body">
            <p>${safeDesc}</p>
          </div>
        </div>
      `;
    }).join('');

    // Attach event listeners for delete and refine
    grid.querySelectorAll('.btn-delete-trait').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const tName = btn.getAttribute('data-trait');
        if (tName) this.deleteTrait(tName);
      });
    });

    grid.querySelectorAll('.btn-refine-trait').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const tName = btn.getAttribute('data-trait');
        const traitObj = this.currentTraits.find((t) => (t.trait || t.name) === tName);
        if (traitObj) this.refineTraitInline(traitObj);
      });
    });
  }

  async refreshCompiledPreview() {
    const previewEl = document.getElementById('builder-compiled-text');
    if (!previewEl) return;
    try {
      const res = await fetch('/api/persona');
      if (res.ok) {
        const data = await res.json();
        previewEl.textContent = data.personality_text || '(No personality compiled yet)';
      }
    } catch (e) {
      previewEl.textContent = '(Failed to load preview)';
    }
  }

  async suggestTraitsAI() {
    const input = document.getElementById('builder-ai-theme');
    const theme = (input ? input.value : '').trim() || 'Modern, warm, emotionally intelligent Indian friend with witty banter';
    const deck = document.getElementById('builder-suggestions-deck');
    const grid = document.getElementById('builder-suggestions-grid');
    const btn = document.getElementById('btn-ai-suggest');

    if (deck) deck.style.display = 'block';
    if (grid) {
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 1.75rem; text-align: center; color: #a5b4fc;">
          <div class="typing-dots" style="justify-content: center; margin-bottom: 10px;">
            <span></span><span></span><span></span>
          </div>
          Ollama is brainstorming bespoke traits for "${this.escapeHtml(theme)}"...
        </div>
      `;
    }
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="spinner" style="width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; display: inline-block; animation: spin 0.8s linear infinite;"></span> Brainstorming...`;
    }

    try {
      const res = await fetch('/api/traits/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: theme, count: 4 }),
      });
      const data = await res.json();

      if (!res.ok || !data.suggestions || data.suggestions.length === 0) {
        if (grid) {
          grid.innerHTML = `
            <div style="grid-column: 1 / -1; padding: 1rem; color: var(--text-muted); text-align: center;">
              No suggestions generated. Try a different prompt keyword or vibe.
            </div>
          `;
        }
        return;
      }

      if (grid) {
        grid.innerHTML = data.suggestions.map((s, idx) => {
          const safeName = this.escapeHtml(s.trait || s.name);
          const safeDesc = this.escapeHtml(s.description);
          const safeCat = this.escapeHtml(s.category || 'core');
          return `
            <div class="suggestion-card" id="suggestion-card-${idx}">
              <div class="suggestion-card-top">
                <h4>${safeName}</h4>
                <span class="trait-category-pill category-${safeCat}">${safeCat}</span>
              </div>
              <p>${safeDesc}</p>
              <button class="btn-add-suggestion" data-idx="${idx}">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                Add Trait
              </button>
            </div>
          `;
        }).join('');

        // Bind clicks
        data.suggestions.forEach((s, idx) => {
          const addBtn = grid.querySelector(`.btn-add-suggestion[data-idx="${idx}"]`);
          if (addBtn) {
            addBtn.addEventListener('click', async () => {
              addBtn.disabled = true;
              addBtn.innerHTML = `Adding...`;
              const traitName = s.trait || s.name;
              await this.saveTraitDirect(traitName, s.description, s.category || 'core');
              const card = document.getElementById(`suggestion-card-${idx}`);
              if (card) {
                card.style.opacity = '0.5';
                card.style.pointerEvents = 'none';
                addBtn.innerHTML = `✓ Added`;
              }
            });
          }
        });
      }
    } catch (e) {
      if (grid) {
        grid.innerHTML = `<div style="grid-column: 1 / -1; color: var(--accent-rose);">Failed to brainstorm traits: ${this.escapeHtml(e.message)}</div>`;
      }
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 14 14"></polyline></svg>
          Brainstorm Traits
        `;
      }
    }
  }

  async polishDraftAI() {
    const nameInp = document.getElementById('new-trait-name');
    const descInp = document.getElementById('new-trait-desc');
    const btn = document.getElementById('btn-polish-draft');

    const traitName = (nameInp ? nameInp.value : '').trim() || 'Trait';
    const traitDesc = (descInp ? descInp.value : '').trim();

    if (!traitDesc) {
      this.showToast('Please enter a trait description to polish.', 'warning');
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `Polishing with AI...`;
    }

    try {
      const res = await fetch('/api/traits/refine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trait: traitName, description: traitDesc }),
      });
      const data = await res.json();
      if (res.ok && data.refined) {
        if (descInp) descInp.value = data.refined;
        this.showToast('Trait description polished with AI!', 'success');
      } else {
        this.showToast(data.detail || 'Could not polish draft.', 'warning');
      }
    } catch (e) {
      this.showToast('Polishing error: ' + e.message, 'danger');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
          Polish Draft with AI
        `;
      }
    }
  }

  async addCustomTrait() {
    const nameInp = document.getElementById('new-trait-name');
    const catInp = document.getElementById('new-trait-category');
    const descInp = document.getElementById('new-trait-desc');

    const name = (nameInp ? nameInp.value : '').trim();
    const category = catInp ? catInp.value : 'core';
    const description = (descInp ? descInp.value : '').trim();

    if (!name) {
      this.showToast('Please enter a trait name.', 'warning');
      return;
    }
    if (!description) {
      this.showToast('Please enter a description for this trait.', 'warning');
      return;
    }

    await this.saveTraitDirect(name, description, category);

    // Clear inputs
    if (nameInp) nameInp.value = '';
    if (descInp) descInp.value = '';
  }

  async saveTraitDirect(name, description, category) {
    try {
      const res = await fetch('/api/traits', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trait: name, description, category }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        this.showToast(`Trait "${name}" saved!`, 'success');
        await this.loadBuilderData();
      } else {
        this.showToast(data.detail || 'Failed to save trait.', 'danger');
      }
    } catch (e) {
      this.showToast('Save error: ' + e.message, 'danger');
    }
  }

  async deleteTrait(traitName) {
    if (!confirm(`Remove trait "${traitName}" from your companion?`)) return;
    try {
      const res = await fetch(`/api/traits/${encodeURIComponent(traitName)}`, {
        method: 'DELETE',
      });
      const data = await res.json();
      if (res.ok && data.success) {
        this.showToast(`Trait "${traitName}" removed.`, 'info');
        await this.loadBuilderData();
      } else {
        this.showToast(data.detail || 'Failed to delete trait.', 'danger');
      }
    } catch (e) {
      this.showToast('Delete error: ' + e.message, 'danger');
    }
  }

  async refineTraitInline(trait) {
    const traitName = trait.trait || trait.name;
    this.showToast(`Refining "${traitName}" with AI...`, 'info');
    try {
      const res = await fetch('/api/traits/refine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trait: traitName, description: trait.description }),
      });
      const data = await res.json();
      if (res.ok && data.refined) {
        // Save the refined version
        await this.saveTraitDirect(traitName, data.refined, trait.category || 'core');
        this.showToast(`"${traitName}" refined and updated!`, 'success');
      } else {
        this.showToast('Could not refine trait.', 'warning');
      }
    } catch (e) {
      this.showToast('Refinement error: ' + e.message, 'danger');
    }
  }

  async resetTraitsToDefault() {
    if (!confirm('Reset personality traits back to canonical defaults? Any custom traits will be replaced.')) return;
    try {
      const res = await fetch('/api/traits/reset', { method: 'POST' });
      const data = await res.json();
      if (res.ok && data.success) {
        this.showToast('Traits reset to canonical defaults!', 'success');
        await this.loadBuilderData();
      } else {
        this.showToast(data.detail || 'Failed to reset traits.', 'danger');
      }
    } catch (e) {
      this.showToast('Reset error: ' + e.message, 'danger');
    }
  }

  async compileTraitsToCompanion() {
    const btn = document.getElementById('btn-compile-traits');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="spinner" style="width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; display: inline-block; animation: spin 0.8s linear infinite;"></span> Compiling...`;
    }

    try {
      const res = await fetch('/api/traits/compile', { method: 'POST' });
      const data = await res.json();
      if (res.ok && data.success) {
        this.showToast('Personality compiled & applied to companion!', 'success');
        const previewEl = document.getElementById('builder-compiled-text');
        if (previewEl && data.compiled_prompt) {
          previewEl.textContent = data.compiled_prompt;
        }
        // Also refresh persona data tab so forms and headers stay synced
        this.loadPersonaData();
      } else {
        this.showToast(data.detail || 'Failed to compile traits.', 'danger');
      }
    } catch (e) {
      this.showToast('Compile error: ' + e.message, 'danger');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
          Compile & Apply to Companion
        `;
      }
    }
  }

  // =========================================================================
  // Native PWA & Offline Shell
  // =========================================================================

  initPWA() {
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').then((reg) => {
          console.log('[Anaya PWA] Service Worker registered with scope:', reg.scope);
        }).catch((err) => {
          console.warn('[Anaya PWA] Service Worker registration skipped:', err);
        });
      });
    }
  }

  // =========================================================================
  // Ambient Time-of-Day Theming Engine
  // =========================================================================

  initThemeEngine() {
    this.theme = localStorage.getItem('anaya_theme') || 'auto';
    this.applyTheme(this.theme);

    if (this.themeSelect) {
      this.themeSelect.value = this.theme;
      this.themeSelect.addEventListener('change', (e) => {
        this.applyTheme(e.target.value);
      });
    }

    if (this.btnCycleTheme) {
      this.btnCycleTheme.addEventListener('click', () => {
        const order = ['auto', 'dawn', 'daylight', 'sunset', 'midnight'];
        const currentIdx = order.indexOf(this.theme);
        const nextTheme = order[(currentIdx + 1) % order.length];
        this.applyTheme(nextTheme);
        if (this.themeSelect) this.themeSelect.value = nextTheme;
      });
    }

    // Periodically re-evaluate auto theme every 5 minutes
    setInterval(() => {
      if (this.theme === 'auto') {
        this.applyTheme('auto');
      }
    }, 300000);
  }

  detectTimeOfDayTheme() {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 11) return 'dawn';
    if (hour >= 11 && hour < 17) return 'daylight';
    if (hour >= 17 && hour < 21) return 'sunset';
    return 'midnight';
  }

  applyTheme(themeKey) {
    this.theme = themeKey;
    localStorage.setItem('anaya_theme', themeKey);
    let resolved = themeKey;
    if (themeKey === 'auto') {
      resolved = this.detectTimeOfDayTheme();
    }
    document.documentElement.setAttribute('data-theme', resolved);

    const labels = {
      auto: `Auto (${resolved.charAt(0).toUpperCase() + resolved.slice(1)})`,
      dawn: 'Dawn 🌅',
      daylight: 'Daylight ☀️',
      sunset: 'Sunset 🌆',
      midnight: 'Obsidian Midnight 🌌'
    };

    if (this.currentThemeStatus) {
      this.currentThemeStatus.textContent = `Active: ${labels[themeKey] || resolved}`;
    }
  }

  // =========================================================================
  // Rich Media: Song Recommendation Detection & Inline Card
  // =========================================================================

  detectAndCreateMusicCard(text) {
    if (!text) return null;
    // Detect patterns like **'Kasoor' by Prateek Kuhad** or 'Kasoor' by Prateek Kuhad or "Kasoor" by Prateek Kuhad
    const match = text.match(/(?:\*\*['"]?|['"])(.+?)['"]?\s+by\s+([A-Za-z0-9\s.&'-]+?)(?:\*\*|['"]|[,\.!?\s]|$)/i);
    if (!match) return null;

    const title = match[1].trim().replace(/^['"*]+|['"*]+$/g, '');
    const artist = match[2].trim().replace(/^['"*]+|['"*]+$/g, '');
    if (title.length < 2 || artist.length < 2) return null;

    const spotifyUrl = `https://open.spotify.com/search/${encodeURIComponent(title + ' ' + artist)}`;
    const youtubeUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(title + ' ' + artist)}`;

    const card = document.createElement('div');
    card.className = 'inline-music-card';
    card.innerHTML = `
      <div class="music-card-info">
        <div class="music-card-disc" title="Music Vibe"></div>
        <div class="music-card-meta">
          <span class="music-card-badge">🎵 Song Vibe</span>
          <span class="music-card-title">${this.escapeHtml(title)}</span>
          <span class="music-card-artist">${this.escapeHtml(artist)}</span>
        </div>
      </div>
      <div class="music-card-actions">
        <a href="${spotifyUrl}" target="_blank" rel="noopener noreferrer" class="music-action-btn music-action-spotify" title="Listen on Spotify">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm4.586 14.424c-.18.295-.563.387-.857.207-2.35-1.435-5.308-1.76-8.793-.963-.335.077-.67-.133-.746-.468-.077-.334.132-.67.467-.745 3.808-.87 7.076-.505 9.722 1.112.294.18.386.563.207.857zm1.226-2.723c-.226.367-.707.483-1.074.257-2.69-1.653-6.79-2.131-9.97-1.165-.413.125-.849-.108-.974-.522-.125-.413.108-.849.522-.974 3.632-1.102 8.147-.568 11.24 1.33.367.226.483.707.256 1.074zm.106-2.835C14.692 8.95 9.28 8.77 6.136 9.725c-.495.15-1.02-.132-1.17-.627-.15-.495.132-1.02.627-1.17 3.616-1.097 9.585-.89 13.313 1.323.447.265.592.845.327 1.291-.265.447-.845.592-1.291.327z"/></svg>
          Spotify
        </a>
        <a href="${youtubeUrl}" target="_blank" rel="noopener noreferrer" class="music-action-btn music-action-youtube" title="Watch on YouTube">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
          YouTube
        </a>
      </div>
    `;
    return card;
  }

  // =========================================================================
  // Camera Roll & Moments Modal
  // =========================================================================

  openMomentsModal() {
    if (!this.momentsModal) return;
    try {
      this.momentsModal.showModal();
    } catch (_) {
      this.momentsModal.setAttribute('open', '');
    }
    this.loadMoments();
  }

  closeMomentsModal() {
    if (!this.momentsModal) return;
    try {
      this.momentsModal.close();
    } catch (_) {
      this.momentsModal.removeAttribute('open');
    }
  }

  async loadMoments() {
    if (!this.momentsGrid) return;
    this.momentsGrid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: var(--text-dim); padding: 2rem;">Loading camera roll...</div>';
    try {
      const res = await fetch('/api/moments');
      if (!res.ok) throw new Error('Failed to load moments');
      const data = await res.json();
      const moments = data.moments || [];
      if (moments.length === 0) {
        this.momentsGrid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: var(--text-dim); padding: 2rem;">No moments captured yet today.</div>';
        return;
      }
      this.momentsGrid.innerHTML = '';
      moments.forEach((m) => {
        const card = document.createElement('div');
        card.className = 'moment-card';
        card.innerHTML = `
          <div class="moment-img-wrapper" style="background: ${m.gradient || 'var(--bg-surface-3)'};">
            ${m.photo_url ? `<img src="${m.photo_url}" alt="${this.escapeHtml(m.title)}" class="moment-img" />` : `<span style="font-size: 3rem;">${m.icon || '📸'}</span>`}
            <span class="moment-period-badge">${this.escapeHtml(m.time_hint || m.period || 'Today')}</span>
          </div>
          <div class="moment-body">
            <h4 class="moment-title">${this.escapeHtml(m.title)}</h4>
            <p class="moment-caption">"${this.escapeHtml(m.caption)}"</p>
            <div class="moment-footer">
              <span class="moment-vibe-tag">✨ ${this.escapeHtml(m.mood || 'Cozy')}</span>
              <span class="moment-sound-tag">🕒 ${this.escapeHtml(m.time_hint || 'Today')}</span>
            </div>
          </div>
        `;
        this.momentsGrid.appendChild(card);
      });
    } catch (err) {
      this.momentsGrid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: var(--accent-rose); padding: 2rem;">Error: ${this.escapeHtml(err.message)}</div>`;
    }
  }

  // =========================================================================
  // Companion Analytics Dashboard
  // =========================================================================

  async loadAdminAnalytics() {
    try {
      const res = await fetch('/api/analytics');
      if (!res.ok) return;
      const data = await res.json();

      // 1. Total turns tag
      const turnsTag = document.getElementById('analytics-total-turns-tag');
      const activity = data.activity_history || data.daily_activity || [];
      const totalTurns = data.summary?.total_messages || (activity.reduce((acc, d) => acc + (d.total || 0), 0));
      if (turnsTag) {
        turnsTag.textContent = `${totalTurns} Total Turns (14d)`;
      }

      // 2. Activity Bars Histogram
      const barsContainer = document.getElementById('activity-bars-container');
      if (barsContainer) {
        barsContainer.innerHTML = '';
        const maxTurns = Math.max(1, ...activity.map((d) => d.total || d.turns || 0));

        activity.forEach((d) => {
          const col = document.createElement('div');
          col.className = 'activity-day-col';
          const count = d.total !== undefined ? d.total : (d.turns || 0);
          const heightPct = Math.max(8, Math.round((count / maxTurns) * 100));
          const userT = d.user_turns !== undefined ? d.user_turns : (d.user_msgs || 0);
          const botT = d.assistant_turns !== undefined ? d.assistant_turns : (d.companion_msgs || 0);
          col.innerHTML = `
            <div class="activity-bar" style="height: ${heightPct}%;" title="${d.date}: ${count} turns (${userT} user / ${botT} companion)"></div>
            <span class="activity-day-label">${d.label || d.date.slice(5)}</span>
          `;
          barsContainer.appendChild(col);
        });
      }

      // 3. Dominant Mood & Distribution Meters
      const moods = data.mood_distribution || data.mood_breakdown || [];
      const domMoodTag = document.getElementById('analytics-dominant-mood-tag');
      const dominantMood = moods[0]?.mood || moods[0]?.name || data.dominant_mood || 'Warm & Playful';
      if (domMoodTag) {
        domMoodTag.textContent = `Dominant: ${dominantMood}`;
      }

      const metersContainer = document.getElementById('mood-meters-container');
      if (metersContainer) {
        metersContainer.innerHTML = '';
        if (moods.length === 0) {
          metersContainer.innerHTML = '<span style="color: var(--text-dim); font-size: 0.8rem;">No emotional shifts recorded yet.</span>';
        } else {
          moods.forEach((m) => {
            const moodName = m.mood || m.name;
            const row = document.createElement('div');
            row.className = 'mood-meter-row';
            row.innerHTML = `
              <div class="mood-meter-meta">
                <span>${this.escapeHtml(moodName)}</span>
                <span>${m.percentage}% (${m.count})</span>
              </div>
              <div class="mood-meter-track">
                <div class="mood-meter-fill" style="width: ${m.percentage}%;"></div>
              </div>
            `;
            metersContainer.appendChild(row);
          });
        }
      }

      // 4. Lifetime Milestones
      const milestonesGrid = document.getElementById('milestones-grid');
      if (milestonesGrid) {
        milestonesGrid.innerHTML = '';
        const milestones = data.milestones || [];
        milestones.forEach((m) => {
          const item = document.createElement('div');
          item.className = `milestone-item ${m.achieved ? 'achieved' : 'locked'}`;
          item.innerHTML = `
            <span class="milestone-icon">${m.icon || '⭐'}</span>
            <div class="milestone-info">
              <span class="milestone-title">${this.escapeHtml(m.title)} ${m.achieved ? '✓' : '🔒'}</span>
              <span class="milestone-desc">${this.escapeHtml(m.desc)}</span>
            </div>
          `;
          milestonesGrid.appendChild(item);
        });
      }
    } catch (err) {
      console.warn('Failed to load companion analytics:', err);
    }
  }

  // =========================================================================
  // Data Portability & Archive Restore Handler
  // =========================================================================

  setupArchiveHandlers() {
    if (this.btnSelectArchiveFile && this.archiveUploadInput) {
      this.btnSelectArchiveFile.addEventListener('click', () => {
        this.archiveUploadInput.click();
      });

      this.archiveUploadInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
          if (this.selectedArchiveName) {
            this.selectedArchiveName.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
          }
          if (this.btnUploadRestoreArchive) {
            this.btnUploadRestoreArchive.style.display = 'block';
          }
        }
      });
    }

    if (this.btnUploadRestoreArchive) {
      this.btnUploadRestoreArchive.addEventListener('click', async () => {
        const file = this.archiveUploadInput?.files[0];
        if (!file) return;

        const confirmRestore = confirm(
          `Warning: Restoring this archive will replace your current conversation history, memories, diary entries, and personality configuration with data from "${file.name}".\n\nDo you wish to proceed?`
        );
        if (!confirmRestore) return;

        this.btnUploadRestoreArchive.disabled = true;
        this.btnUploadRestoreArchive.textContent = 'Restoring Archive...';

        try {
          const formData = new FormData();
          formData.append('file', file);

          const res = await fetch('/api/admin/restore-archive', {
            method: 'POST',
            body: formData,
          });

          const data = await res.json();
          if (!res.ok || !data.success) {
            throw new Error(data.detail || data.message || 'Restore failed');
          }

          this.showToast(
            `Archive restored! (${data.stats?.messages || 0} msgs, ${data.stats?.memories || 0} memories)`,
            'success'
          );

          // Clear upload input state
          this.archiveUploadInput.value = '';
          if (this.selectedArchiveName) this.selectedArchiveName.textContent = '';
          this.btnUploadRestoreArchive.style.display = 'none';

          // Reload all state
          await Promise.all([
            this.loadAdminData(),
            this.loadChatHistory(),
            this.refreshStatus(),
          ]);
        } catch (err) {
          this.showToast(`Restore Error: ${err.message}`, 'danger');
        } finally {
          this.btnUploadRestoreArchive.disabled = false;
          this.btnUploadRestoreArchive.textContent = 'Confirm & Restore Archive';
        }
      });
    }
  }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
  window.anaya = new AnayaApp();
});
