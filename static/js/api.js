// 统一 API 请求封装

const API_BASE = "/api";

/**
 * 基础请求函数，统一处理 ApiResponse 的 code 与 message。
 * @param {string} path 接口路径（如 "/courses"）
 * @param {object} options fetch 配置
 * @returns {Promise<any>} 返回 ApiResponse 中的 data 字段
 */
async function request(path, options = {}) {
    const url = path.startsWith("http") ? path : `${API_BASE}${path}`;

    let response;
    try {
        response = await fetch(url, options);
    } catch (err) {
        alert("网络请求失败，请确认后端服务已启动");
        throw err;
    }

    let body;
    try {
        body = await response.json();
    } catch (err) {
        alert("响应解析失败");
        throw err;
    }

    // 统一处理 ApiResponse
    if (body.code !== 200) {
        alert(body.message || "请求失败");
        const error = new Error(body.message || "请求失败");
        error.code = body.code;
        throw error;
    }
    return body.data;
}

// 便捷方法
const api = {
    get(path) {
        return request(path, { method: "GET" });
    },
    post(path, data) {
        return request(path, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
    },
    del(path) {
        return request(path, { method: "DELETE" });
    },
    patch(path, data) {
        return request(path, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
    },
    upload(path, file) {
        // multipart/form-data：不手动设置 Content-Type，由浏览器自动生成 boundary
        const formData = new FormData();
        formData.append("file", file);
        return request(path, { method: "POST", body: formData });
    },
};
