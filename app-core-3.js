function renderDishes(){
  const q=($("#dishSearch")?.value||"").trim(), cat=$("#dishCat")?.value||"", spice=$("#dishSpice")?.value??"", cook=$("#dishCook")?.value??"";
  const arr=state.dishes.filter(d=>(!q||d.name.includes(q)||d.ingredients.includes(q)||(d.tags||[]).join(",").includes(q))&&(!cat||d.category===cat)&&(spice===""||Number(d.spiceLevel||0)===Number(spice))&&(!cook||d.cookMethod===cook));
  $("#dishList").innerHTML=arr.length?arr.map(dishCard).join(""):`<div class="empty">没有匹配的菜品</div>`;
}
function openDishForm(){
  editingDish=null;$("#dishModalTitle").textContent="新增菜品";$("#dishName").value="";$("#dishCategory").value="荤菜";
  $("#dishMeals").value="午餐,晚餐";$("#dishTags").value="";$("#dishSpiceEdit").value="0";$("#dishCookEdit").value="炒";$("#dishImageData").value="";$("#dishIngredients").value="鸡胸肉 150g\n西兰花 100g\n食用油 5g";$("#dishRecipe").value="";
  previewDish();$("#dishDialog").showModal()
}
function editDish(id){
  const d=state.dishes.find(x=>x.id===id); if(!d)return;editingDish=id;
  $("#dishModalTitle").textContent="编辑菜品";$("#dishName").value=d.name;$("#dishCategory").value=d.category;
  $("#dishMeals").value=(d.meals||[]).join(",");$("#dishTags").value=(d.tags||[]).join(",");$("#dishSpiceEdit").value=String(d.spiceLevel||0);$("#dishCookEdit").value=d.cookMethod||"炒";$("#dishImageData").value=d.image||"";$("#dishIngredients").value=d.ingredients;$("#dishRecipe").value=d.recipe||"";
  previewDish();$("#dishDialog").showModal()
}

