/* Nirobo Quick answers: finds the best hand-checked answer card for a question.
   Needs tokens(), score(), sk() and lev() from search-core.js. Cards live in data/answers.json. */
var NiroboAnswers=(function(){
var GENERIC=["number","numbers","bangladesh","national","important","list","check","code","get","take","help","call","নম্বর","বাংলাদেশ","তালিকা","বাংলাদেশের","bangladeshe","bangladesher"];
function prep(c){if(c._p)return c;c.words=String(c.kw||"").toLowerCase().split(/\s+/).filter(Boolean);c.sk=c.words.map(sk);c._p=1;return c}
function norm(q){return String(q).replace(/[০-৯]/g,function(d){return"০১২৩৪৫৬৭৮৯".indexOf(d)}).replace(/-/g," ")}
function has(toks,group){return toks.some(function(t){return group.some(function(w){return w===t||(t.length>=5&&w.length>=5&&lev(w,t)<=1)})})}
function find(q,cards){var toks=tokens(norm(q));if(!toks.length||!cards||!cards.length)return null;var best=null,bn=0;
 cards.forEach(function(c){prep(c);
  if(c.need&&!c.need.every(function(g){return has(toks,g)}))return;
  var n=score(c,toks);
  if(toks.length===1&&c.an&&c.an.indexOf(toks[0])>-1)n+=6;
  if(n>bn){bn=n;best=c}});
 return best&&bn>=6?best:null}
/* Softer match: cards that share even one real keyword with the search. Used for "Questions you may have". */
function suggest(q,cards,max){var toks=tokens(norm(q)).filter(function(t){return GENERIC.indexOf(t)<0});if(!toks.length||!cards||!cards.length)return[];var out=[];
 cards.forEach(function(c){prep(c);var n=score(c,toks);if(toks.length===1&&c.an&&c.an.indexOf(toks[0])>-1)n+=6;if(n>=3)out.push({c:c,n:n})});
 out.sort(function(x,y){return y.n-x.n});return out.slice(0,max||5).map(function(x){return x.c})}
return{find:find,suggest:suggest}})();
