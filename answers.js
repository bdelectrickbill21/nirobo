/* Nirobo Quick answers: finds the best hand-checked answer card for a question.
   Needs tokens(), score(), sk() and lev() from search-core.js. Cards live in data/answers.json. */
var NiroboAnswers=(function(){
function prep(c){if(c._p)return c;c.words=String(c.kw||"").toLowerCase().split(/\s+/).filter(Boolean);c.sk=c.words.map(sk);c._p=1;return c}
function has(toks,group){return toks.some(function(t){return group.some(function(w){return w===t||(t.length>=5&&w.length>=5&&lev(w,t)<=1)})})}
function find(q,cards){var toks=tokens(String(q).replace(/[০-৯]/g,function(d){return"০১২৩৪৫৬৭৮৯".indexOf(d)}).replace(/-/g," "));if(!toks.length||!cards||!cards.length)return null;var best=null,bn=0;
 cards.forEach(function(c){prep(c);
  if(c.need&&!c.need.every(function(g){return has(toks,g)}))return;
  var n=score(c,toks);
  if(toks.length===1&&c.an&&c.an.indexOf(toks[0])>-1)n+=6;
  if(n>bn){bn=n;best=c}});
 return best&&bn>=6?best:null}
return{find:find}})();
