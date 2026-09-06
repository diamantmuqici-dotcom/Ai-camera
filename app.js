"use strict";

window.PixelCameraApp = Object.freeze({
  version:"modular-1",
  serviceWorkerSupported:"serviceWorker" in navigator,
  install(){
    if(this.serviceWorkerSupported&&location.protocol!=="file:")
      return navigator.serviceWorker.register("./service-worker.js").catch(()=>null);
    return Promise.resolve(null);
  }
});
window.PixelCameraApp.install();
