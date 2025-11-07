// pages/success/success.js
Page({
  data: {
    name: '',
    cardNumber: '',
    documentType: '',
    dateTime: ''
  },

  onLoad(options) {
    this.setData({
      name: options.name || '',
      cardNumber: options.cardNumber || '',
      documentType: options.documentType || '',
      dateTime: options.dateTime || ''
    })
  },

  goBack() {
    wx.reLaunch({
      url: '/pages/index/index'
    })
  }
})

