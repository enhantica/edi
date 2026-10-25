import assert from 'node:assert/strict';

// Install before the app starts. Only browser boundaries change; Qt still saves and packs the project.
export function installDownloadBoundary({denyStorage=true}={}) {
  const state=window.__downloadBoundary={calls:[],storage:[],workers:[],pending:[],denied:denyStorage,failures:[]};
  const fail=kind=>{state.failures.push(kind);throw new DOMException('Private-session storage unavailable','UnknownError');};
  const nativeDirectory=navigator.storage.getDirectory.bind(navigator.storage),nativeOpen=indexedDB.open.bind(indexedDB);
  Object.defineProperty(navigator.storage,'getDirectory',{configurable:true,value:async()=>{state.storage.push('opfs');if(state.denied)fail('opfs');return nativeDirectory();}});
  Object.defineProperty(indexedDB,'open',{configurable:true,value:(...args)=>{state.storage.push('indexeddb');if(state.denied)fail('indexeddb');return nativeOpen(...args);}});
  for(const name of ['showDirectoryPicker','showOpenFilePicker','showSaveFilePicker'])
    Object.defineProperty(window,name,{configurable:true,value:undefined});
  const NativeWorker=window.Worker;
  window.Worker=class extends NativeWorker {
    constructor(url,options) {
      const prefix=`let storageDenied=${state.denied};
const nativeDirectory=navigator.storage.getDirectory.bind(navigator.storage),nativeOpen=indexedDB.open.bind(indexedDB);
addEventListener('message',event=>{if(event.data?.__denyStorage){storageDenied=true;event.stopImmediatePropagation();}});
const access=kind=>{postMessage({__privateStorage:kind,denied:storageDenied});if(storageDenied)throw new DOMException('Private-session storage unavailable','UnknownError');};
Object.defineProperty(navigator.storage,'getDirectory',{value:async()=>{access('worker-opfs');return nativeDirectory();}});
Object.defineProperty(indexedDB,'open',{value:(...args)=>{access('worker-indexeddb');return nativeOpen(...args);}});
`;
      const absolute=new URL(url,location.href).href;
      const source=prefix+(options?.type==='module'?`await import(${JSON.stringify(absolute)});`:`importScripts(${JSON.stringify(absolute)});`);
      super(URL.createObjectURL(new Blob([source],{type:'text/javascript'})),options);
      this.addEventListener('message',event=>{
        if(event.data?.__privateStorage){state.storage.push(event.data.__privateStorage);if(event.data.denied)state.failures.push(event.data.__privateStorage);event.stopImmediatePropagation();}
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
  state.deny=()=>{state.denied=true;for(const worker of state.workers)worker.postMessage({__denyStorage:true});};
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

export function assertFallbackChoices(folder,zip,copy,tooltip) {
  assert.equal(folder.enabled,false,'Without File System Access, Folder must be visible but disabled');
  assert.equal(zip.checked,true,'Without File System Access, Zip archive must be selected');
  assert.equal(zip.enabled,true,'The fallback ZIP format must remain usable');
  assert.equal(copy.checked,true,'Fallback Save-as must keep working in browser storage as a copy');
  assert.equal(copy.enabled,false,'Fallback Save-a-copy must be checked and disabled');
  assert.equal(typeof tooltip,'string','The disabled Folder choice must expose the actual visible tooltip text');
  assert(/folder/i.test(tooltip)&&/Chrome/i.test(tooltip)&&/Edge/i.test(tooltip),
    'The Folder tooltip must explain the browser limitation and name Chrome and Edge');
}

export function assertBrowserWarning(text,icon,privateStorage=false) {
  assert.equal(typeof text,'string','The browser-storage warning must expose its actual rendered text');
  assert.equal(icon.visible,true,'The storage warning must show the app warning icon');
  assert(/warning|exclamation/i.test(icon.text||''),'The warning uses the app warning icon, not a blank label');
  assert(/Save project as/i.test(text),'The warning must explain how to keep the project on disk');
  if(privateStorage)assert(/keep.*nothing|cannot.*keep|not.*keep|unavailable/i.test(text),
    'Unavailable storage must explain in plain words that the browser keeps nothing');
  else assert(/browser/i.test(text)&&/clear/i.test(text),
    'The first browser Save must warn that browser storage may be cleared');
  assert(!/DOMException|UnknownError|unknown transient|out of memory/i.test(text),
    'A storage fallback must never expose the raw browser exception');
}

export function checkChoiceAndWarningControls() {
  const folder={enabled:false},zip={checked:true,enabled:true},copy={checked:true,enabled:false};
  const tooltip='This browser cannot write a folder; Chrome and Edge can.';
  assertFallbackChoices(folder,zip,copy,tooltip);
  for(const [index,key,value] of [[0,'enabled',true],[1,'checked',false],[1,'enabled',false],[2,'checked',false],[2,'enabled',true]]){
    const choices=[{...folder},{...zip},{...copy}];choices[index][key]=value;
    assert.throws(()=>assertFallbackChoices(...choices,tooltip),/must/,
      'Every disabled or checked fallback choice must independently enforce the owner decision');
  }
  assert.throws(()=>assertFallbackChoices(folder,zip,copy,undefined),/actual visible tooltip/,
    'A missing tooltip observation cannot satisfy the disabled Folder explanation');
  const icon={visible:true,text:'exclamation-triangle'};
  assertBrowserWarning('Saved in this browser only. Browser data may be cleared; use Save project as…',icon);
  assertBrowserWarning('This browser keeps nothing. Use Save project as…',icon,true);
  assert.throws(()=>assertBrowserWarning('UnknownError: use Save project as…; this browser keeps nothing',icon,true),/raw browser exception/,
    'The private-storage warning must refuse raw exceptions even when plain fallback words are also present');
  assert.throws(()=>assertBrowserWarning('Browser data may be cleared; use Save project as…',{visible:false,text:'warning'}),/warning icon/,
    'A hidden warning icon cannot satisfy the visible popup requirement');
}
