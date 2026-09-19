"use strict";
window.PixelCameraTests = function(){
  const out=[];const test=(name,fn)=>{try{if(fn()===false)throw new Error("assertion failed");out.push({name,ok:true})}catch(e){out.push({name,ok:false,error:e.message})}};
  test("zoom clamp",()=>new ZoomEngine({max:10}).set(99)===10);
  test("pinch apart zooms in",()=>new ZoomEngine({max:10}).pinch(1,100,200)===2);
  test("pinch together zooms out",()=>new ZoomEngine({max:10}).pinch(4,200,100)===2);
  test("lens classification",()=>new LensManager().classify({label:"Pixel Ultrawide"})==="ULTRAWIDE");
  test("plate-like OCR normalization",()=>ReaderTools?.looksLikePlate("RKS 1234")===true);
  test("scene low light",()=>SceneAnalyzer.analyze({mean:30}).lowLight===true);
  return out;
};