function loadDishImage(input){
  const f=input.files?.[0];if(!f)return;
  const r=new FileReader();r.onload=()=>{$("#dishImageData").value=r.result;$("#dishImagePreview").src=r.result;$("#dishImagePreview").style.display="block"};r.readAsDataURL(f);
}
function previewDish(){
  const p=nutrientsFromText($("#dishIngredients").value||"");
  $("#dishPreview").innerHTML=`<b>识别结果：</b> ${p.rows.length} 项食材<br>
    能量 ${round(p.total.kcal)} kcal；蛋白 ${round(p.total.protein)}g；脂肪 ${round(p.total.fat)}g；碳水 ${round(p.total.carbs)}g；纤维 ${round(p.total.fiber)}g；钠 ${round(p.total.sodium,0)}mg
    ${p.unmatched.length?`<div class="unmatched">未识别：${p.unmatched.join("；")}（可到“食材营养库”新增）</div>`:`<div class="ok">配料均已识别</div>`}`;
}
function saveDish(){
  const name=$("#dishName").value.trim(), ing=$("#dishIngredients").value.trim();
  if(!name||!ing)return toast("请填写菜名和配料");
  const d={id:editingDish||nid(),name,category:$("#dishCategory").value,
    meals:$("#dishMeals").value.split(/[,，]/).map(x=>x.trim()).filter(Boolean),
    tags:$("#dishTags").value.split(/[,，]/).map(x=>x.trim()).filter(Boolean),ingredients:ing,recipe:$("#dishRecipe").value.trim(),spiceLevel:+$("#dishSpiceEdit").value||0,cookMethod:$("#dishCookEdit").value||"炒",image:$("#dishImageData").value||""};
  if(editingDish){const i=state.dishes.findIndex(x=>x.id===editingDish);state.dishes[i]=d}else state.dishes.unshift(d);
  save();renderDishes();renderMenu();$("#dishDialog").close();toast("菜品已保存")
}
function deleteDish(id){
  if(!confirm("删除这个菜品？今日菜单中的对应项目也会移除。"))return;
  state.dishes=state.dishes.filter(x=>x.id!==id);state.menu=state.menu.filter(x=>x.dishId!==id);save();allRender()
}
function foodRow(f){
  return `<tr><td><b>${f.name}</b><div class="menu-sub">${f.aliases||""}</div></td><td>${f.kcal}</td><td>${f.protein}</td><td>${f.fat}</td><td>${f.carbs}</td><td>${f.fiber}</td><td>${f.sodium}</td><td>${f.unitWeight||""}</td><td>${f.price??8}</td><td><button class="btn small" onclick="editFood('${f.id}')">编辑</button></td></tr>`;
}
function renderFoods(){
  const q=($("#foodSearch")?.value||"").trim();
  const arr=state.foods.filter(f=>!q||f.name.includes(q)||(f.aliases||"").includes(q));
  $("#foodTable").innerHTML=arr.map(foodRow).join("")
}
function openFoodForm(){editingFood=null;$("#foodModalTitle").textContent="新增食材";["foodName","foodAliases"].forEach(id=>$("#"+id).value="");["fKcal","fProtein","fFat","fCarbs","fFiber","fSodium","fUnit","fPrice"].forEach(id=>$("#"+id).value="0");$("#foodDialog").showModal()}
function editFood(id){
  const f=state.foods.find(x=>x.id===id); if(!f)return;editingFood=id;$("#foodModalTitle").textContent="编辑食材";
  $("#foodName").value=f.name;$("#foodAliases").value=f.aliases||"";$("#fKcal").value=f.kcal;$("#fProtein").value=f.protein;$("#fFat").value=f.fat;
  $("#fCarbs").value=f.carbs;$("#fFiber").value=f.fiber;$("#fSodium").value=f.sodium;$("#fUnit").value=f.unitWeight||100;$("#fPrice").value=f.price??8;$("#foodDialog").showModal()
}
function saveFood(){
  const name=$("#foodName").value.trim();if(!name)return toast("请填写食材名称");
  const f={id:editingFood||nid(),name,aliases:$("#foodAliases").value.trim(),kcal:+$("#fKcal").value||0,protein:+$("#fProtein").value||0,fat:+$("#fFat").value||0,carbs:+$("#fCarbs").value||0,fiber:+$("#fFiber").value||0,sodium:+$("#fSodium").value||0,unitWeight:+$("#fUnit").value||100,price:+$("#fPrice").value||0};
  if(editingFood){const i=state.foods.findIndex(x=>x.id===editingFood);state.foods[i]=f}else state.foods.push(f);
  save();renderFoods();renderDishes();renderMenu();$("#foodDialog").close();toast("食材已保存")
}
function renderSettings(){
  $("#familyCount").value=familySize();
  nutrientKeys.forEach(k=>$("#t_"+k).value=state.settings.target[k]);if($("#maxSpice"))$("#maxSpice").value=String(state.settings.maxSpice??2);if($("#preferredCookMethod"))$("#preferredCookMethod").value=state.settings.preferredCookMethod||""
}
function saveSettings(){
  state.settings.family=Math.max(1,+$("#familyCount").value||1);
  nutrientKeys.forEach(k=>state.settings.target[k]=+$("#t_"+k).value||0);state.settings.maxSpice=+$("#maxSpice").value||0;state.settings.preferredCookMethod=$("#preferredCookMethod").value||"";
  save();renderMenu();if(isLocalHost)broadcastHostSnapshot();toast("设置已保存")
}
function exportData(){
  const blob=new Blob([JSON.stringify(state,null,2)],{type:"application/json"});
  const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=`家庭点菜数据_${new Date().toISOString().slice(0,10)}.json`;a.click();URL.revokeObjectURL(a.href)
}
function importData(input){
  const file=input.files[0];if(!file)return;
  const r=new FileReader();r.onload=()=>{
    try{const x=JSON.parse(r.result);if(!x.foods||!x.dishes)throw 0;state=x;save();allRender();initFamilyLink();toast("数据已恢复")}
    catch(e){alert("文件格式不正确")}
  };r.readAsText(file);input.value=""
}
function resetData(){if(confirm("恢复示例数据？你自己的菜品和设置会被覆盖，建议先导出备份。")){state=freshDefaultState();save();allRender();initFamilyLink();toast("已恢复1000道家常菜示例数据")}}


