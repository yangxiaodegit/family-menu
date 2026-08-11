function allRender(){renderMenu();renderDishes();renderFoods();renderMembers();renderPantry();renderWeek();renderBudget();renderSettings();renderLiveDishList();renderLiveState()}
function renderMenu(){
  const holder=$("#menuHolder");
  const meals=["早餐","午餐","晚餐","加餐"];
  holder.innerHTML=meals.map(meal=>{
    const items=state.menu.filter(x=>x.meal===meal);
    return `<div class="meal-section">
      <div class="meal-head"><b>${meal}</b><button class="btn small" onclick="openAddToMeal('${meal}')">＋加菜</button></div>
      ${items.length?items.map(it=>{
        const d=state.dishes.find(x=>x.id===it.dishId), n=d?dishNut(d):{};
        return `<div class="menu-item"><div><div class="menu-title">${d?.name||"已删除菜品"} <span class="tag">${it.servings}份/人</span></div>
          <div class="menu-sub">${d?`${round(n.kcal*it.servings)} kcal · 蛋白 ${round(n.protein*it.servings)}g`:""}</div></div>
          <div class="actions"><button class="btn small" onclick="changeServing('${it.id}',-0.5)">−</button><button class="btn small" onclick="changeServing('${it.id}',0.5)">＋</button><button class="btn small danger" onclick="removeMenu('${it.id}')">移除</button></div></div>`;
      }).join(""):`<div class="note">还没有选择菜品</div>`}
    </div>`
  }).join("");
  const n=menuNut(), t=state.settings.target;
  $("#nutritionSummary").innerHTML=`
    <div class="kpis">
      <div class="kpi"><span>今日能量</span><b>${round(n.kcal)} kcal</b></div>
      <div class="kpi"><span>蛋白质</span><b>${round(n.protein)} g</b></div>
      <div class="kpi"><span>膳食纤维</span><b>${round(n.fiber)} g</b></div>
      <div class="kpi"><span>家庭人数</span><b>${familySize()} 人</b></div>
      <div class="kpi"><span>全家估算能量</span><b>${round(n.kcal*familySize())} kcal</b></div>
      <div class="kpi"><span>菜品数</span><b>${state.menu.length}</b></div>
    </div>
    ${nutrientKeys.map(k=>barRow(k,n[k],t[k])).join("")}
    <div class="note">上方营养目标按“每人/每天”统计；全家采购量会按家庭人数自动放大。</div>`;
  renderShopping();
  renderBudget();
}
function renderShopping(){
  const acc={};
  state.menu.forEach(it=>{
    const d=state.dishes.find(x=>x.id===it.dishId); if(!d)return;
    const p=parseIngredients(d.ingredients);
    p.rows.forEach(r=>{
      const key=r.name;
      acc[key]=(acc[key]||0)+r.grams*Number(it.servings||1)*familySize();
    });
  });
  const entries=Object.entries(acc).sort((a,b)=>a[0].localeCompare(b[0],"zh"));
  $("#shoppingList").innerHTML=entries.length?entries.map(([k,v])=>`<div><b>${k}</b> <span style="float:right">${round(v)} g</span></div>`).join(""):`<div class="empty">生成菜单后，这里会自动汇总全家的备菜量。</div>`;
}
function addMenu(meal,dishId,servings=1){
  state.menu.push({id:nid(),meal,dishId,servings});save();renderMenu();toast("已加入今日菜单");
}
function removeMenu(id){state.menu=state.menu.filter(x=>x.id!==id);save();renderMenu()}
function changeServing(id,delta){
  const x=state.menu.find(x=>x.id===id); if(!x)return;
  x.servings=Math.max(.5,Math.min(3,round((x.servings||1)+delta,1)));save();renderMenu()
}
function clearMenu(){if(confirm("清空今日菜单？")){state.menu=[];save();renderMenu()}}
function openAddToMeal(meal){
  const options=state.dishes.filter(d=>(d.meals||[]).includes(meal));
  $("#pickMealTitle").textContent=`给${meal}加菜`;
  $("#pickMealList").innerHTML=options.map(d=>`<div class="menu-item"><div><b>${d.name}</b><div class="menu-sub">${d.category} · ${round(dishNut(d).kcal)} kcal/份</div></div><button class="btn small primary" onclick="addMenu('${meal}','${d.id}');$('#pickDialog').close()">加入</button></div>`).join("");
  $("#pickDialog").showModal();
}
function choose(arr){return arr[Math.floor(Math.random()*arr.length)]}
function candidates(meal,cats){
  return state.dishes.filter(d=>(d.meals||[]).includes(meal) && cats.includes(d.category));
}
function buildRandom(){
  const slots=[
    ["早餐",["主食"]],["早餐",["蛋白","奶饮"]],["早餐",["水果"]],
    ["午餐",["主食"]],["午餐",["荤菜","豆制品"]],["午餐",["素菜"]],["午餐",["汤"]],
    ["晚餐",["主食"]],["晚餐",["荤菜","豆制品"]],["晚餐",["素菜"]],["晚餐",["汤"]],
    ["加餐",["水果","奶饮"]]
  ];
  const menu=[];
  for(const [meal,cats] of slots){const c=candidates(meal,cats); if(c.length)menu.push({id:nid(),meal,dishId:choose(c).id,servings:1})}
  state.menu=menu;save();renderMenu();toast("已随机生成今日菜单");
}
function scoreNut(n,t){
  const weights={kcal:4,protein:2.2,fat:1.4,carbs:1.5,fiber:1.8,sodium:.8};
  return nutrientKeys.reduce((s,k)=>{
    const r=(n[k]-t[k])/(t[k]||1);
    const over=(k==="sodium"&&r>0)?1.8:1;
    return s+weights[k]*r*r*over;
  },0);
}
function buildScientific(){
  // 用固定餐次结构 + 随机搜索，在当前菜品库中寻找更接近用户目标的一组菜单。
  const slots=[
    ["早餐",["主食"]],["早餐",["蛋白","奶饮"]],["早餐",["水果"]],
    ["午餐",["主食"]],["午餐",["荤菜","豆制品"]],["午餐",["素菜"]],["午餐",["汤"]],
    ["晚餐",["主食"]],["晚餐",["荤菜","豆制品"]],["晚餐",["素菜"]],["晚餐",["汤"]],
    ["加餐",["水果","奶饮"]]
  ];
  let best=null,bestScore=Infinity;
  for(let z=0;z<1800;z++){
    const menu=[]; const used=new Set();
    for(const [meal,cats] of slots){
      let c=candidates(meal,cats).filter(d=>!dishBlocked(d));
      if(!c.length)continue;
      let pool=c.filter(d=>!used.has(d.id)); if(!pool.length)pool=c;
      const d=choose(pool);used.add(d.id);
      menu.push({id:nid(),meal,dishId:d.id,servings:1});
    }
    // 小范围尝试份量微调，提高贴近度
    menu.forEach(it=>{
      if(Math.random()<.18) it.servings=1.5;
      else if(Math.random()<.12) it.servings=.5;
    });
    const n=sumNut(menu);
    let sc=scoreNut(n,state.settings.target);
    const cost=menuCost(menu), budget=Number(state.budget?.daily||0);
    if(budget>0 && cost>budget) sc += ((cost-budget)/budget)**2 * (state.budget.mode==="save"?8:3);
    sc -= menu.reduce((s,it)=>{const d=state.dishes.find(x=>x.id===it.dishId);return s+(d?pantryCoverage(d):0)},0)*0.05;
    if(sc<bestScore){bestScore=sc;best=menu}
  }
  state.menu=best||[];save();renderMenu();toast("已按当前营养目标生成搭配");
}

