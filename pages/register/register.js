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

    // 根据文档类型获取对应的数据库
    const storageKey = documentType === '就业协议书' ? 'agreementData' : 'registrationData'
    let dataList = wx.getStorageSync(storageKey) || []

    // 检查是否存在重复的姓名
    const nameExists = dataList.some(item => item.name === name.trim())
    if (nameExists) {
      wx.showModal({
        title: '提交失败',
        content: `${documentType}库已存在该签章资料持有人,请重新提交`,
        showCancel: false
      })
      return
    }

    // 检查是否存在重复的一卡通号
    const cardExists = dataList.some(item => item.cardNumber === cardNumber.trim())
    if (cardExists) {
      wx.showModal({
        title: '提交失败',
        content: `${documentType}库已存在签章资料持有人一卡通号,请重新提交`,
        showCancel: false
      })
      return
    }

    // 保存数据
    const newRecord = {
      name: name.trim(),
      cardNumber: cardNumber.trim(),
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
      url: `/pages/success/success?name=${name.trim()}&cardNumber=${cardNumber.trim()}&documentType=${documentType}&dateTime=${newRecord.dateTime}`
    })
  }
})

