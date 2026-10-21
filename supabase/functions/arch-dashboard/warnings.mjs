export const WARNING_FEED='https://www.met.ie/Open_Data/json/warning_EI04.json';
const text=value=>String(value||'').replace(/<[^>]*>/g,' ').replace(/&nbsp;/g,' ').replace(/&amp;/g,'&').replace(/\s+/g,' ').trim();
export function parseWarnings(payload,now=Date.now()) {
 if(!Array.isArray(payload))throw Error('Invalid warning feed');
 const items=payload.filter(w=>['yellow','orange','red'].includes(String(w.level).toLowerCase()) &&
  w.regions?.includes('EI04') && w.status!=='Cancel' &&
  Number.isFinite(Date.parse(w.onset)) && Date.parse(w.expiry)>now && Date.parse(w.expiry)>Date.parse(w.onset))
 .map(w=>({id:w.capId,level:w.level.toLowerCase(),headline:text(w.headline),description:text(w.description),onset:w.onset,expiry:w.expiry,issued:w.issued,updated:w.updated}));
 const seen=new Set();return items.filter(w=>{const key=[w.level,w.headline,w.onset,w.expiry,w.description].join("|");if(seen.has(key))return false;seen.add(key);return true;});
}
let cached=null, fetchedAt=0;
export async function getWarnings(){
 if(cached&&Date.now()-fetchedAt<300000)return cached;
 try{
  const response=await fetch(WARNING_FEED,{signal:AbortSignal.timeout(10000),headers:{Accept:'application/json'}});
  if(!response.ok)throw Error('Warning feed HTTP '+response.status);
  const items=parseWarnings(await response.json());
  fetchedAt=Date.now();cached={available:true,items,fetchedAt:new Date(fetchedAt).toISOString(),source:WARNING_FEED};
  return cached;
 }catch(e){console.error('Met Eireann warning feed unavailable',String(e));return {available:false,items:[],fetchedAt:null,source:WARNING_FEED};}
}
