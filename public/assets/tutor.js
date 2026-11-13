(() => {
  const root = document.querySelector("[data-ai-tutor]");
  if (!root) return;

  const list = root.querySelector("[data-tutor-messages]");
  const form = root.querySelector("[data-tutor-form]");
  const input = root.querySelector("[data-tutor-input]");
  const send = root.querySelector("[data-tutor-send]");
  const status = root.querySelector("[data-tutor-status]");
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const lessonId = Number(root.dataset.lessonId || 0) || null;
  const exerciseId = Number(root.dataset.exerciseId || 0) || null;
  const questionId = Number(root.dataset.questionId || 0) || null;
  const history = [];

  function addMessage(role, text) {
    const item = document.createElement("article");
    item.className = "ai-message ai-message-" + role;
    const label = document.createElement("span");
    label.className = "ai-message-label";
    label.textContent = role === "assistant" ? "Professeur IA" : "Toi";
    const content = document.createElement("p");
    content.className = "ai-message-content";
    content.textContent = text;
    item.append(label, content);
    list.append(item);
    list.scrollTop = list.scrollHeight;
  }

  function setBusy(busy, message = "") {
    send.disabled = busy;
    input.disabled = busy;
    send.textContent = busy ? "Réflexion…" : "Envoyer";
    status.textContent = message;
  }

  function sendMessage(message) {
    const trimmed = message.trim();
    if (!trimmed || send.disabled) return;
    addMessage("user", trimmed);
    history.push({ role: "user", content: trimmed });
    input.value = "";
    setBusy(true, "Le professeur prépare son explication…");

    fetch("/api/tutor", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf,
      },
      body: JSON.stringify({
        messages: history.slice(-12),
        lesson_id: lessonId,
        exercise_id: exerciseId,
        question_id: questionId,
      }),
    })
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.message || "Le professeur IA est momentanément indisponible.");
        return data;
      })
      .then((data) => {
        const answer = String(data.answer || "").trim();
        if (!answer) throw new Error("Le professeur n'a pas renvoyé de réponse.");
        history.push({ role: "assistant", content: answer });
        addMessage("assistant", answer);
        setBusy(false, "");
      })
      .catch((error) => {
        history.pop();
        addMessage("assistant", error.message || "Une erreur est survenue. Réessaie.");
        setBusy(false, "");
      });
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    sendMessage(input.value);
  });

  root.querySelectorAll("[data-tutor-prompt]").forEach((button) => {
    button.addEventListener("click", () => sendMessage(button.dataset.tutorPrompt || button.textContent || ""));
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  addMessage("assistant", "Salam ! أنا الأستاذ الذكي ديالك فـ INFOCONCOURS. سولني على الدرس، صيفط ليا جوابك أو كود فيه خطأ، وغادي نشرح ليك فين المشكل وكيفاش تصلحو. أثناء الامتحان، المساعد كيتوقف حتى تسالي.");
  input.focus();
})();
