<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Ecma TC 一覧

> Ecma International の技術委員会 (TC39 など) をカードで一覧表示。

- URL: https://memo.taka1156.site/ecma.html
- タグ: JavaScript
- 日付: 2026-10-31

---

Ecma TC 一覧

# Ecma TC一覧

Ecma Internationalの技術委員会 TC1〜TC57 全57件。活動中と任務完了を、状態・分野・キーワードで絞り込めます。

状態

分野

検索 タスクグループがあるTCのみ

件を表示

条件をリセット

条件に合うTCはありません。条件をリセットしてください。

JavaScript関連(活動中) その他の活動中TC プログラミング言語系(任務完了) その他の任務完了TC

出典: [Ecma International Technical Committees](https://ecma-international.org/technical-committees/) 、 [TCs which have accomplished their tasks](https://ecma-international.org/technical-committees/tcs-which-have-accomplished-their-tasks/) (2026年10月31日時点)。日本語名は要約です。

## ページ内のデータ（JavaScript で描画される部分）

```js
var JS = "JavaScript", LANG = "プログラミング言語", DOC = "文書・データ形式", MEDIA = "記憶媒体・機器",
    COMM = "通信・接続", SAFE = "安全・環境・人間工学", SYS = "ソフトウェア・システム";
var CATS = [JS, LANG, DOC, MEDIA, COMM, SAFE, SYS];
/* [番号, a=活動中 / c=任務完了, 分野, 英語名, 日本語名, タスクグループ] */
var TCS = [
 [1,"c",DOC,"Codes (Coded character sets)","文字コード",[]],
 [2,"c",LANG,"General programming languages","汎用プログラミング言語",[]],
 [3,"c",SYS,"Problem analysis and flow charting","問題分析・流れ図",[]],
 [4,"c",MEDIA,"Optical Character Recognition","光学文字認識(OCR)",[]],
 [5,"c",LANG,"ALGOL","ALGOL",[]],
 [6,"c",LANG,"COBOL","COBOL",[]],
 [7,"c",MEDIA,"Magnetic ink character recognition","磁気インク文字認識",[]],
 [8,"c",LANG,"FORTRAN","FORTRAN",[]],
 [9,"c",COMM,"Data transmission","データ伝送",[]],
 [10,"c",LANG,"PL/1","PL/1",[]],
 [11,"c",SYS,"Numerical control","数値制御",[]],
 [12,"a",SAFE,"Product safety","製品安全",[]],
 [13,"c",MEDIA,"Keyboards","キーボード",[]],
 [14,"c",DOC,"Paper sizes","用紙サイズ",[]],
 [15,"c",MEDIA,"Volume and file structure","ボリューム・ファイル構造",[]],
 [16,"c",MEDIA,"Rigid magnetic disks","剛体磁気ディスク",[]],
 [17,"c",MEDIA,"Magnetic tapes and tape cartridges","磁気テープ・カートリッジ",[]],
 [18,"c",MEDIA,"I/O interface","I/Oインタフェース",[]],
 [19,"c",MEDIA,"Flexible disk cartridges","フレキシブルディスクカートリッジ",[]],
 [20,"a",SAFE,"Electromagnetic Compatibility and Electromagnetic Fields (EMC and EMF)","電磁両立性・電磁界",[]],
 [21,"c",LANG,"BASIC","BASIC",[]],
 [22,"c",SYS,"Database","データベース",[]],
 [23,"c",COMM,"Open Systems Interconnection","OSI(開放型システム間相互接続)",[]],
 [24,"c",COMM,"Communications protocols","通信プロトコル",[]],
 [25,"c",COMM,"Data networks","データネットワーク",[]],
 [26,"a",SAFE,"Acoustics","騒音・音響",[
   ["TG1","Noise and vibration measurement of small air-moving devices"],
   ["TG2","Noise measurement of MFDs and related product categories"],
   ["TG3","Psychoacoustic standards for IT and CE equipment"],
   ["TG4","Airborne noise measurement of computer equipment and rack equipment"],
   ["TG5","Modular acoustic data acquisition systems"],
   ["TG6","Hard Disk Drive (HDD) disturbance noise"]]],
 [27,"c",LANG,"Ada","Ada",[]],
 [28,"c",SAFE,"Ergonomics of work stations","ワークステーションの人間工学",[]],
 [29,"c",DOC,"Document architecture and interchange","文書アーキテクチャ・交換",[]],
 [30,"c",COMM,"SCSI Small Computer Systems Interface","SCSI",[]],
 [31,"a",MEDIA,"Information storage","情報記憶",[
   ["TG2","Holographic information storage"],
   ["TG3","Volume and file structure"]]],
 [32,"a",DOC,"Multimedia coding and communications","マルチメディア符号化・通信",[]],
 [33,"c",SYS,"Portable Common Tool Environment (PCTE)","PCTE(可搬共通ツール環境)",[]],
 [34,"c",MEDIA,"Office devices","オフィス機器",[]],
 [35,"c",SYS,"User system interface","ユーザーシステムインタフェース",[]],
 [36,"c",SYS,"IT security","ITセキュリティ",[]],
 [37,"c",SYS,"Application Programming Interface for Windows (APIW)","Windows用API(APIW)",[]],
 [38,"a",SAFE,"Product-related environmental attributes","製品の環境属性",[
   ["TG1","Chemical emissions"],
   ["TG3","Environmental declarations"]]],
 [39,"a",JS,"ECMAScript","JavaScript言語仕様",[
   ["TG1","General ECMAScript language"],
   ["TG2","ECMAScript internationalization API specification"],
   ["TG3","Security"],
   ["TG4","Source map specification"],
   ["TG5","Experiments in programming language standardization"]]],
 [40,"c",SYS,"Object data interfaces","オブジェクトデータインタフェース",[]],
 [41,"c",SYS,"Platform independent computing environment","プラットフォーム非依存計算環境",[]],
 [42,"c",COMM,"Interconnects","インターコネクト",[]],
 [43,"c",DOC,"Universal 3D (U3D)","U3D(3Dデータ形式)",[]],
 [44,"c",MEDIA,"Holographic Information Storage Systems (HISS)","ホログラフィック情報記憶",[]],
 [45,"a",DOC,"Office Open XML formats","Office文書形式",[]],
 [46,"a",DOC,"Open XML Paper Specification (OpenXPS)","固定レイアウト文書",[]],
 [47,"c",COMM,"Near Field Communications","NFC",[]],
 [48,"c",COMM,"High rate wireless communications","高速無線通信",[]],
 [49,"a",LANG,"Programming languages","プログラミング言語",[
   ["TG2","C#"],
   ["TG3","Common Language Infrastructure"],
   ["TG4","Eiffel language"]]],
 [50,"a",COMM,"Close proximity electric induction data transfer","近接電磁誘導データ転送",[]],
 [51,"a",COMM,"Access systems and information exchange between systems","システム間のアクセス・情報交換",[
   ["TG1","Near Field Communications"]]],
 [52,"a",LANG,"Dart","Dart言語",[]],
 [53,"a",JS,"ECMAScript modules for embedded systems","組み込み向けECMAScriptモジュール",[]],
 [54,"a",SYS,"Software and system transparency","ソフトウェア・システムの透明性(SBOM)",[
   ["TG1","Transparency exchange API"],
   ["TG2","Package URL"],
   ["TG3","Common Lifecycle Enumeration (CLE)"],
   ["TG4","Contributing.yaml specification"]]],
 [55,"a",JS,"Web-interoperable server runtimes","Web相互運用可能なサーバーランタイム",[]],
 [56,"a",SYS,"Natural language interaction protocol for communication with AI agents","AIエージェントとの自然言語通信プロトコル",[]],
 [57,"a",LANG,"High-Level Shading Language (HLSL)","HLSL(シェーダ言語)",[]]
];

var state = { status: "all", cat: "all", q: "", tgOnly: false };
var grid = document.getElementById("grid");
var STATUSES = [["all","すべて"],["a","活動中"],["c","任務完了"]];

function colorOf(t) {
  if (t[1] === "a") return t[2] === JS ? "js" : "act";
  return t[2] === LANG ? "lang" : "off";
}
function matches(t, ignore) {
  if (ignore !== "status" && state.status !== "all" && t[1] !== state.status) return false;
  if (ignore !== "cat" && state.cat !== "all" && t[2] !== state.cat) return false;
  if (state.tgOnly && !t[5].length) return false;
  if (state.q) {
    var hay = ("TC" + t[0] + " " + t[3] + " " + t[4] + " " + t[2] + " " + t[5].map(function (g) { return g[0] + " " + g[1]; }).join(" ")).toLowerCase();
    var words = state.q.toLowerCase().split(/\s+/).filter(Boolean);
    for (var i = 0; i < words.length; i++) if (hay.indexOf(words[i]) < 0) return false;
  }
  return true;
}
function el(tag, cls, text) {
  var e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}
function chips(rowId, items, key) {
  var row = document.getElementById(rowId);
  Array.prototype.slice.call(row.querySelectorAll(".chip")).forEach(function (c) { row.removeChild(c); });
  items.forEach(function (it) {
    var b = el("button", "chip");
    b.type = "button";
    b.setAttribute("aria-pressed", String(state[key] === it.value));
    b.appendChild(document.createTextNode(it.label));
    b.appendChild(el("span", "n", String(it.n)));
    b.addEventListener("click", function () { state[key] = it.value; render(); });
    row.appendChild(b);
  });
}
function render() {
  var shown = TCS.filter(function (t) { return matches(t); });
  chips("statusRow", STATUSES.map(function (s) {
    return { value: s[0], label: s[1], n: TCS.filter(function (t) { return matches(t, "status") && (s[0] === "all" || t[1] === s[0]); }).length };
  }), "status");
  chips("catRow", [{ value: "all", label: "すべて" }].concat(CATS.map(function (c) { return { value: c, label: c }; })).map(function (c) {
    c.n = TCS.filter(function (t) { return matches(t, "cat") && (c.value === "all" || t[2] === c.value); }).length;
    return c;
  }), "cat");
  grid.textContent = "";
  shown.forEach(function (t) {
    var card = el("article", "card " + colorOf(t));
    var top = el("div", "top");
    top.appendChild(el("span", "num", "TC" + t[0]));
    top.appendChild(el("span", "pill sub", t[1] === "a" ? "活動中" : "任務完了"));
    card.appendChild(top);
    card.appendChild(el("div", "en", t[3]));
    card.appendChild(el("div", "ja sub", t[4]));
    if (t[5].length) {
      var ul = el("ul", "tgs");
      t[5].forEach(function (g) {
        var li = el("li");
        li.appendChild(el("b", null, g[0]));
        li.appendChild(document.createTextNode(g[1]));
        ul.appendChild(li);
      });
      card.appendChild(ul);
    }
    grid.appendChild(card);
  });
  document.getElementById("count").textContent = shown.length + " / " + TCS.length;
  document.getElementById("empty").hidden = shown.length > 0;
}
document.getElementById("q").addEventListener("input", function (e) { state.q = e.target.value.trim(); render(); });
document.getElementById("tgOnly").addEventListener("change", function (e) { state.tgOnly = e.target.checked; render(); });
document.getElementById("reset").addEventListener("click", function () {
  state = { status: "all", cat: "all", q: "", tgOnly: false };
  document.getElementById("q").value = "";
  document.getElementById("tgOnly").checked = false;
  render();
});
render();
```
