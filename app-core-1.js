
window.addEventListener("error",e=>{
  console.error(e.error||e.message);
  const t=document.getElementById("toast");
  if(t){t.textContent="页面出现错误，请刷新后重试";t.classList.add("show");setTimeout(()=>t.classList.remove("show"),2500)}
});


const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const KEY="familyMenuApp_v5";
const clone=o=>JSON.parse(JSON.stringify(o));
const round=(n,d=1)=>Number((n||0).toFixed(d));
const nid=()=>Date.now().toString(36)+Math.random().toString(36).slice(2,6);
const nutrientKeys=["kcal","protein","fat","carbs","fiber","sodium"];
const nutrientLabels={kcal:"能量 kcal",protein:"蛋白质 g",fat:"脂肪 g",carbs:"碳水 g",fiber:"膳食纤维 g",sodium:"钠 mg"};

const DEFAULT={
  settings:{family:3,maxSpice:2,preferredCookMethod:"", target:{kcal:2000,protein:65,fat:60,carbs:300,fiber:25,sodium:2000}},
  foods:[
    {id:"rice",name:"熟米饭",aliases:"米饭,白米饭",kcal:116,protein:2.6,fat:.3,carbs:25.9,fiber:.3,sodium:2,unitWeight:150},
    {id:"oats",name:"燕麦片",aliases:"燕麦",kcal:377,protein:13.2,fat:6.7,carbs:67.7,fiber:10.1,sodium:5,unitWeight:40},
    {id:"noodle",name:"熟面条",aliases:"面条",kcal:110,protein:3.3,fat:.6,carbs:22.8,fiber:1.2,sodium:2,unitWeight:150},
    {id:"bread",name:"全麦面包",aliases:"面包,吐司",kcal:246,protein:9.4,fat:3.4,carbs:46.2,fiber:6.0,sodium:430,unitWeight:35},
    {id:"chicken",name:"鸡胸肉",aliases:"鸡肉,鸡胸",kcal:118,protein:24.6,fat:1.9,carbs:0,fiber:0,sodium:44,unitWeight:100},
    {id:"beef",name:"瘦牛肉",aliases:"牛肉",kcal:137,protein:20.2,fat:6.2,carbs:0,fiber:0,sodium:53,unitWeight:100},
    {id:"pork",name:"猪里脊",aliases:"里脊肉,瘦猪肉",kcal:143,protein:20.3,fat:6.2,carbs:0,fiber:0,sodium:48,unitWeight:100},
    {id:"salmon",name:"三文鱼",aliases:"鲑鱼",kcal:139,protein:17.2,fat:7.8,carbs:0,fiber:0,sodium:47,unitWeight:100},
    {id:"shrimp",name:"虾仁",aliases:"虾",kcal:93,protein:18.6,fat:.8,carbs:2.8,fiber:0,sodium:165,unitWeight:100},
    {id:"egg",name:"鸡蛋",aliases:"蛋,鸡蛋液",kcal:144,protein:13.3,fat:8.8,carbs:2.8,fiber:0,sodium:131,unitWeight:50},
    {id:"tofu",name:"北豆腐",aliases:"豆腐",kcal:116,protein:12.2,fat:6.7,carbs:2.0,fiber:.4,sodium:7,unitWeight:100},
    {id:"milk",name:"纯牛奶",aliases:"牛奶",kcal:61,protein:3.2,fat:3.3,carbs:4.8,fiber:0,sodium:42,unitWeight:250},
    {id:"yogurt",name:"无糖酸奶",aliases:"酸奶",kcal:72,protein:3.5,fat:3.3,carbs:7.4,fiber:0,sodium:40,unitWeight:150},
    {id:"broccoli",name:"西兰花",aliases:"花椰菜",kcal:36,protein:4.1,fat:.6,carbs:4.3,fiber:4.4,sodium:18,unitWeight:100},
    {id:"spinach",name:"菠菜",aliases:"",kcal:28,protein:2.6,fat:.3,carbs:4.5,fiber:1.7,sodium:85,unitWeight:100},
    {id:"tomato",name:"西红柿",aliases:"番茄",kcal:15,protein:.9,fat:.2,carbs:3.3,fiber:1.0,sodium:5,unitWeight:100},
    {id:"cucumber",name:"黄瓜",aliases:"青瓜",kcal:16,protein:.8,fat:.2,carbs:3.0,fiber:.5,sodium:5,unitWeight:100},
    {id:"carrot",name:"胡萝卜",aliases:"红萝卜",kcal:32,protein:1.0,fat:.2,carbs:7.7,fiber:1.1,sodium:71,unitWeight:100},
    {id:"mushroom",name:"鲜香菇",aliases:"香菇,蘑菇",kcal:26,protein:2.2,fat:.3,carbs:5.2,fiber:3.3,sodium:1,unitWeight:100},
    {id:"potato",name:"土豆",aliases:"马铃薯",kcal:81,protein:2.6,fat:.2,carbs:17.8,fiber:1.1,sodium:8,unitWeight:100},
    {id:"sweetpotato",name:"红薯",aliases:"地瓜,番薯",kcal:86,protein:1.6,fat:.2,carbs:20.1,fiber:1.6,sodium:55,unitWeight:150},
    {id:"corn",name:"甜玉米",aliases:"玉米",kcal:112,protein:4.0,fat:1.2,carbs:22.8,fiber:2.9,sodium:1,unitWeight:150},
    {id:"apple",name:"苹果",aliases:"",kcal:53,protein:.4,fat:.2,carbs:13.7,fiber:1.7,sodium:2,unitWeight:180},
    {id:"banana",name:"香蕉",aliases:"",kcal:93,protein:1.4,fat:.2,carbs:22.0,fiber:1.2,sodium:1,unitWeight:120},
    {id:"orange",name:"橙子",aliases:"橙",kcal:48,protein:.8,fat:.2,carbs:11.1,fiber:1.6,sodium:1,unitWeight:180},
    {id:"oil",name:"食用油",aliases:"植物油,橄榄油,花生油",kcal:899,protein:0,fat:99.9,carbs:0,fiber:0,sodium:0,unitWeight:10},
    {id:"salt",name:"食盐",aliases:"盐",kcal:0,protein:0,fat:0,carbs:0,fiber:0,sodium:39300,unitWeight:2},
    {id:"soy",name:"生抽",aliases:"酱油",kcal:53,protein:5.6,fat:.1,carbs:7.8,fiber:0,sodium:5750,unitWeight:10},
    {id:"onion",name:"洋葱",aliases:"",kcal:40,protein:1.1,fat:.2,carbs:9.0,fiber:.9,sodium:4,unitWeight:100},
    {id:"garlic",name:"大蒜",aliases:"蒜",kcal:128,protein:4.5,fat:.2,carbs:27.6,fiber:1.1,sodium:19,unitWeight:5}
  ],
  dishes:[
    {id:"d1",name:"牛奶燕麦杯",category:"主食",meals:["早餐"],tags:["高纤","快手"],ingredients:"燕麦片 45g\n纯牛奶 250ml\n香蕉 60g"},
    {id:"d2",name:"全麦鸡蛋吐司",category:"主食",meals:["早餐"],tags:["蛋白质"],ingredients:"全麦面包 70g\n鸡蛋 1个\n西红柿 60g"},
    {id:"d3",name:"水煮鸡蛋",category:"蛋白",meals:["早餐","加餐"],tags:["快手"],ingredients:"鸡蛋 1个"},
    {id:"d4",name:"无糖酸奶水果杯",category:"奶饮",meals:["早餐","加餐"],tags:["清爽"],ingredients:"无糖酸奶 180g\n苹果 100g"},
    {id:"d5",name:"香蕉",category:"水果",meals:["早餐","加餐"],tags:["水果"],ingredients:"香蕉 1个"},
    {id:"d6",name:"苹果",category:"水果",meals:["早餐","加餐"],tags:["水果"],ingredients:"苹果 1个"},
    {id:"d7",name:"香煎鸡胸肉",category:"荤菜",meals:["午餐","晚餐"],tags:["高蛋白","低脂"],ingredients:"鸡胸肉 150g\n食用油 6g\n食盐 1g"},
    {id:"d8",name:"番茄炖牛肉",category:"荤菜",meals:["午餐","晚餐"],tags:["高蛋白"],ingredients:"瘦牛肉 130g\n西红柿 160g\n洋葱 40g\n食用油 5g\n食盐 1g"},
    {id:"d9",name:"西兰花炒虾仁",category:"荤菜",meals:["午餐","晚餐"],tags:["高蛋白","蔬菜"],ingredients:"虾仁 120g\n西兰花 150g\n食用油 6g\n食盐 1g"},
    {id:"d10",name:"香煎三文鱼",category:"荤菜",meals:["午餐","晚餐"],tags:["优质脂肪"],ingredients:"三文鱼 150g\n食用油 4g\n食盐 1g"},
    {id:"d11",name:"家常豆腐",category:"豆制品",meals:["午餐","晚餐"],tags:["植物蛋白"],ingredients:"北豆腐 180g\n西红柿 80g\n食用油 6g\n生抽 5g"},
    {id:"d12",name:"蒜蓉西兰花",category:"素菜",meals:["午餐","晚餐"],tags:["高纤"],ingredients:"西兰花 200g\n大蒜 5g\n食用油 5g\n食盐 1g"},
    {id:"d13",name:"清炒菠菜",category:"素菜",meals:["午餐","晚餐"],tags:["绿叶菜"],ingredients:"菠菜 200g\n食用油 5g\n食盐 1g"},
    {id:"d14",name:"香菇胡萝卜",category:"素菜",meals:["午餐","晚餐"],tags:["菌菇"],ingredients:"鲜香菇 150g\n胡萝卜 80g\n食用油 5g\n食盐 1g"},
    {id:"d15",name:"黄瓜番茄沙拉",category:"素菜",meals:["午餐","晚餐"],tags:["清爽"],ingredients:"黄瓜 120g\n西红柿 120g\n食用油 3g\n食盐 0.5g"},
    {id:"d16",name:"米饭",category:"主食",meals:["午餐","晚餐"],tags:["主食"],ingredients:"熟米饭 200g"},
    {id:"d17",name:"红薯",category:"主食",meals:["早餐","午餐","晚餐"],tags:["粗粮"],ingredients:"红薯 220g"},
    {id:"d18",name:"玉米",category:"主食",meals:["早餐","午餐","晚餐"],tags:["粗粮"],ingredients:"甜玉米 180g"},
    {id:"d19",name:"番茄蛋花汤",category:"汤",meals:["午餐","晚餐"],tags:["清淡"],ingredients:"西红柿 120g\n鸡蛋 0.5个\n食盐 0.5g"},
    {id:"d20",name:"香菇豆腐汤",category:"汤",meals:["午餐","晚餐"],tags:["清淡"],ingredients:"鲜香菇 60g\n北豆腐 80g\n食盐 0.5g"},
    {id:"d21",name:"土豆牛肉碗",category:"荤菜",meals:["午餐","晚餐"],tags:["饱腹"],ingredients:"瘦牛肉 110g\n土豆 150g\n胡萝卜 50g\n食用油 5g\n食盐 1g"},
    {id:"d22",name:"鸡丝蔬菜面",category:"主食",meals:["午餐","晚餐"],tags:["一碗餐"],ingredients:"熟面条 220g\n鸡胸肉 80g\n菠菜 80g\n胡萝卜 40g\n食盐 1g"}
  ],
  menu:[],
  members:[
    {id:"m1",name:"成人1",type:"成人",kcal:2000,protein:65,allergy:"",avoid:""},
    {id:"m2",name:"成人2",type:"成人",kcal:2000,protein:65,allergy:"",avoid:""},
    {id:"m3",name:"儿童",type:"儿童",kcal:1600,protein:45,allergy:"",avoid:""}
  ],
  pantry:[],
  week:[],
  budget:{daily:100,mode:"normal"}
};

