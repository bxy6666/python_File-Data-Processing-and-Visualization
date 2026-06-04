const chartEl = document.querySelector("#chart");
const chartDescriptionEl = document.querySelector("#chart-description");
const fileInput = document.querySelector("#file-input");
const fileMetaEl = document.querySelector("#file-meta");
const selectedUploadPanel = document.querySelector("#selected-upload-panel");
const datasetListEl = document.querySelector("#dataset-list");
const processedListEl = document.querySelector("#processed-list");
const datasetSearchInput = document.querySelector("#dataset-search");
const datasetStatusFilter = document.querySelector("#dataset-status-filter");
const datasetPreviewPanel = document.querySelector("#dataset-preview-panel");
const currentDatasetPanel = document.querySelector("#current-dataset-panel");
const workflowStageEls = document.querySelectorAll("[data-flow-stage]");
const clusterDistributionEl = document.querySelector("#cluster-distribution");
const processStateEl = document.querySelector("#process-state");
const predictRowsEl = document.querySelector("#predict-rows");
const predictButtonEl = document.querySelector("#predict-button");
const predictResultEl = document.querySelector("#predict-result");
const predictColumnsEl = document.querySelector("#predict-columns");
const predictExampleEl = document.querySelector("#predict-example");
const predictFillExampleEl = document.querySelector("#predict-fill-example");
const workflowMetrics = {
  rawRows: document.querySelector("#metric-raw-rows"),
  cleanRows: document.querySelector("#metric-clean-rows"),
  removedRows: document.querySelector("#metric-removed-rows"),
  missingChange: document.querySelector("#metric-missing-change"),
  k: document.querySelector("#metric-k"),
  rowsUsed: document.querySelector("#metric-rows-used"),
  featureCount: document.querySelector("#metric-feature-count"),
  inertia: document.querySelector("#metric-inertia"),
};
const chartTypeInput = document.querySelector("#chart-type");
const visualPanel = document.querySelector('[data-step="visual"]');
const chartChoiceButtons = document.querySelectorAll("[data-chart-choice]");
const unavailableLabel = "暂不可用";
const jsonHeaders = { "Content-Type": "application/json" };
const supportedFilePattern = /\.(csv|xls|xlsx)$/i;
let selectedUploadFiles = [];
let currentPredictExampleRows = [];
let currentClusterAxisRanges = {};
let latestDatasets = [];
let latestActiveDataset = null;

const stepStateLabels = {
  idle: "待调用",
  pending: "调用中",
  success: "已完成",
  unavailable: unavailableLabel,
  error: "异常",
};

