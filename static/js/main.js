// 页面主逻辑

let currentCourse = null; // 当前选中的课程 { id, name }
let isThinking = false; // 是否正在等待 AI 回答

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initCourseModal();
    initUpload();
    initChat();
    initQuiz();
    initReview();
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
        fileInput.value = "";
    });
}

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

// ============ 智能问答 ============
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
    card.dataset.answered = "0";

    // 题目
    const questionEl = document.createElement("div");
    questionEl.className = "quiz-question";
    questionEl.textContent = `${index + 1}. ${q.question}`;
    card.appendChild(questionEl);

    if (q.type === "short") {
        // 简答题：渲染输入框
        const textarea = document.createElement("textarea");
        textarea.className = "quiz-textarea";
        textarea.placeholder = "请输入你的答案…";
        card.appendChild(textarea);
    } else {
        // 客观题：选项列表
        const optionsEl = document.createElement("div");
        optionsEl.className = "quiz-options";
        (q.options || []).forEach((opt, i) => {
            const optEl = document.createElement("div");
            optEl.className = "quiz-option";
            optEl.textContent = opt;
            optEl.dataset.index = String(i);
            optEl.addEventListener("click", () => handleOptionSelect(q, card, optEl));
            optionsEl.appendChild(optEl);
        });
        card.appendChild(optionsEl);
    }

    // 操作区：提交答案 + 查看解析
    const actionsEl = document.createElement("div");
    actionsEl.className = "quiz-actions";
    const submitBtn = document.createElement("button");
    submitBtn.className = "btn btn-primary btn-sm";
    submitBtn.textContent = "提交答案";
    submitBtn.addEventListener("click", () => submitQuizAnswer(q, card, submitBtn));
    actionsEl.appendChild(submitBtn);
    const toggleBtn = document.createElement("button");
    toggleBtn.className = "btn btn-secondary btn-sm";
    toggleBtn.textContent = "查看解析";
    actionsEl.appendChild(toggleBtn);
    card.appendChild(actionsEl);

    // 解析区（默认折叠，提交答案后填充）
    const answerEl = document.createElement("div");
    answerEl.className = "quiz-answer";
    answerEl.hidden = true;
    card.appendChild(answerEl);

    toggleBtn.addEventListener("click", () => {
        answerEl.hidden = !answerEl.hidden;
        toggleBtn.textContent = answerEl.hidden ? "查看解析" : "收起解析";
    });

    return card;
}

function handleOptionSelect(q, card, optEl) {
    if (card.dataset.answered === "1") return;
    if (q.type === "multiple") {
        optEl.classList.toggle("selected");
    } else {
        card.querySelectorAll(".quiz-option").forEach((o) => o.classList.remove("selected"));
        optEl.classList.add("selected");
    }
}

async function submitQuizAnswer(q, card, submitBtn) {
    const textarea = q.type === "short" ? card.querySelector(".quiz-textarea") : null;

    let userAnswer;
    if (q.type === "short") {
        userAnswer = textarea.value.trim();
        if (!userAnswer) {
            alert("请先输入答案");
            return;
        }
    } else {
        userAnswer = collectUserAnswer(q, card);
        if (!userAnswer) {
            alert("请先选择答案");
            return;
        }
    }

    submitBtn.disabled = true;
    try {
        const result = await api.post(`/questions/${q.id}/submit`, {
            user_answer: userAnswer,
        });
        card.dataset.answered = "1";

        const answerEl = card.querySelector(".quiz-answer");
        answerEl.hidden = false;

        if (q.type === "short") {
            // 简答题：禁用输入框，展示 AI 评分 + 批改理由 + 参考答案 + 解析
            if (textarea) textarea.disabled = true;
            answerEl.innerHTML =
                '<div class="answer-line"><strong>AI 评分：</strong>' + (result.score != null ? result.score + "分" : "无") + "</div>" +
                '<div class="explanation-line"><strong>批改理由：</strong>' + escapeHtml(result.reason || "无") + "</div>" +
                '<div class="answer-line"><strong>参考答案：</strong>' + escapeHtml(result.correct_answer || "无") + "</div>" +
                '<div class="explanation-line"><strong>解析：</strong>' + escapeHtml(result.explanation || "无") + "</div>";
        } else {
            // 客观题：标对错 + 答案 + 解析
            markOptions(q, card, result.correct, result.correct_answer);
            answerEl.innerHTML =
                '<div class="answer-line"><strong>答案：</strong>' + escapeHtml(result.correct_answer || "无") + "</div>" +
                '<div class="explanation-line"><strong>解析：</strong>' + escapeHtml(result.explanation || "无") + "</div>";
        }

        const toggleBtn = card.querySelector(".quiz-actions .btn-secondary");
        if (toggleBtn) toggleBtn.textContent = "收起解析";

        if (result.mistake_id) {
            alert("已加入错题本");
        }
    } catch (err) {
        // 错误已在 api.js 中提示
    } finally {
        submitBtn.disabled = false;
    }
}

