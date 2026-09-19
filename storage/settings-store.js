"use strict";
class SettingsStore {
  constructor(key="pixel-ai-camera-settings"){this.key=key}
  load(fallback={}){try{return {...fallback,...JSON.parse(localStorage.getItem(this.key)||"{}")}}catch{return {...fallback}}}
  save(value){try{localStorage.setItem(this.key,JSON.stringify(value));return true}catch{return false}}
  clear(){try{localStorage.removeItem(this.key)}catch{}}
  export(value){return JSON.stringify(value,null,2)}
  import(text){const v=JSON.parse(text);if(!v||typeof v!=="object"||Array.isArray(v))throw new Error("Invalid settings");this.save(v);return v}
}
window.SettingsStore=SettingsStore;