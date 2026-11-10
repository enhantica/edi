"""Exercise real input ordering with deterministic delayed viewport transitions."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_real_input_waits_for_motion_and_rendering_but_refuses_a_stuck_viewport():
    source = (ROOT / 'tests/unit/app/UiInteraction.js').read_text().replace('.pragma library', '')
    driver = r"""
function scenario(kind) {
    let frames = 0, presses = 0, updates = 0, message = "", renderedBeforePress = false;
    const root = {visible:true,width:400,height:300,children:[],moving:true};
    const tab = {objectName:"sideBar.tab.extras",visible:true,enabled:true,
                 width:50,height:25,checked:false,parent:root,children:[]};
    root.children = [tab];
    const window = {contentItem:root,contentArea:[root],appBarCentralTabs:{currentIndex:0},
                    update() { ++updates; }};
    function tick() { ++frames; if (kind !== "stuck" && frames >= 2) root.moving = false; }
    function require(ok, why) { if (!ok) throw Error(why); }
    const test = {
        verify:require,
        waitForPolish() { return true; },
        waitForRendering() {
            require(updates > 0, "A rendering barrier must request a frame");
            --updates; tick(); renderedBeforePress = presses === 0; return true;
        },
        tryVerify(fn, deadline, why) {
            for (let n=0;n<8 && !fn();++n) tick();
            require(fn(),why);
        },
        mouseClick(item) {
            ++presses;
            if (!root.moving && renderedBeforePress) item.checked = true;
        },
        tryCompare(item, key, value, deadline, why) {
            for (let n=0;n<8 && item[key]!==value;++n) tick();
            require(item[key]===value,why);
        }
    };
    try { click(test,null,window,"sideBar.tab.extras"); }
    catch (error) { message = error.message; }
    return {kind,presses,checked:tab.checked,message};
}
process.stdout.write(JSON.stringify([scenario("delayed"),scenario("stuck")]));
"""
    outcome = subprocess.run(
        ['node', '-e', source + driver], capture_output=True, text=True, timeout=3, check=False
    )
    assert outcome.returncode == 0, (
        'The real input actor must execute in the delayed-motion control'
    )
    delayed, stuck = json.loads(outcome.stdout)
    assert delayed['presses'] == 1 and delayed['checked'] and not delayed['message'], (
        'A tab press must wait for viewport motion and a rendered settled layout before input'
    )
    assert stuck['presses'] == 0 and 'before locating' in stuck['message'], (
        'A stuck viewport must fail before tab input and expose the product stall'
    )
