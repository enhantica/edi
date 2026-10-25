import assert from 'node:assert/strict';

// Install before the app starts. Only browser boundaries change; Qt still saves and packs the project.
export function installDownloadBoundary() {
  const state=window.__downloadBoundary={calls:[],storage:[],workers:[],pending:[],denied:true};
  const fail=kind=>{state.storage.push(kind);throw new DOMException('Private-session storage unavailable','UnknownError');};
  Object.defineProperty(navigator.storage,'getDirectory',{configurable:true,value:async()=>fail('opfs')});
  Object.defineProperty(indexedDB,'open',{configurable:true,value:()=>fail('indexeddb')});
  for(const name of ['showDirectoryPicker','showOpenFilePicker','showSaveFilePicker'])
    Object.defineProperty(window,name,{configurable:true,value:undefined});
  const NativeWorker=window.Worker;
  window.Worker=class extends NativeWorker {
    constructor(url,options) {
      const prefix=`const deny=kind=>{postMessage({__privateStorage:kind});throw new DOMException('Private-session storage unavailable','UnknownError');};\nObject.defineProperty(navigator.storage,'getDirectory',{value:async()=>deny('worker-opfs')});\nObject.defineProperty(indexedDB,'open',{value:()=>deny('worker-indexeddb')});\n`;
      const absolute=new URL(url,location.href).href;
      const source=prefix+(options?.type==='module'?`await import(${JSON.stringify(absolute)});`:`importScripts(${JSON.stringify(absolute)});`);
      super(URL.createObjectURL(new Blob([source],{type:'text/javascript'})),options);
      this.addEventListener('message',event=>{
        if(event.data?.__privateStorage){state.storage.push(event.data.__privateStorage);event.stopImmediatePropagation();}
      });
      state.workers.push(this);
    }
  };
  const nativeClick=HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click=function(){
    if(!this.download)return nativeClick.call(this);
    const item={name:this.download,url:this.href};state.calls.push(item);
    state.pending.push(()=>nativeClick.call(this));
  };
  state.release=()=>{for(const next of state.pending.splice(0))next();};
  state.cancel=()=>{state.pending.length=0;};
}

export function assertPendingNotice(text,fromFile) {
  assert.equal(typeof text,'string','A visible download notice must expose its actual rendered text for inspection');
  assert(!/\b(downloaded|saved|finished|completed)\b/i.test(text),
    'While browser permission is pending, the notice must not claim a finished download');
  if(!fromFile)assert(!/replace.{0,60}(original|old|existing)\s+file/i.test(text),
    'A built-in example has no original disk file to replace');
}

export function checkNoticeControls() {
  assertPendingNotice('',false);
  assertPendingNotice('Your browser will ask whether to download example.zip.',false);
  assertPendingNotice('Download requested. To replace the original file, choose it in your browser.',true);
  for(const text of ['Downloaded example.zip to the browser downloads folder.','The download completed.','Saved example.zip.'])
    assert.throws(()=>assertPendingNotice(text,true),/must not claim a finished download/,
      'Every premature completion wording must be refused while permission is pending');
  assert.throws(()=>assertPendingNotice('To replace the original file, choose it.',false),/no original disk file/,
    'Replacement guidance for a bundled example must be refused independently of completion wording');
  assert.throws(()=>assertPendingNotice(undefined,false),/actual rendered text/,
    'An invisible accessibility label cannot stand in for the rendered download notice');
}
