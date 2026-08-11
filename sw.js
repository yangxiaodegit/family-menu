const CACHE="family-menu-v8-1";
const ASSETS=["./","./index.html","./styles.css?v=8.1.2","./manifest.webmanifest","./icons/icon-192.png","./icons/icon-512.png","./data-foods-01.js?v=8.1.2","./data-dishes-01.js?v=8.1.2","./data-dishes-02.js?v=8.1.2","./data-dishes-03.js?v=8.1.2","./data-dishes-04.js?v=8.1.2","./data-dishes-05.js?v=8.1.2","./data-dishes-06.js?v=8.1.2","./data-dishes-07.js?v=8.1.2","./data-dishes-08.js?v=8.1.2","./data-dishes-09.js?v=8.1.2","./data-dishes-10.js?v=8.1.2","./data-dishes-11.js?v=8.1.2","./data-dishes-12.js?v=8.1.2","./data-dishes-13.js?v=8.1.2","./data-dishes-14.js?v=8.1.2","./data-dishes-15.js?v=8.1.2","./data-dishes-16.js?v=8.1.2","./data-dishes-17.js?v=8.1.2","./data-dishes-18.js?v=8.1.2","./data-dishes-19.js?v=8.1.2","./app-core-1.js?v=8.1.2","./app-core-2.js?v=8.1.2","./app-core-3.js?v=8.1.2","./app.js?v=8.1.2"];
self.addEventListener("install",e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS))));
self.addEventListener("activate",e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))));
self.addEventListener("fetch",e=>{
  if(e.request.method!=="GET")return;
  e.respondWith(caches.match(e.request).then(cached=>cached||fetch(e.request).then(resp=>{
    const copy=resp.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return resp;
  }).catch(()=>caches.match("./index.html"))));
});
