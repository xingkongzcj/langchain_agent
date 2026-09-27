// 页面主逻辑

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initNewCourse();
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

// 新建课程
function initNewCourse() {
    const btn = document.getElementById("btn-new-course");
    btn.addEventListener("click", async () => {
        const name = prompt("请输入课程名称：");
        if (!name || !name.trim()) return;
        try {
            await api.post("/courses", { name: name.trim() });
            await loadCourses();
        } catch (err) {
            // 错误已在 api.js 中提示
        }
    });
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
            li.addEventListener("click", () => {
                document.querySelectorAll(".course-item").forEach((item) => {
                    item.classList.remove("active");
                });
                li.classList.add("active");
                document.getElementById("current-course-name").textContent = course.name;
            });
            list.appendChild(li);
        });
    } catch (err) {
        // 错误已在 api.js 中提示
    }
}