const apiMessages = {
  NOT_IMPLEMENTED: "该步骤暂不可用，等待功能接入。",
  DATA_NOT_READY: "请先完成上传、清洗或分析后再创建图表。",
  INVALID_CHART: "请选择支持的图表类型。",
  INVALID_FILE: "文件无法读取，请检查格式、编码或内容。",
  NO_FILE: "请选择或拖入一个 CSV / Excel 文件。",
  INVALID_PREDICT_INPUT: "预测输入格式无效，请检查 JSON 内容和字段。",
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

function getStatusTarget() {
  return processStateEl || fileMetaEl || chartDescriptionEl;
}

function showLocalMessage(message, isError = false) {
  const target = getStatusTarget();
  if (!target) {
    return;
  }

  target.textContent = message;
  target.dataset.state = isError ? "error" : "normal";
  target.classList.toggle("error", isError);
  target.classList.toggle("success", !isError);
}

function showApiMessage(data, isError = false) {
  showLocalMessage(apiMessages[data.code] || data["message"] || (isError ? "操作失败。" : "操作完成。"), isError);
}

async function requestJson(url, options = {}, settings = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!settings.silent) {
    showApiMessage(data, !response.ok);
  }
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

function isSupportedFile(file) {
  return Boolean(file && supportedFilePattern.test(file.name));
}

function fileKey(file) {
  return `${file.name}-${file.size}-${file.lastModified}`;
}

function fileExtension(filename = "") {
  return filename.includes(".") ? filename.split(".").pop().toUpperCase() : "FILE";
}

function fileIconClass(filename = "") {
  return /\.(csv|xls|xlsx)$/i.test(filename) ? "table" : "document";
}

function syncFileInputFiles() {
  if (!fileInput || typeof DataTransfer === "undefined") {
    return;
  }

  const dataTransfer = new DataTransfer();
  selectedUploadFiles.forEach((file) => dataTransfer.items.add(file));
  fileInput.files = dataTransfer.files;
}

function updateFileMeta(files = selectedUploadFiles) {
  if (!fileMetaEl) {
    return;
  }

  fileMetaEl.dataset.state = "normal";
  fileMetaEl.classList.remove("error", "success");

  if (!files.length) {
    fileMetaEl.textContent = "尚未选择文件";
    return;
  }

  const totalSize = files.reduce((sum, file) => sum + file.size, 0);
  const firstFile = files[0];
  const suffix = fileExtension(firstFile.name);
  const moreText = files.length > 1 ? ` 等 ${files.length} 个文件` : "";
  fileMetaEl.textContent = `${firstFile.name}${moreText} · ${suffix} · ${formatFileSize(totalSize)}`;
}

function clearSelectedUploadFiles() {
  selectedUploadFiles = [];
  syncFileInputFiles();
  updateFileMeta();
  renderSelectedUploadPanel();
}

function addSelectedFiles(files) {
  const incomingFiles = Array.from(files || []);
  if (!incomingFiles.length) {
    updateFileMeta();
    return false;
  }

  const knownKeys = new Set(selectedUploadFiles.map(fileKey));
  const acceptedFiles = [];
  const rejectedFiles = [];
  const duplicatedFiles = [];

  incomingFiles.forEach((file) => {
    const key = fileKey(file);
    if (!isSupportedFile(file)) {
      rejectedFiles.push(file);
      return;
    }
    if (knownKeys.has(key)) {
      duplicatedFiles.push(file);
      return;
    }

    knownKeys.add(key);
    acceptedFiles.push(file);
  });

  if (acceptedFiles.length) {
    selectedUploadFiles = selectedUploadFiles.concat(acceptedFiles);
    syncFileInputFiles();
    updateFileMeta();
    renderSelectedUploadPanel();
  }

  const messages = [];
  if (acceptedFiles.length) {
    messages.push(`已添加 ${acceptedFiles.length} 个文件`);
  }
  if (duplicatedFiles.length) {
    messages.push(`已忽略 ${duplicatedFiles.length} 个重复文件`);
  }
  if (rejectedFiles.length) {
    messages.push(`已忽略 ${rejectedFiles.length} 个不支持格式`);
  }

  showLocalMessage(messages.join("，") || "请选择 CSV / Excel 文件。", rejectedFiles.length > 0 && !acceptedFiles.length);
  return acceptedFiles.length > 0;
}

function createText(tagName, className, text) {
  const element = document.createElement(tagName);
  if (className) {
    element.className = className;
  }
  element.textContent = text;
  return element;
}

function createUploadEmptyState() {
  const label = document.createElement("label");
  label.className = "upload-dropzone";
  label.htmlFor = "file-input";
  label.innerHTML = `
    <span class="upload-icon">CSV</span>
    <strong>拖入文件或点击选择</strong>
    <small>支持 .csv、.xls、.xlsx，可一次选择多个数据文件</small>
  `;
  return label;
}

function createPendingFileRow(file) {
  const row = document.createElement("div");
  row.className = "selected-file-item";

  const meta = document.createElement("div");
  meta.className = "selected-file-meta";
  meta.appendChild(createText("span", `selected-file-icon ${fileIconClass(file.name)}`, fileExtension(file.name)));

  const copy = document.createElement("div");
  copy.className = "selected-file-copy";
  const name = createText("span", "selected-file-name", file.name);
  name.title = file.name;
  copy.appendChild(name);
  copy.appendChild(createText("span", "selected-file-size", formatFileSize(file.size)));
  meta.appendChild(copy);
  row.appendChild(meta);

  return row;
}

function renderSelectedUploadPanel() {
  if (!selectedUploadPanel) {
    return;
  }

  selectedUploadPanel.innerHTML = "";
  if (!selectedUploadFiles.length) {
    selectedUploadPanel.appendChild(createUploadEmptyState());
    return;
  }

  const panel = document.createElement("div");
  panel.className = "selected-files-panel";

  const header = document.createElement("div");
  header.className = "selected-files-header";
  header.appendChild(createText("h4", "", `已选择数据文件（${selectedUploadFiles.length}）`));
  const clearButton = createText("button", "text-danger-button", "清空");
  clearButton.type = "button";
  clearButton.dataset.uploadAction = "clear";
  header.appendChild(clearButton);
  panel.appendChild(header);

  const list = document.createElement("div");
  list.className = "selected-files-list";
  selectedUploadFiles.forEach((file) => {
    list.appendChild(createPendingFileRow(file));
  });
  panel.appendChild(list);

  const footer = document.createElement("div");
  footer.className = "selected-files-footer";
  footer.appendChild(
    createText(
      "span",
      "selected-files-summary",
      `已选择 ${selectedUploadFiles.length} 个文件 · 总大小 ${formatFileSize(selectedUploadFiles.reduce((sum, file) => sum + file.size, 0))}`
    )
  );

  const actions = document.createElement("div");
  actions.className = "selected-files-actions";
  const addMoreLabel = createText("label", "continue-add-button", "继续添加文件");
  addMoreLabel.htmlFor = "file-input";
  actions.appendChild(addMoreLabel);

  const submitButton = createText("button", "upload-submit-button", "上传数据");
  submitButton.type = "submit";
  actions.appendChild(submitButton);
  footer.appendChild(actions);
  panel.appendChild(footer);
  selectedUploadPanel.appendChild(panel);
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function addBadge(container, text, variant = "") {
  const badge = createText("span", `dataset-badge ${variant}`.trim(), text);
  container.appendChild(badge);
}

function datasetMetaText(dataset) {
  const metadata = dataset.metadata || {};
  return `${formatNumber(metadata.rows)} 行 · ${formatNumber(metadata.column_count)} 列 · 缺失 ${formatNumber(metadata.missing_values)}`;
}

function datasetStatusKey(dataset) {
  const status = dataset.status || {};
  if (status.has_analysis_result) {
    return "analyzed";
  }
  if (status.has_cleaned_dataset) {
    return "cleaned";
  }
  return "raw";
}

function datasetMatchesFilters(dataset) {
  const keyword = (datasetSearchInput?.value || "").trim().toLowerCase();
  const statusFilter = datasetStatusFilter?.value || "all";
  const metadata = dataset.metadata || {};
  const searchableText = [
    dataset.filename,
    metadata.format,
    ...(metadata.columns || []),
  ].join(" ").toLowerCase();

  if (keyword && !searchableText.includes(keyword)) {
    return false;
  }

  if (statusFilter === "all") {
    return true;
  }

  return datasetStatusKey(dataset) === statusFilter;
}

function filteredDatasets() {
  return latestDatasets.filter(datasetMatchesFilters);
}

function appendDatasetBadges(container, dataset) {
  if (dataset.is_active) {
    addBadge(container, "当前", "active");
  }
  if (dataset.status?.has_cleaned_dataset) {
    addBadge(container, "已清洗", "success");
  }
  if (dataset.status?.has_analysis_result) {
    addBadge(container, "已分析", "success");
  }
  if (!dataset.status?.has_cleaned_dataset && !dataset.status?.has_analysis_result) {
    addBadge(container, "待处理");
  }
}

function createDatasetRow(dataset) {
  const row = document.createElement("article");
  row.className = "selected-file-item dataset-file-item";
  row.dataset.action = "activate";
  row.dataset.datasetId = dataset.id;
  row.tabIndex = 0;
  if (dataset.is_active) {
    row.classList.add("is-active");
  }

  const meta = document.createElement("div");
  meta.className = "selected-file-meta";

  const icon = createText("span", `selected-file-icon ${fileIconClass(dataset.filename)}`, fileExtension(dataset.filename));
  meta.appendChild(icon);

  const copy = document.createElement("div");
  copy.className = "selected-file-copy";
  const name = createText("span", "selected-file-name", dataset.filename || "未命名数据");
  name.title = dataset.filename || "未命名数据";
  copy.appendChild(name);
  copy.appendChild(createText("span", "selected-file-size", datasetMetaText(dataset)));

  meta.appendChild(copy);
  row.appendChild(meta);

  const badges = document.createElement("div");
  badges.className = "dataset-badges dataset-row-status";
  appendDatasetBadges(badges, dataset);
  row.appendChild(badges);

  return row;
}

function choosePanelDataset(datasets) {
  return datasets.find((dataset) => dataset.is_active) || datasets[0];
}

function createPanelButton(text, action, dataset, options = {}) {
  const button = createText("button", `secondary-button ${options.danger ? "danger" : ""}`.trim(), text);
  button.type = "button";
  button.dataset.action = action;
  if (dataset) {
    button.dataset.datasetId = dataset.id;
    button.dataset.filename = dataset.filename || "该文件";
  }
  if (options.target) {
    button.dataset.target = options.target;
  }
  if (options.exportType) {
    button.dataset.exportType = options.exportType;
  }
  if (options.title) {
    button.title = options.title;
  }
  if (options.disabled) {
    button.disabled = true;
    button.title = options.title || "当前文件暂未生成该结果";
  }
  return button;
}

function createPanelFooter(datasets, processedOnly = false) {
  const targetDataset = choosePanelDataset(datasets);
  const footer = document.createElement("div");
  footer.className = "selected-files-footer";

  const metadata = targetDataset?.metadata || {};
  const summary = createText(
    "span",
    "selected-files-summary",
    targetDataset
      ? `${datasets.length} 个文件 · 当前 ${targetDataset.filename || "未命名数据"} · ${formatNumber(metadata.rows)} 行`
      : "暂无可操作文件"
  );
  footer.appendChild(summary);

  if (!targetDataset) {
    return footer;
  }

  const actions = document.createElement("div");
  actions.className = "selected-files-actions";

  if (!processedOnly) {
    actions.appendChild(
      createPanelButton("处理", "activate-go", targetDataset, {
        target: "/workflow",
        title: "进入清洗与分析流程",
      })
    );
    actions.appendChild(createPanelButton("图表", "activate-go", targetDataset, { target: "/visualization" }));
    actions.appendChild(createPanelButton("删除", "delete", targetDataset, { danger: true }));
    footer.appendChild(actions);
    return footer;
  }

  const exportType = targetDataset.status?.has_analysis_result ? "result" : "cleaned";
  actions.appendChild(createPanelButton("图表", "activate-go", targetDataset, { target: "/visualization" }));
  actions.appendChild(
    createPanelButton("导出", "export", targetDataset, {
      exportType,
      disabled: !targetDataset.status?.has_cleaned_dataset && !targetDataset.status?.has_analysis_result,
      title: targetDataset.status?.has_analysis_result ? "导出分析结果" : "导出清洗数据",
    })
  );
  actions.appendChild(createPanelButton("删除", "delete", targetDataset, { danger: true }));

  footer.appendChild(actions);
  return footer;
}

function createDatasetPanel(datasets, title, emptyText, processedOnly = false) {
  const panel = document.createElement("div");
  panel.className = "selected-files-panel dataset-files-panel";

  const header = document.createElement("div");
  header.className = "selected-files-header";
  header.appendChild(createText("h4", "", `${title}（${datasets.length}）`));
  if (datasets.length) {
    const clearButton = createText("button", "text-danger-button", "清空");
    clearButton.type = "button";
    clearButton.dataset.action = "clear-datasets";
    clearButton.dataset.datasetIds = datasets.map((dataset) => dataset.id).join(",");
    clearButton.dataset.panelName = title;
    header.appendChild(clearButton);
  }
  panel.appendChild(header);

  if (!datasets.length) {
    panel.appendChild(createText("div", "empty-state compact", emptyText));
    return panel;
  }

  const list = document.createElement("div");
  list.className = "selected-files-list";
  datasets.forEach((dataset) => {
    list.appendChild(createDatasetRow(dataset, processedOnly));
  });
  panel.appendChild(list);
  panel.appendChild(createPanelFooter(datasets, processedOnly));
  return panel;
}

function renderDatasetList(container, datasets, emptyText, processedOnly = false) {
  if (!container) {
    return;
  }

  container.innerHTML = "";
  container.appendChild(createDatasetPanel(datasets, processedOnly ? "处理后文件" : "上传文件", emptyText, processedOnly));
}

function renderCurrentDatasetPanel(activeDataset) {
  if (!currentDatasetPanel) {
    return;
  }

  currentDatasetPanel.innerHTML = "";
  currentDatasetPanel.classList.add("current-file-panel");

  if (!activeDataset) {
    const emptyCopy = document.createElement("div");
    emptyCopy.className = "current-file-copy";
    emptyCopy.appendChild(createText("p", "eyebrow", "Selected File"));
    emptyCopy.appendChild(createText("h2", "", "未选择数据文件"));
    emptyCopy.appendChild(createText("p", "", "请先添加新文件后再进行清洗或分析。"));
    currentDatasetPanel.appendChild(emptyCopy);

    const addLink = createText("a", "continue-add-button current-add-link", "添加新文件");
    addLink.href = "/documents";
    currentDatasetPanel.appendChild(addLink);
    return;
  }

  const fileRow = document.createElement("article");
  fileRow.className = "selected-file-item current-file-item";

  const meta = document.createElement("div");
  meta.className = "selected-file-meta";
  meta.appendChild(createText("span", `selected-file-icon ${fileIconClass(activeDataset.filename)}`, fileExtension(activeDataset.filename)));

  const copy = document.createElement("div");
  copy.className = "selected-file-copy";
  const name = createText("span", "selected-file-name", activeDataset.filename || "当前数据");
  name.title = activeDataset.filename || "当前数据";
  copy.appendChild(name);
  copy.appendChild(createText("span", "selected-file-size", datasetMetaText(activeDataset)));
  meta.appendChild(copy);
  fileRow.appendChild(meta);
  currentDatasetPanel.appendChild(fileRow);

  const actions = document.createElement("div");
  actions.className = "current-file-actions";

  const removeButton = createText("button", "secondary-button danger", "移除");
  removeButton.type = "button";
  removeButton.dataset.action = "delete";
  removeButton.dataset.datasetId = activeDataset.id;
  removeButton.dataset.filename = activeDataset.filename || "该文件";
  actions.appendChild(removeButton);

  const addLink = createText("a", "continue-add-button current-add-link", "添加新文件");
  addLink.href = "/documents";
  actions.appendChild(addLink);

  currentDatasetPanel.appendChild(actions);
}

function setElementText(element, value) {
  if (element) {
    element.textContent = value;
  }
}

function setProcessState(text, isError = false) {
  if (!processStateEl) {
    return;
  }

  processStateEl.textContent = text;
  processStateEl.dataset.state = isError ? "error" : "normal";
  processStateEl.classList.toggle("error", isError);
  processStateEl.classList.toggle("success", !isError);
}

function formatMetric(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) {
    return String(value);
  }

  if (Number.isInteger(numberValue)) {
    return String(numberValue);
  }

  return numberValue.toFixed(2);
}

function setWorkflowMetric(metricName, value) {
  setElementText(workflowMetrics[metricName], formatMetric(value));
}

function clearWorkflowMetrics() {
  Object.keys(workflowMetrics).forEach((metricName) => {
    setWorkflowMetric(metricName, "-");
  });
  renderClusterDistribution([]);
}

function setFlowStage(stageName, state, statusText, metaText) {
  const stageEl = document.querySelector(`[data-flow-stage="${stageName}"]`);
  if (!stageEl) {
    return;
  }

  stageEl.dataset.state = state;
  setElementText(stageEl.querySelector("[data-flow-status]"), statusText);
  setElementText(stageEl.querySelector("[data-flow-meta]"), metaText);
}

function countColumns(metadata = {}) {
  if (Number.isFinite(Number(metadata.column_count))) {
    return Number(metadata.column_count);
  }
  if (Array.isArray(metadata.columns)) {
    return metadata.columns.length;
  }
  return metadata.columns || "-";
}

function featureCount(columns) {
  if (Array.isArray(columns)) {
    return columns.length;
  }
  return columns || "-";
}

function getClusterCenterEntries(cluster, maxAxes = 8) {
  const center = (cluster && cluster.center) || {};
  const entries = Object.entries(center)
    .filter(([, value]) => Number.isFinite(Number(value)))
    .map(([name, value]) => ({ name, value: Number(value) }));

  return entries.slice(0, maxAxes);
}

function buildClusterAxisRanges(clusters = []) {
  const axisRanges = {};

  clusters.forEach((cluster) => {
    const center = (cluster && cluster.center) || {};
    Object.entries(center).forEach(([name, value]) => {
      const numeric = Number(value);
      if (!Number.isFinite(numeric)) {
        return;
      }

      if (!(name in axisRanges)) {
        axisRanges[name] = { min: numeric, max: numeric };
        return;
      }

      if (numeric < axisRanges[name].min) {
        axisRanges[name].min = numeric;
      }
      if (numeric > axisRanges[name].max) {
        axisRanges[name].max = numeric;
      }
    });
  });

  return axisRanges;
}

function buildRadarSvg(entries, axisRanges = {}) {
  const size = 260;
  const cx = size / 2;
  const cy = size / 2;
  const radius = 92;
  const levels = 4;
  const axisCount = entries.length;

  if (!axisCount) {
    return '<p class="cluster-drawer-empty">当前类别缺少可绘制的数值特征。</p>';
  }

  const normalized = entries.map((item) => {
    const axisRange = axisRanges[item.name] || {};
    const axisMin = Number(axisRange.min);
    const axisMax = Number(axisRange.max);
    if (!Number.isFinite(axisMin) || !Number.isFinite(axisMax)) {
      return 0;
    }

    const denominator = axisMax - axisMin;
    if (denominator === 0) {
      return 1;
    }

    const ratio = (item.value - axisMin) / denominator;
    return Math.max(0, Math.min(1, ratio));
  });

  const points = normalized
    .map((value, index) => {
      const angle = -Math.PI / 2 + (index / axisCount) * Math.PI * 2;
      const x = cx + Math.cos(angle) * (radius * value);
      const y = cy + Math.sin(angle) * (radius * value);
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");

  const rings = [];
  for (let level = 1; level <= levels; level += 1) {
    const levelRadius = radius * (level / levels);
    const ringPoints = entries
      .map((_, index) => {
        const angle = -Math.PI / 2 + (index / axisCount) * Math.PI * 2;
        const x = cx + Math.cos(angle) * levelRadius;
        const y = cy + Math.sin(angle) * levelRadius;
        return `${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(" ");
    rings.push(`<polygon class="radar-ring" points="${ringPoints}"/>`);
  }

  const axes = entries
    .map((item, index) => {
      const angle = -Math.PI / 2 + (index / axisCount) * Math.PI * 2;
      const x = cx + Math.cos(angle) * radius;
      const y = cy + Math.sin(angle) * radius;
      const labelX = cx + Math.cos(angle) * (radius + 18);
      const labelY = cy + Math.sin(angle) * (radius + 18);
      return `
        <line class="radar-axis" x1="${cx}" y1="${cy}" x2="${x.toFixed(2)}" y2="${y.toFixed(2)}" />
        <text class="radar-label" x="${labelX.toFixed(2)}" y="${labelY.toFixed(2)}" text-anchor="middle">${item.name}</text>
      `;
    })
    .join("");

  return `
    <svg class="cluster-radar" viewBox="0 0 ${size} ${size}" role="img" aria-label="类别特征雷达图">
      <g>${rings.join("")}</g>
      <g>${axes}</g>
      <polygon class="radar-shape" points="${points}" />
      <circle class="radar-center" cx="${cx}" cy="${cy}" r="3" />
    </svg>
  `;
}

function createClusterDrawer(cluster, axisRanges = {}) {
  const drawer = document.createElement("div");
  drawer.className = "cluster-drawer";
  drawer.hidden = true;

  const body = document.createElement("div");
  body.className = "cluster-drawer-body";

  const chart = document.createElement("div");
  chart.className = "cluster-drawer-chart";

  const values = document.createElement("div");
  values.className = "cluster-drawer-values";

  const entries = getClusterCenterEntries(cluster);
  chart.innerHTML = buildRadarSvg(entries, axisRanges);

  if (entries.length) {
    values.innerHTML = entries
      .map((item) => {
        const axisRange = axisRanges[item.name] || {};
        const axisMin = Number(axisRange.min);
        const axisMax = Number(axisRange.max);
        const axisMinText = Number.isFinite(axisMin) ? axisMin.toFixed(3) : "-";
        const axisMaxText = Number.isFinite(axisMax) ? axisMax.toFixed(3) : "-";
        return `<div class="cluster-drawer-item"><span>${item.name}</span><strong>${item.value.toFixed(3)} (${axisMinText} ~ ${axisMaxText})</strong></div>`;
      })
      .join("");
  } else {
    values.innerHTML = '<p class="cluster-drawer-empty">无可展示的中心特征。</p>';
  }

  body.appendChild(chart);
  body.appendChild(values);
  drawer.appendChild(body);
  return drawer;
}

function renderClusterDistribution(clusters = []) {
  if (!clusterDistributionEl) {
    return;
  }

  clusterDistributionEl.innerHTML = "";
  if (!Array.isArray(clusters) || !clusters.length) {
    currentClusterAxisRanges = {};
    clusterDistributionEl.appendChild(createText("p", "", "完成分析后显示聚类分布。"));
    return;
  }

  const counts = clusters.map((cluster) => Number(cluster.count) || 0);
  const maxCount = Math.max(...counts, 1);
  currentClusterAxisRanges = buildClusterAxisRanges(clusters);

  const tip = createText("p", "cluster-hint", "点击类别可展开该簇的特征雷达图");
  clusterDistributionEl.appendChild(tip);

  clusters.forEach((cluster, index) => {
    const count = Number(cluster.count) || 0;
    const item = document.createElement("article");
    item.className = "cluster-item";

    const row = document.createElement("button");
    row.type = "button";
    row.className = "cluster-row cluster-row-button";
    row.title = `查看类别 ${formatNumber(cluster.cluster)} 特征`;
    row.setAttribute("aria-expanded", "false");
    row.setAttribute("aria-controls", `cluster-drawer-${index}`);

    row.appendChild(createText("span", "cluster-label", `类别 ${formatNumber(cluster.cluster)}`));

    const track = document.createElement("span");
    track.className = "cluster-track";
    const bar = document.createElement("span");
    bar.className = "cluster-bar";
    bar.style.width = `${Math.max(6, (count / maxCount) * 100)}%`;
    track.appendChild(bar);
    row.appendChild(track);

    row.appendChild(createText("span", "cluster-count", `${formatNumber(count)} 行`));

    const drawer = createClusterDrawer(cluster, currentClusterAxisRanges);
    drawer.id = `cluster-drawer-${index}`;

    row.addEventListener("click", () => {
      const isOpen = row.getAttribute("aria-expanded") === "true";

      if (isOpen) {
        row.setAttribute("aria-expanded", "false");
        item.classList.remove("is-open");
        drawer.hidden = true;
        return;
      }

      row.setAttribute("aria-expanded", "true");
      item.classList.add("is-open");
      drawer.hidden = false;
    });

    item.appendChild(row);
    item.appendChild(drawer);
    clusterDistributionEl.appendChild(item);
  });
}

function renderWorkflowProgress(activeDataset) {
  if (!workflowStageEls.length && !clusterDistributionEl) {
    updatePredictGuidance(activeDataset);
    return;
  }

  if (!activeDataset) {
    setFlowStage("upload", "active", "等待文件", "请先添加一个 CSV 或 Excel 文件");
    setFlowStage("clean", "pending", "等待上传", "上传后可选择清洗规则");
    setFlowStage("analyze", "pending", "等待清洗", "清洗完成后可执行 K-Means");
    setFlowStage("export", "pending", "等待结果", "完成清洗或分析后可导出");
    setProcessState("请先添加新文件后开始处理。");
    clearWorkflowMetrics();
    updatePredictGuidance(activeDataset);
    return;
  }

  const status = activeDataset.status || {};
  const metadata = activeDataset.metadata || {};
  const cleanSummary = activeDataset.clean_summary || {};
  const analysisSummary = activeDataset.analysis_summary || {};
  const rawRows = metadata.rows;
  const rawColumns = countColumns(metadata);
  const rawMissing = metadata.missing_values;

  setFlowStage(
    "upload",
    "done",
    "已上传",
    `${formatMetric(rawRows)} 行 · ${formatMetric(rawColumns)} 列 · 缺失 ${formatMetric(rawMissing)}`
  );

  if (status.has_cleaned_dataset) {
    setFlowStage(
      "clean",
      "done",
      "已清洗",
      `保留 ${formatMetric(cleanSummary.output_rows)} 行 · 移除 ${formatMetric(cleanSummary.removed_rows)} 行`
    );
  } else {
    setFlowStage("clean", "active", "等待清洗", "点击开始处理后自动执行");
  }

  if (status.has_analysis_result) {
    setFlowStage(
      "analyze",
      "done",
      `已聚类 K=${formatMetric(analysisSummary.k)}`,
      `使用 ${formatMetric(analysisSummary.rows_used)} 行 · ${formatMetric(featureCount(analysisSummary.columns))} 个字段`
    );
  } else if (status.has_cleaned_dataset) {
    setFlowStage("analyze", "active", "等待分析", "开始处理会在清洗后继续分析");
  } else {
    setFlowStage("analyze", "pending", "等待清洗", "清洗完成后可执行 K-Means");
  }

  if (status.has_analysis_result) {
    setFlowStage("export", "active", "可导出分析结果", "下载 JSON 或进入图表分析");
    setProcessState("当前文件已完成清洗和分析，可导出或进入图表分析。");
  } else if (status.has_cleaned_dataset) {
    setFlowStage("export", "active", "可导出清洗数据", "下载 CSV 或继续分析");
    setProcessState("当前文件已清洗，点击开始处理会重新清洗并继续分析。");
  } else {
    setFlowStage("export", "pending", "等待结果", "完成清洗或分析后可导出");
    setProcessState("确认清洗规则和 k 值后，点击开始处理。");
  }

  setWorkflowMetric("rawRows", rawRows);
  setWorkflowMetric("cleanRows", status.has_cleaned_dataset ? cleanSummary.output_rows : "-");
  setWorkflowMetric("removedRows", status.has_cleaned_dataset ? cleanSummary.removed_rows : "-");
  setElementText(
    workflowMetrics.missingChange,
    status.has_cleaned_dataset
      ? `${formatMetric(cleanSummary.missing_values_before)} -> ${formatMetric(cleanSummary.missing_values_after)}`
      : "-"
  );
  setWorkflowMetric("k", status.has_analysis_result ? analysisSummary.k : "-");
  setWorkflowMetric("rowsUsed", status.has_analysis_result ? analysisSummary.rows_used : "-");
  setWorkflowMetric("featureCount", status.has_analysis_result ? featureCount(analysisSummary.columns) : "-");
  setWorkflowMetric("inertia", status.has_analysis_result ? analysisSummary.inertia : "-");
  renderClusterDistribution(status.has_analysis_result ? analysisSummary.clusters : []);
  updatePredictGuidance(activeDataset);
}

function renderDatasetViews() {
  const datasets = filteredDatasets();
  const processedDatasets = datasets.filter(
    (dataset) => dataset.status?.has_cleaned_dataset || dataset.status?.has_analysis_result
  );

  renderDatasetList(datasetListEl, datasets, "暂无上传文件。");
  renderDatasetList(processedListEl, processedDatasets, "暂无处理结果。", true);
  renderCurrentDatasetPanel(latestActiveDataset);
  renderWorkflowProgress(latestActiveDataset);
}

function renderDatasetPreviewEmpty(message = "暂无可预览数据。") {
  if (!datasetPreviewPanel) {
    return;
  }

  datasetPreviewPanel.innerHTML = "";
  const heading = document.createElement("div");
  heading.className = "section-heading compact";
  heading.appendChild(createText("p", "eyebrow", "Preview"));
  heading.appendChild(createText("h2", "", "当前文件预览"));
  heading.appendChild(createText("p", "", "前 10 行数据与清洗建议。"));
  datasetPreviewPanel.appendChild(heading);
  datasetPreviewPanel.appendChild(createText("div", "empty-state compact", message));
}

function renderDatasetPreviewLoading(dataset) {
  renderDatasetPreviewEmpty(`${dataset?.filename || "当前文件"} 正在加载预览...`);
}

function appendPreviewMetric(container, label, value) {
  const item = document.createElement("div");
  item.className = "preview-metric";
  item.appendChild(createText("span", "", label));
  item.appendChild(createText("strong", "", formatMetric(value)));
  container.appendChild(item);
}

function ruleLabel(rule) {
  return {
    drop_missing: "删除缺失行",
    drop_duplicates: "删除重复行",
    handle_outliers: "处理异常值",
  }[rule] || rule;
}

function appendPreviewSuggestions(container, profile) {
  const suggestions = document.createElement("div");
  suggestions.className = "preview-suggestions";
  suggestions.appendChild(createText("h3", "", "清洗建议"));

  const ruleEntries = Object.entries(profile?.recommended_rules || {}).filter(([, enabled]) => enabled);
  if (!ruleEntries.length) {
    suggestions.appendChild(createText("p", "", "当前数据未发现明显缺失、重复或 IQR 异常值。"));
    container.appendChild(suggestions);
    return;
  }

  const list = document.createElement("div");
  list.className = "dataset-badges inline";
  ruleEntries.forEach(([rule]) => {
    addBadge(list, ruleLabel(rule), "success");
  });
  suggestions.appendChild(list);
  container.appendChild(suggestions);
}

function renderDatasetPreview(preview, profile, dataset) {
  if (!datasetPreviewPanel) {
    return;
  }

  datasetPreviewPanel.innerHTML = "";
  const previewTypeText = preview.type === "cleaned" ? "清洗后数据" : "原始数据";

  const heading = document.createElement("div");
  heading.className = "section-heading compact";
  heading.appendChild(createText("p", "eyebrow", "Preview"));
  heading.appendChild(createText("h2", "", dataset?.filename || "当前文件预览"));
  heading.appendChild(createText("p", "", `${previewTypeText} · ${formatNumber(preview.total_rows)} 行 · ${formatNumber(preview.total_columns)} 列`));
  datasetPreviewPanel.appendChild(heading);

  const metrics = document.createElement("div");
  metrics.className = "preview-metrics";
  appendPreviewMetric(metrics, "缺失值", profile?.missing_values ?? "-");
  appendPreviewMetric(metrics, "重复行", profile?.duplicate_rows ?? "-");
  appendPreviewMetric(metrics, "异常行", profile?.outlier_rows ?? "-");
  datasetPreviewPanel.appendChild(metrics);

  appendPreviewSuggestions(datasetPreviewPanel, profile);

  const tableWrap = document.createElement("div");
  tableWrap.className = "preview-table-wrap";
  const table = document.createElement("table");
  table.className = "preview-table";

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  preview.columns.forEach((column) => {
    headRow.appendChild(createText("th", "", column));
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  preview.rows.forEach((row) => {
    const tr = document.createElement("tr");
    preview.columns.forEach((column) => {
      const value = row[column];
      tr.appendChild(createText("td", "", value === null || value === undefined || value === "" ? "-" : String(value)));
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  tableWrap.appendChild(table);
  datasetPreviewPanel.appendChild(tableWrap);
}

async function loadDatasetPreview(dataset) {
  if (!datasetPreviewPanel) {
    return;
  }

  if (!dataset) {
    renderDatasetPreviewEmpty();
    return;
  }

  const previewType = dataset.status?.has_cleaned_dataset ? "cleaned" : "raw";
  renderDatasetPreviewLoading(dataset);

  const previewResult = await requestJson(
    `/api/datasets/${encodeURIComponent(dataset.id)}/preview?type=${previewType}&limit=10`,
    {},
    { silent: true }
  );
  if (!previewResult.response.ok) {
    renderDatasetPreviewEmpty(previewResult.data.message || "预览数据暂不可用。");
    return;
  }

  const profileResult = await requestJson(
    `/api/datasets/${encodeURIComponent(dataset.id)}/clean-profile`,
    {},
    { silent: true }
  );
  const profile = profileResult.response.ok ? profileResult.data.data?.profile : null;
  renderDatasetPreview(previewResult.data.data?.preview, profile, dataset);
}

async function loadDatasets() {
  if (!datasetListEl && !processedListEl && !currentDatasetPanel && !datasetPreviewPanel) {
    return;
  }

  const { response, data } = await requestJson("/api/datasets", {}, { silent: true });
  if (!response.ok) {
    return;
  }

  const payload = data.data || {};
  latestDatasets = payload.datasets || [];
  latestActiveDataset = payload.active_dataset || null;
  const datasets = filteredDatasets();
  const processedDatasets = datasets.filter(
    (dataset) => dataset.status?.has_cleaned_dataset || dataset.status?.has_analysis_result
  );

  renderDatasetList(datasetListEl, datasets, "暂无上传文件。");
  renderDatasetList(processedListEl, processedDatasets, "暂无处理结果。", true);
  renderCurrentDatasetPanel(latestActiveDataset);
  renderWorkflowProgress(latestActiveDataset);
  await loadDatasetPreview(latestActiveDataset);
}

function triggerDownload(exportData) {
  const content = exportData?.content;
  if (content === undefined || content === null) {
    return;
  }

  const filename = exportData.filename || "dataflow-export.txt";
  const type = exportData.format === "json" ? "application/json;charset=utf-8" : "text/csv;charset=utf-8";
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function exportData(exportType, datasetId) {
  const params = new URLSearchParams({ type: exportType });
  if (datasetId) {
    params.set("dataset_id", datasetId);
  }

  const { response, data } = await requestJson(`/api/export?${params.toString()}`);
  if (response.ok) {
    triggerDownload(data.data?.export);
  }
  return { response, data };
}

async function activateDataset(datasetId, target) {
  const { response } = await requestJson(`/api/datasets/${encodeURIComponent(datasetId)}/activate`, {
    method: "POST",
  });

  if (response.ok && target) {
    window.location.href = target;
    return;
  }

  if (response.ok) {
    await loadDatasets();
  }
}

async function deleteDataset(datasetId, filename) {
  const confirmed = window.confirm(`确定删除「${filename || "该文件"}」吗？删除后对应清洗和分析结果也会移除。`);
  if (!confirmed) {
    return;
  }

  const { response } = await requestJson(`/api/datasets/${encodeURIComponent(datasetId)}`, {
    method: "DELETE",
  });

  if (response.ok) {
    await loadDatasets();
  }
}

async function deleteDatasets(datasetIds, panelName) {
  const ids = datasetIds.filter(Boolean);
  if (!ids.length) {
    return;
  }

  const confirmed = window.confirm(`确定清空「${panelName || "文件列表"}」中的 ${ids.length} 个文件吗？对应处理结果也会移除。`);
  if (!confirmed) {
    return;
  }

  for (const datasetId of ids) {
    await requestJson(`/api/datasets/${encodeURIComponent(datasetId)}`, { method: "DELETE" }, { silent: true });
  }
  showLocalMessage(`已清空 ${ids.length} 个文件。`);
  await loadDatasets();
}

async function handleDatasetAction(event) {
  const target = event.target.closest("[data-action], [data-export-type]");
  if (!target) {
    return;
  }

  if (target.disabled) {
    return;
  }

  const exportType = target.dataset.exportType;
  if (exportType) {
    await exportData(exportType, target.dataset.datasetId);
    return;
  }

  const action = target.dataset.action;
  if (action === "activate") {
    await activateDataset(target.dataset.datasetId);
  }

  if (action === "activate-go") {
    await activateDataset(target.dataset.datasetId, target.dataset.target);
  }

  if (action === "delete") {
    await deleteDataset(target.dataset.datasetId, target.dataset.filename);
  }

  if (action === "clear-datasets") {
    await deleteDatasets((target.dataset.datasetIds || "").split(","), target.dataset.panelName);
  }
}

if (fileInput) {
  fileInput.addEventListener("change", () => {
    addSelectedFiles(fileInput.files);
    fileInput.value = "";
  });
}

if (selectedUploadPanel && fileInput) {
  ["dragenter", "dragover"].forEach((eventName) => {
    selectedUploadPanel.addEventListener(eventName, (event) => {
      event.preventDefault();
      selectedUploadPanel.classList.add("is-dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    selectedUploadPanel.addEventListener(eventName, (event) => {
      event.preventDefault();
      selectedUploadPanel.classList.remove("is-dragover");
    });
  });

  selectedUploadPanel.addEventListener("drop", (event) => {
    addSelectedFiles(event.dataTransfer?.files);
  });

  selectedUploadPanel.addEventListener("click", (event) => {
    const target = event.target.closest("[data-upload-action]");
    if (!target) {
      return;
    }

    if (target.dataset.uploadAction === "clear") {
      clearSelectedUploadFiles();
      showLocalMessage("已清空待上传文件。");
    }

  });
}

const uploadForm = document.querySelector("#upload-form");
if (uploadForm) {
  uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setStepState("upload", "pending");

    if (!selectedUploadFiles.length) {
      const data = { code: "NO_FILE", message: "请选择或拖入一个 CSV / Excel 文件。" };
      showApiMessage(data, true);
      setStepState("upload", "error", "未选择文件");
      return;
    }

    for (const file of selectedUploadFiles) {
      const formData = new FormData();
      formData.append("file", file);
      const { response } = await requestJson("/api/upload", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        finishStep("upload", response, unavailableLabel);
        return;
      }
    }

    setStepState("upload", "success", "已上传");
    clearSelectedUploadFiles();
    await loadDatasets();
  });
}

function getCleanPayload() {
  return {
    drop_missing: document.querySelector("#drop-missing")?.checked || false,
    drop_duplicates: document.querySelector("#drop-duplicates")?.checked || false,
    handle_outliers: document.querySelector("#handle-outliers")?.checked || false,
  };
}

function getAnalyzePayload() {
  return {
    method: "kmeans",
    k: Number(document.querySelector("#cluster-count")?.value || 3),
  };
}

function buildPredictExampleRows(columns = []) {
  if (!Array.isArray(columns) || !columns.length) {
    return [];
  }

  const rowA = {};
  const rowB = {};
  columns.forEach((column, index) => {
    rowA[column] = Number((10 + (index + 1) * 2.5).toFixed(2));
    rowB[column] = Number((30 + (index + 1) * 3.5).toFixed(2));
  });

  return [rowA, rowB];
}

function updatePredictGuidance(activeDataset) {
  if (!predictColumnsEl && !predictExampleEl && !predictRowsEl && !predictFillExampleEl) {
    return;
  }

  const columns = activeDataset?.analysis_summary?.columns;
  const hasColumns = Array.isArray(columns) && columns.length > 0;

  if (!hasColumns) {
    currentPredictExampleRows = [];
    if (predictColumnsEl) {
      predictColumnsEl.textContent = "预测所需属性：请先完成 K-Means 分析后自动显示。";
    }
    if (predictExampleEl) {
      predictExampleEl.textContent = "示例会在完成分析后自动生成。";
    }
    if (predictRowsEl) {
      predictRowsEl.placeholder = '[{"sales": 15, "profit": 2.3}, {"sales": 75, "profit": 9.8}]';
    }
    if (predictFillExampleEl) {
      predictFillExampleEl.disabled = true;
    }
    return;
  }

  currentPredictExampleRows = buildPredictExampleRows(columns);
  const prettyExample = JSON.stringify(currentPredictExampleRows, null, 2);

  if (predictColumnsEl) {
    predictColumnsEl.textContent = `预测所需属性：${columns.join("、")}`;
  }
  if (predictExampleEl) {
    predictExampleEl.textContent = prettyExample;
  }
  if (predictRowsEl) {
    predictRowsEl.placeholder = prettyExample;
  }
  if (predictFillExampleEl) {
    predictFillExampleEl.disabled = false;
  }
}

function parsePredictRows() {
  const rawText = predictRowsEl?.value?.trim() || "";
  if (!rawText) {
    throw new Error("请输入预测样本 JSON 数组");
  }

  let rows;
  try {
    rows = JSON.parse(rawText);
  } catch (_error) {
    throw new Error("JSON 格式不正确，请输入数组，例如 [{\"sales\": 10, \"profit\": 2}] ");
  }

  if (!Array.isArray(rows) || !rows.length) {
    throw new Error("预测输入必须是非空 JSON 数组");
  }

  return rows;
}

function renderPredictResult(data) {
  if (!predictResultEl) {
    return;
  }

  const summary = data?.data?.summary || {};
  const result = data?.data?.result || {};
  const rows = Array.isArray(result.predictions) ? result.predictions : [];

  const lines = [];
  lines.push(`预测完成：使用 ${summary.rows_used ?? "-"} 行，跳过 ${summary.rows_skipped ?? "-"} 行`);
  lines.push(`字段：${Array.isArray(summary.columns) ? summary.columns.join(", ") : "-"}`);
  lines.push("预测结果：");
  rows.slice(0, 20).forEach((item) => {
    lines.push(`- row_index=${item.row_index}, cluster=${item.cluster}, distance=${item.distance}`);
  });

  if (rows.length > 20) {
    lines.push(`... 其余 ${rows.length - 20} 条已省略`);
  }

  predictResultEl.textContent = lines.join("\n");
}

async function runCleanStep() {
  setStepState("clean", "pending");
  setStepState("analyze", "idle", "等待清洗");
  setStepState("export", "idle", "待调用");
  setFlowStage("clean", "active", "清洗中", "正在应用缺失、重复和异常处理规则");
  setFlowStage("analyze", "pending", "等待清洗", "清洗成功后自动开始分析");
  setFlowStage("export", "pending", "等待结果", "处理完成后可导出");
  setProcessState("正在清洗数据...");

  const { response } = await postJson("/api/clean", getCleanPayload());
  finishStep("clean", response, "已清洗");

  if (response.ok) {
    await loadDatasets();
  } else {
    setFlowStage("clean", "error", "清洗失败", "请检查当前文件和清洗规则");
    setProcessState("清洗失败，分析未执行。", true);
  }

  return response;
}

async function runAnalyzeStep() {
  setStepState("analyze", "pending");
  setFlowStage("analyze", "active", "分析中", "正在计算 K-Means 聚类");
  setProcessState("清洗完成，正在进行 K-Means 分析...");

  const { response } = await postJson("/api/analyze", getAnalyzePayload());
  finishStep("analyze", response, "已分析");

  if (response.ok) {
    await loadDatasets();
    setFlowStage("export", "active", "可导出分析结果", "下载 JSON 或进入图表分析");
    setProcessState("处理完成，可导出结果或进入图表分析。");
  } else {
    setFlowStage("analyze", "error", "分析失败", "请检查数据是否包含可分析数值字段");
    setProcessState("分析失败，请检查数据字段或 k 值设置。", true);
  }

  return response;
}

async function runPredictStep() {
  if (!predictRowsEl || !predictResultEl) {
    return;
  }

  let rows;
  try {
    rows = parsePredictRows();
  } catch (error) {
    setStepState("predict", "error", "输入错误");
    predictResultEl.textContent = error.message;
    showLocalMessage(error.message, true);
    return;
  }

  setStepState("predict", "pending", "预测中");
  predictResultEl.textContent = "正在执行预测...";

  const { response, data } = await postJson("/api/predict", { rows });
  finishStep("predict", response, "已预测");

  if (response.ok) {
    renderPredictResult(data);
    return;
  }

  predictResultEl.textContent = data?.message || "预测失败，请检查输入字段是否和分析字段一致。";
}

const processButton = document.querySelector("#process-button");
if (processButton) {
  processButton.addEventListener("click", async () => {
    processButton.disabled = true;
    processButton.textContent = "处理中";

    try {
      const cleanResult = await runCleanStep();
      if (!cleanResult.ok) {
        return;
      }

      await runAnalyzeStep();
    } finally {
      processButton.disabled = false;
      processButton.textContent = "开始处理";
    }
  });
}

if (predictButtonEl) {
  predictButtonEl.addEventListener("click", async () => {
    predictButtonEl.disabled = true;
    predictButtonEl.textContent = "预测中";
    try {
      await runPredictStep();
    } finally {
      predictButtonEl.disabled = false;
      predictButtonEl.textContent = "执行预测";
    }
  });
}

if (predictFillExampleEl) {
  predictFillExampleEl.addEventListener("click", () => {
    if (!predictRowsEl) {
      return;
    }

    if (!currentPredictExampleRows.length) {
      showLocalMessage("请先完成分析后再填充示例。", true);
      return;
    }

    predictRowsEl.value = JSON.stringify(currentPredictExampleRows, null, 2);
    showLocalMessage("已填充预测示例，可直接点击执行预测。");
  });
}

document.querySelectorAll("[data-export-type]").forEach((button) => {
  button.addEventListener("click", async () => {
    setStepState("export", "pending");
    setFlowStage("export", "active", "导出中", "正在生成下载文件");
    const { response } = await exportData(button.dataset.exportType, button.dataset.datasetId);
    finishStep("export", response, "已导出");
    setFlowStage("export", response.ok ? "done" : "error", response.ok ? "已导出" : "导出失败", response.ok ? "下载已触发" : "请确认结果已生成");
  });
});

[datasetListEl, processedListEl, currentDatasetPanel].forEach((container) => {
  if (container) {
    container.addEventListener("click", handleDatasetAction);
  }
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
    const responseData = data.data || {};

    if (responseData.figure && chartEl) {
      if (visualPanel) {
        visualPanel.dataset.state = "success";
      }
      Plotly.react(chartEl, responseData.figure.data, responseData.figure.layout || {}, { responsive: true });
      if (chartDescriptionEl) {
        chartDescriptionEl.textContent = responseData.description || "图表已创建。";
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
      chartDescriptionEl.textContent = responseData.description || "数据准备完成后，系统会自动选择展示内容并生成图表说明。";
    }
  });
}

if (chartEl) {
  chartEl.textContent = "上传并处理数据后，图表会显示在这里。";
}

if (datasetSearchInput) {
  datasetSearchInput.addEventListener("input", renderDatasetViews);
}

if (datasetStatusFilter) {
  datasetStatusFilter.addEventListener("change", renderDatasetViews);
}

renderSelectedUploadPanel();
updateFileMeta();
loadDatasets();
