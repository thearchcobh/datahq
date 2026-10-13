// The Arch • Labour. Add this script to a medium Scriptable Home Screen widget.
const ENDPOINT='https://tqrgwcixxifzdzsphdxj.supabase.co/functions/v1/arch-labour-widget';
const KEY='thearch.labour.widget.token.v1';
// Personal installation copies can provide this token; never commit a real token.
const INSTALL_TOKEN='';
if(INSTALL_TOKEN&&!Keychain.contains(KEY))Keychain.set(KEY,INSTALL_TOKEN);
if(!Keychain.contains(KEY)&&!config.runsInWidget){
 const a=new Alert();a.title='Connect The Arch';a.message='Enter your private widget access key.';a.addSecureTextField('Access key');a.addAction('Connect');a.addCancelAction('Cancel');
 if(await a.presentAlert()===0)Keychain.set(KEY,a.textFieldValue(0).trim());
}
const fm=FileManager.local(), cache=fm.joinPath(fm.cacheDirectory(),'arch-labour-v1.json');
let data=null, offline=false, error='Run this script to connect';
if(Keychain.contains(KEY)){
 try{
  const r=new Request(ENDPOINT);r.headers={Authorization:'Bearer '+Keychain.get(KEY)};r.timeoutInterval=25;
  const d=await r.loadJSON();if(r.response.statusCode!==200||d.version!==1){if(r.response.statusCode===401){Keychain.remove(KEY);if(fm.fileExists(cache))fm.remove(cache);}throw Error(d.error||'Unavailable');}
  data=d;fm.writeString(cache,JSON.stringify(d));
 }catch(e){offline=true;error=String(e.message||e);if(fm.fileExists(cache)){try{data=JSON.parse(fm.readString(cache));}catch{}}}
}
const w=new ListWidget();w.setPadding(15,17,13,17);w.backgroundColor=new Color('192B29');
w.url='scriptable:///run?scriptName='+encodeURIComponent(Script.name());w.refreshAfterDate=new Date(Date.now()+15*60000);
const white=new Color('FAF8F1'),muted=new Color('BAC8C2'),amber=new Color('F1C575'),green=new Color('A4D4AE'),red=new Color('FF9E91');
function text(parent,s,size,color=white,bold=false){const t=parent.addText(s);t.font=bold?Font.boldSystemFont(size):Font.systemFont(size);t.textColor=color;t.lineLimit=1;t.minimumScaleFactor=0.7;return t;}
const top=w.addStack();text(top,'THE ARCH',12,white,true);top.addSpacer();text(top,'TARGET 32%',10,muted,true);w.addSpacer(9);
if(data){
 const age=Date.now()-Date.parse(data.asOf), stale=data.stale||age>90*60000||offline;
 const currentDay=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Dublin',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 const oldDate=data.date!==currentDay;
 const signal=p=>stale||data.warnings.length?amber:p==null?muted:p<=32?green:p<=35?amber:red;
 const pct=p=>p==null?'—':p.toFixed(1)+'%';
 const euro=n=>n==null?'—':'€'+Math.round(n).toLocaleString('en-IE');
 const row=w.addStack();const left=row.addStack();left.layoutVertically();
 text(left,oldDate?data.date:'TODAY · EST.',10,muted,true);text(left,pct(data.today.pct),36,signal(data.today.pct),true);
 row.addSpacer();const right=row.addStack();right.layoutVertically();text(right,'WEEK TO DATE',10,muted,true);text(right,pct(data.week.pct),27,signal(data.week.pct),true);
 w.addSpacer(5);text(w,`${euro(data.today.labour)} labour  /  ${euro(data.today.sales)} net sales`,11,white);
 w.addSpacer();
 const dt=new Date(data.asOf);const stamp=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Dublin',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}).format(dt);
 text(w,(offline?'OFFLINE · ':stale?'STALE · ':'')+stamp+' Irish',9,stale?amber:muted);
 if(data.warnings.length)text(w,data.warnings[0],9,amber);
}else{text(w,'Labour unavailable',21,amber,true);w.addSpacer(8);text(w,error,11,muted);}
Script.setWidget(w);if(!config.runsInWidget)await w.presentMedium();Script.complete();
