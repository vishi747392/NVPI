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
assert.ok(!page.includes('rashmi-aastha-sample-flat.mp4'),'Broken local video returned');
assert.ok(!page.includes('site-progress-video.mp4'),'Broken local video returned');
assert.ok(page.includes("daily==='fashion'"),'Direct fashion share-link routing missing');
console.log('NVPI static smoke checks passed:',tabs.length,'tabs; Facebook Share; Daily Desk; no deleted local media links.');
