// pages/export/export.js
const studentRecords = require('../../utils/studentRecords.js')

Page({
  data: {
    username: '',
    password: '',
    authenticated: false,
    agreementCount: 0,
    registrationCount: 0,
    totalCount: 0,
    totalStudents: 0,      // 新增: 总学生数
    bothSubmitted: 0        // 新增: 两种都提交的学生数
  },

  onLoad() {
    this.loadStats()
  },

  onUsernameInput(e) {
    this.setData({
      username: e.detail.value
    })
  },

  onPasswordInput(e) {
    this.setData({
      password: e.detail.value
    })
  },

  loadStats() {
    // 使用新的统计工具
    const stats = studentRecords.getStatistics()
    
    this.setData({
      agreementCount: stats.agreementCount,
      registrationCount: stats.registrationCount,
      totalStudents: stats.totalStudents,
      bothSubmitted: stats.bothSubmitted,
      totalCount: stats.totalRecords
    })
  },

  onLogin() {
    const { username, password } = this.data
    
    if (!username.trim()) {
      wx.showModal({
        title: '提示',
        content: '请输入账号',
        showCancel: false
      })
      return
    }

    if (!password.trim()) {
      wx.showModal({
        title: '提示',
        content: '请输入密码',
        showCancel: false
      })
      return
    }

    // 验证账号密码
    if (username === 'splzl123' && password === 'SPl25924512') {
      this.setData({
        authenticated: true
      })
      wx.showToast({
        title: '登录成功',
        icon: 'success'
      })
    } else {
      wx.showModal({
        title: '登录失败',
        content: '账号或密码错误,请重试',
        showCancel: false
      })
    }
  },

  onLogout() {
    this.setData({
      authenticated: false,
      username: '',
      password: ''
    })
  },

  // 将数据转换为CSV格式
  convertToCSV(data, type) {
    if (!data || data.length === 0) {
      return ''
    }

    // CSV表头
    let csv = '\ufeff姓名,一卡通号,资料类型,提交时间\n'
    
    // CSV数据行
    data.forEach(item => {
      csv += `${item.name},${item.cardNumber},${item.documentType},${item.dateTime}\n`
    })

    return csv
  },

  // 导出就业协议书数据
  exportAgreement() {
    const agreementData = wx.getStorageSync('agreementData') || []
    
    if (agreementData.length === 0) {
      wx.showModal({
        title: '提示',
        content: '就业协议书暂无数据',
        showCancel: false
      })
      return
    }

    this.exportData(agreementData, '就业协议书数据')
  },

  // 导出就业推荐表数据
  exportRegistration() {
    const registrationData = wx.getStorageSync('registrationData') || []
    
    if (registrationData.length === 0) {
      wx.showModal({
        title: '提示',
        content: '就业推荐表暂无数据',
        showCancel: false
      })
      return
    }

    this.exportData(registrationData, '就业推荐表数据')
  },

  // 导出所有数据
  exportAll() {
    const agreementData = wx.getStorageSync('agreementData') || []
    const registrationData = wx.getStorageSync('registrationData') || []
    const allData = [...agreementData, ...registrationData]
    
    if (allData.length === 0) {
      wx.showModal({
        title: '提示',
        content: '暂无数据',
        showCancel: false
      })
      return
    }

    this.exportData(allData, '全部数据')
  },

  // 执行导出操作
  exportData(data, fileName) {
    const csv = this.convertToCSV(data)
    const fs = wx.getFileSystemManager()
    const filePath = `${wx.env.USER_DATA_PATH}/${fileName}_${Date.now()}.csv`

    // 写入文件
    fs.writeFile({
      filePath: filePath,
      data: csv,
      encoding: 'utf8',
      success: () => {
        // 分享或打开文档
        wx.shareFileMessage({
          filePath: filePath,
          fileName: `${fileName}.csv`,
          success: () => {
            wx.showToast({
              title: '导出成功',
              icon: 'success'
            })
          },
          fail: (err) => {
            // 如果分享失败,尝试打开文档
            wx.openDocument({
              filePath: filePath,
              fileType: 'csv',
              showMenu: true,
              success: () => {
                wx.showToast({
                  title: '文件已生成',
                  icon: 'success'
                })
              },
              fail: (err) => {
                // 显示详细的数据列表
                this.showDataList(data, fileName)
              }
            })
          }
        })
      },
      fail: (err) => {
        console.error('写入文件失败:', err)
        // 显示详细的数据列表作为备选方案
        this.showDataList(data, fileName)
      }
    })
  },

  // 显示数据列表(备选方案)
  showDataList(data, title) {
    let content = `共${data.length}条记录:\n\n`
    data.forEach((item, index) => {
      content += `${index + 1}. ${item.name} - ${item.cardNumber}\n   ${item.documentType} - ${item.dateTime}\n\n`
    })

    wx.showModal({
      title: title,
      content: content,
      showCancel: false,
      confirmText: '我知道了'
    })
  }
})

