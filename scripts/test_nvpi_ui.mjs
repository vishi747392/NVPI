import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const page=fs.readFileSync(new URL('../index.html', import.meta.url),'utf8');
const script=page.match(/<script>([\s\S]*?)<\/script>/);
assert.ok(script?.[1], 'Expected inline NVPI script');
new vm.Script(script[1],{filename:'index.html script'});
const tabs=['home','property','sports','reels','fashion','share','games','tools'];
for(const id of tabs){
  assert.ok(page.includes('id="'+id+'"'), 'Missing '+id+' section');
  assert.ok(page.includes('data-tab="'+id+'"'), 'Missing '+id+' bottom tab');
}
assert.ok(page.includes('https://www.facebook.com/sharer/sharer.php?u='),'Facebook share dialog missing');
assert.ok(page.includes('copyNVPIUrl'),'Copy link fallback missing');
assert.ok(page.includes('shareNVPIOnFacebook'),'Share buttons missing');
assert.ok(page.includes("loadDailyDesk()"),'Daily updates not initialized');
assert.ok(page.includes("'/daily/updates.json'"),'11 AM daily feed source removed');
assert.ok(page.includes('naigaon-property-guide.vishi747392.chatgpt.site/assets/naigaon-actual-drone-view.jpg'),'Original site photo not restored');
assert.ok(page.includes('naigaon-property-guide.vishi747392.chatgpt.site/assets/rashmi-aastha-sample-flat.mp4'),'Original video source not restored');
assert.ok(page.includes('data-fbshare'),'Reel card Facebook Share option missing');
assert.ok(page.includes('data-systemshare'),'Reel card share option missing');
assert.ok(page.includes('function openDailyArticle()'),'Daily article reader missing');
assert.ok(page.includes('role="navigation" aria-label="Explore NVPI sections"'),'Home category chips not clickable');
assert.ok(page.includes("daily==='fashion'"),'Direct fashion share-link routing missing');
console.log('NVPI static smoke checks passed:',tabs.length,'tabs; Facebook Share; Daily Desk; original photos, real archived video sources and clickable home categories.');
