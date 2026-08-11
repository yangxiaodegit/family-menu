let hostPeer=null;
let isLocalHost=false;
let memberPeer=null;
let hostConnection=null;
let hostConnections=[];
let sharedSnapshot=null;

function liveName(){
  return ($("#liveName")?.value||localStorage.getItem("familyLiveName")||"家人").trim()||"家人";
}
function persistLiveName(){const n=liveName();localStorage.setItem("familyLiveName",n);return n}
function setLiveStatus(text,online=false){
  const el=$("#liveStatus");if(!el)return;el.textContent=text;el.style.background=online?"#e7f6ec":"#f0f2ed";el.style.color=online?"#267a44":"#6b7168";
}
function setHostStatus(text,online=false){
  const el=$("#hostStatus");if(!el)return;el.textContent=text;el.style.background=online?"#e7f6ec":"#f0f2ed";el.style.color=online?"#267a44":"#6b7168";
}
function familyShareUrl(){
  const u=new URL(location.href);u.search="";u.hash="live";return u.toString();
}
function initFamilyLink(){
  if($("#familyLink"))$("#familyLink").value=familyShareUrl();
  if($("#liveName"))$("#liveName").value=localStorage.getItem("familyLiveName")||"";
  renderHostStats();
}
async function loadPeerJS(){
  if(typeof Peer!=="undefined")return;
  await loadScriptOnce("https://unpkg.com/peerjs@1.5.5/dist/peerjs.min.js","peerjs");
}
function saveLiveNameAndReconnect(){persistLiveName();ensureFamilyConnection()}
function hostHistory(){
  try{return JSON.parse(localStorage.getItem("familyMenuHistory_v8")||"[]")}catch(e){return []}
}
function saveHostHistory(rows){localStorage.setItem("familyMenuHistory_v8",JSON.stringify(rows))}
function currentSharedSnapshot(){
  return {
    pantry:state.pantry,
    members:state.members,
    settings:state.settings,
    budget:state.budget,
    menu:state.menu,
    history:hostHistory(),
    votes:liveState.votes||{},
    onlineMembers:liveState.members||{},
    updatedAt:new Date().toISOString()
  };
}
function applySharedSnapshot(snap){
  if(!snap)return;
  sharedSnapshot=snap;
  if(Array.isArray(snap.pantry))state.pantry=clone(snap.pantry);
  if(Array.isArray(snap.members))state.members=clone(snap.members);
  if(snap.settings)state.settings=clone(snap.settings);
  if(snap.budget)state.budget=clone(snap.budget);
  if(Array.isArray(snap.menu))state.menu=clone(snap.menu);
  if(Array.isArray(snap.history))saveHostHistory(clone(snap.history));
  liveState.votes=clone(snap.votes||{});
  liveState.members=clone(snap.onlineMembers||{});
  save();allRender();renderHistory();renderLiveState();renderLiveDishList();renderHostStats();
}
function sendHostSnapshot(conn){
  try{if(conn?.open)conn.send({type:"snapshot",snapshot:currentSharedSnapshot()})}catch(e){}
}
function broadcastHostSnapshot(){
  sharedSnapshot=currentSharedSnapshot();
  hostConnections.forEach(sendHostSnapshot);
  renderHostStats();
}
async function startLocalHost(){return ensureFamilyConnection()}
function stopLocalHost(reset=true){
  try{hostConnections.forEach(c=>c.close())}catch(e){}
  try{hostPeer?.destroy()}catch(e){}
  hostConnections=[];hostPeer=null;isLocalHost=false;
  if(reset)setHostStatus("未启动");
  renderHostStats();
}
function handleHostClientMessage(conn,data){
  if(!data||!data.type)return;
  if(data.type==="hello"){
    conn._memberId=data.member.id;
    liveState.members[data.member.id]=data.member;
    broadcastHostSnapshot();
  }else if(data.type==="vote"){
    applyVote(data.memberId,data.dishId,data.on);
    broadcastHostSnapshot();
  }else if(data.type==="clearMine"){
    Object.keys(liveState.votes).forEach(d=>{
      liveState.votes[d]=(liveState.votes[d]||[]).filter(id=>id!==data.memberId);
      if(!liveState.votes[d].length)delete liveState.votes[d];
    });
    broadcastHostSnapshot();
  }else if(data.type==="requestSnapshot"){
    sendHostSnapshot(conn);
  }else if(data.type==="saveToday"){
    saveTodayToHistory(true);
  }
}
async function joinFamilyAsMember(){return ensureFamilyConnection()}
function applyVote(memberId,dishId,on){
  liveState.votes[dishId]=liveState.votes[dishId]||[];
  const has=liveState.votes[dishId].includes(memberId);
  if(on&&!has)liveState.votes[dishId].push(memberId);
  if(!on&&has)liveState.votes[dishId]=liveState.votes[dishId].filter(x=>x!==memberId);
  if(!liveState.votes[dishId].length)delete liveState.votes[dishId];
}
function toggleLiveVote(dishId){
  const has=(liveState.votes[dishId]||[]).includes(liveGuestId);
  if(isLocalHost){
    applyVote(liveGuestId,dishId,!has);broadcastHostSnapshot();
  }else if(hostConnection?.open){
    hostConnection.send({type:"vote",memberId:liveGuestId,dishId,on:!has});
  }else toast("暂时未连接，正在重试");
}
function clearMyVotes(){
  if(isLocalHost){
    Object.keys(liveState.votes).forEach(d=>{
      liveState.votes[d]=liveState.votes[d].filter(x=>x!==liveGuestId);
      if(!liveState.votes[d].length)delete liveState.votes[d];
    });
    broadcastHostSnapshot();
  }else if(hostConnection?.open)hostConnection.send({type:"clearMine",memberId:liveGuestId});
}
function renderLiveState(){
  if(!$("#liveMembers"))return;
  const members=Object.values(liveState.members||{});
  $("#liveMembers").innerHTML=members.length?members.map(m=>`<span class="live-person">${m.online!==false?'<i class="live-dot"></i>':''}${m.name}</span>`).join(""):`<span class="note">暂无在线成员</span>`;
  const rows=Object.entries(liveState.votes||{}).map(([dishId,voters])=>{
    const d=state.dishes.find(x=>x.id===dishId);if(!d)return null;
    const names=voters.map(id=>liveState.members[id]?.name||"家人");
    return {d,names,count:names.length};
  }).filter(Boolean).sort((a,b)=>b.count-a.count);
  $("#liveOrderSummary").innerHTML=rows.length?rows.map(x=>`<div class="menu-item"><div><b>${x.d.name}</b><div class="vote-row">${x.names.map(n=>`<span class="voter">${n}</span>`).join("")}</div></div><span class="tag">${x.count}人想吃</span></div>`).join(""):`<div class="empty">还没人点菜</div>`;
}
function renderLiveDishList(){
  const el=$("#liveDishList");if(!el)return;
  const q=($("#liveDishSearch")?.value||"").trim();
  const arr=state.dishes.filter(d=>!q||d.name.includes(q)||d.ingredients.includes(q));
  el.innerHTML=arr.map(d=>{
    const voters=liveState.votes[d.id]||[],mine=voters.includes(liveGuestId),names=voters.map(id=>liveState.members[id]?.name||"家人");
    return `<div class="dish live-dish ${mine?"selected":""}">
      <img class="dish-cover" src="${dishCover(d)}" alt="${d.name}">
      <div class="dish-top"><div><b>${d.name}</b><div class="menu-sub">${d.category} · ${spiceText(d.spiceLevel)} · ${cookText(d.cookMethod)}</div></div>
      <button class="btn small ${mine?"danger":"primary"}" onclick="toggleLiveVote('${d.id}')">${mine?"取消":"我要吃"}</button></div>
      <div class="vote-row">${names.map(n=>`<span class="voter">${n}</span>`).join("")}</div>
    </div>`;
  }).join("");
}
function applyLiveOrdersToToday(){
  const ids=Object.entries(liveState.votes||{}).filter(([_,v])=>v.length).sort((a,b)=>b[1].length-a[1].length).map(([id])=>id);
  if(!ids.length){toast("还没人点菜");return}
  ids.forEach(id=>{
    const d=state.dishes.find(x=>x.id===id);if(!d)return;
    const meal=(d.meals||[]).find(m=>["午餐","晚餐"].includes(m))||d.meals?.[0]||"晚餐";
    if(!state.menu.some(x=>x.dishId===id))state.menu.push({id:nid(),meal,dishId:id,servings:1});
  });
  save();renderMenu();
  if(isLocalHost)broadcastHostSnapshot();
  else if(hostConnection?.open)hostConnection.send({type:"requestSnapshot"});
  toast("已加入今日菜单");
}
function syncHostSnapshotNow(){
  if(!isLocalHost){toast("请先启动家庭主机");return}
  broadcastHostSnapshot();toast("已广播最新数据");
}
function renderHostStats(){
  const el=$("#hostStats");if(!el)return;
  const h=hostHistory();
  el.innerHTML=`<div class="sync-kpi">
    <div class="kpi"><span>主机状态</span><b>${isLocalHost?"在线":"离线"}</b></div>
    <div class="kpi"><span>连接家人</span><b>${hostConnections.filter(c=>c.open).length}</b></div>
    <div class="kpi"><span>历史天数</span><b>${h.length}</b></div>
    <div class="kpi"><span>库存食材</span><b>${state.pantry.length}</b></div>
  </div>`;
}
async function copyFamilyLink(){
  const url=familyShareUrl();
  try{await navigator.clipboard.writeText(url);toast("家庭链接已复制")}catch(e){prompt("复制家庭链接：",url)}
}
async function shareFamilyLink(){
  const url=familyShareUrl();
  if(navigator.share){try{await navigator.share({title:"家庭一起点菜",text:"打开这个链接一起点菜：",url})}catch(e){}}
  else copyFamilyLink();
}


