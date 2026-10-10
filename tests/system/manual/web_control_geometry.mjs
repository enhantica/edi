// Read current Qt geometry before trusted pointer input; synthetic states are not UI evidence.
import assert from 'node:assert/strict';

export async function controlPointer(evaluate, objectName) {
  assert.equal(await evaluate('typeof window.ediControlGeometry'), 'function',
    'The web app must expose current native control geometry when its AX rectangles are stale');
  const item = await evaluate(`window.ediControlGeometry(${JSON.stringify(objectName)})`);
  assert(item?.objectName === objectName && item.visible === true && item.enabled === true,
    'The pointer target must be the actual named, effectively visible and enabled native Qt control');
  assert(['x','y','width','height'].every(key => typeof item[key] === 'number' && Number.isFinite(item[key])) &&
    item.width > 0 && item.height > 0 && item.x >= 0 && item.y >= 0 &&
    item.x + item.width <= 1280 && item.y + item.height <= 768,
    'Native control geometry must be finite, positive and wholly inside the actual fixed browser viewport');
  return {x:item.x + item.width/2,y:item.y + item.height/2};
}
