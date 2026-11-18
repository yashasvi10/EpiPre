async function postJSON(url, body, targetId) {
  const target=document.getElementById(targetId); if(target) target.textContent="Connecting to public API...";
  try {
    const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    const data=await r.json(); if(!r.ok||!data.success) throw new Error(data.error||"Request failed");
    if(target) target.textContent=JSON.stringify(data);
    return data;
  } catch(e) { if(target) target.textContent="API error: "+e.message; return null; }
}
function fetchBluesky(){postJSON("/api/social/bluesky",{term:document.getElementById("bsky-term").value},"social-result").then(()=>location.reload());}
function fetchMastodon(){postJSON("/api/social/mastodon",{tag:document.getElementById("mast-tag").value,instance:"https://mastodon.social"},"social-result").then(()=>location.reload());}
function fetchWeather(city){postJSON("/api/weather",{city},"weather-result").then(d=>{if(d)document.getElementById("weather-result").textContent=`${d.location}: ${d.temperature}°C · humidity ${d.humidity}% · precipitation ${d.precipitation} mm`;});}
function fetchNews(){postJSON("/api/news",{term:document.getElementById("news-term").value},"news-result").then(()=>location.reload());}
function refreshMonitor(term){postJSON("/api/monitor",{term},"monitor-result").then(d=>{if(d)document.getElementById("monitor-result").textContent=JSON.stringify(d.results);});}
