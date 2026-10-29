/* Nirobo Study: calculator, percentages, equation solver and formula cards.
   No AI and no internet. Needs tokens(), score() and sk() from search-core.js. */
var NiroboStudy=(function(){
var BD="০১২৩৪৫৬৭৮৯";
function asc(s){return String(s).replace(/[০-৯]/g,function(d){return BD.indexOf(d)})}
function fmt(x){if(!isFinite(x))return null;if(Math.abs(x)<1e-12)return"0";return String(Number(x.toPrecision(12)))}
function frac(x){if(Math.abs(x-Math.round(x))<1e-9)return null;for(var q=2;q<=1000;q++){var p=Math.round(x*q);if(Math.abs(x-p/q)<1e-9)return p+"/"+q}return null}
function show(x){var f=frac(x),d=fmt(x);if(d===null)return null;return f?f+" (≈ "+String(Number(x.toPrecision(6)))+")":d}
function norm(q){return asc(q).toLowerCase().replace(/[−–—]/g,"-").replace(/×/g,"*").replace(/÷/g,"/").replace(/π/g,"pi").replace(/√/g,"sqrt").replace(/²/g,"^2").replace(/³/g,"^3").replace(/\*\*/g,"^").trim()}

/* ---------- calculator ---------- */
var FN={sqrt:Math.sqrt,cbrt:Math.cbrt,abs:Math.abs,exp:Math.exp,ln:Math.log,log:Math.log10,floor:Math.floor,ceil:Math.ceil,round:Math.round,
 sin:function(x){return Math.sin(x*Math.PI/180)},cos:function(x){return Math.cos(x*Math.PI/180)},tan:function(x){return Math.tan(x*Math.PI/180)},
 asin:function(x){return Math.asin(x)*180/Math.PI},acos:function(x){return Math.acos(x)*180/Math.PI},atan:function(x){return Math.atan(x)*180/Math.PI}};
var TRIG=/(^|[^a-z])(sin|cos|tan|asin|acos|atan)\(/;
function calc(s){var i=0,depth=0;
 function pk(){return s.charAt(i)}
 function expr(){var r=term();while(pk()==="+"||pk()==="-"){var o=s.charAt(i++),t=term();r=o==="+"?r+t:r-t}return r}
 function term(){var r=unary();for(;;){var c=pk();if(c==="*"){i++;r*=unary()}else if(c==="/"){i++;r/=unary()}else if(c==="("||/[a-z]/.test(c)){r*=unary()}else break}return r}
 function unary(){if(pk()==="-"){i++;return-unary()}if(pk()==="+"){i++;return unary()}return power()}
 function power(){var b=post();if(pk()==="^"){i++;return Math.pow(b,unary())}return b}
 function post(){var r=primary();for(;;){if(pk()==="!"){i++;r=fact(r)}else if(pk()==="%"){i++;r=r/100}else break}return r}
 function fact(n){if(n<0||n!==Math.floor(n)||n>170)throw 1;var r=1;for(var k=2;k<=n;k++)r*=k;return r}
 function primary(){if(++depth>40)throw 1;var c=pk(),r;
  if(c==="("){i++;r=expr();if(pk()!==")")throw 1;i++}
  else if(/[0-9.]/.test(c)){var m=/^(\d+\.?\d*|\.\d+)/.exec(s.slice(i));if(!m)throw 1;i+=m[0].length;r=parseFloat(m[0])}
  else if(/[a-z]/.test(c)){var w=/^[a-z]+/.exec(s.slice(i))[0];i+=w.length;
   if(w==="pi")r=Math.PI;else if(w==="e")r=Math.E;
   else if(FN[w]){if(pk()!=="(")throw 1;i++;var a=expr();if(pk()!==")")throw 1;i++;r=FN[w](a)}else throw 1}
  else throw 1;
  depth--;return r}
 var v=expr();if(i!==s.length)throw 1;return v}
function mathLike(s){
 if(/^\d{1,4}[-\/.]\d{1,2}[-\/.]\d{1,4}$/.test(s)||/^\+?\d[\d\s-]{8,}$/.test(s))return false;
 if(!/[0-9]/.test(s)||!/^[0-9a-z+\-*\/^().,%!\s]+$/.test(s))return false;
 return /[+*\/^!]|\d\s*-\s*[\d(.]|\(|[a-z]+\s*\d/.test(s)&&!/^\d+%$/.test(s)}
function tryCalc(q){var s=norm(q).replace(/^(what is|whats|calculate|calc|hisab|koto|কত|হিসাব)\s+/,"").replace(/[=?]+$/,"").trim();
 s=s.replace(/(sqrt|cbrt)\s*(\d+\.?\d*)/g,"$1($2)").replace(/(\d),(?=\d{3}\b)/g,"$1").replace(/(\d)\s*x\s*(?=\d)/g,"$1*").replace(/\s+/g,"");
 if(!mathLike(s))return null;
 try{var v=calc(s),f=fmt(v);if(f===null)return{k:"calc",expr:s,val:null};return{k:"calc",expr:s.replace(/\*/g,"×").replace(/\//g,"÷").replace(/sqrt/g,"√"),val:f,deg:TRIG.test(s)}}catch(e){return null}}

/* ---------- percentages: "20% of 500" ---------- */
function tryPct(q){var s=norm(q).replace(/^(what is|whats|calculate|calc|koto|কত|হিসাব)\s+/,"").replace(/[=?]+$/,"").trim();
 var m=/^(\d+(?:\.\d+)?)\s*(?:%|percent|shotangsho|shatangsho|শতাংশ)\s*(?:of|er|এর)\s*(\d+(?:\.\d+)?)$/.exec(s);
 if(!m)return null;var p=parseFloat(m[1]),y=parseFloat(m[2]);return{k:"pct",p:fmt(p),y:fmt(y),val:fmt(p/100*y)}}

/* ---------- equations (degree 1 and 2) ---------- */
function padd(a,b,s){var n=Math.max(a.length,b.length),r=[];for(var i=0;i<n;i++)r[i]=(a[i]||0)+s*(b[i]||0);return r}
function pmul(a,b){var r=[];for(var i=0;i<a.length;i++)for(var j=0;j<b.length;j++)r[i+j]=(r[i+j]||0)+a[i]*b[j];return r}
function ppow(a,n){var r=[1];for(var i=0;i<n;i++)r=pmul(r,a);return r}
function isConst(a){for(var i=1;i<a.length;i++)if(Math.abs(a[i])>1e-12)return false;return true}
function poly(s,v){var i=0;
 function pk(){return s.charAt(i)}
 function expr(){var r=term();while(pk()==="+"||pk()==="-"){var o=s.charAt(i++),t=term();r=padd(r,t,o==="+"?1:-1)}return r}
 function term(){var r=unary();for(;;){var c=pk();if(c==="*"){i++;r=pmul(r,unary())}
  else if(c==="/"){i++;var d=unary();if(!isConst(d)||Math.abs(d[0])<1e-12)throw 1;r=r.map(function(x){return x/d[0]})}
  else if(c==="("||c===v){r=pmul(r,power())}else break}return r}
 function unary(){if(pk()==="-"){i++;return unary().map(function(x){return-x})}if(pk()==="+"){i++;return unary()}return power()}
 function power(){var b=primary();if(pk()==="^"){i++;var e=unary();if(!isConst(e)||e[0]<0||e[0]!==Math.floor(e[0])||e[0]>6)throw 1;return ppow(b,e[0])}return b}
 function primary(){var c=pk();
  if(c==="("){i++;var r=expr();if(pk()!==")")throw 1;i++;return r}
  if(/[0-9.]/.test(c)){var m=/^(\d+\.?\d*|\.\d+)/.exec(s.slice(i));if(!m)throw 1;i+=m[0].length;return[parseFloat(m[0])]}
  if(c===v){i++;return[0,1]}throw 1}
 var r=expr();if(i!==s.length)throw 1;return r}
var SUP={"2":"²","1":"","0":""};
function termStr(c,v,p,first){if(Math.abs(c)<1e-12)return"";var a=Math.abs(c),n=(a===1&&p>0)?"":fmt(a),sym=p===0?"":(v+(p===2?"²":"")),sg=c<0?"-":"+";
 return(first?(c<0?"−":""):(" "+(c<0?"−":"+")+" "))+n+sym}
function stdForm(co,v){var s="",first=true;for(var p=2;p>=0;p--){var t=termStr(co[p]||0,v,p,first);if(t){s+=t;first=false}}return(s||"0")+" = 0"}
function tryEq(q){var s=norm(q).replace(/\s+/g,"").replace(/[?]+$/,"");
 if((s.match(/=/g)||[]).length!==1||!/[0-9]/.test(s))return null;
 var letters=s.replace(/[^a-z]/g,"");if(!letters)return null;var set={};letters.split("").forEach(function(c){set[c]=1});
 var keys=Object.keys(set);if(keys.length!==1)return null;var v=keys[0];
 if(!/^[0-9a-z+\-*\/^().]+=[0-9a-z+\-*\/^().]+$/.test(s))return null;
 var parts=s.split("="),L,R;try{L=poly(parts[0],v);R=poly(parts[1],v)}catch(e){return null}
 var f=padd(L,R,-1);while(f.length>1&&Math.abs(f[f.length-1])<1e-12)f.pop();var deg=f.length-1;
 if(deg>2)return{k:"eq",deg:3,v:v};
 if(deg===0)return{k:"eq",deg:0,v:v,same:Math.abs(f[0])<1e-12};
 var out={k:"eq",deg:deg,v:v,std:stdForm(f,v)};
 if(deg===1){var a=f[1],b=f[0];out.a=fmt(a);out.b=fmt(b);out.roots=[show(-b/a)];return out}
 var A=f[2],B=f[1],C=f[0],D=B*B-4*A*C;out.a=fmt(A);out.b=fmt(B);out.c=fmt(C);out.D=fmt(D);
 if(D>1e-12){out.kind="two";out.roots=[show((-B+Math.sqrt(D))/(2*A)),show((-B-Math.sqrt(D))/(2*A))]}
 else if(Math.abs(D)<=1e-12){out.kind="one";out.roots=[show(-B/(2*A))]}
 else{out.kind="none";var re=-B/(2*A),im=Math.abs(Math.sqrt(-D)/(2*A));out.roots=[fmt(re)+" + "+fmt(im)+"i",fmt(re)+" − "+fmt(im)+"i"]}
 return out}

/* ---------- formula cards ---------- */
var F=[
{id:"circle",kw:"circle circular area circumference radius diameter pi britto britter britta bittor byasardho byas poridhi khetrofol বৃত্ত বৃত্তের ব্যাসার্ধ ব্যাস পরিধি ক্ষেত্রফল",
 t:{en:"Circle: area and circumference",bl:"Britto: khetrofol o poridhi",bn:"বৃত্ত: ক্ষেত্রফল ও পরিধি"},
 lines:["A = πr²","C = 2πr"],
 w:{en:"A = area, C = circumference, r = radius, π ≈ 3.1416 (or 22/7)",bl:"A = khetrofol, C = poridhi, r = byasardho, π ≈ 3.1416 (ba 22/7)",bn:"A = ক্ষেত্রফল, C = পরিধি, r = ব্যাসার্ধ, π ≈ 3.1416 (বা 22/7)"},
 ex:"r = 7  →  A = 22/7 × 49 = 154,  C = 2 × 22/7 × 7 = 44"},
{id:"rect",kw:"rectangle square area perimeter length width breadth ayotokkhetro ayotakar borgo borgokkhetro khetrofol poriseema doirgho prostho আয়তক্ষেত্র আয়তক্ষেত্রের বর্গ বর্গক্ষেত্র ক্ষেত্রফল পরিসীমা দৈর্ঘ্য প্রস্থ",
 t:{en:"Rectangle and square",bl:"Ayotokkhetro o borgokkhetro",bn:"আয়তক্ষেত্র ও বর্গক্ষেত্র"},
 lines:["Rectangle:  A = l × w,   P = 2(l + w)","Square:  A = a²,   P = 4a"],
 w:{en:"l = length, w = width, a = side, A = area, P = perimeter",bl:"l = doirgho, w = prostho, a = bahu, A = khetrofol, P = poriseema",bn:"l = দৈর্ঘ্য, w = প্রস্থ, a = বাহু, A = ক্ষেত্রফল, P = পরিসীমা"},
 ex:"l = 8, w = 5  →  A = 40,  P = 26"},
{id:"tri",kw:"triangle area base height heron herons tribhuj tribhuz tribhuja bhumi uchchota ucchota khetrofol ত্রিভুজ ত্রিভুজের ভূমি উচ্চতা হেরন ক্ষেত্রফল",an:["heron","herons","হেরন"],
 t:{en:"Triangle area (and Heron's formula)",bl:"Tribhujer khetrofol (Heron-er sutro)",bn:"ত্রিভুজের ক্ষেত্রফল (হেরনের সূত্র)"},
 lines:["A = ½ × base × height","A = √( s(s − a)(s − b)(s − c) ),   s = (a + b + c) / 2"],
 w:{en:"a, b, c = the three sides, s = half of the perimeter",bl:"a, b, c = tin bahu, s = poriseemar ordhek",bn:"a, b, c = তিন বাহু, s = পরিসীমার অর্ধেক"},
 ex:"base 10, height 6  →  A = 30;   sides 3, 4, 5  →  s = 6,  A = 6"},
{id:"pyth",kw:"pythagoras pythagorean pythagorus pitagoras hypotenuse right triangle theorem sutro otibhuj sukkhokon somokoni পিথাগোরাস পিথাগোরাসের অতিভুজ সমকোণী উপপাদ্য",an:["pythagoras","pythagorean","পিথাগোরাস","পিথাগোরাসের"],
 t:{en:"Pythagoras theorem",bl:"Pythagoras-er upoddo",bn:"পিথাগোরাসের উপপাদ্য"},
 lines:["a² + b² = c²"],
 w:{en:"c = hypotenuse (the longest side), a and b = the other two sides",bl:"c = otibhuj (shobcheye boro bahu), a o b = onno duti bahu",bn:"c = অতিভুজ (সবচেয়ে বড় বাহু), a ও b = অন্য দুই বাহু"},
 ex:"a = 3, b = 4  →  c = √(9 + 16) = 5"},
{id:"quad",kw:"quadratic equation discriminant roots solve dwighat dwighaat sridhar sridharacharya somikoron mul দ্বিঘাত সমীকরণ শ্রীধর আচার্য মূল নিরূপক",an:["quadratic","discriminant","দ্বিঘাত","dwighat","sridhar","sridharacharya"],tip:1,
 t:{en:"Quadratic formula",bl:"Dwighat somikoroner sutro",bn:"দ্বিঘাত সমীকরণের সূত্র"},
 lines:["ax² + bx + c = 0","x = ( −b ± √(b² − 4ac) ) / 2a","D = b² − 4ac"],
 w:{en:"D > 0: two real roots.  D = 0: one root.  D < 0: no real roots.",bl:"D > 0: duti bastob mul.  D = 0: ekti mul.  D < 0: bastob mul nei.",bn:"D > 0: দুটি বাস্তব মূল।  D = 0: একটি মূল।  D < 0: বাস্তব মূল নেই।"},
 ex:"x² − 5x + 6 = 0  →  D = 1,  x = 3 or x = 2"},
{id:"ident",pat:/\(a[+\-]b\)(\^?[23]|[²³])/,kw:"algebra identity identities expand expansion bijgonit bijganit sutrabali বীজগণিত অভেদ",
 t:{en:"Algebra identities",bl:"Bijgoniter sutro (identity)",bn:"বীজগণিতের সূত্র (অভেদ)"},
 lines:["(a + b)² = a² + 2ab + b²","(a − b)² = a² − 2ab + b²","a² − b² = (a + b)(a − b)","(a + b)³ = a³ + 3a²b + 3ab² + b³","a³ + b³ = (a + b)(a² − ab + b²)","a³ − b³ = (a − b)(a² + ab + b²)"],
 w:{en:"These are true for all numbers a and b.",bl:"Ei sutrogulo a ar b-er shob manei shotti.",bn:"এই সূত্রগুলো a ও b-এর সব মানের জন্য সত্য।"},
 ex:"(3 + 2)² = 9 + 12 + 4 = 25"},
{id:"sphere",kw:"sphere ball gola golok গোলক গোলকের volume surface area ayotan tolokkhetro আয়তন",an:["sphere","গোলক","golok"],
 t:{en:"Sphere: volume and surface area",bl:"Golok: ayotan o tolkkhetro",bn:"গোলক: আয়তন ও পৃষ্ঠতলের ক্ষেত্রফল"},
 lines:["V = 4/3 × πr³","S = 4πr²"],
 w:{en:"V = volume, S = surface area, r = radius",bl:"V = ayotan, S = prishthotoler khetrofol, r = byasardho",bn:"V = আয়তন, S = পৃষ্ঠতলের ক্ষেত্রফল, r = ব্যাসার্ধ"},
 ex:"r = 3  →  V = 36π ≈ 113.1,   S = 36π ≈ 113.1"},
{id:"cyl",kw:"cylinder belon বেলন volume surface area ayotan curved total আয়তন",an:["cylinder","belon","বেলন"],
 t:{en:"Cylinder: volume and surface area",bl:"Belon: ayotan o tolkkhetro",bn:"বেলন: আয়তন ও তলের ক্ষেত্রফল"},
 lines:["V = πr²h","Curved surface = 2πrh","Total surface = 2πr(r + h)"],
 w:{en:"r = radius of the base, h = height",bl:"r = bhumir byasardho, h = uchchota",bn:"r = ভূমির ব্যাসার্ধ, h = উচ্চতা"},
 ex:"r = 7, h = 10  →  V = 22/7 × 49 × 10 = 1540"},
{id:"cone",kw:"cone sonku shonku শঙ্কু volume surface area slant curved ayotan আয়তন",an:["shonku","sonku","শঙ্কু"],
 t:{en:"Cone: volume and surface area",bl:"Shonku: ayotan o tolkkhetro",bn:"শঙ্কু: আয়তন ও তলের ক্ষেত্রফল"},
 lines:["V = ⅓ × πr²h","Slant height  l = √(r² + h²)","Curved surface = πrl","Total surface = πr(r + l)"],
 w:{en:"r = radius of the base, h = height, l = slant height",bl:"r = bhumir byasardho, h = uchchota, l = tirjok uchchota",bn:"r = ভূমির ব্যাসার্ধ, h = উচ্চতা, l = হেলানো উচ্চতা"},
 ex:"r = 3, h = 4  →  l = 5,  V = 12π ≈ 37.7"},
{id:"cube",kw:"cube cuboid ghonok ayatghon ayotghon ঘনক আয়তঘন volume surface area ayotan আয়তন",an:["cuboid","ghonok","ঘনক","আয়তঘন"],
 t:{en:"Cube and cuboid",bl:"Ghonok o ayotghon",bn:"ঘনক ও আয়তঘন"},
 lines:["Cube:  V = a³,   total surface = 6a²","Cuboid:  V = l × w × h,   total surface = 2(lw + wh + hl)"],
 w:{en:"a = edge, l = length, w = width, h = height",bl:"a = dhar, l = doirgho, w = prostho, h = uchchota",bn:"a = ধার, l = দৈর্ঘ্য, w = প্রস্থ, h = উচ্চতা"},
 ex:"cuboid 5 × 4 × 3  →  V = 60,  surface = 2(20 + 12 + 15) = 94"},
{id:"speed",kw:"speed velocity distance time gati gotibeg gotibeg bega durotto doorotto somoy দ্রুতি বেগ দূরত্ব সময় গতিবেগ",
 t:{en:"Speed, distance and time",bl:"Gotibeg, durotto o somoy",bn:"দ্রুতি, দূরত্ব ও সময়"},
 lines:["speed = distance / time","distance = speed × time","time = distance / speed"],
 w:{en:"Use matching units (for example km, hours and km/h).",bl:"Ekoi ekok babohar korun (jemon km, ghonta o km/h).",bn:"একই একক ব্যবহার করুন (যেমন কিমি, ঘণ্টা ও কিমি/ঘণ্টা)।"},
 ex:"120 km in 2 hours  →  speed = 60 km/h"},
{id:"pct",kw:"percentage percent increase decrease change shotangsho shatangsho শতাংশ শতকরা বৃদ্ধি হ্রাস",tip:2,
 t:{en:"Percentage",bl:"Shotangsho",bn:"শতকরা (শতাংশ)"},
 lines:["x% of y = (x / 100) × y","Percentage change = (new − old) / old × 100"],
 w:{en:"x = the percent, y = the whole amount",bl:"x = shotangsho, y = mot poriman",bn:"x = শতাংশ, y = মোট পরিমাণ"},
 ex:"20% of 500 = 100;   50 → 60 is a 20% increase"},
{id:"interest",kw:"interest simple compound sud suud sudh choksibridhi chokrobriddhi principal munafa মুনাফা সুদ সরল চক্রবৃদ্ধি আসল হার",an:["chokrobriddhi","choksibridhi","চক্রবৃদ্ধি"],
 t:{en:"Simple and compound interest",bl:"Shorol o chokrobriddhi sud",bn:"সরল ও চক্রবৃদ্ধি সুদ"},
 lines:["Simple interest:  I = P × r × t / 100","Compound amount:  A = P (1 + r/100)ⁿ","Compound interest = A − P"],
 w:{en:"P = principal, r = rate per year (%), t or n = years, A = total amount",bl:"P = ashol, r = bochhorer har (%), t ba n = bochhor, A = mot taka",bn:"P = আসল, r = বার্ষিক হার (%), t বা n = বছর, A = মোট টাকা"},
 ex:"P = 1000, r = 10%, 2 years  →  simple I = 200;   compound A = 1210"},
{id:"avg",kw:"average mean gor gorposhi gor-er গড় গড়ের",
 t:{en:"Average (mean)",bl:"Gor (average)",bn:"গড়"},
 lines:["average = sum of all values / number of values"],
 w:{en:"Add all the numbers, then divide by how many there are.",bl:"Shob shonkha jog korun, tarpor koyti shonkha tā diye bhag korun.",bn:"সব সংখ্যা যোগ করে কয়টি সংখ্যা আছে তা দিয়ে ভাগ করুন।"},
 ex:"4, 7, 10  →  21 / 3 = 7"},
{id:"pl",kw:"profit loss cost selling labh khoti kroy bikroy mullo লাভ ক্ষতি ক্রয়মূল্য বিক্রয়মূল্য ক্রয় বিক্রয়",
 t:{en:"Profit and loss",bl:"Labh o khoti",bn:"লাভ ও ক্ষতি"},
 lines:["Profit = SP − CP   (when SP > CP)","Loss = CP − SP   (when CP > SP)","Profit % = profit / CP × 100","Loss % = loss / CP × 100"],
 w:{en:"CP = cost price, SP = selling price",bl:"CP = kroy mullo, SP = bikroy mullo",bn:"CP = ক্রয়মূল্য, SP = বিক্রয়মূল্য"},
 ex:"CP = 200, SP = 250  →  profit = 50,  profit % = 25%"},
{id:"ohm",kw:"ohm ohms law voltage current resistance power watt electricity bidyut volt ampere resistor ওহম ওমের বিভব বিদ্যুৎ প্রবাহ রোধ ক্ষমতা",an:["ohm","ohms","ওহম","ওমের"],
 t:{en:"Ohm's law and electric power",bl:"Ohm-er sutro o boidyutik khomota",bn:"ওহমের সূত্র ও বৈদ্যুতিক ক্ষমতা"},
 lines:["V = I × R","P = V × I = I²R = V²/R"],
 w:{en:"V = voltage (volt), I = current (ampere), R = resistance (ohm), P = power (watt)",bl:"V = volt, I = ampere, R = rodh (ohm), P = khomota (watt)",bn:"V = বিভব (ভোল্ট), I = প্রবাহ (অ্যাম্পিয়ার), R = রোধ (ওহম), P = ক্ষমতা (ওয়াট)"},
 ex:"I = 2 A, R = 5 Ω  →  V = 10 V,  P = 20 W"},
{id:"newton",kw:"newton second law motion force mass acceleration weight gravity bol tvoron toron bhor ottokorshon নিউটন বল ভর ত্বরণ ওজন অভিকর্ষ",
 t:{en:"Force, mass and weight (Newton's second law)",bl:"Bol, bhor o ojon (Newton-er 2nd sutro)",bn:"বল, ভর ও ওজন (নিউটনের দ্বিতীয় সূত্র)"},
 lines:["F = m × a","W = m × g     (g ≈ 9.8 m/s²)"],
 w:{en:"F = force (N), m = mass (kg), a = acceleration (m/s²), W = weight",bl:"F = bol (N), m = bhor (kg), a = toron (m/s²), W = ojon",bn:"F = বল (N), m = ভর (kg), a = ত্বরণ (m/s²), W = ওজন"},
 ex:"m = 5 kg, a = 2 m/s²  →  F = 10 N"},
{id:"work",kw:"work energy power kinetic potential joule karjo kaj shokti gotishokti sthitishokti khomota কাজ শক্তি ক্ষমতা গতিশক্তি স্থিতিশক্তি",
 t:{en:"Work, energy and power",bl:"Kaj, shokti o khomota",bn:"কাজ, শক্তি ও ক্ষমতা"},
 lines:["W = F × d","P = W / t","Kinetic energy = ½ m v²","Potential energy = m g h"],
 w:{en:"W = work (J), F = force (N), d = distance (m), P = power (W), t = time (s), m = mass, v = speed, h = height",bl:"W = kaj (J), F = bol (N), d = durotto (m), P = khomota (W), t = somoy (s), m = bhor, v = gotibeg, h = uchchota",bn:"W = কাজ (J), F = বল (N), d = দূরত্ব (m), P = ক্ষমতা (W), t = সময় (s), m = ভর, v = বেগ, h = উচ্চতা"},
 ex:"m = 2 kg, v = 3 m/s  →  kinetic energy = 9 J"},
{id:"density",kw:"density mass volume ghonotto ghanatto ঘনত্ব",an:["density","ghonotto"],
 t:{en:"Density",bl:"Ghonotto",bn:"ঘনত্ব"},
 lines:["ρ = m / V"],
 w:{en:"ρ = density, m = mass, V = volume",bl:"ρ = ghonotto, m = bhor, V = ayotan",bn:"ρ = ঘনত্ব, m = ভর, V = আয়তন"},
 ex:"m = 200 g, V = 50 cm³  →  ρ = 4 g/cm³"},
{id:"trig",kw:"trigonometry trigonometric sin cos tan sine cosine tangent trikonomiti trikonomiti identity ত্রিকোণমিতি সাইন কস",an:["trigonometry","trikonomiti","ত্রিকোণমিতি"],
 t:{en:"Trigonometry basics",bl:"Trikonomitir mul sutro",bn:"ত্রিকোণমিতির মূল সূত্র"},
 lines:["sin θ = opposite / hypotenuse","cos θ = adjacent / hypotenuse","tan θ = opposite / adjacent = sin θ / cos θ","sin²θ + cos²θ = 1"],
 w:{en:"In a right triangle, for the angle θ.",bl:"Somokoni tribhuje, θ konér jonno.",bn:"সমকোণী ত্রিভুজে θ কোণের জন্য।"},
 ex:"sin 30° = 1/2,   cos 60° = 1/2,   tan 45° = 1"},
{id:"log",kw:"logarithm log ln exponent index indices laws power lagharitham logarithm ghat sutro সূচক লগারিদম ঘাত",an:["logarithm","লগারিদম","logarithms"],
 t:{en:"Logarithm and index laws",bl:"Logarithm o suchoker niyom",bn:"লগারিদম ও সূচকের নিয়ম"},
 lines:["log(ab) = log a + log b","log(a/b) = log a − log b","log(aⁿ) = n log a","aᵐ × aⁿ = aᵐ⁺ⁿ,   aᵐ / aⁿ = aᵐ⁻ⁿ,   (aᵐ)ⁿ = aᵐⁿ,   a⁰ = 1"],
 w:{en:"Here log means log to base 10.",bl:"Ekhane log mane base 10 log.",bn:"এখানে log মানে ভিত্তি ১০ এর লগ।"},
 ex:"log 100 = 2,   2³ × 2⁴ = 2⁷ = 128"},
{id:"prog",kw:"arithmetic geometric progression sequence series ap gp nth term dhara onudhara shreni shomantor gunottor সমান্তর গুণোত্তর ধারা অনুক্রম",an:["progression","onudhara","অনুক্রম"],
 t:{en:"Arithmetic and geometric progression",bl:"Shomantor o gunottor dhara",bn:"সমান্তর ও গুণোত্তর ধারা"},
 lines:["AP:  nth term = a + (n − 1)d","AP:  sum = n/2 × ( 2a + (n − 1)d )","GP:  nth term = a rⁿ⁻¹","GP:  sum = a(rⁿ − 1) / (r − 1)    (r ≠ 1)"],
 w:{en:"a = first term, d = common difference, r = common ratio, n = number of terms",bl:"a = prothom podo, d = shadharon antor, r = shadharon onupat, n = podo shonkha",bn:"a = প্রথম পদ, d = সাধারণ অন্তর, r = সাধারণ অনুপাত, n = পদসংখ্যা"},
 ex:"AP 2, 5, 8, …  →  10th term = 2 + 9 × 3 = 29"},
{id:"coord",kw:"distance formula slope gradient line midpoint points coordinate dura durotto dal dhal sarolrekha মধ্যবিন্দু দূরত্ব ঢাল সরলরেখা স্থানাঙ্ক",an:["midpoint","স্থানাঙ্ক","মধ্যবিন্দু"],
 t:{en:"Coordinate geometry",bl:"Sthanankko jyamiti",bn:"স্থানাঙ্ক জ্যামিতি"},
 lines:["Distance = √( (x₂ − x₁)² + (y₂ − y₁)² )","Midpoint = ( (x₁ + x₂)/2 , (y₁ + y₂)/2 )","Slope  m = (y₂ − y₁) / (x₂ − x₁)","Line:  y = mx + c"],
 w:{en:"Two points (x₁, y₁) and (x₂, y₂).",bl:"Duti bindu (x₁, y₁) o (x₂, y₂).",bn:"দুটি বিন্দু (x₁, y₁) ও (x₂, y₂)।"},
 ex:"(1, 2) and (4, 6)  →  distance = 5,  slope = 4/3"},
{id:"perm",kw:"permutation combination factorial npr ncr arrangement selection pormutation kombinesion kombinesion nirbachon ক্রমবিন্যাস সমাবেশ",an:["permutation","combination","factorial","ক্রমবিন্যাস","সমাবেশ"],
 t:{en:"Permutation and combination",bl:"Kromobinnyas o shomabesh",bn:"ক্রমবিন্যাস ও সমাবেশ"},
 lines:["n! = n × (n − 1) × … × 1","ⁿPᵣ = n! / (n − r)!","ⁿCᵣ = n! / ( r! (n − r)! )"],
 w:{en:"P counts arrangements (order matters). C counts selections (order does not matter).",bl:"P mane shajano (kromo gurutwopurno). C mane nirbachon (kromo gurutwopurno noy).",bn:"P মানে সাজানো (ক্রম গুরুত্বপূর্ণ)। C মানে বাছাই (ক্রম গুরুত্বপূর্ণ নয়)।"},
 ex:"⁵C₂ = 5! / (2! × 3!) = 10"},
{id:"prob",kw:"probability chance sombhabyota somvabyota probability সম্ভাবনা সম্ভাব্যতা",an:["probability","সম্ভাবনা","সম্ভাব্যতা"],
 t:{en:"Probability",bl:"Shombhabyota",bn:"সম্ভাবনা"},
 lines:["P(event) = favourable outcomes / all possible outcomes","0 ≤ P ≤ 1","P(not A) = 1 − P(A)"],
 w:{en:"The answer is always between 0 (impossible) and 1 (certain).",bl:"Uttor shobshomoy 0 (osombhob) theke 1 (nishchit)-er moddhe thake.",bn:"উত্তর সবসময় ০ (অসম্ভব) থেকে ১ (নিশ্চিত)-এর মধ্যে থাকে।"},
 ex:"A die: P(even number) = 3/6 = 1/2"},
{id:"quad4",kw:"trapezium trapezoid parallelogram rhombus area samantorik somantorik সামান্তরিক ট্রাপিজিয়াম রম্বস ক্ষেত্রফল",an:["trapezium","parallelogram","rhombus","সামান্তরিক","রম্বস"],
 t:{en:"Parallelogram, trapezium and rhombus",bl:"Samantorik, trapezium o rombas",bn:"সামান্তরিক, ট্রাপিজিয়াম ও রম্বস"},
 lines:["Parallelogram:  A = base × height","Trapezium:  A = ½ (a + b) h","Rhombus:  A = ½ d₁ d₂"],
 w:{en:"a, b = parallel sides, h = height, d₁, d₂ = diagonals",bl:"a, b = somantoral bahu, h = uchchota, d₁, d₂ = kor",bn:"a, b = সমান্তরাল বাহু, h = উচ্চতা, d₁, d₂ = কর্ণ"},
 ex:"a = 6, b = 10, h = 4  →  A = 32"},
{id:"poly",kw:"polygon angles interior exterior sum bohubhuj konkoner বহুভুজ কোণ",an:["polygon","বহুভুজ"],
 t:{en:"Angles of a polygon",bl:"Bohubhujer kon",bn:"বহুভুজের কোণ"},
 lines:["Sum of interior angles = (n − 2) × 180°","Each angle of a regular polygon = (n − 2) × 180° / n","Sum of exterior angles = 360°"],
 w:{en:"n = number of sides",bl:"n = bahur shonkha",bn:"n = বাহুর সংখ্যা"},
 ex:"Hexagon (n = 6):  sum = 720°,  each = 120°"},
{id:"temp",kw:"temperature celsius fahrenheit kelvin convert tapmatra তাপমাত্রা সেলসিয়াস ফারেনহাইট কেলভিন",an:["celsius","fahrenheit","kelvin","সেলসিয়াস","ফারেনহাইট"],
 t:{en:"Temperature conversion",bl:"Tapmatra rupantor",bn:"তাপমাত্রা রূপান্তর"},
 lines:["°F = °C × 9/5 + 32","°C = (°F − 32) × 5/9","K = °C + 273.15    (often 273 in school)"],
 w:{en:"°C = Celsius, °F = Fahrenheit, K = Kelvin",bl:"°C = Celsius, °F = Fahrenheit, K = Kelvin",bn:"°C = সেলসিয়াস, °F = ফারেনহাইট, K = কেলভিন"},
 ex:"100 °C  →  212 °F"}
];
F.forEach(function(f){f.words=f.kw.toLowerCase().split(/\s+/);f.sk=f.words.map(sk)});
var FW=/formulas?|formulae|sutro|sutra|shutro|shutra|সূত্র|সুত্র|ফর্মুলা|ফরমুলা/gi;
function tryFormula(q){var flag=false,s=q.replace(FW,function(){flag=true;return" "});
 var low=asc(s).toLowerCase().replace(/\s+/g,"");
 for(var i=0;i<F.length;i++)if(F[i].pat&&F[i].pat.test(low))return{k:"formula",f:F[i]};
 var toks=tokens(s);if(!toks.length)return null;var best=null,bn=0;
 F.forEach(function(f){var n=score(f,toks);if(toks.length===1&&f.an&&f.an.indexOf(toks[0])>-1)n+=5;if(n>bn){bn=n;best=f}});
 return best&&(bn>=5||(bn>=3&&flag))?{k:"formula",f:best}:null}

function answer(q){q=String(q||"").trim();if(!q||q.length>120)return null;
 return tryPct(q)||tryEq(q)||tryCalc(q)||tryFormula(q)}
return{answer:answer,formulas:F}})();
