const CACHE="family-menu-v8-1";
const ASSETS=["./","./index.html","./styles.css","./manifest.webmanifest","./icons/icon-192.png","./icons/icon-512.png","./data-foods-01.js","./data-dishes-01.js","./data-dishes-02.js","./data-dishes-03.js","./data-dishes-04.js","./data-dishes-05.js","./data-dishes-06.js","./data-dishes-07.js","./data-dishes-08.js","./data-dishes-09.js","./data-dishes-10.js","./data-dishes-11.js","./data-dishes-12.js","./data-dishes-13.js","./data-dishes-14.js","./data-dishes-15.js","./data-dishes-16.js","./data-dishes-17.js","./data-dishes-18.js","./data-dishes-19.js","./app-core-1.js","./app-core-2.js","./app-core-3.js","./app.js"];
self.addEventListener("install",e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS))));
self.addEventListener("activate",e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))));
self.addEventListener("fetch",e=>{
  if(e.request.method!=="GET")return;
  e.respondWith(caches.match(e.request).then(cached=>cached||fetch(e.request).then(resp=>{
    const copy=resp.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return resp;
  }).catch(()=>caches.match("./index.html"))));
});
