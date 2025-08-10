# Serper.dev JavaScript Snippets

Updated: 2025-08-10

Assumes:
- Node 18+
- `npm i axios dotenv p-limit`
- `.env` contains `SERPER_API_KEY`

Shared helper (ESM):
```js
import 'dotenv/config';
import axios from 'axios';

const KEY = process.env.SERPER_API_KEY;
const BASE = 'https://google.serper.dev';

export async function serper(endpoint, payload){
  const { data } = await axios.post(`${BASE}/${endpoint}`, payload, {
    headers: { 'X-API-KEY': KEY, 'Content-Type': 'application/json' },
    timeout: 15000,
  });
  return data;
}
```

## 1) Web Search (`/search`)
```js
const res = await serper('search', { q: 'immigration lawyer Toronto', gl: 'ca', hl: 'en', num: 10 });
console.log(res.organic?.map(o => ({ title: o.title, url: o.link })));
```

## 2) Places (`/places`)
```js
const res = await serper('places', { q: 'immigration lawyer Vancouver', gl: 'ca', hl: 'en', num: 20 });
console.log(res.places?.map(p => ({ name: p.title, phone: p.phoneNumber, website: p.website })));
```

## 3) Images (`/images`)
```js
const res = await serper('images', { q: 'canada immigration office', gl: 'ca', hl: 'en', num: 8 });
console.log(res.images?.map(i => ({ title: i.title, imageUrl: i.imageUrl })));
```

## 4) News (`/news`)
```js
const res = await serper('news', { q: 'canada immigration policy', gl: 'ca', hl: 'en' });
console.log(res.news?.map(n => ({ title: n.title, date: n.date })));
```

## 5) Scholar (`/scholar`)
```js
const res = await serper('scholar', { q: 'immigration law Canada', hl: 'en' });
console.log(res.organic?.map(p => ({ title: p.title, citedBy: p.citedBy })));
```

## 6) Shopping (`/shopping`)
```js
const res = await serper('shopping', { q: 'immigration law textbook', hl: 'en', gl: 'ca' });
console.log(res.shopping?.map(s => ({ title: s.title, price: s.price })));
```

## 7) Jobs (`/jobs`)
```js
const res = await serper('jobs', { q: 'immigration paralegal Toronto', hl: 'en', gl: 'ca' });
console.log(res.jobs?.map(j => ({ title: j.title, company: j.company, location: j.location })));
```

## 8) Patents (`/patents`)
```js
const res = await serper('patents', { q: 'biometric visa processing', hl: 'en' });
console.log(res.organic?.map(p => ({ title: p.title, patentId: p.patentId })));
```

## 9) Videos (`/videos`)
```js
const res = await serper('videos', { q: 'canada immigration seminar', hl: 'en', gl: 'ca' });
console.log(res.videos?.map(v => ({ title: v.title, url: v.link })));
```

## 10) Time (`/time`)
```js
const res = await serper('time', { q: 'time in Toronto' });
console.log(res.time?.current);
```

## 11) Weather (`/weather`)
```js
const res = await serper('weather', { q: 'weather Toronto' });
console.log(res.weather?.temperature, res.weather?.description);
```

## 12) Finance (`/finance`)
```js
const res = await serper('finance', { q: 'NASDAQ:GOOGL' });
console.log(res.finance?.map(f => ({ symbol: f.symbol, price: f.price })));
```

## 13) Autocomplete (`/autocomplete`)
```js
const res = await serper('autocomplete', { q: 'immigration law' });
console.log(res.suggestions);
```

## 14) Batch + Delay
```js
const queries = ['immigration lawyer Montreal', 'immigration lawyer Ottawa'];
for(const q of queries){
  const res = await serper('search', { q, gl:'ca', hl:'en', num:10 });
  console.log(q, res.organic?.length || 0);
  await new Promise(r => setTimeout(r, 1200));
}
```

## 15) Concurrency Control (p-limit)
```js
import pLimit from 'p-limit';
const limit = pLimit(3);
const queries = ['A','B','C','D'];
const results = await Promise.all(queries.map(q => limit(() => serper('search',{ q, hl:'en'}))));
console.log(results.length);
```

## 16) Retry Wrapper
```js
export async function safeSerper(endpoint, payload, retries=3){
  for(let i=0;i<retries;i++){
    try{ return await serper(endpoint, payload); }
    catch(e){ if(i===retries-1) throw e; await new Promise(r=>setTimeout(r, 500*(i+1))); }
  }
}
```

## 17) Seed Leads from Organic Results
```js
const res = await serper('search',{ q:'immigration lawyer Calgary phone email', gl:'ca', hl:'en', num:10 });
const leads = res.organic?.map(o => ({ title:o.title, url:o.link })) || [];
console.log(leads);
```

## 18) Estimate API Calls
```js
export function estimateCalls(regions, roles, pages){
  return regions.length * roles.length * pages;
}
```

## 19) Deduplicate by Domain
```js
export function dedupeByDomain(items){
  const seen = new Set();
  return items.filter(it => {
    try {
      const d = new URL(it.url).hostname.replace(/^www\./,'');
      if(seen.has(d)) return false; seen.add(d); return true;
    } catch { return false; }
  });
}
```

## 20) CSV Helper
```js
export function toCSV(rows){
  if(!rows.length) return '';
  const headers = Object.keys(rows[0]);
  const esc = v => '"'+String(v??'').replace(/"/g,'""')+'"';
  return [headers.join(','), ...rows.map(r => headers.map(h => esc(r[h])).join(','))].join('\n');
}
```

Notes:
- Respect rate limits and ToS.
- Cache common queries when feasible.
- Add adaptive backoff on 429/5xx.