function mealCandidateScore(menu,meal){
  const n=sumNut(menu),ratio={早餐:.28,午餐:.38,晚餐:.34}[meal]||.33,t=state.settings.target;
  const targets={kcal:t.kcal*ratio,protein:t.protein*ratio,fat:t.fat*ratio,carbs:t.carbs*ratio,fiber:t.fiber*ratio,sodium:t.sodium*ratio};
  let sc=0;nutrientKeys.forEach(k=>{const diff=(n[k]-targets[k])/(targets[k]||1);sc+=diff*diff*(k==="kcal"?4:k==="protein"?2:1)});
  sc-=menu.reduce((s,it)=>{const d=state.dishes.find(x=>x.id===it.dishId);return s+(d?pantryCoverage(d):0)},0)*.08;
  sc+=menu.reduce((s,it)=>s+recentDishPenalty(it.dishId),0);
  return sc;
}
function makeMealCandidate(meal){
  const maxSpice=Number(state.settings.maxSpice??2),used=new Set(),out=[];
  const slots=meal==="早餐"?[["主食"],["蛋白","奶饮","豆制品"],["水果"]]:[["主食"],["荤菜","蛋白","豆制品"],["素菜"],["素菜"],["汤"]];
  slots.forEach(cats=>{
    let arr=state.dishes.filter(d=>(d.meals||[]).includes(meal)&&cats.includes(d.category)&&!dishBlocked(d)&&Number(d.spiceLevel||0)<=maxSpice&&!used.has(d.id)&&(!state.settings.preferredCookMethod||d.cookMethod===state.settings.preferredCookMethod));
    if(!arr.length)return;
    const sample=arr.sort(()=>Math.random()-.5).slice(0,35).sort((a,b)=>pantryCoverage(b)-pantryCoverage(a));
    const d=sample[0]||arr[0];used.add(d.id);out.push({id:nid(),meal,dishId:d.id,servings:1});
  });
  return out;
}
function recommendMeal(meal,randomMode=false){
  const candidates=[];
  for(let i=0;i<(randomMode?140:520);i++){const m=makeMealCandidate(meal);candidates.push({m,s:mealCandidateScore(m,meal)})}
  candidates.sort((a,b)=>a.s-b.s);
  const chosen=randomMode?candidates[Math.floor(Math.random()*Math.min(15,candidates.length))]:candidates[0];
  state.menu=state.menu.filter(x=>x.meal!==meal).concat(clone(chosen?.m||[]));
  save();renderMenu();toast(`${meal}${randomMode?"随机":"科学"}推荐已生成`);
}

