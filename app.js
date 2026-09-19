"use strict";

window.PixelCameraApp=Object.freeze({
  version:"rework-2026-09",
  serviceWorkerSupported:"serviceWorker" in navigator,
  async install(){
    if(!this.serviceWorkerSupported||location.protocol==="file:") return null;
    try{
      return await navigator.serviceWorker.register("./service-worker.js",{scope:"./"});
    }catch(error){
      console.warn("[PixelCameraApp] service worker registration failed",error);
      return null;
    }
  }
});

window.PixelCameraApp.install();
