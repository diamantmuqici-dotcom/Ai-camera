"use strict";
class AppController{
  constructor(){this.performance=null;this.deviceProfile=DeviceProfile?.classify?.()||"UNKNOWN"}
  attach({video,track}={}){this.performance=new PerformanceMonitor(video);this.track=track;this.profile=this.deviceProfile;return this}
  tick(){this.performance?.tick()}
  report(){return {profile:this.profile,performance:this.performance?.report?.()||null,capabilities:CapabilityReport?.build?.(this.track)||null}}
}
window.PixelAppController=AppController;