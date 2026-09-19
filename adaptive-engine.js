"use strict";

/*
 * Adaptive camera controller.
 * Changes only settings that the browser exposes and only when the change is
 * likely to improve capture quality or reduce load. It never invents hardware.
 */
window.AdaptiveEngine = {
  active:false,
  lastZoomBand:"",
  lastApply:0,
  timer:0,
  battery:null,
  thermalLimited:false,

  init(){
    if(this.active)return;
    this.active=true;
    if(navigator.getBattery){
      navigator.getBattery().then(b=>{
        this.battery=b;
        const update=()=>{
          this.thermalLimited=Number(b.level)<0.12 && !b.charging;
        };
        update(); b.addEventListener("levelchange",update);
        b.addEventListener("chargingchange",update);
      }).catch(()=>{});
    }
  },

  cameraReady(){
    this.init();
    this.evaluate("camera-ready",true);
  },

  zoomChanged(zoom){
    const z=Number(zoom)||1;
    const band=z<1.5?"wide":z<4?"normal":z<10?"tele":"long";
    if(band===this.lastZoomBand)return;
    this.lastZoomBand=band;
    this.evaluate("zoom-"+band,false);
  },

  evaluate(reason,force){
    if(!APP?.track)return;
    const now=performance.now();
    if(!force && now-this.lastApply<1200)return;
    this.lastApply=now;

    const caps=APP.caps||{};
    const current=APP.settings||{};
    const targetFps=this.chooseFps(caps,current);
    const targetSize=this.chooseSize(caps,current);

    const advanced={};
    if(targetFps && this.needs(current.frameRate,targetFps,.5))advanced.frameRate=targetFps;
    if(targetSize?.width && this.needs(current.width,targetSize.width,64))advanced.width=targetSize.width;
    if(targetSize?.height && this.needs(current.height,targetSize.height,64))advanced.height=targetSize.height;

    if(Object.keys(advanced).length){
      clearTimeout(this.timer);
      this.timer=setTimeout(async()=>{
        try{
          await APP.track.applyConstraints({advanced:[advanced]});
          APP.settings=APP.track.getSettings?.()||APP.settings;
          const st=APP.settings;
          const chip=document.getElementById("chipRes");
          if(chip)chip.textContent=`${st.width||"?"}×${st.height||"?"}`;
        }catch(e){
          // Browsers frequently reject runtime resolution changes. Keep the stream.
          console.debug("[adaptive] constraint change rejected",reason,e?.name||e);
        }
      },80);
    }
  },

  needs(actual,target,tolerance){
    return Number.isFinite(target)&&Number.isFinite(actual)&&Math.abs(actual-target)>tolerance;
  },

  chooseFps(caps,current){
    const range=caps.frameRate;
    if(!range)return null;
    const max=Number(range.max)||30,min=Number(range.min)||1;
    let desired=Number(S?.vid?.fps)||30;
    if(this.thermalLimited)desired=Math.min(desired,30);
    if(window.Motion?.shake>0.65)desired=Math.min(desired,30);
    return Math.max(min,Math.min(max,desired));
  },

  chooseSize(caps,current){
    const wr=caps.width,hr=caps.height;
    if(!wr||!hr)return null;

    const z=Number(window.Zoom?.target)||1;
    const perf=S?.sys?.perf||"balanced";
    const maxW=Number(wr.max)||current.width||1920;
    const maxH=Number(hr.max)||current.height||1080;
    const minW=Number(wr.min)||640,minH=Number(hr.min)||360;

    // High zoom benefits from sensor resolution; battery mode avoids unnecessary 4K.
    let requested=Number(S?.cam?.res==="2160"?3840:S?.cam?.res==="1440"?2560:1920);
    if(S?.cam?.res==="max")requested=maxW;
    if(perf==="battery")requested=Math.min(requested,1920);
    if(z>=8)requested=Math.min(maxW,Math.max(requested,2560));

    const aspect=(current.width&&current.height)?current.width/current.height:16/9;
    const width=Math.max(minW,Math.min(maxW,requested));
    const height=Math.max(minH,Math.min(maxH,Math.round(width/aspect)));
    return {width,height};
  }
};
