const messageEl = document.querySelector("#message");
const outputEl = document.querySelector("#response-output");
const chartEl = document.querySelector("#chart");
const chartDescriptionEl = document.querySelector("#chart-description");
const fileInput = document.querySelector("#file-input");
const fileMetaEl = document.querySelector("#file-meta");
const chartTypeInput = document.querySelector("#chart-type");
const visualPanel = document.querySelector('[data-step="visual"]');
const chartChoiceButtons = document.querySelectorAll("[data-chart-choice]");
const unavailableLabel = "暂不可用";
const jsonHeaders = { "Content-Type": "application/json" };

const stepStateLabels = {
  idle: "待调用",
  pending: "调用中",
  success: "已完成",
  unavailable: unavailableLabel,
  error: "异常",
};

function setStepState(stepName, state, label = stepStateLabels[state]) {
  const stepEl = document.querySelector(`[data-step="${stepName}"]`);
  const stateEl = document.querySelector(`#${stepName}-state`);

  if (stepEl) {
    stepEl.dataset.state = state;
  }

  if (stateEl) {
    stateEl.textContent = label;
  }
}

function showResponse(data, isError = false) {
  if (!messageEl || !outputEl) {
    return;
  }

  const userMessages = {
    NOT_IMPLEMENTED: "该步骤暂不可用，等待数据处理功能接入。",
    DATA_NOT_READY: "请先完成上传、清洗或分析后再创建图表。",
    INVALID_CHART: "请选择支持的图表类型。",
  };

  messageEl.textContent = userMessages[data.code] || data.message || "接口已响应。";
  messageEl.classList.toggle("error", isError);
  messageEl.classList.toggle("success", !isError);
  outputEl.textContent = JSON.stringify(data, null, 2);
}

async function readJsonResponse(response) {
  const data = await response.json();
  showResponse(data, !response.ok);
  return data;
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const data = await readJsonResponse(response);
  return { response, data };
}

function postJson(url, payload) {
  return requestJson(url, {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });
}

function finishStep(stepName, response, successLabel) {
  setStepState(stepName, response.ok ? "success" : "unavailable", response.ok ? successLabel : unavailableLabel);
}

function formatFileSize(size) {
  if (!Number.isFinite(size)) {
    return "";
  }

  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

if (fileInput && fileMetaEl) {
  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (!file) {
      fileMetaEl.textContent = "尚未选择文件";
      return;
    }

    const suffix = file.name.includes(".") ? file.name.split(".").pop().toUpperCase() : "未知格式";
    fileMetaEl.textContent = `${file.name} · ${suffix} · ${formatFileSize(file.size)}`;
  });
}

const uploadForm = document.querySelector("#upload-form");
if (uploadForm) {
  uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setStepState("upload", "pending");
    const formData = new FormData();
    const file = fileInput?.files[0];

    if (file) {
      formData.append("file", file);
    }

    const { response } = await requestJson("/api/upload", {
      method: "POST",
      body: formData,
    });
    finishStep("upload", response, "已上传");
  });
}

const cleanButton = document.querySelector("#clean-button");
if (cleanButton) {
  cleanButton.addEventListener("click", async () => {
    setStepState("clean", "pending");
    const payload = {
      drop_missing: document.querySelector("#drop-missing")?.checked || false,
      drop_duplicates: document.querySelector("#drop-duplicates")?.checked || false,
      handle_outliers: document.querySelector("#handle-outliers")?.checked || false,
    };

    const { response } = await postJson("/api/clean", payload);
    finishStep("clean", response, "已清洗");
  });
}

const analyzeButton = document.querySelector("#analyze-button");
if (analyzeButton) {
  analyzeButton.addEventListener("click", async () => {
    setStepState("analyze", "pending");
    const payload = {
      method: "kmeans",
      k: Number(document.querySelector("#cluster-count")?.value || 3),
    };

    const { response } = await postJson("/api/analyze", payload);
    finishStep("analyze", response, "已分析");
  });
}

document.querySelectorAll("[data-export-type]").forEach((button) => {
  button.addEventListener("click", async () => {
    setStepState("export", "pending");
    const exportType = button.dataset.exportType;
    const { response } = await requestJson(`/api/export?type=${encodeURIComponent(exportType)}`);
    finishStep("export", response, "已导出");
  });
});

chartChoiceButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const chart = button.dataset.chartChoice || "scatter";
    if (chartTypeInput) {
      chartTypeInput.value = chart;
    }

    chartChoiceButtons.forEach((item) => {
      const isSelected = item === button;
      item.classList.toggle("is-selected", isSelected);
      item.setAttribute("aria-pressed", String(isSelected));
    });
  });
});

const visualForm = document.querySelector("#visual-form");
if (visualForm) {
  visualForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (visualPanel) {
      visualPanel.dataset.state = "pending";
    }

    const params = new URLSearchParams({
      chart: chartTypeInput?.value || "scatter",
    });

    const { response, data } = await requestJson(`/api/visualize?${params.toString()}`);

    if (data.figure && chartEl) {
      if (visualPanel) {
        visualPanel.dataset.state = "success";
      }
      Plotly.react(chartEl, data.figure.data, data.figure.layout || {}, { responsive: true });
      if (chartDescriptionEl) {
        chartDescriptionEl.textContent = data.description || "图表已创建。";
      }
      return;
    }

    if (visualPanel) {
      visualPanel.dataset.state = response.ok ? "success" : "unavailable";
    }
    if (chartEl) {
      Plotly.purge(chartEl);
      chartEl.textContent = "请先完成上传、清洗或分析后再生成图表。";
    }
    if (chartDescriptionEl) {
      chartDescriptionEl.textContent = data.description || "数据准备完成后，系统会自动选择展示内容并生成图表说明。";
    }
  });
}

if (chartEl) {
  chartEl.textContent = "上传并处理数据后，图表会显示在这里。";
}
