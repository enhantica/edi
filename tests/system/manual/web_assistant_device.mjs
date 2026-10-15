// Device UX policy from accepted packet ce3017419, not provider readiness.
// Runs in the existing real browser/CDP driver; no replacement app or VM.
import assert from 'node:assert/strict';
export const deviceCases = [
  {id:'iphone', ua:'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1', platform:'iPhone', touch:5, available:false},
  {id:'android-tablet', ua:'Mozilla/5.0 (Linux; Android 14; Tablet) AppleWebKit/537.36 Chrome/130.0 Safari/537.36', platform:'Linux armv8l', touch:5, available:false},
  {id:'ipad-desktop', ua:'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/605.1.15 Version/18.0 Safari/605.1.15', platform:'MacIntel', touch:5, available:false},
  {id:'mac-high-touch-missing-platform', ua:'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/605.1.15 Safari/605.1.15', touch:5, available:false},
  {id:'chromeos', ua:'Mozilla/5.0 (X11; CrOS x86_64 16000.0.0) AppleWebKit/537.36 Chrome/130.0 Safari/537.36', platform:'Linux x86_64', touch:5, hints:{mobile:false,platform:'Chrome OS'}, available:true},
  {id:'chromiumos', ua:'Mozilla/5.0 (X11; CrOS x86_64 16000.0.0) AppleWebKit/537.36 Chrome/130.0 Safari/537.36', platform:'Linux x86_64', touch:0, hints:{mobile:false,platform:'Chromium OS'}, available:true},
  {id:'unknown', ua:'IndependentUnrecognizedBrowser/1', platform:'IndependentUnknown', touch:0, available:false},
  {id:'touch-narrow-windows', ua:'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36', platform:'Win32', touch:10, available:true, width:640},
  {id:'mac-desktop', ua:'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/605.1.15 Version/18.0 Safari/605.1.15', platform:'MacIntel', touch:0, available:true},
];
const reason='AI chat is not available on this device. Use a supported computer.';
const disabled=node=>(node.properties||[]).some(p=>p.name==='disabled' && p.value.value===true);
const checked=node=>(node.properties||[]).find(p=>p.name==='checked')?.value.value;
export async function inspectAssistantDevices({send,evaluate,frame,url,record,capture}) {
  // One existing browser/target, fresh app instance per immutable device decision.
  let script;
  const geometry=name=>evaluate(`window.ediControlGeometry(${JSON.stringify(name)})`);
  const panelShown=async()=> (await geometry('assistant.panel')).visible===true;
  const pointer=async(name)=>{
    const item=await geometry(name);
    assert(item.visible===true && item.width>0 && item.height>0,
      'I16/device: input uses the real visible named Qt control');
    for(const type of ['mousePressed','mouseReleased']) await send('Input.dispatchMouseEvent',
      {type,x:item.x+item.width/2,y:item.y+item.height/2,button:'left',clickCount:1});
    await frame();
  };
  const shortcut=async(modifiers)=>{
    for(const type of ['keyDown','keyUp']) await send('Input.dispatchKeyEvent',
      {type,key:'A',code:'KeyA',windowsVirtualKeyCode:65,modifiers});
    await frame();
  };
  for(const specimen of deviceCases) {
    if(script)await send('Page.removeScriptToEvaluateOnNewDocument',{identifier:script});
    const source=`(() => {
      const facts=${JSON.stringify(specimen)};
      for(const [name,value] of Object.entries({userAgent:facts.ua,platform:facts.platform,maxTouchPoints:facts.touch,userAgentData:facts.hints}))
        Object.defineProperty(navigator,name,{configurable:true,get:()=>value});
      window.__ediDeviceFixture=facts.id;
      if(!sessionStorage.getItem('edi-device-seeded-'+facts.id)) {
        localStorage.setItem('edi.settings.ini','[Assistant]\nshown=true\nwidth=347\n[Edi.Preferences]\nsideBarSide=Left\n');
        sessionStorage.setItem('edi-device-seeded-'+facts.id,'true');
      }
    })();`;
    script=(await send('Page.addScriptToEvaluateOnNewDocument',{source})).identifier;
    await send('Emulation.setDeviceMetricsOverride',
      {width:specimen.width||1280,height:768,deviceScaleFactor:1,mobile:false});
    await send('Page.navigate',{url});
    const deadline=Date.now()+90000;
    let ready=false;
    do {
      try {ready=await evaluate(`window.__ediDeviceFixture===${JSON.stringify(specimen.id)} && typeof window.ediControlGeometry==='function' && document.getElementById('screen')?.style.display==='block'`);}
      catch(error) {if(!/context|navigat/i.test(error.message))throw error;}
      if(!ready)await frame();
    } while(!ready && Date.now()<deadline);
    assert(ready,'I16/device: each immutable navigator fixture reaches the actual initialized app');
    let tree=await send('Accessibility.getFullAXTree');
    const activate=tree.nodes.find(n=>/(?:activate|enable) screen reader/i.test(n.name?.value||'') && n.role?.value==='button');
    if(activate) {
      const node=await send('DOM.resolveNode',{backendNodeId:activate.backendDOMNodeId});
      await send('Runtime.callFunctionOn',{objectId:node.object.objectId,functionDeclaration:'function(){this.click();}'});
      await frame();
    }
    const toggle=await geometry('assistant.toggle');
    assert(toggle.visible===true && toggle.enabled===specimen.available,
      'I16/device: toolbar stays visible and follows eligibility, never viewport/touch alone');
    assert.equal(await panelShown(),specimen.available,
      'I16/device: restored shown=true is effective only on eligible devices');
    // Eligibility was checked at the narrow size; further actions use the normal viewport.
    await send('Emulation.setDeviceMetricsOverride',{width:1280,height:768,deviceScaleFactor:1,mobile:false});
    await frame();
    tree=await send('Accessibility.getFullAXTree');
    const toggleAX=tree.nodes.find(n=>!n.ignored && n.role?.value==='button' && /Show or hide assistant/.test(n.name?.value||''));
    assert(toggleAX && disabled(toggleAX)===!specimen.available,
      'I16/device: real accessible AI-open action reports the same disabled state');
    if(!specimen.available)assert((toggleAX.description?.value||'').includes(reason),
      'I16/device: disabled toolbar exposes the same readable accessibility explanation');
    await pointer('assistant.toggle');
    assert.equal(await panelShown(),false,
      'I16/device: disabled pointer cannot open; eligible pointer retains normal hide behavior');
    for(const modifiers of [10,12]) {
      await shortcut(modifiers);
      assert.equal(await panelShown(),specimen.available,
        'I16/device: Ctrl/Meta+Shift+A cannot reopen unsupported entry and still opens a computer');
      if(specimen.available)await pointer('assistant.toggle');
    }
    await pointer('appBar.button.preferences');await pointer('preferences.tab.appearance');
    const checkbox=await geometry('preferences.assistantShown');
    assert(checkbox.visible===true && checkbox.enabled===specimen.available,
      'I16/device: the actual preference consumes the same eligibility');
    tree=await send('Accessibility.getFullAXTree');
    if(!specimen.available) {
      assert(tree.nodes.some(n=>!n.ignored && (n.name?.value||'').includes(reason)),
        'I16/device: a visible wrapped explanation is discoverable without hovering');
      const boxes=tree.nodes.filter(n=>!n.ignored && n.role?.value==='checkbox' && disabled(n));
      assert(boxes.length===1 && checked(boxes[0])===false,
        'I16/device: the disabled Assistant preference is effectively unchecked in actual AX');
      await pointer('preferences.assistantShown');
      assert.equal(await panelShown(),false,'I16/device: disabled preference input cannot open chat');
    }
    // Close a real popup with Escape, preserving normal workflow access.
    for(const type of ['keyDown','keyUp'])await send('Input.dispatchKeyEvent',{type,key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
    await frame();
    await pointer('appBar.button.preferences');await pointer('preferences.tab.appearance');
    assert.equal((await geometry('preferences.assistantShown')).enabled,specimen.available,
      'I16/device: reopening Preferences cannot bypass the captured availability decision');
    for(const type of ['keyDown','keyUp'])await send('Input.dispatchKeyEvent',{type,key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
    await frame();
    if(specimen.available) {
      await pointer('assistant.toggle');
      tree=await send('Accessibility.getFullAXTree');
      assert(tree.nodes.some(n=>!n.ignored && /Sign in with ChatGPT|browser AI connection.*unavailable|connection.*unavailable.*build/i.test(n.name?.value||'')),
        'I12/device: eligible computer remains truthfully disconnected, not provider-ready');
      const sendControl=await geometry('assistant.send');
      assert(sendControl.enabled===false,'I12/device: device eligibility never enables unconnected inference');
    }
    const stored=await evaluate(`localStorage.getItem('edi.settings.ini')`);
    if(!specimen.available)assert(/\[Assistant\][\s\S]*?shown=true/.test(stored||''),
      'I16/device: platform gating does not erase the saved assistant preference');
    assert((await geometry('appBar.button.preferences')).enabled===true,
      'I16/device: ordinary scientific-shell controls remain usable');
    await record({fixture:specimen.id,expectedAvailable:specimen.available,toggle,checkbox,stored});
    await capture(specimen.id);
  }
  if(script)await send('Page.removeScriptToEvaluateOnNewDocument',{identifier:script});
}