let editingMember=null;
function renderMembers(){
  const el=$("#memberList");if(!el)return;
  el.innerHTML=(state.members||[]).length?(state.members||[]).map(m=>`<div class="member-card">
    <div class="dish-top"><div><b>${m.name}</b> <span class="tag">${m.type}</span><div class="menu-sub">目标 ${m.kcal} kcal · 蛋白 ${m.protein}g</div></div>
    <div class="actions"><button class="btn small" onclick="editMember('${m.id}')">编辑</button><button class="btn small danger" onclick="deleteMember('${m.id}')">删除</button></div></div>
    ${(m.allergy||m.avoid)?`<div class="menu-sub" style="margin-top:7px">过敏：${m.allergy||"无"} ｜ 忌口：${m.avoid||"无"}</div>`:""}
  </div>`).join(""):`<div class="empty">还没有家庭成员</div>`;
  const terms=restrictionTerms();
  $("#restrictionSummary").innerHTML=`<div class="kpis"><div class="kpi"><span>家庭成员</span><b>${familySize()} 人</b></div><div class="kpi"><span>限制食材</span><b>${terms.length} 项</b></div></div>
    <div>${terms.length?terms.map(x=>`<span class="tag">${x}</span>`).join(""):"<span class='note'>暂无过敏或忌口设置</span>"}</div>`;
}
function openMemberForm(){
  editingMember=null;$("#memberModalTitle").textContent="新增家庭成员";$("#memberName").value="";$("#memberType").value="成人";$("#mKcal").value=2000;$("#mProtein").value=65;$("#memberAllergy").value="";$("#memberAvoid").value="";$("#memberDialog").showModal()
}
function editMember(id){
  const m=state.members.find(x=>x.id===id);if(!m)return;editingMember=id;$("#memberModalTitle").textContent="编辑家庭成员";$("#memberName").value=m.name;$("#memberType").value=m.type;$("#mKcal").value=m.kcal;$("#mProtein").value=m.protein;$("#memberAllergy").value=m.allergy||"";$("#memberAvoid").value=m.avoid||"";$("#memberDialog").showModal()
}
function saveMember(){
  const name=$("#memberName").value.trim();if(!name)return toast("请填写成员称呼");
  const m={id:editingMember||nid(),name,type:$("#memberType").value,kcal:+$("#mKcal").value||2000,protein:+$("#mProtein").value||65,allergy:$("#memberAllergy").value.trim(),avoid:$("#memberAvoid").value.trim()};
  if(editingMember){const i=state.members.findIndex(x=>x.id===editingMember);state.members[i]=m}else state.members.push(m);
  save();renderMembers();renderMenu();if(isLocalHost)broadcastHostSnapshot();$("#memberDialog").close();toast("成员已保存")
}
function deleteMember(id){if(confirm("删除这个家庭成员？")){state.members=state.members.filter(x=>x.id!==id);save();renderMembers();renderMenu()}}

function openPantryForm(){
  $("#pantryFood").innerHTML=state.foods.map(f=>`<option value="${f.id}">${f.name}</option>`).join("");
  $("#pantryGrams").value=500;$("#pantryDialog").showModal()
}
function savePantry(){
  const foodId=$("#pantryFood").value, grams=+$("#pantryGrams").value||0;
  let x=state.pantry.find(x=>x.foodId===foodId);
  if(x)x.grams=grams;else state.pantry.push({foodId,grams});
  save();renderPantry();if(isLocalHost)broadcastHostSnapshot();$("#pantryDialog").close();toast("库存已保存")
}
function setPantry(id,v){const x=state.pantry.find(x=>x.foodId===id);if(x){x.grams=Math.max(0,+v||0);save();renderPantry()}}
function removePantry(id){state.pantry=state.pantry.filter(x=>x.foodId!==id);save();renderPantry()}
function renderPantry(){
  const el=$("#pantryList");if(!el)return;
  el.innerHTML=state.pantry.length?state.pantry.map(x=>{const f=state.foods.find(y=>y.id===x.foodId);return `<div class="stock-row"><div><b>${f?.name||"未知食材"}</b></div><input type="number" value="${x.grams}" onchange="setPantry('${x.foodId}',this.value)"><button class="btn small danger" onclick="removePantry('${x.foodId}')">删除</button></div>`}).join(""):`<div class="empty">还没有录入库存</div>`;
  const rec=[...state.dishes].filter(d=>!dishBlocked(d)).map(d=>({d,c:pantryCoverage(d)})).filter(x=>x.c>0).sort((a,b)=>b.c-a.c).slice(0,8);
  $("#pantryRecommendations").innerHTML=rec.length?rec.map(x=>`<div class="dish"><b>${x.d.name}</b><div class="menu-sub">库存覆盖约 ${Math.round(x.c*100)}% · ${round(dishNut(x.d).kcal)} kcal/份</div><div class="actions" style="margin-top:8px"><button class="btn small" onclick="editDish('${x.d.id}')">看做法</button></div></div>`).join(""):`<div class="empty">录入库存后会显示推荐</div>`;
}

