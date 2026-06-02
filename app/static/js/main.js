const messageEl = document.querySelector("#message");
const outputEl = document.querySelector("#response-output");
const chartEl = document.querySelector("#chart");

function showResponse(data, isError = false) {
  messageEl.textContent = data.message || "接口已响应。";
  messageEl.classList.toggle("error", isError);
  outputEl.textContent = JSON.stringify(data, null, 2);
}

async function readJsonResponse(response) {
  const data = await response.json();
  showResponse(data, !response.ok);
  return data;
}

document.querySelector("#upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData();
  const file = document.querySelector("#file-input").files[0];

  if (file) {
    formData.append("file", file);
  }

  const response = await fetch("/api/upload", {
    method: "POST",
    body: formData,
  });
  await readJsonResponse(response);
});

document.querySelector("#clean-button").addEventListener("click", async () => {
  const payload = {
    drop_missing: document.querySelector("#drop-missing").checked,
    drop_duplicates: document.querySelector("#drop-duplicates").checked,
    handle_outliers: document.querySelector("#handle-outliers").checked,
  };

  const response = await fetch("/api/clean", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await readJsonResponse(response);
});

document.querySelector("#analyze-button").addEventListener("click", async () => {
  const columns = document
    .querySelector("#analyze-columns")
    .value.split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  const payload = {
    method: "kmeans",
    columns,
    k: Number(document.querySelector("#cluster-count").value),
  };

  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await readJsonResponse(response);
});

document.querySelectorAll("[data-export-type]").forEach((button) => {
  button.addEventListener("click", async () => {
    const exportType = button.dataset.exportType;
    const response = await fetch(`/api/export?type=${encodeURIComponent(exportType)}`);
    await readJsonResponse(response);
  });
});

document.querySelector("#visual-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const params = new URLSearchParams({
    chart: document.querySelector("#chart-type").value,
    x: document.querySelector("#x-field").value.trim(),
    y: document.querySelector("#y-field").value.trim(),
    color: document.querySelector("#color-field").value.trim(),
  });

  const response = await fetch(`/api/visualize?${params.toString()}`);
  const data = await readJsonResponse(response);

  if (data.figure) {
    Plotly.react(chartEl, data.figure.data, data.figure.layout || {}, { responsive: true });
    return;
  }

  Plotly.purge(chartEl);
  chartEl.textContent = "等待上传、清洗或分析模块接入后生成图表。";
});

chartEl.textContent = "图表将在数据模块接入后显示。";
