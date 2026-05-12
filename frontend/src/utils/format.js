/**
 * 数据格式化工具
 * 统一管理系统中所有数值的小数点展示格式
 */

/**
 * 格式化TCI得分
 * @param {number} score - 原始分数
 * @param {number} decimals - 小数位数，默认2位
 * @returns {string} 格式化后的分数字符串
 */
export const formatScore = (score, decimals = 2) => {
  if (score === null || score === undefined || score === '') return '-'
  const num = parseFloat(score)
  if (isNaN(num)) return '-'
  return num.toFixed(decimals)
}

/**
 * 格式化百分比
 * @param {number} value - 原始数值（0-5范围，会自动转换为百分比）
 * @param {number} decimals - 小数位数，默认1位
 * @returns {string} 格式化后的百分比字符串
 */
export const formatPercentage = (value, decimals = 1) => {
  if (value === null || value === undefined || value === '') return '-'
  const num = parseFloat(value)
  if (isNaN(num)) return '-'
  const percentage = (num / 5) * 100
  return percentage.toFixed(decimals) + '%'
}

/**
 * 格式化排名数字
 * @param {number} rank - 排名
 * @returns {string} 格式化后的排名字符串
 */
export const formatRank = (rank) => {
  if (rank === null || rank === undefined || rank === '') return '-'
  return '第 ' + rank + ' 名'
}

/**
 * 通用数字格式化
 * @param {number} value - 原始数值
 * @param {number} decimals - 小数位数
 * @returns {string} 格式化后的字符串
 */
export const formatNumber = (value, decimals = 2) => {
  if (value === null || value === undefined || value === '') return '-'
  const num = parseFloat(value)
  if (isNaN(num)) return '-'
  return num.toFixed(decimals)
}

export default {
  formatScore,
  formatPercentage,
  formatRank,
  formatNumber
}
