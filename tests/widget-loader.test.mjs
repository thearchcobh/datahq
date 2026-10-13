import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
import bundle from '../supabase/functions/arch-labour-widget/widget-bundle.mjs';
const source=fs.readFileSync('widgets/Arch-Labour-Loader.js','utf8');
const data={version:1,date:'2026-10-13',asOf:'2026-10-13T17:35:00Z',warnings:[],today:{pct:32,sales:100,labour:32},week:{pct:32},lastWeek:{pct:29.8},lastFiveDays:[{date:'2026-10-12',pct:41}]};
async function test(mode,seed){
 const disk=new Map(seed?[['/library/arch-widget-code-v1.json',JSON.stringify(bundle)]]:[]);let shown,labels=[];
 const element=()=>({addText(s){labels.push(s);return{}},addStack:()=>element(),addSpacer(){},layoutVertically(){},setPadding(){},async presentMedium(){}});
 const ctx={Intl,Date,JSON,Math,Error,encodeURIComponent,config:{runsInWidget:true},Keychain:{contains:()=>true,get:()=> 'test',remove(){}},FileManager:{local:()=>({joinPath:(a,b)=>a+'/'+b,libraryDirectory:()=>'/library',cacheDirectory:()=>'/cache',fileExists:p=>disk.has(p),readString:p=>disk.get(p),writeString:(p,s)=>disk.set(p,s),remove:p=>disk.delete(p)})},Request:class{constructor(url){this.url=url;this.response={statusCode:200}}async loadJSON(){if(!this.url.includes('?asset='))return data;if(mode==='offline')throw Error('offline');if(mode==='unauthorized'){this.response.statusCode=401;return{}};if(mode==='syntax')return{...bundle,code:'! syntax error !'};if(mode==='runtime')return{...bundle,code:'throw Error("bad update")'};return bundle;}},ListWidget:class{constructor(){return element()}},Color:class{},Font:{boldSystemFont:()=>'',systemFont:()=>''},Script:{name:()=> 'Arch Labour',setWidget:w=>shown=w,complete(){}}};
 await vm.runInNewContext('(async()=>{'+source+'})()',ctx);
 assert.ok(shown);return{disk,labels};
}
const updated=await test('ok',false);assert.ok(updated.labels.includes('Last week  29.8%'));assert.ok(updated.labels.includes('MON'));assert.ok(!updated.labels.includes('TARGET 32%'));
assert.ok((await test('ok',false)).disk.has('/library/arch-widget-code-v1.json'));
for(const mode of ['offline','syntax','runtime'])assert.ok((await test(mode,true)).labels.some(x=>x.includes('SAVED CODE')));
assert.ok((await test('offline',false)).labels.includes('offline'));
const denied=await test('unauthorized',true);assert.equal(denied.disk.size,0);assert.ok(denied.labels.includes('Widget access key rejected.'));
console.log('PASS: first download, offline cache, invalid syntax, runtime rollback, first-run offline, rejected credentials.');
