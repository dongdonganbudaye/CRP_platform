// pages/register/register.js
Page({
  data: {
    name: '',
    cardNumber: '',
    documentTypes: ['就业协议书', '就业推荐表'],
    documentIndex: 0,
    submitActive: false
  },

  onNameInput(e) {
    this.setData({
      name: e.detail.value
    })
  },

  onCardNumberInput(e) {
    this.setData({
      cardNumber: e.detail.value
    })
  },

  onDocumentChange(e) {
    this.setData({
      documentIndex: parseInt(e.detail.value)
    })
  },

  onSubmitTouchStart() {
    this.setData({ submitActive: true })
  },

  onSubmitTouchEnd() {
    this.setData({ submitActive: false })
  },

  onSubmit() {
    const { name, cardNumber, documentTypes, documentIndex } = this.data
    const documentType = documentTypes[documentIndex]

    // 验证输入
    if (!name.trim()) {
      wx.showModal({
        title: '提示',
        content: '请输入签章资料持有人姓名',
        showCancel: false
      })
      return
    }

    if (!cardNumber.trim()) {
      wx.showModal({
        title: '提示',
        content: '请输入签章资料持有人一卡通号',
        showCancel: false
      })
      return
    }

    // 获取所有数据（合并两个库）
    const agreementData = wx.getStorageSync('agreementData') || []
    const registrationData = wx.getStorageSync('registrationData') || []
    const allData = [...agreementData, ...registrationData]

    // 检查该一卡通号是否已经提交过该类型的资料
    const existingRecord = allData.find(item => 
      item.cardNumber === cardNumber.trim() && item.documentType === documentType
    )

    if (existingRecord) {
      wx.showModal({
        title: '提交失败',
        content: `一卡通号 ${cardNumber.trim()} 已提交过${documentType}`,
        showCancel: false
      })
      return
    }

    // 检查该一卡通号是否已存在（用于获取姓名信息）
    const cardRecord = allData.find(item => item.cardNumber === cardNumber.trim())

    // 如果该一卡通号已存在但姓名不一致，不允许提交
    if (cardRecord && cardRecord.name !== name.trim()) {
      wx.showModal({
        title: '提交失败',
        content: `一卡通号 ${cardNumber.trim()} 已登记姓名为 "${cardRecord.name}"\n您输入的姓名是 "${name.trim()}"\n\n姓名不一致，请核对后重新提交`,
        showCancel: false
      })
      return
    }

    // 保存数据
    this.saveRecord(name.trim(), cardNumber.trim(), documentType)
  },

  saveRecord(name, cardNumber, documentType) {
    // 根据文档类型获取对应的数据库
    const storageKey = documentType === '就业协议书' ? 'agreementData' : 'registrationData'
    let dataList = wx.getStorageSync(storageKey) || []

    // 创建新记录
    const newRecord = {
      name: name,
      cardNumber: cardNumber,
      documentType: documentType,
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

    dataList.push(newRecord)
    wx.setStorageSync(storageKey, dataList)

    // 跳转到成功页面
    wx.redirectTo({
      url: `/pages/success/success?name=${name}&cardNumber=${cardNumber}&documentType=${documentType}&dateTime=${newRecord.dateTime}`
    })
  }
})