function saveTodayToHistory(fromRemote=false){
  if(!state.menu.length){toast("今日菜单还是空的");return}
  if(!isLocalHost && !fromRemote){
    if(hostConnection?.open){hostConnection.send({type:"saveToday"});toast("已提交给家庭主机保存");return}
  }
  const today=new Date().toISOString().slice(0,10);
  const payload={
    menu:state.menu.map(x=>({meal:x.meal,dishId:x.dishId,servings:x.servings})),
    dishes:state.menu.map(x=>{const d=state.dishes.find(y=>y.id===x.dishId);return d?{id:d.id,name:d.name,category:d.category,spiceLevel:d.spiceLevel,cookMethod:d.cookMethod}:null}).filter(Boolean),
    nutrition:menuNut(),cost:menuCost()
  };
  let rows=hostHistory().filter(x=>x.meal_date!==today);
  rows.unshift({meal_date:today,payload,created_at:new Date().toISOString()});
  saveHostHistory(rows.slice(0,365));
  renderHistory();renderHostStats();
  if(isLocalHost)broadcastHostSnapshot();
  toast("今天的菜单已保存到家庭主机");
}
function activeHistory(){return hostHistory()}
function recentDishPenalty(dishId){
  const rows=activeHistory().slice(0,7);let p=0;
  rows.forEach((r,i)=>{if((r.payload?.menu||[]).some(x=>x.dishId===dishId))p+=(i<3?1.4:.45)});
  return p;
}
function renderHistory(){
  const list=$("#historyList"),ins=$("#historyInsight");if(!list||!ins)return;
  const rows=activeHistory();
  list.innerHTML=rows.length?rows.slice(0,30).map(r=>{
    const by={早餐:[],午餐:[],晚餐:[],加餐:[]};
    (r.payload?.menu||[]).forEach(x=>{
      const d=(r.payload?.dishes||[]).find(y=>y.id===x.dishId);if(d)(by[x.meal]||by.晚餐).push(d)
    });
    return `<div class="history-day"><div class="history-date"><b>${r.meal_date}</b><span class="tag">${round(r.payload?.nutrition?.kcal||0)} kcal</span></div>
      ${["早餐","午餐","晚餐","加餐"].map(m=>by[m].length?`<div class="history-meal"><b>${m}</b><br>${by[m].map(d=>`<span class="history-chip">${d.name}</span>`).join("")}</div>`:"").join("")}
    </div>`;
  }).join(""):`<div class="empty">还没有历史记录。</div>`;
  const last7=rows.slice(0,7),names=[],methods={};
  last7.forEach(r=>(r.payload?.dishes||[]).forEach(d=>{names.push(d.name);methods[d.cookMethod]=(methods[d.cookMethod]||0)+1}));
  const top=Object.entries(methods).sort((a,b)=>b[1]-a[1])[0];
  ins.innerHTML=`<div class="kpis"><div class="kpi"><span>记录天数</span><b>${last7.length}</b></div><div class="kpi"><span>不同菜品</span><b>${new Set(names).size}</b></div><div class="kpi"><span>常用做法</span><b>${top?top[0]:"—"}</b></div></div>
  <div class="note">${last7.length?"科学推荐会降低最近吃过菜品的权重，并增加烹饪方式多样性。":"开始保存历史后，推荐会越来越贴合你家的饮食节奏。"}</div>`;
}


