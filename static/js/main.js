// 页面主逻辑

let currentCourse = null; // 当前选中的课程 { id, name }
let isThinking = false; // 是否正在等待 AI 回答

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initCourseModal();
    initUpload();
    initChat();
    initQuiz();
    loadCourses();
});

// Tab 切换
function initTabs() {
    const tabs = document.querySelectorAll(".tab");
    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            tabs.forEach((t) => t.classList.remove("active"));
            tab.classList.add("active");
            document.querySelectorAll(".tab-panel").forEach((panel) => {
                panel.classList.remove("active");
            });
            document.getElementById(`tab-${tab.dataset.tab}`).classList.add("active");
        });
    });
}

// 新建课程弹窗
function initCourseModal() {
    const modal = document.getElementById("course-modal");
    const openBtn = document.getElementById("btn-new-course");
    const cancelBtn = document.getElementById("btn-modal-cancel");
    const confirmBtn = document.getElementById("btn-modal-confirm");
    const nameInput = document.getElementById("input-course-name");
    const descInput = document.getElementById("input-course-desc");

    openBtn.addEventListener("click", () => {
        nameInput.value = "";
        descInput.value = "";
        modal.hidden = false;
        nameInput.focus();
    });

    cancelBtn.addEventListener("click", () => {
        modal.hidden = true;
    });

    // 点击遮罩关闭
    modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.hidden = true;
    });

    confirmBtn.addEventListener("click", async () => {
        const name = nameInput.value.trim();
        if (!name) {
            alert("请输入课程名称");
            return;
        }
        const desc = descInput.value.trim();
        try {
            await api.post("/courses", { name, description: desc || null });
            modal.hidden = true;
            await loadCourses();
        } catch (err) {
            // 错误已在 api.js 中提示
        }
    });
}

// 上传文档
function initUpload() {
    const uploadBtn = document.getElementById("btn-upload");
    const fileInput = document.getElementById("file-input");

    uploadBtn.addEventListener("click", () => {
        if (!currentCourse) {
            alert("请先在左侧选择课程");
            return;
        }
        fileInput.click();
    });

    fileInput.addEventListener("change", async () => {
        const file = fileInput.files[0];
        if (!file) return;
        await uploadDocument(file);
        fileInput.value = ""; // 允许重复选择同一文件
    });
}

// 上传文档
async function uploadDocument(file) {
    const status = document.getElementById("upload-status");
    status.hidden = false;
    status.className = "upload-status loading";
    status.textContent = `正在上传并解析「${file.name}」，请稍候…`;

    try {
        await api.upload(`/courses/${currentCourse.id}/documents`, file);
        status.className = "upload-status success";
        status.textContent = `「${file.name}」上传成功`;
        await loadDocuments(currentCourse.id);
    } catch (err) {
        status.className = "upload-status error";
        status.textContent = "上传失败，请重试";
    }
}

// 智能问答
function initChat() {
    const sendBtn = document.getElementById("btn-send");
    const input = document.getElementById("chat-input");

    sendBtn.addEventListener("click", () => sendMessage());
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendMessage();
    });
}

async function sendMessage() {
    if (isThinking) return;

    const input = document.getElementById("chat-input");
    const question = input.value.trim();
    if (!question) return;
    if (!currentCourse) {
        alert("请先在左侧选择课程");
        return;
    }

    appendMessage("user", question);
    input.value = "";

    isThinking = true;
    const thinkingEl = appendThinking();

    try {
        const result = await api.post(`/courses/${currentCourse.id}/chat`, {
            question,
            session_id: null,
        });
        thinkingEl.remove();
        appendMessage("assistant", result.answer, result.sources);
    } catch (err) {
        thinkingEl.remove();
        const msg = err && err.code === 400 ? "请先上传文档" : "请求失败，请稍后重试";
        appendMessage("assistant", msg);
    } finally {
        isThinking = false;
    }
}

// 追加思考中气泡
function appendThinking() {
    const container = document.getElementById("chat-messages");
    clearHint(container);

    const msgDiv = document.createElement("div");
    msgDiv.className = "message assistant";
    msgDiv.innerHTML = '<div class="bubble thinking">AI 思考中…</div>';
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
    return msgDiv;
}

