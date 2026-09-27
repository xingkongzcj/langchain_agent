// 页面主逻辑

let currentCourse = null; // 当前选中的课程 { id, name }

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initCourseModal();
    initUpload();
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
