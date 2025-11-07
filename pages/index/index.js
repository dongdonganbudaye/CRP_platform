// pages/index/index.js
Page({
  data: {
    registerActive: false,
    exportActive: false
  },

  onRegisterTouchStart() {
    this.setData({ registerActive: true })
  },

  onRegisterTouchEnd() {
    this.setData({ registerActive: false })
  },

  onExportTouchStart() {
    this.setData({ exportActive: true })
  },

  onExportTouchEnd() {
    this.setData({ exportActive: false })
  },

  goToRegister() {
    wx.navigateTo({
      url: '/pages/register/register'
    })
  },

  goToExport() {
    wx.navigateTo({
      url: '/pages/export/export'
    })
  }
})

