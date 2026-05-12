/**
 * 报告导出工具
 * 使用html2canvas + jsPDF解决中文显示问题
 */

import * as XLSX from 'xlsx'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import { formatScore } from './format'

export const exportUtils = {
  /**
   * 导出排名数据为Excel
   */
  exportToExcel(rankings, industry = '排名报告', filename = 'ranking_report') {
    if (!rankings || rankings.length === 0) {
      throw new Error('没有数据可导出')
    }

    const exportData = rankings.map((r, index) => ({
      '排名': index + 1,
      '候选人': r.candidate_id,
      'TCI得分': formatScore(r.tci_score),
      '跳槽风险': r.penalty_applied ? '是' : '否',
      '行业': industry
    }))

    const ws = XLSX.utils.json_to_sheet(exportData)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '排名数据')

    const colWidths = [
      { wch: 8 },
      { wch: 15 },
      { wch: 12 },
      { wch: 10 },
      { wch: 15 }
    ]
    ws['!cols'] = colWidths

    XLSX.writeFile(wb, `${filename}_${Date.now()}.xlsx`)
  },

  /**
   * 生成报告HTML模板
   */
  generateReportHTML(reportData) {
    const { rankings, industry, candidates } = reportData
    const firstCandidate = candidates && candidates[0] ? candidates[0] : null

    const dimensionNames = {
      education: '教育背景',
      experience: '工作经历',
      skill_achievement: '技能成果',
      comprehensive: '综合素质'
    }

    let dimensionWeightsHTML = ''

    if (firstCandidate && firstCandidate.dimension_weights) {
      const weights = firstCandidate.dimension_weights
      dimensionWeightsHTML = Object.entries(weights).map(([key, value]) => {
        const name = dimensionNames[key] || key
        return `<div class="weight-item">
          <span class="label">${name}</span>
          <span class="value">${(value * 100).toFixed(1)}%</span>
        </div>`
      }).join('')
    }

    const rankingRowsHTML = rankings.slice(0, 10).map((r, index) => `
      <tr ${index % 2 === 1 ? 'class="alt-row"' : ''}>
        <td>${index + 1}</td>
        <td>${r.candidate_id}</td>
        <td>${formatScore(r.tci_score)}</td>
        <td>${r.penalty_applied ? '<span class="risk">是</span>' : '否'}</td>
      </tr>
    `).join('')

    return `
      <div class="report-container">
        <div class="header">
          <h1>人才简历综合优选系统</h1>
          <h2>${industry}行业人才排名报告</h2>
          <p class="date">生成时间: ${new Date().toLocaleString('zh-CN')}</p>
        </div>

        <div class="section">
          <h3>Top 10 候选人排名</h3>
          <table class="ranking-table">
            <thead>
              <tr>
                <th>排名</th>
                <th>候选人</th>
                <th>TCI得分</th>
                <th>跳槽风险</th>
              </tr>
            </thead>
            <tbody>
              ${rankingRowsHTML}
            </tbody>
          </table>
        </div>

        ${dimensionWeightsHTML ? `
        <div class="section">
          <h3>维度权重分布</h3>
          <div class="weights">${dimensionWeightsHTML}</div>
        </div>
        ` : ''}

        <div class="footer">
          <p>基于AHP+熵权法的多维度评分模型生成</p>
        </div>
      </div>

      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: "Microsoft YaHei", "PingFang SC", "SimHei", sans-serif; }
        .report-container { padding: 40px; max-width: 800px; margin: 0 auto; color: #333; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 28px; color: #2e86ab; margin-bottom: 10px; }
        .header h2 { font-size: 20px; color: #666; margin-bottom: 10px; }
        .header .date { font-size: 12px; color: #999; }
        .section { margin-bottom: 30px; }
        .section h3 { font-size: 16px; color: #333; border-bottom: 2px solid #2e86ab; padding-bottom: 8px; margin-bottom: 15px; }
        .ranking-table { width: 100%; border-collapse: collapse; }
        .ranking-table th { background: #2e86ab; color: white; padding: 12px 8px; text-align: left; }
        .ranking-table td { padding: 10px 8px; border-bottom: 1px solid #ddd; }
        .ranking-table .alt-row { background: #f9f9f9; }
        .ranking-table .risk { color: #e74c3c; font-weight: bold; }
        .weights { margin-bottom: 15px; }
        .weight-item { display: flex; justify-content: space-between; padding: 8px 12px; background: #f5f5f5; margin-bottom: 8px; border-radius: 4px; }
        .weight-item .label { color: #666; }
        .weight-item .value { font-weight: bold; color: #2e86ab; }
        .footer { text-align: center; padding-top: 20px; border-top: 1px solid #ddd; }
        .footer p { font-size: 12px; color: #999; }
      </style>
    `
  },

  /**
   * 生成候选人详评HTML模板
   */
  generateCandidateHTML(candidate) {
    const dimensionNames = {
      education: '教育背景',
      experience: '工作经历',
      skill_achievement: '技能成果',
      comprehensive: '综合素质'
    }

    const scores = candidate.dimensional_scores || {}
    const dimensionScoresHTML = Object.entries(scores).map(([key, value]) => {
      const name = dimensionNames[key] || key
      const percentage = ((value / 5) * 100).toFixed(1)
      return `<div class="score-item">
        <span class="label">${name}</span>
        <span class="percentage">${percentage}%</span>
        <div class="progress-bar"><div class="progress" style="width: ${percentage}%"></div></div>
      </div>`
    }).join('')

    return `
      <div class="candidate-container">
        <div class="header">
          <h1>候选人详细评估报告</h1>
          <div class="divider"></div>
        </div>

        <div class="info-section">
          <h2>${candidate.candidate_id}</h2>
          <p class="industry">${candidate.industry || '行业'}</p>
        </div>

        <div class="score-section">
          <div class="overall-score">
            <span class="label">综合评分</span>
            <span class="value">${formatScore(candidate.tci_score)}</span>
          </div>
          <div class="rank-info">
            <span class="label">行业排名</span>
            <span class="value">第 ${candidate.rank || '-'} 名</span>
            ${candidate.penalty_applied ? '<span class="risk">存在跳槽风险</span>' : ''}
          </div>
        </div>

        <div class="section">
          <h3>维度得分详情</h3>
          <div class="scores-list">
            ${dimensionScoresHTML}
          </div>
        </div>

        <div class="footer">
          <p>人才简历综合优选系统 | 基于AHP+熵权法评分</p>
        </div>
      </div>

      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: "Microsoft YaHei", "PingFang SC", "SimHei", sans-serif; }
        .candidate-container { padding: 40px; max-width: 600px; margin: 0 auto; color: #333; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 24px; color: #2e86ab; }
        .header .divider { height: 3px; background: linear-gradient(to right, #2e86ab, #4ecdc4); margin-top: 15px; border-radius: 2px; }
        .info-section { text-align: center; margin-bottom: 30px; }
        .info-section h2 { font-size: 28px; color: #333; margin-bottom: 8px; }
        .info-section .industry { font-size: 14px; color: #666; background: #e8f4f8; display: inline-block; padding: 4px 16px; border-radius: 20px; }
        .score-section { display: flex; gap: 20px; margin-bottom: 30px; }
        .overall-score { flex: 1; background: linear-gradient(135deg, #2e86ab, #3498db); color: white; padding: 25px; border-radius: 12px; text-align: center; }
        .overall-score .label { font-size: 14px; opacity: 0.9; }
        .overall-score .value { font-size: 42px; font-weight: bold; display: block; margin-top: 5px; }
        .rank-info { flex: 1; background: #f8f9fa; padding: 25px; border-radius: 12px; display: flex; flex-direction: column; justify-content: center; }
        .rank-info .label { font-size: 14px; color: #666; }
        .rank-info .value { font-size: 24px; font-weight: bold; color: #333; }
        .rank-info .risk { color: #e74c3c; font-size: 12px; margin-top: 5px; }
        .section h3 { font-size: 16px; color: #333; border-left: 4px solid #2e86ab; padding-left: 12px; margin-bottom: 15px; }
        .scores-list { background: #f8f9fa; padding: 20px; border-radius: 12px; }
        .score-item { margin-bottom: 15px; }
        .score-item:last-child { margin-bottom: 0; }
        .score-item .label { display: block; color: #666; font-size: 14px; margin-bottom: 5px; }
        .score-item .percentage { float: right; font-weight: bold; color: #2e86ab; }
        .score-item .progress-bar { height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden; }
        .score-item .progress { height: 100%; background: linear-gradient(to right, #2e86ab, #4ecdc4); border-radius: 4px; }
        .footer { text-align: center; padding-top: 30px; border-top: 1px solid #eee; margin-top: 30px; }
        .footer p { font-size: 12px; color: #999; }
      </style>
    `
  },

  /**
   * 导出PDF（使用html2canvas解决中文问题）
   */
  exportToPDF(reportData, filename = 'ranking_report') {
    return new Promise((resolve, reject) => {
      try {
        const htmlContent = this.generateReportHTML(reportData)

        const container = document.createElement('div')
        container.innerHTML = htmlContent
        container.style.cssText = 'position: absolute; left: -9999px; top: 0; width: 800px; background: white;'
        document.body.appendChild(container)

        html2canvas(container, {
          scale: 2,
          useCORS: true,
          allowTaint: true,
          logging: false
        }).then(canvas => {
          document.body.removeChild(container)

          const imgData = canvas.toDataURL('image/png')
          const pdf = new jsPDF({
            orientation: 'portrait',
            unit: 'mm',
            format: 'a4'
          })

          const imgWidth = 210
          const pageHeight = 297
          const imgHeight = (canvas.height * imgWidth) / canvas.width

          let heightLeft = imgHeight
          let position = 0

          pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
          heightLeft -= pageHeight

          while (heightLeft >= 0) {
            position = heightLeft - imgHeight
            pdf.addPage()
            pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
            heightLeft -= pageHeight
          }

          pdf.save(`${filename}_${Date.now()}.pdf`)
          resolve()
        }).catch(error => {
          document.body.removeChild(container)
          reject(error)
        })
      } catch (error) {
        reject(error)
      }
    })
  },

  /**
   * 导出候选人PDF
   */
  exportCandidatePDF(candidate, filename = 'candidate_report') {
    return new Promise((resolve, reject) => {
      try {
        const htmlContent = this.generateCandidateHTML(candidate)

        const container = document.createElement('div')
        container.innerHTML = htmlContent
        container.style.cssText = 'position: absolute; left: -9999px; top: 0; width: 600px; background: white;'
        document.body.appendChild(container)

        html2canvas(container, {
          scale: 2,
          useCORS: true,
          allowTaint: true,
          logging: false
        }).then(canvas => {
          document.body.removeChild(container)

          const imgData = canvas.toDataURL('image/png')
          const pdf = new jsPDF({
            orientation: 'portrait',
            unit: 'mm',
            format: 'a4'
          })

          const imgWidth = 210
          const pageHeight = 297
          const imgHeight = (canvas.height * imgWidth) / canvas.width

          pdf.addImage(imgData, 'PNG', 0, 0, imgWidth, imgHeight)

          pdf.save(`${filename}_${candidate.candidate_id}_${Date.now()}.pdf`)
          resolve()
        }).catch(error => {
          document.body.removeChild(container)
          reject(error)
        })
      } catch (error) {
        reject(error)
      }
    })
  }
}

export default exportUtils
