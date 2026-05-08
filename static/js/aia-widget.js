document.addEventListener("DOMContentLoaded", () => {
    const chatSessionKey = "aia_chat_session_v1";
    const toggleBtn = document.getElementById("aia-toggle-btn");
    const closeBtn = document.getElementById("aia-close-btn");
    const chatWidget = document.getElementById("aia-widget");
    const chatAuth = document.getElementById("aia-auth");
    const chatBody = document.getElementById("aia-body");
    const chatLoader = document.getElementById("aia-loader");
    const chatError = document.getElementById("aia-error");
    const chatControls = document.getElementById("aia-controls");
    const nameInput = document.getElementById("aia-name-input");
    const emailInput = document.getElementById("aia-email-input");
    const startBtn = document.getElementById("aia-start-btn");
    const messageInput = document.getElementById("aia-message-input");
    const sendBtn = document.getElementById("aia-send-btn");
    const clearMemoryBtn = document.getElementById("aia-clear-memory-btn");
    const feedbackBlock = document.getElementById("aia-feedback");
    const rateButtonsBox = document.getElementById("aia-rate-buttons");
    const commentInput = document.getElementById("aia-comment-input");
    const sendCommentBtn = document.getElementById("aia-send-comment-btn");
    const commentHint = document.getElementById("aia-comment-hint");

    if (!toggleBtn || !chatWidget) {
        return;
    }

    let currentName = "";
    let currentEmail = "";
    let currentSessionId = "";
    let isChatActivated = false;
    let isDialogClosed = false;
    let lastSupportMessageId = 0;
    let supportPollTimer = null;
    let supportConnectedShown = false;
    let selectedRating = 0;
    const maxMessageLength = 250;

    const saveSession = () => {
        const payload = {
            name: currentName,
            email: currentEmail,
            session_id: currentSessionId,
        };
        localStorage.setItem(chatSessionKey, JSON.stringify(payload));
    };

    const loadSession = () => {
        const raw = localStorage.getItem(chatSessionKey);
        if (!raw) {
            return null;
        }
        try {
            return JSON.parse(raw);
        } catch (error) {
            localStorage.removeItem(chatSessionKey);
            return null;
        }
    };

    const appendMessage = (role, text) => {
        const item = document.createElement("div");
        item.className = `chat-msg chat-msg-${role}`;
        item.textContent = text;
        chatBody.appendChild(item);
        chatBody.scrollTop = chatBody.scrollHeight;
    };

    const showError = (text) => {
        chatError.textContent = text;
        chatError.classList.remove("d-none");
    };

    const clearError = () => {
        chatError.textContent = "";
        chatError.classList.add("d-none");
    };

    const toggleLoader = (isVisible) => {
        chatLoader.classList.toggle("d-none", !isVisible);
    };

    const openChat = () => chatWidget.classList.remove("d-none");
    const closeChat = () => chatWidget.classList.add("d-none");
    const markSupportMessageSeen = (message) => {
        const msgId = Number.parseInt(String(message?.id ?? ""), 10);
        if (!Number.isNaN(msgId) && msgId > lastSupportMessageId) {
            lastSupportMessageId = msgId;
        }
    };

    const appendSupportMessages = (messages) => {
        if (!Array.isArray(messages) || messages.length === 0) {
            return;
        }
        messages.forEach((message) => {
            if ((message?.actor || "").toLowerCase() !== "support") {
                return;
            }
            if (!supportConnectedShown) {
                appendMessage("system", "Оператор подключился");
                supportConnectedShown = true;
            }
            markSupportMessageSeen(message);
            appendMessage("support", message.content || "");
        });
    };

    const pollSupportInbox = async () => {
        if (!currentSessionId || !isChatActivated) {
            return;
        }
        try {
            const response = await fetch(
                `/api/aia/support-inbox/${encodeURIComponent(currentSessionId)}?after_id=${lastSupportMessageId}`
            );
            const data = await response.json();
            if (!response.ok || !data.ok) {
                return;
            }
            appendSupportMessages(data.messages || []);
            const lastId = Number.parseInt(String(data.last_id ?? ""), 10);
            if (!Number.isNaN(lastId) && lastId > lastSupportMessageId) {
                lastSupportMessageId = lastId;
            }
            if (Boolean(data.dialog_closed)) {
                setClosedUiState(true);
            }
        } catch (error) {
            // Keep silent on polling errors to avoid noisy UI.
        }
    };

    const startSupportPolling = () => {
        if (supportPollTimer) {
            return;
        }
        supportPollTimer = window.setInterval(() => {
            pollSupportInbox();
        }, 5000);
    };

    const stopSupportPolling = () => {
        if (!supportPollTimer) {
            return;
        }
        window.clearInterval(supportPollTimer);
        supportPollTimer = null;
    };

    const setClosedUiState = (isClosed) => {
        isDialogClosed = Boolean(isClosed);
        chatControls.classList.toggle("d-none", isDialogClosed);
        feedbackBlock?.classList.toggle("d-none", !isDialogClosed);
    };

    const setCommentAvailability = (enabled) => {
        if (commentInput) {
            commentInput.disabled = !enabled;
        }
        if (sendCommentBtn) {
            sendCommentBtn.disabled = !enabled;
        }
        if (commentHint) {
            commentHint.classList.toggle("d-none", enabled);
        }
    };

    const updateStarSelection = (rating) => {
        const stars = rateButtonsBox?.querySelectorAll("[data-aia-rate]") || [];
        stars.forEach((star) => {
            const value = Number.parseInt(star.getAttribute("data-aia-rate") || "0", 10);
            star.classList.toggle("is-active", value <= rating);
        });
    };

    const syncDialogState = async () => {
        if (!currentSessionId) {
            setClosedUiState(false);
            return;
        }
        try {
            const response = await fetch(`/api/aia/dialog/${encodeURIComponent(currentSessionId)}`);
            const data = await response.json();
            if (!response.ok || !data.ok) {
                return;
            }
            const status = (data?.dialog?.status || "").toString().toLowerCase();
            setClosedUiState(status === "closed");
            appendSupportMessages(data?.messages || []);
        } catch (error) {
            // Keep current UI state if snapshot request failed.
        }
    };

    const sendAiaText = async (message, showInChat = true) => {
        if (isDialogClosed) {
            showError("Диалог уже завершен. Поставьте оценку и добавьте комментарий при необходимости.");
            return;
        }
        if (showInChat) {
            appendMessage("user", message);
        }
        toggleLoader(true);
        try {
            const response = await fetch("/api/aia/text", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    message,
                }),
            });
            const data = await response.json();
            if (!response.ok || !data.ok) {
                showError(data.error || "Ошибка при обработке запроса.");
                return;
            }
            appendMessage("assistant", data.answer || "Ответ не получен.");
            await syncDialogState();
        } catch (error) {
            showError("Не удалось получить ответ. Попробуйте позже.");
        } finally {
            toggleLoader(false);
        }
    };

    const activateChat = async () => {
        if (isChatActivated) {
            return;
        }
        toggleLoader(true);
        try {
            const response = await fetch("/api/aia/auth", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: currentName,
                    email: currentEmail,
                    session_id: currentSessionId || undefined,
                }),
            });
            const data = await response.json();
            if (!response.ok || !data.ok) {
                showError(data.error || "Не удалось авторизоваться в AIA.");
                return;
            }

            isChatActivated = true;
            chatAuth.classList.add("d-none");
            chatBody.classList.remove("d-none");
            setClosedUiState(false);

            currentSessionId = data.session_id || currentSessionId;
            saveSession();

            const history = Array.isArray(data.history) ? data.history : [];
            if (data.has_previous_history && history.length > 0) {
                const shouldContinue = window.confirm(
                    "Найдена история диалога AIA. Нажмите OK, чтобы продолжить, или Отмена, чтобы очистить историю."
                );
                if (shouldContinue) {
                    history.forEach((item) => {
                        const actor = (item.actor || "").toLowerCase();
                        if (actor === "support") {
                            if (!supportConnectedShown) {
                                appendMessage("system", "Оператор подключился");
                                supportConnectedShown = true;
                            }
                            appendMessage("support", item.content || "");
                        } else {
                            const role = actor === "user" ? "user" : "assistant";
                            appendMessage(role, item.content || "");
                        }
                        markSupportMessageSeen(item);
                    });
                } else {
                    await sendAiaText("очистить историю", false);
                    lastSupportMessageId = 0;
                    supportConnectedShown = false;
                    selectedRating = 0;
                    updateStarSelection(0);
                    setCommentAvailability(false);
                }
            } else {
                appendMessage("assistant", "Здравствуйте! Я AIA. Чем могу помочь?");
            }
            await syncDialogState();
            startSupportPolling();
        } catch (error) {
            showError("Не удалось подключиться к AIA.");
        } finally {
            toggleLoader(false);
        }
    };

    startBtn.addEventListener("click", async () => {
        clearError();
        currentName = (nameInput.value || "").trim();
        currentEmail = (emailInput.value || "").trim().toLowerCase();
        if (!currentName || !currentEmail) {
            showError("Введите имя и email.");
            return;
        }
        saveSession();
        await activateChat();
    });

    sendBtn.addEventListener("click", async () => {
        clearError();
        const message = (messageInput.value || "").trim();
        if (!message) {
            return;
        }
        if (message.length > maxMessageLength) {
            showError(`Превышен размер сообщения. Допустимо не более ${maxMessageLength} символов.`);
            return;
        }
        messageInput.value = "";
        await sendAiaText(message);
    });

    messageInput.addEventListener("keydown", async (event) => {
        if (event.key !== "Enter") {
            return;
        }
        if (event.shiftKey) {
            return;
        }
        event.preventDefault();
        sendBtn.click();
    });

    clearMemoryBtn.addEventListener("click", async () => {
        clearError();
        if (!currentSessionId) {
            showError("Сначала начните чат.");
            return;
        }
        await sendAiaText("очистить историю");
    });

    rateButtonsBox?.addEventListener("click", async (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) {
            return;
        }
        const ratingRaw = target.getAttribute("data-aia-rate");
        if (!ratingRaw || !currentSessionId) {
            return;
        }
        clearError();
        const rating = Number.parseInt(ratingRaw, 10);
        if (Number.isNaN(rating)) {
            return;
        }
        try {
            const response = await fetch("/api/aia/rate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    rating,
                }),
            });
            const data = await response.json();
            if (!response.ok || !data.ok) {
                showError(data.error || "Не удалось сохранить оценку.");
                return;
            }
            selectedRating = rating;
            updateStarSelection(selectedRating);
            setCommentAvailability(true);
            const rawRateMessage = (data.message || "Оценка сохранена.").trim();
            const cleanedRateMessage = rawRateMessage.replace(
                /\.\s*При желании добавьте комментарий:\s*\/comment\s*<текст>\.?/i,
                "."
            );
            appendMessage("assistant", cleanedRateMessage);
        } catch (error) {
            showError("Не удалось отправить оценку.");
        }
    });

    sendCommentBtn?.addEventListener("click", async () => {
        clearError();
        const comment = (commentInput?.value || "").trim();
        if (!currentSessionId) {
            showError("Сначала начните чат.");
            return;
        }
        if (!selectedRating) {
            showError("Сначала поставьте оценку звездами.");
            return;
        }
        if (!comment) {
            showError("Введите комментарий.");
            return;
        }
        try {
            const response = await fetch("/api/aia/comment", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    comment,
                }),
            });
            const data = await response.json();
            if (!response.ok || !data.ok) {
                showError(data.error || "Не удалось отправить комментарий.");
                return;
            }
            appendMessage("assistant", data.message || "Комментарий сохранен.");
            commentInput.value = "";
        } catch (error) {
            showError("Не удалось отправить комментарий.");
        }
    });

    toggleBtn.addEventListener("click", openChat);
    closeBtn.addEventListener("click", () => {
        closeChat();
        stopSupportPolling();
    });

    const savedSession = loadSession();
    setCommentAvailability(false);
    updateStarSelection(0);
    if (savedSession?.name && savedSession?.email) {
        currentName = (savedSession.name || "").trim();
        currentEmail = (savedSession.email || "").trim().toLowerCase();
        currentSessionId = (savedSession.session_id || "").trim();
        nameInput.value = currentName;
        emailInput.value = currentEmail;
        activateChat();
    }
});
