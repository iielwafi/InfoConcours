(() => {
  if (typeof document === "undefined") return;

  const root = document.getElementById("pomodoroApp");
  if (!root) return;

  const $ = (selector) => root.querySelector(selector);
  const form = $("#pomodoroSaveForm");
  const focusInput = $("#pomodoroFocusMinutes");
  const breakInput = $("#pomodoroBreakMinutes");
  const domainSelect = $("#pomodoroDomain");
  const minutesInput = $("#pomodoroSavedMinutes");
  const clock = $("#pomodoroClock");
  const ring = $("#pomodoroRing");
  const phaseLabel = $("#pomodoroPhase");
  const phaseChip = $("#pomodoroPhaseChip");
  const status = $("#pomodoroStatus");
  const startButton = $("#pomodoroStart");
  const resetButton = $("#pomodoroReset");
  const retryButton = $("#pomodoroRetrySave");
  const sessionsLabel = $("#pomodoroSessions");
  const taskInput = $("#pomodoroTask");

  if (!form || !focusInput || !breakInput || !domainSelect || !minutesInput || !clock || !ring || !status || !startButton || !resetButton) return;

  const messages = {
    fr: {
      focus: "CONCENTRATION",
      shortBreak: "PAUSE COURTE",
      longBreak: "PAUSE LONGUE",
      ready: "Prêt à te concentrer ?",
      focusRunning: "Concentration en cours. Garde une seule tâche en tête.",
      shortRunning: "Pause courte en cours. Éloigne-toi un instant de l’écran.",
      longRunning: "Pause longue en cours. Profite-en pour vraiment déconnecter.",
      paused: "Minuteur en pause. Tu peux reprendre quand tu es prête.",
      focusComplete: "Bravo ! Ton temps de concentration est enregistré. La pause démarre.",
      breakComplete: "Pause terminée. Tu peux repartir sur un nouveau cycle.",
      saving: "Enregistrement de ta séance de concentration…",
      saved: "Séance enregistrée dans ton suivi d’étude.",
      saveFailed: "La séance n’a pas pu être enregistrée. Vérifie ta connexion puis réessaie.",
      noDomain: "Choisis une matière avant de démarrer le focus.",
      invalidDuration: "Choisis une durée valide pour le focus et la pause.",
      focusStart: "Démarrer le focus",
      breakStart: "Démarrer la pause",
      pause: "Pause",
      resume: "Reprendre",
      reset: "Réinitialiser",
      longNext: "Quatrième cycle : une pause longue de 15 minutes t’attend."
    },
    ar: {
      focus: "التركيز",
      shortBreak: "استراحة قصيرة",
      longBreak: "استراحة طويلة",
      ready: "واجدة تبداي التركيز؟",
      focusRunning: "وقت التركيز. ركزي غير على مهمة وحدة.",
      shortRunning: "استراحة قصيرة. بعدي شوية على الشاشة.",
      longRunning: "استراحة طويلة. خدي وقتك ترتاحي.",
      paused: "المؤقت موقوف مؤقتاً. تقدري تكملي ملي تكوني واجدة.",
      focusComplete: "برافو! تسجّل وقت التركيز ديالك، ودابا بدات الاستراحة.",
      breakComplete: "سالات الاستراحة. تقدري تبداي دورة تركيز جديدة.",
      saving: "كنسجلو حصة التركيز…",
      saved: "تسجلات الحصة فالتتبع ديال القراية.",
      saveFailed: "ما قدرناش نسجلو الحصة. تأكدي من الاتصال وعاودي المحاولة.",
      noDomain: "اختاري المادة قبل ما تبداي التركيز.",
      invalidDuration: "اختاري مدة صحيحة للتركيز والاستراحة.",
      focusStart: "بداي التركيز",
      breakStart: "بداي الاستراحة",
      pause: "وقفي مؤقتاً",
      resume: "كمّلي",
      reset: "عاودي من الأول",
      longNext: "الدورة الرابعة: عندك استراحة طويلة ديال 15 دقيقة."
    }
  };

  const t = (key) => {
    const language = document.documentElement.lang === "ar" ? "ar" : "fr";
    return messages[language][key] || messages.fr[key] || key;
  };

  const clampMinutes = (value, min, max, fallback) => {
    const numeric = Number(value);
    return Number.isInteger(numeric) && numeric >= min && numeric <= max ? numeric : fallback;
  };

  const focusMinutes = () => clampMinutes(focusInput.value, 1, 180, 25);
  const breakMinutes = () => clampMinutes(breakInput.value, 1, 60, 5);
  const formatTime = (value) => {
    const total = Math.max(0, Math.floor(value));
    return String(Math.floor(total / 60)).padStart(2, "0") + ":" + String(total % 60).padStart(2, "0");
  };

  const localDateKey = () => {
    const now = new Date();
    return [now.getFullYear(), String(now.getMonth() + 1).padStart(2, "0"), String(now.getDate()).padStart(2, "0")].join("-");
  };
  const userId = document.body.dataset.userId || "student";
  const storageKey = "ic-pomodoro:" + userId + ":" + localDateKey();

  let completedSessions = 0;
  try {
    const stored = Number(localStorage.getItem(storageKey));
    completedSessions = Number.isInteger(stored) && stored >= 0 ? stored : 0;
  } catch (_) {
    completedSessions = 0;
  }

  let phase = "focus";
  let remainingSeconds = focusMinutes() * 60;
  let phaseDuration = remainingSeconds;
  let running = false;
  let deadline = 0;
  let intervalId = null;
  let lastFocusMinutes = 0;
  let lastFocusDomain = "";
  let activeFocusMinutes = focusMinutes();
  let activeFocusDomain = domainSelect.value;
  let focusSnapshotReady = false;
  let needsSave = false;
  let saving = false;

  function saveCount() {
    try { localStorage.setItem(storageKey, String(completedSessions)); } catch (_) {}
  }

  function phaseKey() {
    if (phase === "focus") return "focus";
    return phase === "longBreak" ? "longBreak" : "shortBreak";
  }

  function render() {
    clock.textContent = formatTime(remainingSeconds);
    phaseLabel.textContent = t(phaseKey());
    phaseChip.textContent = t(phaseKey());
    sessionsLabel.textContent = String(completedSessions);

    const progress = phaseDuration > 0 ? ((phaseDuration - remainingSeconds) / phaseDuration) * 360 : 0;
    ring.style.setProperty("--pomodoro-progress", Math.max(0, Math.min(360, progress)) + "deg");
    ring.setAttribute("aria-valuenow", String(Math.round(progress / 3.6)));

    startButton.textContent = running
      ? t("pause")
      : (phase === "focus" ? t("focusStart") : t("breakStart"));
    startButton.setAttribute("aria-pressed", running ? "true" : "false");

    if (retryButton) retryButton.hidden = !needsSave || saving;
    resetButton.disabled = running || saving;
  }

  function setStatus(key) {
    status.textContent = t(key);
  }

  function stopTicker() {
    if (intervalId !== null) window.clearInterval(intervalId);
    intervalId = null;
    running = false;
  }

  function updateRemainingFromDeadline() {
    remainingSeconds = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
  }

  function startTicker() {
    if (running || remainingSeconds <= 0) return;
    if (phase === "focus" && !domainSelect.value) {
      setStatus("noDomain");
      return;
    }
    if (phase === "focus" && !focusSnapshotReady) {
      activeFocusMinutes = focusMinutes();
      activeFocusDomain = domainSelect.value;
      phaseDuration = remainingSeconds;
      focusSnapshotReady = true;
    }
    running = true;
    deadline = Date.now() + remainingSeconds * 1000;
    intervalId = window.setInterval(tick, 250);
    setStatus(phase === "focus" ? "focusRunning" : (phase === "longBreak" ? "longRunning" : "shortRunning"));
    render();
  }

  function pauseTicker() {
    if (!running) return;
    updateRemainingFromDeadline();
    stopTicker();
    setStatus("paused");
    render();
  }

  async function saveFocusSession() {
    if (!needsSave || saving) return;
    saving = true;
    render();
    setStatus("saving");
    minutesInput.value = String(lastFocusMinutes);
    const previousDomain = domainSelect.value;
    domainSelect.value = lastFocusDomain;

    try {
      const response = await fetch(form.action || "/study", {
        method: "POST",
        body: new FormData(form),
        credentials: "same-origin",
        redirect: "follow"
      });
      const finalPath = response.url ? new URL(response.url).pathname : "";
      if (!response.ok || finalPath !== "/dashboard") throw new Error("study_session_save_failed");
      needsSave = false;
      setStatus("saved");
    } catch (_) {
      domainSelect.value = previousDomain;
      setStatus("saveFailed");
    } finally {
      saving = false;
      render();
    }
  }

  function finishFocus() {
    stopTicker();
    lastFocusMinutes = activeFocusMinutes;
    lastFocusDomain = activeFocusDomain;
    focusSnapshotReady = false;
    minutesInput.value = String(lastFocusMinutes);
    needsSave = true;
    completedSessions += 1;
    saveCount();

    const longBreak = completedSessions % 4 === 0;
    phase = longBreak ? "longBreak" : "shortBreak";
    remainingSeconds = (longBreak ? 15 : breakMinutes()) * 60;
    phaseDuration = remainingSeconds;
    setStatus(longBreak ? "longNext" : "focusComplete");
    render();

    void saveFocusSession();
    startTicker();
  }

  function finishBreak() {
    stopTicker();
    phase = "focus";
    remainingSeconds = focusMinutes() * 60;
    phaseDuration = remainingSeconds;
    focusSnapshotReady = false;
    setStatus("breakComplete");
    render();
  }

  function tick() {
    if (!running) return;
    updateRemainingFromDeadline();
    render();
    if (remainingSeconds > 0) return;
    remainingSeconds = 0;
    if (phase === "focus") finishFocus();
    else finishBreak();
  }

  startButton.addEventListener("click", () => {
    if (running) pauseTicker();
    else startTicker();
  });

  resetButton.addEventListener("click", () => {
    if (running || saving) return;
    stopTicker();
    phase = "focus";
    remainingSeconds = focusMinutes() * 60;
    phaseDuration = remainingSeconds;
    focusSnapshotReady = false;
    setStatus("ready");
    render();
  });

  if (retryButton) retryButton.addEventListener("click", () => { void saveFocusSession(); });

  document.querySelectorAll("[data-pomodoro-preset]").forEach((button) => {
    button.addEventListener("click", () => {
      if (running || saving) return;
      const values = String(button.dataset.pomodoroPreset || "").split(",").map(Number);
      const nextFocus = clampMinutes(values[0], 1, 180, 25);
      const nextBreak = clampMinutes(values[1], 1, 60, 5);
      focusInput.value = String(nextFocus);
      breakInput.value = String(nextBreak);
      phase = "focus";
      remainingSeconds = nextFocus * 60;
      phaseDuration = remainingSeconds;
      focusSnapshotReady = false;
      setStatus("ready");
      render();
    });
  });

  focusInput.addEventListener("change", () => {
    focusInput.value = String(focusMinutes());
    if (!running && phase === "focus") {
      remainingSeconds = focusMinutes() * 60;
      phaseDuration = remainingSeconds;
      focusSnapshotReady = false;
      setStatus("ready");
      render();
    }
  });

  breakInput.addEventListener("change", () => {
    breakInput.value = String(breakMinutes());
    if (!running && phase !== "focus") {
      remainingSeconds = breakMinutes() * 60;
      phaseDuration = remainingSeconds;
      render();
    }
  });

  if (taskInput) {
    taskInput.addEventListener("input", () => {
      const value = taskInput.value.trim();
      taskInput.setAttribute("aria-label", value || (document.documentElement.lang === "ar" ? "هدف جلسة التركيز" : "Objectif de la séance de focus"));
    });
  }

  setStatus("ready");
  render();
})();
