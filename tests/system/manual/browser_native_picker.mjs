// Observe actual Qt picker options while replacing only the unautomatable OS chooser.
import assert from 'node:assert/strict';

export function assertNativePickerCapture(capture, extensions, multiple) {
  assert(capture && Array.isArray(capture.calls) && capture.calls.length===1,
    'One actual Qt Load action must make exactly one native picker request');
  const options=capture.calls[0];
  assert.equal(options.multiple,multiple,
    'The actual Qt picker retains the caller-owned selection cardinality');
  assert.equal(options.excludeAcceptAllOption,true,
    'The normalized Qt filter retains its exact extension restriction');
  assert(Array.isArray(options.types) && options.types.length===1,
    'The actual Qt picker has exactly one declared file type');
  assert.deepEqual(Object.keys(options.types[0].accept || {}),['application/octet-stream'],
    'The actual Qt filter retains its declared MIME family');
  assert.deepEqual(options.types[0].accept['application/octet-stream'],extensions,
    'The actual Qt picker receives separate ordered extensions without a comma-bearing suffix');
  assert.equal(capture.reads,1,
    'Qt must read the returned real file handle exactly once');
}

export async function installNativePickerTransport(evaluate, bytes, name) {
  const payload=Buffer.from(bytes).toString('base64');
  await evaluate(`(() => {
    if (window.__e04NativePickerTransport) throw Error('Native picker transport is already installed');
    const previous=Object.getOwnPropertyDescriptor(window,'showOpenFilePicker');
    const capture={calls:[],reads:0,previous};
    window.__e04NativePickerTransport=capture;
    Object.defineProperty(window,'showOpenFilePicker',{configurable:true,writable:true,value:async options=>{
      capture.calls.push(JSON.parse(JSON.stringify(options)));
      if (capture.calls.length!==1) throw Error('Native picker request repeated');
      return [{kind:'file',name:${JSON.stringify(name)},getFile:async()=>{
        ++capture.reads;
        const bytes=Uint8Array.from(atob(${JSON.stringify(payload)}),c=>c.charCodeAt(0));
        return new File([bytes],${JSON.stringify(name)},{type:'application/octet-stream'});
      }}];
    }});
    return true;
  })()`);
  return {
    snapshot:()=>evaluate(`(() => {const c=window.__e04NativePickerTransport;
      return {calls:c.calls,reads:c.reads};})()`),
    restore:()=>evaluate(`(() => {const c=window.__e04NativePickerTransport;
      if (!c) throw Error('Native picker transport is missing');
      if (c.previous) Object.defineProperty(window,'showOpenFilePicker',c.previous);
      else delete window.showOpenFilePicker;
      delete window.__e04NativePickerTransport;
      return true;
    })()`),
  };
}

export function nativePickerTransportControls() {
  const good={calls:[{multiple:false,excludeAcceptAllOption:true,
    types:[{accept:{'application/octet-stream':['.cif','.edi']}}]}],reads:1};
  assertNativePickerCapture(good,['.cif','.edi'],false);
  const mutate=change=>{const record=structuredClone(good);change(record);return record;};
  for(const bad of [null,{calls:[],reads:0},
    mutate(c=>c.calls.push(structuredClone(c.calls[0]))),
    mutate(c=>c.calls[0].multiple=true),
    mutate(c=>delete c.calls[0].multiple),
    mutate(c=>c.calls[0].excludeAcceptAllOption=false),
    mutate(c=>c.calls[0].types=[]),
    mutate(c=>c.calls[0].types.push(structuredClone(c.calls[0].types[0]))),
    mutate(c=>c.calls[0].types[0].accept={'text/plain':['.cif','.edi']}),
    mutate(c=>c.calls[0].types[0].accept['application/octet-stream']=['.cif,.edi']),
    mutate(c=>c.calls[0].types[0].accept['application/octet-stream']=['.edi','.cif']),
    mutate(c=>c.calls[0].types[0].accept['application/octet-stream']=['.cif']),
    mutate(c=>c.reads=0),mutate(c=>c.reads=2)]) {
    assert.throws(()=>assertNativePickerCapture(bad,['.cif','.edi'],false),assert.AssertionError,
      'Missing/repeated calls, wrong cardinality, invalid filter order/shape or unread handles must refuse');
  }
}
