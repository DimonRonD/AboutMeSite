document.addEventListener("DOMContentLoaded", () => {
    const chatSessionKey = "petlibot_chat_session_v1";
    const toggleBtn = document.getElementById("chat-toggle-btn");
    const closeBtn = document.getElementById("chat-close-btn");
    const chatWidget = document.getElementById("chat-widget");
    const chatAuth = document.getElementById("chat-auth");
    const chatBody = document.getElementById("chat-body");
    const chatLoader = document.getElementById("chat-loader");
    const chatError = document.getElementById("chat-error");
    const chatControls = document.getElementById("chat-controls");
    const nameInput = document.getElementById("chat-name-input");
    const emailInput = document.getElementById("chat-email-input");
    const startBtn = document.getElementById("chat-start-btn");
    const messageInput = document.getElementById("chat-message-input");
    const sendBtn = document.getElementById("chat-send-btn");
    const clearMemoryBtn = document.getElementById("chat-clear-memory-btn");

    let currentName = "";
    let currentEmail = "";
    let isChatActivated = false;
    const maxMessageLength = 250;

    const saveSession = () => {
        const payload = {
            name: currentName,
            email: currentEmail,
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

    const activateChat = async () => {
        if (isChatActivated) {
            return;
        }
        isChatActivated = true;
        chatAuth.classList.add("d-none");
        chatBody.classList.remove("d-none");
        chatControls.classList.remove("d-none");

        try {
            const response = await fetch(
                `/api/chat/history-status?email=${encodeURIComponent(currentEmail)}`
            );
            const data = await response.json();
            if (data.has_history && data.message) {
                appendMessage("assistant", data.message);
            } else {
                appendMessage(
                    "assistant",
                    "Здравствуйте! Я ПетлиБот. Готов подсказать по проектам и услугам сайта."
                );
            }
        } catch (error) {
            appendMessage(
                "assistant",
                "Здравствуйте! Я ПетлиБот. Готов подсказать по проектам и услугам сайта."
            );
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

        appendMessage("user", message);
        messageInput.value = "";
        toggleLoader(true);

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: currentName,
                    email: currentEmail,
                    message,
                }),
            });
            const data = await response.json();
            if (!response.ok || !data.ok) {
                showError(data.error || "Ошибка при обработке запроса.");
                return;
            }
            appendMessage("assistant", data.answer);
        } catch (error) {
            showError("Не удалось получить ответ. Попробуйте позже.");
        } finally {
            toggleLoader(false);
        }
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
        if (!currentEmail) {
            showError("Сначала начните чат.");
            return;
        }
        try {
            const response = await fetch("/api/chat/clear-memory", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: currentEmail }),
            });
            const data = await response.json();
            if (!response.ok || !data.ok) {
                showError(data.error || "Не удалось очистить память.");
                return;
            }
            appendMessage("assistant", data.message);
        } catch (error) {
            showError("Не удалось очистить память.");
        }
    });

    toggleBtn.addEventListener("click", openChat);
    closeBtn.addEventListener("click", closeChat);

    const savedSession = loadSession();
    if (savedSession?.name && savedSession?.email) {
        currentName = (savedSession.name || "").trim();
        currentEmail = (savedSession.email || "").trim().toLowerCase();
        nameInput.value = currentName;
        emailInput.value = currentEmail;
        activateChat();
    }
});