const EXTRA_FOODS=window.EXTRA_FOODS_DATA||[];
const HOME_DISHES_1000=window.HOME_DISHES_DATA||[];
let state=load();
let editingDish=null, editingFood=null;

// ---------- 实时家庭点菜 ----------
let livePeer=null;
let liveHost=false;
let liveRoomId="";
let liveGuestId=localStorage.getItem("familyLiveGuestId")||nid();
localStorage.setItem("familyLiveGuestId",liveGuestId);
let liveConns=[];
let liveHostConn=null;
let liveState={members:{},votes:{}};


function load(){
  try{
    const x=JSON.parse(localStorage.getItem(KEY));
    if(x&&x.foods&&x.dishes){
      if(!x.members)x.members=clone(DEFAULT.members);
      if(!x.pantry)x.pantry=[];
      if(!x.week)x.week=[];
      if(!x.budget)x.budget=clone(DEFAULT.budget);if(x.settings.maxSpice==null)x.settings.maxSpice=2;if(x.settings.preferredCookMethod==null)x.settings.preferredCookMethod="";
      x.foods.forEach(f=>{if(f.price==null)f.price=8});
      const existingNames=new Set(x.foods.map(f=>f.name));
      EXTRA_FOODS.forEach(f=>{if(!existingNames.has(f.name))x.foods.push(clone(f))});
      x.dishes.forEach(d=>{if(d.recipe==null)d.recipe="";if(d.spiceLevel==null)d.spiceLevel=0;if(d.image==null)d.image="";if(d.cookMethod==null)d.cookMethod="炒"});
      return x;
    }
  }catch(e){}
  const d=clone(DEFAULT);
  d.foods.forEach(f=>{if(f.price==null)f.price=8});
  const existingNames=new Set(d.foods.map(f=>f.name));
  EXTRA_FOODS.forEach(f=>{if(!existingNames.has(f.name))d.foods.push(clone(f))});
  d.dishes=clone(HOME_DISHES_1000);
  return d;
}
function save(){localStorage.setItem(KEY,JSON.stringify(state))}
function freshDefaultState(){
  const d=clone(DEFAULT);
  d.foods.forEach(f=>{if(f.price==null)f.price=8});
  const names=new Set(d.foods.map(f=>f.name));
  EXTRA_FOODS.forEach(f=>{if(!names.has(f.name))d.foods.push(clone(f))});
  d.dishes=clone(HOME_DISHES_1000);
  return d;
}