// 追加一条消息
function appendMessage(role, content, sources = null) {
    const container = document.getElementById("chat-messages");
    clearHint(container);

    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${role}`;

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = content;
    msgDiv.appendChild(bubble);

    if (sources && sources.length > 0) {
        const sourcesDiv = document.createElement("div");
        sourcesDiv.className = "sources";
        sources.forEach((s) => {
            const card = document.createElement("div");
            card.className = "source-card";

            const name = document.createElement("div");
            name.className = "source-name";
            name.textContent = s.filename || "未知来源";

            const text = document.createElement("div");
            text.className = "source-text";
            text.textContent = (s.text || "").slice(0, 50) + "...";

            card.appendChild(name);
            card.appendChild(text);
            sourcesDiv.appendChild(card);
        });
        msgDiv.appendChild(sourcesDiv);
    }

    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
    return msgDiv;
}

// 清除初始提示
function clearHint(container) {
    const hint = container.querySelector(".chat-hint");
    if (hint) hint.remove();
}

// ============ 自动出题 ============
function initQuiz() {
    const btn = document.getElementById("btn-generate-quiz");
    btn.addEventListener("click", () => generateQuiz());
}

async function generateQuiz() {
    if (!currentCourse) {
        alert("请先在左侧选择课程");
        return;
    }

    const type = document.getElementById("quiz-type").value;
    const difficulty = document.getElementById("quiz-difficulty").value;
    const count = parseInt(document.getElementById("quiz-count").value, 10);

    const status = document.getElementById("quiz-status");
    const list = document.getElementById("quiz-list");
    status.hidden = false;
    status.className = "upload-status loading";
    status.textContent = "AI 出题中…，请稍候";
    list.innerHTML = "";

    try {
        const batch = await api.post(`/courses/${currentCourse.id}/quizzes/generate`, {
            topic: null,
            question_type: type,
            difficulty,
            count,
        });
        status.hidden = true;
        renderQuiz(batch.questions || []);
    } catch (err) {
        status.className = "upload-status error";
        status.textContent = "出题失败，请重试";
    }
}

function renderQuiz(questions) {
    const container = document.getElementById("quiz-list");
    container.innerHTML = "";
    if (!questions || questions.length === 0) {
        container.innerHTML = '<div class="quiz-empty">未生成题目</div>';
        return;
    }
    questions.forEach((q, index) => {
        container.appendChild(createQuizCard(q, index));
    });
}

function createQuizCard(q, index) {
    const card = document.createElement("div");
    card.className = "quiz-card";

    // 题目
    const questionEl = document.createElement("div");
    questionEl.className = "quiz-question";
    questionEl.textContent = `${index + 1}. ${q.question}`;
    card.appendChild(questionEl);

    if (q.type !== "short") {
        // 客观题：选项列表（简答题主区域仅显示题干）
        const optionsEl = document.createElement("div");
        optionsEl.className = "quiz-options";
        (q.options || []).forEach((opt, i) => {
            const optEl = document.createElement("div");
            optEl.className = "quiz-option";
            optEl.textContent = opt;
            optEl.dataset.index = String(i);
            optEl.addEventListener("click", () => handleOptionClick(q, card, optEl, i));
            optionsEl.appendChild(optEl);
        });
        card.appendChild(optionsEl);
    }

    // 查看解析（默认折叠）
    const actionsEl = document.createElement("div");
    actionsEl.className = "quiz-actions";
    const toggleBtn = document.createElement("button");
    toggleBtn.className = "btn btn-secondary btn-sm";
    toggleBtn.textContent = "查看解析";
    actionsEl.appendChild(toggleBtn);
    card.appendChild(actionsEl);

    const answerEl = document.createElement("div");
    answerEl.className = "quiz-answer";
    answerEl.hidden = true;
    const answerLabel = q.type === "short" ? "参考答案：" : "答案：";
    answerEl.innerHTML =
        '<div class="answer-line"><strong>' + answerLabel + '</strong>' + escapeHtml(q.answer || "无") + "</div>" +
        '<div class="explanation-line"><strong>解析：</strong>' + escapeHtml(q.explanation || "无") + "</div>";
    card.appendChild(answerEl);

    toggleBtn.addEventListener("click", () => {
        answerEl.hidden = !answerEl.hidden;
        toggleBtn.textContent = answerEl.hidden ? "查看解析" : "收起解析";
    });

    return card;
}

function handleOptionClick(q, card, optEl, index) {
    const type = q.type;

    if (type === "multiple") {
        // 多选：toggle 选中，等待提交
        optEl.classList.toggle("selected");
        ensureSubmitButton(q, card);
        return;
    }

    // 单选 / 判断：点击即判
    if (card.dataset.answered) return;
    card.dataset.answered = "1";

    const options = card.querySelectorAll(".quiz-option");
    const correct =
        type === "judge"
            ? q.options[index] === q.answer
            : q.options[index][0] === q.answer;

    options.forEach((opt, i) => {
        opt.classList.add("disabled");
        const isAnswer =
            type === "judge"
                ? q.options[i] === q.answer
                : q.options[i][0] === q.answer;
        if (isAnswer) opt.classList.add("correct");
    });
    optEl.classList.add(correct ? "correct" : "wrong");
}

function ensureSubmitButton(q, card) {
    if (card.querySelector(".btn-submit")) return;
    const actions = card.querySelector(".quiz-actions");
    const submitBtn = document.createElement("button");
    submitBtn.className = "btn btn-primary btn-sm btn-submit";
    submitBtn.textContent = "提交答案";
    submitBtn.addEventListener("click", () => handleMultipleSubmit(q, card));
    actions.prepend(submitBtn);
}

function handleMultipleSubmit(q, card) {
    if (card.dataset.answered) return;
    card.dataset.answered = "1";

    const selected = [];
    card.querySelectorAll(".quiz-option.selected").forEach((opt) => {
        selected.push(q.options[parseInt(opt.dataset.index, 10)][0]);
    });
    const userAnswer = selected.sort().join("");
    const correctAnswer = (q.answer || "").split("").sort().join("");
    const correct = userAnswer === correctAnswer;

    card.querySelectorAll(".quiz-option").forEach((opt) => {
        opt.classList.add("disabled");
        const letter = q.options[parseInt(opt.dataset.index, 10)][0];
        if ((q.answer || "").includes(letter)) opt.classList.add("correct");
    });
    if (!correct) {
        card.querySelectorAll(".quiz-option.selected").forEach((opt) => {
            opt.classList.add("wrong");
        });
    }

    const submitBtn = card.querySelector(".btn-submit");
    if (submitBtn) submitBtn.remove();
}

// 加载课程列表
async function loadCourses() {
    const list = document.getElementById("course-list");
    try {
        const courses = await api.get("/courses");
        list.innerHTML = "";
        if (!courses || courses.length === 0) {
            list.innerHTML = '<li class="course-empty">暂无课程，点击上方按钮新建</li>';
            return;
        }
        courses.forEach((course) => {
            const li = document.createElement("li");
            li.className = "course-item";
            li.textContent = course.name;
            li.dataset.id = course.id;
            li.addEventListener("click", () => selectCourse(course, li));
            list.appendChild(li);
        });
    } catch (err) {
        // 错误已在 api.js 中提示
    }
}

// 选中课程
function selectCourse(course, li) {
    document.querySelectorAll(".course-item").forEach((item) => {
        item.classList.remove("active");
    });
    li.classList.add("active");
    currentCourse = { id: course.id, name: course.name };
    document.getElementById("current-course-name").textContent = course.name;
    document.getElementById("quiz-current-course").textContent = course.name;
    loadDocuments(course.id);
    resetChat();
}

// 切换课程时清空聊天区
function resetChat() {
    const container = document.getElementById("chat-messages");
    container.innerHTML =
        '<div class="chat-hint">当前课程「' + escapeHtml(currentCourse.name) + '」，请在下方提问</div>';
}

// 加载文档列表
async function loadDocuments(courseId) {
    const list = document.getElementById("document-list");
    try {
        const docs = await api.get(`/courses/${courseId}/documents`);
        list.innerHTML = "";
        if (!docs || docs.length === 0) {
            list.innerHTML = '<li class="doc-empty">暂无文档，点击「上传文档」按钮添加</li>';
            return;
        }
        docs.forEach((doc) => {
            const li = document.createElement("li");
            li.className = "doc-item";
            li.innerHTML =
                '<div class="doc-name">' + escapeHtml(doc.filename) + "</div>" +
                '<div class="doc-meta">类型: ' + (doc.file_type || "-") +
                " · 分块: " + doc.chunk_count +
                " · 状态: " + doc.status + "</div>";
            list.appendChild(li);
        });
    } catch (err) {
        // 错误已在 api.js 中提示
    }
}

// 简单的 HTML 转义，防止 XSS
function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
