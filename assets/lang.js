/* 中英切換：?lang=zh|en → 已儲存的選擇 → 瀏覽器語言。兩種語言的全文都在 HTML 內，僅切換顯示。 */
(function () {
  var d = document.documentElement;
  function pick() {
    var m = /[?&]lang=([a-zA-Z-]+)/.exec(location.search), l = m ? m[1].toLowerCase() : null;
    if (l) l = l.indexOf('zh') === 0 ? 'zh' : (l.indexOf('en') === 0 ? 'en' : null);
    if (!l) { try { l = localStorage.getItem('ldigi_lang'); } catch (e) {} }
    if (l !== 'zh' && l !== 'en') {
      var n = (navigator.languages && navigator.languages[0]) || navigator.language || 'en';
      l = /^zh/i.test(n) ? 'zh' : 'en';
    }
    return l;
  }
  function set(l, save) {
    d.setAttribute('data-lang', l);
    d.lang = l === 'zh' ? 'zh-Hant' : 'en';
    var t = d.getAttribute('data-title-' + l); if (t) document.title = t;
    var bs = document.querySelectorAll('.lang button');
    for (var i = 0; i < bs.length; i++) bs[i].className = bs[i].getAttribute('data-set') === l ? 'on' : '';
    if (save) { try { localStorage.setItem('ldigi_lang', l); } catch (e) {} }
  }
  set(pick(), false);
  document.addEventListener('DOMContentLoaded', function () {
    set(d.getAttribute('data-lang'), false);
    var bs = document.querySelectorAll('.lang button');
    for (var i = 0; i < bs.length; i++) bs[i].addEventListener('click', function () {
      var l = this.getAttribute('data-set'); set(l, true);
      try { var u = new URL(location.href); u.searchParams.set('lang', l); history.replaceState(null, '', u); } catch (e) {}
    });
  });
})();
