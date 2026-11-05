import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:390,height:844}});
const errors=[];
page.on('pageerror',err=>errors.push(err.message));
page.on('console',msg=>{if(msg.type()==='error'&&!/net::ERR|favicon/.test(msg.text()))errors.push(msg.text())});
await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded'});
await page.locator('#home.active').waitFor();
await page.locator('.visual-card img').first().evaluate(img=>new Promise(resolve=>{
  if(img.complete)return resolve();
  img.addEventListener('load',resolve,{once:true});
  img.addEventListener('error',resolve,{once:true});
  setTimeout(resolve,12000);
}));
const photos=await page.locator('img[src*="naigaon-property-guide.vishi747392.chatgpt.site"]').evaluateAll(images=>images.map(img=>({src:img.src,loaded:img.complete&&img.naturalWidth>0})));
console.log('RESTORED_IMAGE_LOAD_CHECK',JSON.stringify(photos));
assert.ok(photos.some(img=>img.loaded),'Original master photo host is unreachable — photos still missing');

const expected=[['Real Estate','property'],['All Sports','sports'],['Reels','reels'],['Fashion','fashion'],['Games','games'],['Buyer Tools','tools']];
for(const [label,id] of expected){
  await page.locator('[data-tab=home]').click();
  await page.getByRole('navigation',{name:'Explore NVPI sections'}).getByRole('button',{name:label}).click();
  assert.equal(await page.locator('#'+id).evaluate(x=>x.classList.contains('active')),true,label+' chip should navigate');
}
await page.locator('[data-tab=property]').click();
await page.locator('#property .report-actions .open').first().click();
await page.locator('#reportDetail.active').waitFor();
assert.ok((await page.locator('#reportDetail').innerText()).includes('Related full NVPI guide'));
await page.locator('#reportDetail .back-button').click();
await page.locator('#property.active').waitFor();
await page.locator('[data-tab=reels]').click();
await page.locator('#reels.active').waitFor();
assert.ok(await page.locator('#videoCards .video-card').count()>=4);
assert.equal(await page.locator('#videoCards [data-fbshare]').count(),await page.locator('#videoCards .video-card').count());
assert.equal(await page.locator('#videoCards [data-systemshare]').count(),await page.locator('#videoCards .video-card').count());
await page.locator('#videoCards [data-play]').first().click();
await page.locator('#videoPlayerWrap.show').waitFor();
await page.locator('#videoClose').click();
await page.locator('[data-tab=home]').click();
await page.locator('.category-card').first().click();
await page.locator('#property.active').waitFor();
const news=page.locator('#dailyNews .read-article-btn');
await page.waitForTimeout(500);
if(await news.count()){
  await news.first().click();
  await page.locator('#dailyArticle.active').waitFor();
  assert.ok((await page.locator('#dailyArticle').innerText()).includes('original source'));
}
assert.deepEqual(errors,[],'No unexpected JS errors: '+errors.join(', '));
console.log('PASS: All hero category chips, article opening, real videos, reel share buttons and in-app navigation.');
await browser.close();
