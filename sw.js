// スロット管理システム サービスワーカー
const CACHE_NAME = 'v28-recap';
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './icon-192.svg',
  'https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap',
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'
];

// インストール時：必要なリソースをキャッシュ
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(ASSETS).catch(err => console.log('一部キャッシュ失敗:', err));
    })
  );
  self.skipWaiting();
});

// 有効化時：古いキャッシュを削除
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
    ))
  );
  self.clients.claim();
});

// フェッチ時：ネットワークファースト戦略（更新がすぐ反映される）
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  // HTML/JS/JSONは常にネットワーク優先（最新版を取得）
  const url = new URL(event.request.url);
  const isHTML = event.request.mode === 'navigate' || url.pathname.endsWith('.html');
  const isJSON = url.pathname.endsWith('.json');

  if (isHTML || isJSON) {
    // ネットワーク優先（オフライン時のみキャッシュ）
    event.respondWith(
      fetch(event.request).then(response => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone).catch(() => {}));
        }
        return response;
      }).catch(() => caches.match(event.request) || caches.match('./index.html'))
    );
    return;
  }

  // 画像・フォント・CSS等はキャッシュ優先（変わらないもの）
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        if (!response || response.status !== 200) return response;
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone).catch(() => {}));
        return response;
      });
    })
  );
});