let autoRoleResolving=false;
let autoReconnectTimer=null;
async function ensureFamilyConnection(){
  if(autoRoleResolving)return;
  autoRoleResolving=true;
  clearTimeout(autoReconnectTimer);
  persistLiveName();
  try{await loadPeerJS()}catch(e){
    setLiveStatus("离线可用");
    autoRoleResolving=false;
    return;
  }

  // First, try joining an existing host. If that fails, this device becomes the host automatically.
  try{memberPeer?.destroy()}catch(e){}
  memberPeer=new Peer();

  const tryBecomeHost=()=>{
    try{memberPeer?.destroy()}catch(e){}
    memberPeer=null;
    startLocalHostAuto();
  };

  let opened=false,connected=false;
  memberPeer.on("open",()=>{
    opened=true;
    hostConnection=memberPeer.connect(FAMILY_HOST_ID,{reliable:true});
    hostConnection.on("open",()=>{
      connected=true;
      hostConnection.send({type:"hello",member:{id:liveGuestId,name:liveName(),online:true,host:false}});
      setLiveStatus("已连接",true);
      autoRoleResolving=false;
      if($("#manualReconnectBtn"))$("#manualReconnectBtn").style.display="none";
    });
    hostConnection.on("data",data=>{if(data?.type==="snapshot")applySharedSnapshot(data.snapshot)});
    hostConnection.on("close",()=>{
      setLiveStatus("重新连接中…");
      if($("#manualReconnectBtn"))$("#manualReconnectBtn").style.display="";
      scheduleAutoReconnect();
    });
    setTimeout(()=>{if(!connected)tryBecomeHost()},2600);
  });
  memberPeer.on("error",()=>{if(!connected)tryBecomeHost()});
  setTimeout(()=>{if(!opened&&!connected)tryBecomeHost()},3200);
}
async function startLocalHostAuto(){
  try{await loadPeerJS()}catch(e){setLiveStatus("离线可用");autoRoleResolving=false;return}
  stopLocalHost(false);
  hostPeer=new Peer(FAMILY_HOST_ID);
  hostPeer.on("open",()=>{
    isLocalHost=true;
    liveState.members[liveGuestId]={id:liveGuestId,name:liveName(),online:true,host:true};
    setLiveStatus("已连接",true);
    autoRoleResolving=false;
    if($("#manualReconnectBtn"))$("#manualReconnectBtn").style.display="none";
    broadcastHostSnapshot();
  });
  hostPeer.on("connection",conn=>{
    hostConnections.push(conn);
    conn.on("open",()=>sendHostSnapshot(conn));
    conn.on("data",data=>handleHostClientMessage(conn,data));
    conn.on("close",()=>{
      hostConnections=hostConnections.filter(c=>c!==conn);
      if(conn._memberId&&liveState.members[conn._memberId])liveState.members[conn._memberId].online=false;
      broadcastHostSnapshot();
    });
  });
  hostPeer.on("error",err=>{
    if(err?.type==="unavailable-id"){
      isLocalHost=false;
      autoRoleResolving=false;
      scheduleAutoReconnect(500);
    }else{
      setLiveStatus("离线可用");
      autoRoleResolving=false;
      scheduleAutoReconnect();
    }
  });
}
function scheduleAutoReconnect(delay=1800){
  clearTimeout(autoReconnectTimer);
  autoReconnectTimer=setTimeout(()=>ensureFamilyConnection(),delay);
}
document.addEventListener("visibilitychange",()=>{
  if(document.visibilityState==="visible" && !isLocalHost && !hostConnection?.open)ensureFamilyConnection();
});
window.addEventListener("online",()=>ensureFamilyConnection());

$$(".tab").forEach(b=>b.onclick=()=>{
  $$(".tab").forEach(x=>x.classList.remove("active"));b.classList.add("active");
  $$(".panel").forEach(x=>x.classList.remove("active"));$("#"+b.dataset.tab).classList.add("active")
});
$("#dishIngredients").addEventListener("input",previewDish);
allRender();
initFamilyLink();
renderHistory();
setTimeout(()=>ensureFamilyConnection(),350);
