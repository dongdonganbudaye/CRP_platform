// utils/studentRecords.js
// 学生签章记录管理工具类

/**
 * 根据一卡通号获取学生的所有签章记录
 * @param {string} cardNumber - 一卡通号
 * @returns {object} 学生记录信息
 */
function getStudentRecords(cardNumber) {
  const agreementData = wx.getStorageSync('agreementData') || []
  const registrationData = wx.getStorageSync('registrationData') || []
  const allData = [...agreementData, ...registrationData]
  
  // 查找该一卡通号的所有记录
  const records = allData.filter(item => item.cardNumber === cardNumber)
  
  if (records.length === 0) {
    return {
      exists: false,
      cardNumber: cardNumber,
      name: null,
      submittedTypes: [],
      records: []
    }
  }
  
  // 获取姓名（取第一条记录的姓名）
  const name = records[0].name
  
  // 获取已提交的资料类型
  const submittedTypes = records.map(item => item.documentType)
  
  return {
    exists: true,
    cardNumber: cardNumber,
    name: name,
    submittedTypes: submittedTypes,
    records: records
  }
}

/**
 * 检查一卡通号是否已提交过指定类型的资料
 * @param {string} cardNumber - 一卡通号
 * @param {string} documentType - 资料类型
 * @returns {boolean} 是否已提交
 */
function hasSubmitted(cardNumber, documentType) {
  const agreementData = wx.getStorageSync('agreementData') || []
  const registrationData = wx.getStorageSync('registrationData') || []
  const allData = [...agreementData, ...registrationData]
  
  return allData.some(item => 
    item.cardNumber === cardNumber && item.documentType === documentType
  )
}

/**
 * 获取一卡通号对应的姓名
 * @param {string} cardNumber - 一卡通号
 * @returns {string|null} 姓名或null
 */
function getNameByCardNumber(cardNumber) {
  const agreementData = wx.getStorageSync('agreementData') || []
  const registrationData = wx.getStorageSync('registrationData') || []
  const allData = [...agreementData, ...registrationData]
  
  const record = allData.find(item => item.cardNumber === cardNumber)
  return record ? record.name : null
}

/**
 * 获取所有学生的汇总信息
 * @returns {array} 学生汇总列表
 */
function getAllStudentsSummary() {
  const agreementData = wx.getStorageSync('agreementData') || []
  const registrationData = wx.getStorageSync('registrationData') || []
  const allData = [...agreementData, ...registrationData]
  
  // 按一卡通号分组
  const studentMap = new Map()
  
  allData.forEach(record => {
    if (!studentMap.has(record.cardNumber)) {
      studentMap.set(record.cardNumber, {
        cardNumber: record.cardNumber,
        name: record.name,
        submittedTypes: [],
        records: []
      })
    }
    
    const student = studentMap.get(record.cardNumber)
    student.submittedTypes.push(record.documentType)
    student.records.push(record)
  })
  
  // 转换为数组
  return Array.from(studentMap.values())
}

/**
 * 获取统计信息
 * @returns {object} 统计数据
 */
function getStatistics() {
  const agreementData = wx.getStorageSync('agreementData') || []
  const registrationData = wx.getStorageSync('registrationData') || []
  const allData = [...agreementData, ...registrationData]
  
  // 按一卡通号去重，得到总人数
  const uniqueStudents = new Set(allData.map(item => item.cardNumber))
  
  // 统计各类型提交人数
  const agreementCount = new Set(
    agreementData.map(item => item.cardNumber)
  ).size
  
  const registrationCount = new Set(
    registrationData.map(item => item.cardNumber)
  ).size
  
  // 统计同时提交两种资料的人数
  const bothSubmitted = Array.from(uniqueStudents).filter(cardNumber => {
    const hasAgreement = agreementData.some(item => item.cardNumber === cardNumber)
    const hasRegistration = registrationData.some(item => item.cardNumber === cardNumber)
    return hasAgreement && hasRegistration
  }).length
  
  return {
    totalStudents: uniqueStudents.size,         // 总学生数
    agreementCount: agreementCount,              // 提交就业协议书人数
    registrationCount: registrationCount,        // 提交就业推荐表人数
    bothSubmitted: bothSubmitted,                // 两种都提交人数
    totalRecords: allData.length                 // 总记录数
  }
}

/**
 * 检查姓名和一卡通号是否匹配
 * @param {string} name - 姓名
 * @param {string} cardNumber - 一卡通号
 * @returns {boolean} 是否匹配
 */
function isNameCardMatch(name, cardNumber) {
  const existingName = getNameByCardNumber(cardNumber)
  if (!existingName) {
    return true // 如果一卡通号不存在，认为匹配
  }
  return existingName === name
}

module.exports = {
  getStudentRecords,
  hasSubmitted,
  getNameByCardNumber,
  getAllStudentsSummary,
  getStatistics,
  isNameCardMatch
}

