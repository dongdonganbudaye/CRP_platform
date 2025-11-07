App({
  onLaunch() {
    // 初始化本地存储
    const agreementData = wx.getStorageSync('agreementData') || []
    const registrationData = wx.getStorageSync('registrationData') || []
    
    if (!wx.getStorageSync('agreementData')) {
      wx.setStorageSync('agreementData', [])
    }
    if (!wx.getStorageSync('registrationData')) {
      wx.setStorageSync('registrationData', [])
    }
  },
  
  globalData: {
    userInfo: null
  }
})

