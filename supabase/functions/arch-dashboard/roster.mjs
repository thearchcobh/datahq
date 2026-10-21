// Average one latest wage per employee, so frequent shifts do not skew the rate.
export function costRoster(shifts,cards) {
 const usable=cards.filter(c=>c.status!=='DELETED'&&c.team_member_id&&c.hourly_rate_amount!=null&&Number.isFinite(Number(c.hourly_rate_amount))&&Number(c.hourly_rate_amount)>0).sort((a,b)=>Date.parse(b.start_at)-Date.parse(a.start_at));
 const average=rows=>{const latest=new Map();for(const c of rows)if(!latest.has(c.team_member_id))latest.set(c.team_member_id,Number(c.hourly_rate_amount));return latest.size?Math.round([...latest.values()].reduce((a,b)=>a+b,0)/latest.size):null;};
 return shifts.map((s,i)=>{
  const assigned=!!s.team_member_id;
  const role=usable.filter(c=>s.job_id&&c.job_id===s.job_id);
  const wage=assigned?role.find(c=>c.team_member_id===s.team_member_id):null;
  const roleAverage=assigned?null:average(role);
  const amount=assigned?wage?.hourly_rate_amount??null:roleAverage??average(usable);
  return {...s,team_member_id:assigned?s.team_member_id:'unassigned:'+s.id+':'+i,hourly_rate_amount:amount,wage_estimated:!assigned&&amount!=null,wage_basis:roleAverage!=null?'role average':'staff average',raw_json:{breaks:[],wage:wage?.raw_json?.wage||{title:s.job_title||role[0]?.raw_json?.wage?.title||''}},status:'CLOSED'};
 });
}