function collectUserAnswer(q, card) {
    const selected = card.querySelectorAll(".quiz-option.selected");
    if (selected.length === 0) return "";

    if (q.type === "judge") {
        return selected[0].textContent.trim();
    }
    if (q.type === "multiple") {
        const letters = [];
        selected.forEach((opt) => {
            letters.push(q.options[parseInt(opt.dataset.index, 10)][0]);
        });
        return letters.sort().join("");
    }
    return q.options[parseInt(selected[0].dataset.index, 10)][0];
}

function markOptions(q, card, correct, correctAnswer) {
    const options = card.querySelectorAll(".quiz-option");
    options.forEach((opt) => {
        opt.classList.add("disabled");
        const i = parseInt(opt.dataset.index, 10);
        const isAnswer =
            q.type === "judge"
                ? q.options[i] === correctAnswer
                : (correctAnswer || "").includes(q.options[i][0]);
        if (isAnswer) opt.classList.add("correct");
    });
    if (!correct) {
        card.querySelectorAll(".quiz-option.selected").forEach((opt) => {
            opt.classList.add("wrong");
        });
    }
}

// ============ 错题本 ============
async function loadMistakes(courseId) {
    const list = document.getElementById("mistake-list");
    try {
        const items = await api.get(`/courses/${courseId}/mistakes`);
        list.innerHTML = "";
        if (!items || items.length === 0) {
            list.innerHTML = '<div class="quiz-empty">暂无错题</div>';
            return;
        }
        items.forEach((item) => {
            list.appendChild(createMistakeCard(item));
        });
    } catch (err) {
        // 错误已在 api.js 中提示
    }
}

function createMistakeCard(item) {
    const card = document.createElement("div");
    card.className = "mistake-card";

    const questionEl = document.createElement("div");
    questionEl.className = "mistake-question";
    questionEl.textContent = item.question;

    const wrongEl = document.createElement("div");
    wrongEl.className = "mistake-row wrong-answer";
    wrongEl.textContent = "你的答案：" + (item.user_answer || "无");

    const correctEl = document.createElement("div");
    correctEl.className = "mistake-row correct-answer";
    correctEl.textContent = "正确答案：" + (item.correct_answer || "无");

    const explanationEl = document.createElement("div");
    explanationEl.className = "mistake-row";
    explanationEl.textContent = "解析：" + (item.explanation || "无");

    const btn = document.createElement("button");
    btn.className = "btn btn-primary btn-sm";
    btn.textContent = "标记已掌握";
    btn.addEventListener("click", () => markMastered(item.id, card));

    card.appendChild(questionEl);
    card.appendChild(wrongEl);
    card.appendChild(correctEl);
    card.appendChild(explanationEl);
    card.appendChild(btn);
    return card;
}

async function markMastered(mistakeId, card) {
    try {
        await api.patch(`/mistakes/${mistakeId}`, { status: "mastered" });
        card.remove();
    } catch (err) {
        // 错误已在 api.js 中提示
    }
}

// ============ 课程与文档 ============
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

function selectCourse(course, li) {
    document.querySelectorAll(".course-item").forEach((item) => {
        item.classList.remove("active");
    });
    li.classList.add("active");
    currentCourse = { id: course.id, name: course.name };
    document.getElementById("current-course-name").textContent = course.name;
    document.getElementById("quiz-current-course").textContent = course.name;
    document.getElementById("mistake-current-course").textContent = course.name;
    document.getElementById("review-current-course").textContent = course.name;
    loadDocuments(course.id);
    resetChat();
    resetQuiz();
    loadMistakes(course.id);
    resetReview();
    loadReviewPlans(course.id);
}

