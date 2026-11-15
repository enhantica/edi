import {createInterface} from 'node:readline';
import {openBrowser,observeEvent} from './events.mjs';

const browser = await openBrowser();
process.stdout.write(JSON.stringify({ready:true})+'\n');
try {
  for await (const line of createInterface({input:process.stdin})) {
    const {root,pagePath,eventPath,instant} = JSON.parse(line);
    let result = {instant,ok:true,error:''};
    try {await observeEvent(root,pagePath,eventPath,instant,browser);}
    catch (error) {result = {instant,ok:false,error:String(error.stack || error)};}
    process.stdout.write(JSON.stringify(result)+'\n');
  }
} finally {await browser.close();}
