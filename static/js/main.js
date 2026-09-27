// 页面主逻辑

let currentCourse = null; // 当前选中的课程 { id, name }
let isThinking = false; // 是否正在等待 AI 回答

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initCourseModal();
    initUpload();
    initChat();
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

    // 1. 用户消息立即上屏
    appendMessage("user", question);
    input.value = "";

    // 2. 显示"AI 思考中"加载
    isThinking = true;
    const thinkingEl = appendThinking();

    try {
        // 3. 调用后端 RAG 问答
        const result = await api.post(`/courses/${currentCourse.id}/chat`, {
            question,
            session_id: null,
        });
        thinkingEl.remove();
        // 4. 显示回答与引用来源
        appendMessage("assistant", result.answer, result.sources);
    } catch (err) {
        thinkingEl.remove();
        // 5. 错误提示：知识库为空等业务错误
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

    // 引用来源（浅灰色卡片）
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