function toast(t){const el=$("#toast");el.textContent=t;el.classList.add("show");setTimeout(()=>el.classList.remove("show"),1600)}
function aliases(f){return [f.name,...(f.aliases||"").split(/[,，]/).map(x=>x.trim()).filter(Boolean)]}
function findFood(name){
  const n=name.trim();
  return state.foods.find(f=>aliases(f).some(a=>a===n)) ||
         state.foods.find(f=>aliases(f).some(a=>n.includes(a)||a.includes(n)));
}
function parseIngredients(text){
  const parts=text.split(/\n|；|;/).map(x=>x.trim()).filter(Boolean);
  const rows=[], unmatched=[];
  for(const line0 of parts){
    const line=line0.replace(/[，,]+$/,"").trim();
    const m=line.match(/^(.+?)\s+(\d+(?:\.\d+)?)\s*(kg|千克|公斤|g|克|ml|毫升|个|只|枚|片|勺|碗)?$/i);
    if(!m){unmatched.push(line);continue}
    const name=m[1].trim(), qty=parseFloat(m[2]), unit=(m[3]||"g").toLowerCase();
    const food=findFood(name);
    if(!food){unmatched.push(line);continue}
    let grams=qty;
    if(["kg","千克","公斤"].includes(unit)) grams=qty*1000;
    else if(["个","只","枚","片"].includes(unit)) grams=qty*(food.unitWeight||100);
    else if(unit==="勺") grams=qty*10;
    else if(unit==="碗") grams=qty*150;
    rows.push({line,name:food.name,foodId:food.id,qty,unit,grams});
  }
  return {rows,unmatched};
}
function nutrientsFromText(text){
  const p=parseIngredients(text), total={kcal:0,protein:0,fat:0,carbs:0,fiber:0,sodium:0};
  p.rows.forEach(r=>{
    const f=state.foods.find(x=>x.id===r.foodId), k=r.grams/100;
    nutrientKeys.forEach(n=>total[n]+=Number(f[n]||0)*k);
  });
  nutrientKeys.forEach(n=>total[n]=round(total[n],n==="sodium"?0:1));
  return {...p,total};
}
function dishNut(d){return nutrientsFromText(d.ingredients).total}
function sumNut(items){
  const t={kcal:0,protein:0,fat:0,carbs:0,fiber:0,sodium:0};
  items.forEach(it=>{
    const d=state.dishes.find(x=>x.id===it.dishId); if(!d)return;
    const n=dishNut(d), s=Number(it.servings||1);
    nutrientKeys.forEach(k=>t[k]+=n[k]*s);
  });
  nutrientKeys.forEach(k=>t[k]=round(t[k],k==="sodium"?0:1));
  return t;
}
function menuNut(){return sumNut(state.menu)}
function familySize(){return state.members?.length||state.settings.family||1}
function restrictionTerms(){
  const arr=[];
  (state.members||[]).forEach(m=>[m.allergy,m.avoid].forEach(s=>(s||"").split(/[,，]/).map(x=>x.trim()).filter(Boolean).forEach(x=>arr.push(x))));
  return [...new Set(arr)];
}
function dishBlocked(d){
  const terms=restrictionTerms(); if(!terms.length)return false;
  const text=d.ingredients+" "+d.name;
  return terms.some(t=>text.includes(t));
}
function dishCost(d){
  const p=parseIngredients(d.ingredients);let c=0;
  p.rows.forEach(r=>{const f=state.foods.find(x=>x.id===r.foodId);c+=(Number(f?.price||0)/500)*r.grams});
  return round(c,2);
}
function menuCost(items=state.menu){
  return round(items.reduce((s,it)=>{const d=state.dishes.find(x=>x.id===it.dishId);return s+(d?dishCost(d)*Number(it.servings||1)*familySize():0)},0),2)
}
function pantryCoverage(d){
  const p=parseIngredients(d.ingredients);if(!p.rows.length)return 0;
  let hit=0;
  p.rows.forEach(r=>{const inv=state.pantry.find(x=>x.foodId===r.foodId);if(inv&&inv.grams>0)hit+=Math.min(1,inv.grams/(r.grams*familySize()))});
  return hit/p.rows.length;
}
function pct(v,t){return Math.max(0,Math.min(130,(v/(t||1))*100))}
function barRow(k,v,t){
  const p=pct(v,t);
  return `<div class="nrow"><div class="nline"><span>${nutrientLabels[k]}</span><b>${round(v,k==="sodium"?0:1)} / ${t}</b></div><div class="bar"><i style="width:${Math.min(100,p)}%"></i></div></div>`;
}
