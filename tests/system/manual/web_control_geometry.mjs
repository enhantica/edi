// Read current Qt geometry before trusted pointer input; synthetic states are not UI evidence.
import assert from 'node:assert/strict';

export async function controlPointer(evaluate, objectName, containerName) {
  assert.equal(await evaluate('typeof window.ediControlGeometry'), 'function',
    'The web app must expose current native control geometry when its AX rectangles are stale');
  const read = async name => {
    const item = await evaluate(`window.ediControlGeometry(${JSON.stringify(name)})`);
    assert(item?.objectName === name && item.visible === true && item.enabled === true,
      'The pointer target must be the actual named, effectively visible and enabled native Qt control');
    assert(['x','y','width','height'].every(key => typeof item[key] === 'number' && Number.isFinite(item[key])) &&
      item.width > 0 && item.height > 0 && item.x >= 0 && item.y >= 0 &&
      item.x + item.width <= 1280 && item.y + item.height <= 768,
      'Native control geometry must be finite, positive and wholly inside the actual fixed browser viewport');
    return item;
  };
  const item = await read(objectName);
  if (containerName) {
    const container = await read(containerName);
    assert(item.x >= container.x && item.y >= container.y &&
      item.x + item.width <= container.x + container.width &&
      item.y + item.height <= container.y + container.height,
      'The actual catalogue row must be wholly inside its visible list before trusted pointer input');
  }
  return {x:item.x + item.width/2,y:item.y + item.height/2};
}

// Qt editor focus can scroll its accessibility host; restore the real fixed canvas before input.
export async function restoreCanvasViewport(evaluate) {
  const viewport = await evaluate(`(() => {
    const canvases=[];
    const walk=root=>{for(const item of root.querySelectorAll('*')) {
      if(item.tagName==='CANVAS') canvases.push(item);
      if(item.shadowRoot) walk(item.shadowRoot);
    }};
    walk(document.getElementById('screen'));
    const visible=canvases.filter(item=>item.getBoundingClientRect().width>0);
    if(visible.length!==1) throw Error('the published app must have one visible canvas');
    const canvas=visible[0], before=canvas.getBoundingClientRect().toJSON(), scrolled=[];
    for(let item=canvas.parentElement;item;item=item.parentElement||item.getRootNode().host) {
      if(item.scrollTop||item.scrollLeft) {
        scrolled.push({x:item.scrollLeft,y:item.scrollTop}); item.scrollTo(0,0);
      }
    }
    return {before,after:canvas.getBoundingClientRect().toJSON(),scrolled};
  })()`);
  assert.equal(viewport?.after?.x,0,'Trusted app pointers require the actual fixed canvas origin');
  assert.equal(viewport.after.y,0,'Trusted app pointers require the actual fixed canvas origin');
  assert.equal(viewport.after.width,1280,'Trusted app pointers require the actual fixed canvas width');
  assert.equal(viewport.after.height,768,'Trusted app pointers require the actual fixed canvas height');
  return viewport;
}
