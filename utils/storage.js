// utils/storage.js
// 数据存储工具类

/**
 * 获取就业协议书数据
 */
function getAgreementData() {
  return wx.getStorageSync('agreementData') || []
}

/**
 * 获取报到证数据
 */
function getRegistrationData() {
  return wx.getStorageSync('registrationData') || []
}

/**
 * 保存就业协议书数据
 */
function saveAgreementData(data) {
  wx.setStorageSync('agreementData', data)
}

/**
 * 保存报到证数据
 */
function saveRegistrationData(data) {
  wx.setStorageSync('registrationData', data)
}

/**
 * 根据类型获取数据
 */
function getDataByType(type) {
  if (type === '就业协议书') {
    return getAgreementData()
  } else if (type === '报到证') {
    return getRegistrationData()
  }
  return []
}

/**
 * 根据类型保存数据
 */
function saveDataByType(type, data) {
  if (type === '就业协议书') {
    saveAgreementData(data)
  } else if (type === '报到证') {
    saveRegistrationData(data)
  }
}

/**
 * 检查数据是否重复
 */
function checkDuplicate(type, name, cardNumber) {
  const data = getDataByType(type)
  
  const nameExists = data.some(item => item.name === name)
  const cardExists = data.some(item => item.cardNumber === cardNumber)
  
  return {
    nameExists,
    cardExists,
    hasDuplicate: nameExists || cardExists
  }
}

/**
 * 添加记录
 */
function addRecord(type, name, cardNumber) {
  const data = getDataByType(type)
  
  const newRecord = {
    name: name,
    cardNumber: cardNumber,
    documentType: type,
    timestamp: new Date().getTime(),
    dateTime: new Date().toLocaleString('zh-CN', { 
      year: 'numeric', 
      month: '2-digit', 
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }
  
  data.push(newRecord)
  saveDataByType(type, data)
  
  return newRecord
}

/**
 * 获取所有数据
 */
function getAllData() {
  return [...getAgreementData(), ...getRegistrationData()]
}

/**
 * 清空所有数据
 */
function clearAllData() {
  wx.removeStorageSync('agreementData')
  wx.removeStorageSync('registrationData')
}

module.exports = {
  getAgreementData,
  getRegistrationData,
  saveAgreementData,
  saveRegistrationData,
  getDataByType,
  saveDataByType,
  checkDuplicate,
  addRecord,
  getAllData,
  clearAllData
}