function resetChat() {
    const container = document.getElementById("chat-messages");
    container.innerHTML =
        '<div class="chat-hint">当前课程「' + escapeHtml(currentCourse.name) + '」，请在下方提问</div>';
}

function resetQuiz() {
    document.getElementById("quiz-list").innerHTML =
        '<div class="quiz-empty">请先在左侧选择课程，再生成题目</div>';
    document.getElementById("quiz-status").hidden = true;
}

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

// ============ 复习计划 ============
function initReview() {
    const btn = document.getElementById("btn-generate-plan");
    btn.addEventListener("click", () => generatePlan());
}

async function generatePlan() {
    if (!currentCourse) {
        alert("请先在左侧选择课程");
        return;
    }

    const status = document.getElementById("review-status");
    status.hidden = false;
    status.className = "upload-status loading";
    status.textContent = "AI 生成复习计划中…，请稍候";

    try {
        await api.post(`/courses/${currentCourse.id}/review-plans`, { name: null });
        status.hidden = true;
        await loadReviewPlans(currentCourse.id);
    } catch (err) {
        status.className = "upload-status error";
        status.textContent = "生成失败，请重试";
    }
}

async function loadReviewPlans(courseId) {
    const list = document.getElementById("review-list");
    try {
        const plans = await api.get(`/courses/${courseId}/review-plans`);
        list.innerHTML = "";
        if (!plans || plans.length === 0) {
            list.innerHTML = '<div class="quiz-empty">暂无复习计划，点击上方按钮生成</div>';
            return;
        }
        const detail = await api.get(`/review-plans/${plans[0].id}`);
        renderReviewPlan(detail);
    } catch (err) {
        // 错误已在 api.js 中提示
    }
}

function renderReviewPlan(plan) {
    const list = document.getElementById("review-list");
    list.innerHTML = "";

    const title = document.createElement("div");
    title.className = "review-plan-title";
    title.textContent = plan.name;
    list.appendChild(title);

    if (!plan.items || plan.items.length === 0) {
        const empty = document.createElement("div");
        empty.className = "quiz-empty";
        empty.textContent = "计划中暂无复习条目";
        list.appendChild(empty);
        return;
    }

    // 按日期分组
    const groups = {};
    plan.items.forEach((item) => {
        const key = item.review_date;
        if (!groups[key]) groups[key] = [];
        groups[key].push(item);
    });

    Object.keys(groups).sort().forEach((dateKey) => {
        const group = document.createElement("div");
        group.className = "review-group";

        const dateEl = document.createElement("div");
        dateEl.className = "review-date";
        dateEl.textContent = dateKey;
        group.appendChild(dateEl);

        groups[dateKey].forEach((item) => {
            group.appendChild(createReviewItem(item));
        });

        list.appendChild(group);
    });
}

function createReviewItem(item) {
    const el = document.createElement("div");
    el.className = "review-item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = item.completed;
    checkbox.addEventListener("change", () => toggleReviewItem(item.id, checkbox, el));

    const label = document.createElement("span");
    label.className = "review-knowledge";
    label.textContent = item.knowledge_point || "（无知识点）";
    if (item.completed) label.classList.add("done");

    el.appendChild(checkbox);
    el.appendChild(label);
    return el;
}

async function toggleReviewItem(itemId, checkbox, el) {
    try {
        await api.patch(`/review-items/${itemId}`, { completed: checkbox.checked });
        const label = el.querySelector(".review-knowledge");
        if (checkbox.checked) {
            label.classList.add("done");
        } else {
            label.classList.remove("done");
        }
    } catch (err) {
        checkbox.checked = !checkbox.checked; // 失败回滚
    }
}

function resetReview() {
    document.getElementById("review-list").innerHTML =
        '<div class="quiz-empty">请先在左侧选择课程，再生成复习计划</div>';
    document.getElementById("review-status").hidden = true;
}

// 简单的 HTML 转义，防止 XSS
function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
