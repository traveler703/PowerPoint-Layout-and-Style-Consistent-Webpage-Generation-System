<template>
  <div class="report-panel">
    <div v-if="!store.evaluationReport" class="report-empty">
      <h3>暂无报告</h3>
      <p>生成PPT后系统会自动评估，也可以点击右上角“刷新报告”。</p>
    </div>

    <template v-else>
      <section class="report-summary">
        <div class="report-status" :class="{ passed: store.evaluationReport.passed }">
          {{ store.evaluationReport.passed ? '通过' : '需检查' }}
        </div>
        <div>
          <h3>生成质量报告</h3>
          <p>{{ store.evaluationReport.summary }}</p>
        </div>
      </section>

      <section class="report-metrics">
        <div class="report-metric">
          <span>页面数</span>
          <strong>{{ store.evaluationReport.page_count }}</strong>
        </div>
        <div class="report-metric">
          <span>全局色彩偏差率</span>
          <strong>{{ formatPercent(store.evaluationReport.global_color_deviation_percent) }}</strong>
        </div>
        <div class="report-metric">
          <span>平均每页生成时间</span>
          <strong>{{ formatSeconds(store.evaluationReport.average_generation_time_seconds) }}</strong>
        </div>
      </section>

      <section v-if="store.evaluationReport.metric_notes" class="report-notes">
        <p>{{ store.evaluationReport.metric_notes.color_deviation }}</p>
        <p>{{ store.evaluationReport.metric_notes.overlap_ratio }}</p>
      </section>

      <section class="report-table-wrap">
        <table class="report-table">
          <thead>
            <tr>
              <th>页面</th>
              <th>标题</th>
              <th>元素重叠率</th>
              <th>色彩偏差率</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="page in store.evaluationReport.pages" :key="page.page_number">
              <td>第 {{ page.page_number }} 页</td>
              <td>{{ page.title }}</td>
              <td>{{ formatRatio(page.overlap_ratio) }}</td>
              <td>{{ formatPercent(page.color_deviation_percent) }}</td>
              <td>
                <span class="page-pass" :class="{ warn: !page.passed }">
                  {{ page.passed ? '通过' : '警告' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </div>
</template>

<script setup>
import { store } from '../stores/appStore'

function formatRatio(value) {
  if (typeof value !== 'number') return 'N/A'
  return `${(value * 100).toFixed(2)}%`
}

function formatPercent(value) {
  if (typeof value !== 'number') return 'N/A'
  return `${value.toFixed(2)}%`
}

function formatSeconds(value) {
  if (typeof value !== 'number' || value <= 0) return 'N/A'
  return `${value.toFixed(2)} 秒`
}
</script>

<style scoped>
.report-panel {
  height: 100%;
  padding: 24px;
  overflow: auto;
  background: #f8fafc;
}

.report-empty,
.report-summary,
.report-metrics,
.report-table-wrap {
  max-width: 1100px;
  margin: 0 auto 16px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.report-empty {
  padding: 32px;
  color: #64748b;
}

.report-empty h3,
.report-summary h3 {
  margin: 0 0 8px;
  color: #111827;
}

.report-summary {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  padding: 20px;
}

.report-status {
  flex: 0 0 auto;
  padding: 8px 12px;
  border-radius: 999px;
  color: #92400e;
  background: #fef3c7;
  font-weight: 700;
}

.report-status.passed {
  color: #166534;
  background: #dcfce7;
}

.report-summary p {
  margin: 0;
  color: #4b5563;
  line-height: 1.6;
}

.report-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  overflow: hidden;
}

.report-metric {
  padding: 18px;
  background: #fff;
}

.report-metric span {
  display: block;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 13px;
}

.report-metric strong {
  color: #111827;
  font-size: 24px;
}

.report-table-wrap {
  overflow: auto;
}

.report-notes {
  max-width: 1100px;
  margin: 0 auto 16px;
  padding: 14px 18px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.report-notes p {
  margin: 4px 0;
  color: #334155;
  font-size: 13px;
  line-height: 1.6;
}

.report-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
}

.report-table th,
.report-table td {
  padding: 12px 14px;
  border-bottom: 1px solid #eef2f7;
  text-align: left;
  font-size: 13px;
  color: #111827;
}

.report-table th {
  color: #475569;
  background: #f8fafc;
  font-weight: 700;
}

.page-pass {
  color: #15803d;
  font-weight: 700;
}

.page-pass.warn {
  color: #b45309;
}
</style>
