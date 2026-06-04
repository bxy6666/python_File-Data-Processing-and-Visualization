<template>
  <el-upload
    v-if="!files.length"
    drag
    multiple
    :auto-upload="false"
    :show-file-list="false"
    :accept="accept"
    :on-change="handleAdd"
    class="data-file-uploader"
  >
    <div class="upload-empty">
      <span class="upload-icon">CSV</span>
      <p>将数据文件拖到此处，或 <em>点击选择</em></p>
      <small>支持 .csv / .xls / .xlsx，可同时选择多个文件</small>
    </div>
  </el-upload>

  <div v-else class="selected-files-panel" @dragover.prevent @drop.prevent="handleDrop">
    <div class="selected-files-header">
      <h4>{{ title }}（{{ files.length }}）</h4>
      <el-button text type="danger" @click="$emit('clear-files')">清空</el-button>
    </div>

    <div class="selected-files-list">
      <div v-for="file in files" :key="file.uid" class="selected-file-item">
        <div class="selected-file-meta">
          <span :class="['selected-file-icon', fileIconClass(file.name)]">{{ fileExtension(file.name) }}</span>
          <div class="selected-file-copy">
            <span class="selected-file-name" :title="file.name">{{ file.name }}</span>
            <span class="selected-file-size">{{ fileSummary(file) }}</span>
          </div>
        </div>
      </div>
    </div>

    <el-upload
      multiple
      :auto-upload="false"
      :show-file-list="false"
      :accept="accept"
      :on-change="handleAdd"
      class="add-more-uploader"
    >
      <el-button type="primary">继续添加文件</el-button>
    </el-upload>

    <div class="selected-files-footer">
      <span>已选择 <strong>{{ files.length }}</strong> 个文件</span>
      <div class="selected-files-actions">
        <el-button v-if="mode === 'upload'" type="primary" @click="$emit('process-file', activeFile)">处理</el-button>
        <el-button @click="$emit('show-chart', activeFile)">图表</el-button>
        <el-button v-if="mode === 'processed'" :disabled="!activeFile?.cleaned && !activeFile?.analyzed" @click="$emit('export-csv', activeFile)">导出</el-button>
        <el-button type="danger" @click="$emit('delete-file', activeFile)">删除</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  files: { type: Array, default: () => [] },
  processedFiles: { type: Array, default: () => [] },
  accept: { type: String, default: ".csv,.xlsx,.xls" },
  maxSize: { type: Number, default: 0 },
  mode: { type: String, default: "upload" },
});

const emit = defineEmits([
  "add-files",
  "clear-files",
  "process-file",
  "show-chart",
  "export-csv",
  "delete-file",
]);

const title = computed(() => (props.mode === "processed" ? "处理后文件" : "已选择数据文件"));
const activeFile = computed(() => props.files.find((file) => file.status === "active") || props.files[0]);

function handleAdd(uploadFile) {
  if (!uploadFile?.raw) {
    return;
  }
  emit("add-files", [uploadFile.raw]);
}

function handleDrop(event) {
  emit("add-files", Array.from(event.dataTransfer?.files || []));
}

function fileExtension(filename = "") {
  return filename.includes(".") ? filename.split(".").pop().toUpperCase() : "FILE";
}

function fileIconClass(filename = "") {
  return /\.(csv|xls|xlsx)$/i.test(filename) ? "table" : "document";
}

function formatFileSize(size = 0) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function fileSummary(file) {
  const detail = [formatFileSize(file.size || 0)];
  if (file.rows !== undefined) detail.push(`${file.rows} 行`);
  if (file.columns !== undefined) detail.push(`${file.columns} 列`);
  if (file.missing !== undefined) detail.push(`缺失 ${file.missing}`);
  return detail.join(" · ");
}
</script>

<style scoped>
.selected-files-panel,
.data-file-uploader {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
  padding: 14px 16px;
}

.selected-files-header,
.selected-files-footer,
.selected-file-item,
.selected-file-meta,
.selected-files-actions {
  display: flex;
  align-items: center;
}

.selected-files-header,
.selected-files-footer,
.selected-file-item {
  justify-content: space-between;
}

.selected-files-list {
  display: grid;
  gap: 8px;
  margin: 12px 0;
}

.selected-file-item {
  gap: 12px;
  min-height: 48px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px 10px;
  background: #fbfdff;
}

.selected-file-meta,
.selected-files-actions {
  gap: 10px;
  min-width: 0;
}

.selected-file-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: #eff6ff;
  color: #3b82f6;
  font-size: 10px;
  font-weight: 900;
}

.selected-file-icon.table {
  background: #ecfdf5;
  color: #10b981;
}

.selected-file-copy {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.selected-file-name,
.selected-file-size {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selected-file-name {
  font-size: 14px;
  font-weight: 700;
}

.selected-file-size {
  color: #63727d;
  font-size: 12px;
}
</style>