function dailyPlanScientific(){
  const old=state.menu;buildScientific();const m=clone(state.menu);state.menu=old;return m;
}
function dailyPlanRandom(){
  const old=state.menu;buildRandom();const m=clone(state.menu);state.menu=old;return m;
}
function generateWeek(){
  const old=clone(state.menu), week=[];
  for(let i=0;i<7;i++){buildScientific();week.push(clone(state.menu))}
  state.week=week;state.menu=old;save();renderWeek();renderMenu();toast("已生成一周科学菜单")
}
function randomWeek(){
  const old=clone(state.menu), week=[];
  for(let i=0;i<7;i++){buildRandom();week.push(clone(state.menu))}
  state.week=week;state.menu=old;save();renderWeek();renderMenu();toast("已生成随机周菜单")
}
function useWeekDay(i){if(!state.week[i])return;state.menu=clone(state.week[i]);save();renderMenu();toast(`已把第${i+1}天设为今日菜单`)}
function renderWeek(){
  const board=$("#weekBoard");if(!board)return;
  if(!state.week?.length){board.innerHTML=`<div class="empty" style="grid-column:1/-1">还没有周菜单，点击“生成科学周菜单”。</div>`;$("#weekNutrition").innerHTML="";$("#weekShopping").innerHTML="";return}
  const names=["周一","周二","周三","周四","周五","周六","周日"];
  board.innerHTML=state.week.map((day,i)=>`<div class="day-card"><h3>${names[i]}</h3>${["早餐","午餐","晚餐","加餐"].map(meal=>`<div class="day-meal"><b>${meal}</b><br>${day.filter(x=>x.meal===meal).map(x=>state.dishes.find(d=>d.id===x.dishId)?.name||"").join("、")||"—"}</div>`).join("")}<button class="btn small soft" style="margin-top:8px" onclick="useWeekDay(${i})">设为今日</button></div>`).join("");
  const avg={kcal:0,protein:0,fat:0,carbs:0,fiber:0,sodium:0};
  state.week.forEach(day=>{const n=sumNut(day);nutrientKeys.forEach(k=>avg[k]+=n[k]/state.week.length)});
  $("#weekNutrition").innerHTML=nutrientKeys.map(k=>barRow(k,avg[k],state.settings.target[k])).join("");
  const acc={};
  state.week.forEach(day=>day.forEach(it=>{const d=state.dishes.find(x=>x.id===it.dishId);if(!d)return;parseIngredients(d.ingredients).rows.forEach(r=>acc[r.name]=(acc[r.name]||0)+r.grams*it.servings*familySize())}));
  $("#weekShopping").innerHTML=Object.entries(acc).map(([k,v])=>`<div><b>${k}</b><span style="float:right">${round(v)} g</span></div>`).join("");
}
function renderBudget(){
  if(!$("#dailyBudget"))return;
  $("#dailyBudget").value=state.budget?.daily??100;$("#budgetMode").value=state.budget?.mode||"normal";
  const cost=menuCost(), bud=Number(state.budget?.daily||0), ratio=bud?cost/bud:0;
  $("#todayCost").innerHTML=`<div class="cost-big">¥ ${cost}</div><div class="note">今日全家预计食材成本 / 预算 ¥${bud}</div><div class="nrow"><div class="bar"><i style="width:${Math.min(100,ratio*100)}%"></i></div></div><div class="${ratio>1?"unmatched":"ok"}">${bud?(ratio>1?`预计超预算 ¥${round(cost-bud,2)}`:`预计剩余 ¥${round(bud-cost,2)}`):"未设置预算"}</div>`;
}
function saveBudget(){state.budget={daily:+$("#dailyBudget").value||0,mode:$("#budgetMode").value};save();renderBudget();if(isLocalHost)broadcastHostSnapshot();toast("预算已保存")}




const FAMILY_HOST_ID="family-menu-local-host-v8";
