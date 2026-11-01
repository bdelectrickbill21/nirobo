/* Nirobo retro look: switch, ticker, sticker and badges. Remembers the choice on this phone only. */
(function(){
 var d=document.documentElement,on=true;
 try{on=localStorage.getItem("nirobo-theme")!=="plain"}catch(e){}
 if(on)d.classList.add("retro");
 function ui(){var l=d.lang;return l==="bn"?"bn":l==="bn-Latn"?"bl":"en"}
 function T(k,f){try{var x=I18N[ui()][k];if(x)return x}catch(e){}return f}
 function el(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e}
 function init(){
  var nav=document.getElementById("langs"),body=document.body;
  function label(){var a=document.getElementById("thm");if(!a)return;var r=d.classList.contains("retro");a.textContent=T(r?"rt_plain":"rt_retro",r?"Simple look":"Retro look");a.setAttribute("aria-pressed",String(r));
   var m=document.getElementById("marqt");if(m)m.textContent=T("rt_marq","Welcome to Nirobo!");var st=document.getElementById("stk");if(st)st.textContent=T("rt_sticker","Hand-made in Bangladesh")}
  if(nav&&!document.getElementById("thm")){
   var a=el("a");a.id="thm";a.href="#";a.setAttribute("role","button");
   a.addEventListener("click",function(e){e.preventDefault();var r=d.classList.toggle("retro");try{localStorage.setItem("nirobo-theme",r?"retro":"plain")}catch(x){}label()});nav.appendChild(a);
   if(!document.getElementById("ticker")){var mq=el("div","marq");mq.setAttribute("aria-hidden","true");var sp=el("span");sp.id="marqt";mq.appendChild(sp);nav.insertAdjacentElement("afterend",mq)}}
  var hero=document.querySelector(".hero .tag");
  if(hero&&!document.getElementById("stk")){var s=el("div","sticker");s.id="stk";hero.insertAdjacentElement("afterend",s)}
  var foot=document.querySelector(".foot");
  if(foot&&!foot.querySelector(".badges")){var b=el("div","badges");b.setAttribute("aria-hidden","true");["NO TRACKING","100% FREE","MADE IN BD"].forEach(function(x){b.appendChild(el("span",0,x))});foot.insertBefore(b,foot.firstChild)}
  function win(){body.setAttribute("data-win",document.title)}
  win();var t=document.querySelector("title");if(t)new MutationObserver(win).observe(t,{childList:true});
  label();new MutationObserver(label).observe(d,{attributes:true,attributeFilter:["lang"]})}
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init()
})();
