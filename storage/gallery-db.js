"use strict";
class GalleryDB{
  constructor(name="pixel-ai-camera",version=1){this.name=name;this.version=version;this.db=null}
  async open(){if(!indexedDB)throw new Error("IndexedDB unavailable");if(this.db)return this.db;this.db=await new Promise((res,rej)=>{const r=indexedDB.open(this.name,this.version);r.onupgradeneeded=()=>{const d=r.result;if(!d.objectStoreNames.contains("media")){const s=d.createObjectStore("media",{keyPath:"id",autoIncrement:true});s.createIndex("created","created");s.createIndex("type","type")}};r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)});return this.db}
  async add(item){const db=await this.open();return new Promise((res,rej)=>{const tx=db.transaction("media","readwrite");const r=tx.objectStore("media").add({...item,created:item.created||Date.now()});r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)})}
}
window.GalleryDB=GalleryDB;