function dishCard(d){
  const n=nutrientsFromText(d.ingredients);
  return `<div class="dish">
    <img class="dish-cover" src="${dishCover(d)}" alt="${d.name}">
    <div class="dish-top"><div><b>${d.name}</b><div>${[d.category,...(d.tags||[])].map(x=>`<span class="tag">${x}</span>`).join("")}<span class="tag">${spiceText(d.spiceLevel)}</span><span class="tag">${cookText(d.cookMethod)}</span></div></div>
    <div class="actions"><button class="btn small" onclick="editDish('${d.id}')">编辑</button><button class="btn small danger" onclick="deleteDish('${d.id}')">删</button></div></div>
    <div class="menu-sub" style="margin-top:9px">${round(n.total.kcal)} kcal · 蛋白 ${round(n.total.protein)}g · 脂肪 ${round(n.total.fat)}g · 碳水 ${round(n.total.carbs)}g</div>
    ${n.unmatched.length?`<div class="unmatched">未识别：${n.unmatched.join("；")}</div>`:""}
    ${d.recipe?`<div class="recipe"><b>做法：</b>${d.recipe}</div>`:""}
  </div>`
}

function spiceText(n){return ["🌿 不辣","🌶 微辣","🌶🌶 中辣","🌶🌶🌶 辣","🔥 很辣"][Number(n)||0]}
function cookText(m){return ({煎:"🍳 煎",炸:"🍤 炸",煮:"🍲 煮",炒:"🥘 炒",蒸:"♨️ 蒸",炖:"🍖 炖",焖:"🫕 焖",烤:"🔥 烤",凉拌:"🥗 凉拌",汤羹:"🥣 汤羹"})[m]||m||"其他"}
function setCookMethod(m){$("#dishCook").value=m;renderDishes()}
function dishCover(d){
  if(d.image)return d.image;
  const icons={荤菜:"🍖",素菜:"🥬",豆制品:"◻️",汤:"🥣",主食:"🍚",蛋白:"🍳",水果:"🍎",奶饮:"🥛"};
  const icon=icons[d.category]||"🍽️";
  const title=(d.name||"家常菜").slice(0,8).replace(/[&<>"]/g,"");
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="600" height="360"><defs><linearGradient id="g" x1="0" x2="1"><stop stop-color="#eef6f1"/><stop offset="1" stop-color="#f8efe2"/></linearGradient></defs><rect width="600" height="360" rx="28" fill="url(#g)"/><circle cx="300" cy="145" r="95" fill="#fff" opacity=".96"/><text x="300" y="178" text-anchor="middle" font-size="86">${icon}</text><text x="300" y="300" text-anchor="middle" font-size="28" font-family="sans-serif" font-weight="700" fill="#274737">${title}</text></svg>`;
  return "data:image/svg+xml;charset=utf-8,"+encodeURIComponent(svg);
}
function setDishCategory(cat){$("#dishCat").value=cat;renderDishes()}
function setDishSpice(level){$("#dishSpice").value=String(level);renderDishes()}

