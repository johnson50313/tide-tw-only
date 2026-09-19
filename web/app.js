(function () {
  'use strict';

  var state = {
    data: null,
    currentView: 'chart',
    currentRankTab: 'sectors',
    activeQuadrant: '',
    searchQuery: '',
    rankSort: 'net_5d_yi',
    selectedSector: null,
    chart: null,
    isCompact: localStorage.getItem('bubble_compact') === '1',
    watchlist: { sectors: [], stocks: [] }
  };

  function $(id) { return document.getElementById(id); }

  function getRenderSectors() {
    if (!state.data) return [];
    var all = state.data.sectors;
    if (!state.isCompact) return all;

    var sorted = all.slice().sort(function (a, b) {
      return Math.abs(b.net_5d_yi) - Math.abs(a.net_5d_yi);
    });
    var top15Names = new Set(sorted.slice(0, 15).map(function (s) { return s.name; }));

    // 若有自選項目或選取中板塊，也一併保留
    if (state.selectedSector) top15Names.add(state.selectedSector.name);

    return all.filter(function (s) { return top15Names.has(s.name); });
  }

  function syncCompactBtn() {
    var btn = $('compact-toggle');
    var label = $('compact-toggle-label');
    if (!btn || !label) return;
    btn.classList.toggle('active', state.isCompact);
    if (state.isCompact) {
      label.textContent = '只看熱門 15';
    } else {
      label.textContent = '顯示全部 ' + (state.data ? state.data.sectors.length : '76');
    }
  }

  function signed(v, digits) {
    if (v == null || isNaN(v)) return '--';
    var d = digits == null ? 2 : digits;
    return (v >= 0 ? '+' : '') + Number(v).toFixed(d);
  }

  function loadWatchlist() {
    try {
      var raw = localStorage.getItem('tide_watchlist');
      if (raw) {
        state.watchlist = JSON.parse(raw);
      }
    } catch (e) {
      state.watchlist = { sectors: [], stocks: [] };
    }
  }

  function saveWatchlist() {
    try {
      localStorage.setItem('tide_watchlist', JSON.stringify(state.watchlist));
    } catch (e) {}
    renderWatchlist();
  }

  function isSectorFav(name) {
    return state.watchlist.sectors && state.watchlist.sectors.indexOf(name) !== -1;
  }

  function toggleSectorFav(name) {
    if (!state.watchlist.sectors) state.watchlist.sectors = [];
    var idx = state.watchlist.sectors.indexOf(name);
    if (idx === -1) {
      state.watchlist.sectors.push(name);
    } else {
      state.watchlist.sectors.splice(idx, 1);
    }
    saveWatchlist();
    updateDrawerFavBtn();
  }

  function isStockFav(code) {
    if (!state.watchlist.stocks) return false;
    return state.watchlist.stocks.some(function (s) { return s.code === code; });
  }

  function toggleStockFav(code, name, market) {
    if (!state.watchlist.stocks) state.watchlist.stocks = [];
    var idx = -1;
    for (var i = 0; i < state.watchlist.stocks.length; i++) {
      if (state.watchlist.stocks[i].code === code) { idx = i; break; }
    }
    if (idx === -1) {
      state.watchlist.stocks.push({ code: code, name: name, market: market });
    } else {
      state.watchlist.stocks.splice(idx, 1);
    }
    saveWatchlist();
    if (state.selectedSector) renderDrawerStocks(state.selectedSector);
  }

  function renderWatchlist() {
    var listEl = $('watchlist-items');
    var countEl = $('watchlist-count');
    var secList = state.watchlist.sectors || [];
    var stkList = state.watchlist.stocks || [];
    var totalCount = secList.length + stkList.length;

    countEl.textContent = totalCount;

    if (totalCount === 0) {
      listEl.innerHTML = '<div class="watchlist-empty">尚無自選項目<br>點選成分股或板塊詳情中的 ⭐ 即可加入收藏。</div>';
      return;
    }

    var html = '';
    secList.forEach(function (name) {
      var sec = state.data ? state.data.sectors.filter(function (s) { return s.name === name; })[0] : null;
      var net5 = sec ? signed(sec.net_5d_yi, 1) + '億' : '';
      html += '<div class="watchlist-item" data-type="sector" data-name="' + name + '">'
        + '<div style="display:flex; align-items:center; gap:6px; min-width:0;">'
        + '<span style="color:var(--c-gold); font-size:11px;">📁</span>'
        + '<span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-weight:600;">' + name + '</span>'
        + '</div>'
        + '<div style="display:flex; align-items:center; gap:6px; flex-shrink:0;">'
        + '<span style="font-size:11px;" class="' + (sec && sec.net_5d_yi >= 0 ? 'pos' : 'neg') + '">' + net5 + '</span>'
        + '<button class="remove-btn" data-rem-sec="' + name + '" title="移除">✕</button>'
        + '</div>'
        + '</div>';
    });

    stkList.forEach(function (stk) {
      html += '<div class="watchlist-item" data-type="stock" data-code="' + stk.code + '">'
        + '<div style="display:flex; align-items:center; gap:6px; min-width:0;">'
        + '<span class="search-item-code" style="font-size:11px;">' + stk.code + '</span>'
        + '<span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">' + stk.name + '</span>'
        + '</div>'
        + '<button class="remove-btn" data-rem-stk="' + stk.code + '" title="移除">✕</button>'
        + '</div>';
    });

    listEl.innerHTML = html;

    // 綁定點擊事件
    Array.prototype.forEach.call(listEl.querySelectorAll('.watchlist-item'), function (item) {
      item.addEventListener('click', function (e) {
        if (e.target.classList.contains('remove-btn')) return;
        var type = item.getAttribute('data-type');
        if (type === 'sector') {
          var name = item.getAttribute('data-name');
          var targetSec = state.data.sectors.filter(function (s) { return s.name === name; })[0];
          if (targetSec) {
            openDrawer(targetSec);
            if (state.chart) state.chart.pulseBubble(name);
          }
        } else if (type === 'stock') {
          var code = item.getAttribute('data-code');
          focusStockSearch(code);
        }
      });
    });

    Array.prototype.forEach.call(listEl.querySelectorAll('[data-rem-sec]'), function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        toggleSectorFav(btn.getAttribute('data-rem-sec'));
      });
    });

    Array.prototype.forEach.call(listEl.querySelectorAll('[data-rem-stk]'), function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var code = btn.getAttribute('data-rem-stk');
        var stk = state.watchlist.stocks.filter(function (s) { return s.code === code; })[0];
        if (stk) toggleStockFav(stk.code, stk.name, stk.market);
      });
    });
  }

  function renderMarketStats() {
    if (!state.data) return;
    var d = state.data;
    $('data-date').textContent = '資料日期 ' + d.date;
    $('stat-trading-days').textContent = d.trading_days + ' 日';

    var totalFlow = 0;
    var counts = { surge: 0, rotation: 0, watch: 0, ebb: 0 };

    d.sectors.forEach(function (s) {
      totalFlow += s.net_1d_yi;
      if (counts[s.quadrant] !== undefined) counts[s.quadrant]++;
    });

    var flowEl = $('stat-total-flow');
    flowEl.textContent = signed(totalFlow, 2) + ' 億';
    flowEl.className = 'stat-value ' + (totalFlow >= 0 ? 'pos' : 'neg');

    // 象限計數
    $('count-all').textContent = d.sectors.length;
    $('count-surge').textContent = counts.surge;
    $('count-rotation').textContent = counts.rotation;
    $('count-watch').textContent = counts.watch;
    $('count-ebb').textContent = counts.ebb;

    // 象限進度條佔比
    var total = d.sectors.length || 1;
    $('quadrant-bar').innerHTML = '<div class="quadrant-bar-segment surge" style="width:' + (counts.surge / total * 100) + '%" title="漲潮 ' + counts.surge + '"></div>'
      + '<div class="quadrant-bar-segment rotation" style="width:' + (counts.rotation / total * 100) + '%" title="輪動 ' + counts.rotation + '"></div>'
      + '<div class="quadrant-bar-segment watch" style="width:' + (counts.watch / total * 100) + '%" title="觀察 ' + counts.watch + '"></div>'
      + '<div class="quadrant-bar-segment ebb" style="width:' + (counts.ebb / total * 100) + '%" title="退潮 ' + counts.ebb + '"></div>';

    $('stat-quad-ratio').textContent = Math.round((counts.surge + counts.rotation) / total * 100) + '% 偏多';
  }

  function renderRanking() {
    if (!state.data) return;

    var radarNavTabs = $('radar-nav-tabs');
    var rankSortTabs = $('rank-sort-tabs');
    var rankTitle = $('rank-title');
    var tab = state.currentRankTab || 'sectors';

    if (tab === 'sectors') {
      if (rankSortTabs) rankSortTabs.style.display = 'flex';
      if (rankTitle) rankTitle.textContent = '板塊資金流排行榜';

      var key = state.rankSort;
      var rows = state.data.sectors.slice();

      if (state.activeQuadrant) {
        rows = rows.filter(function (s) { return s.quadrant === state.activeQuadrant; });
      }

      rows.sort(function (a, b) { return b[key] - a[key]; });

      var html = '<table class="rank-table"><thead><tr>'
        + '<th style="width:48px;">#</th>'
        + '<th>板塊名稱</th>'
        + '<th class="num">檔數</th>'
        + '<th class="num">當日淨買 (億)</th>'
        + '<th class="num">近 5 日淨買 (億)</th>'
        + '<th class="num">外資 5 日</th>'
        + '<th class="num">投信 5 日</th>'
        + '<th class="num">自營 5 日</th>'
        + '<th class="num">買超加速度</th>'
        + '<th>狀態</th>'
        + '</tr></thead><tbody>';

      rows.forEach(function (s, i) {
        var medalHtml = (i === 0) ? '<span class="medal-badge medal-1">1</span>'
          : (i === 1) ? '<span class="medal-badge medal-2">2</span>'
          : (i === 2) ? '<span class="medal-badge medal-3">3</span>'
          : '<span style="color:var(--s8);">' + (i + 1) + '</span>';

        html += '<tr data-name="' + s.name + '">'
          + '<td>' + medalHtml + '</td>'
          + '<td style="font-weight:700;">' + s.name + '</td>'
          + '<td class="num" style="color:var(--s9);">' + s.size + '</td>'
          + '<td class="num ' + (s.net_1d_yi >= 0 ? 'pos' : 'neg') + '">' + signed(s.net_1d_yi) + '</td>'
          + '<td class="num ' + (s.net_5d_yi >= 0 ? 'pos' : 'neg') + '">' + signed(s.net_5d_yi) + '</td>'
          + '<td class="num ' + (s.foreign_5d_yi >= 0 ? 'pos' : 'neg') + '" style="font-size:12px;">' + signed(s.foreign_5d_yi, 1) + '</td>'
          + '<td class="num ' + (s.trust_5d_yi >= 0 ? 'pos' : 'neg') + '" style="font-size:12px;">' + signed(s.trust_5d_yi, 1) + '</td>'
          + '<td class="num ' + (s.dealer_5d_yi >= 0 ? 'pos' : 'neg') + '" style="font-size:12px;">' + signed(s.dealer_5d_yi, 1) + '</td>'
          + '<td class="num ' + (s.accel >= 0 ? 'pos' : 'neg') + '">' + signed(s.accel) + '</td>'
          + '<td><span class="q-filter-btn active" data-q="' + s.quadrant + '" style="padding:1px 8px; font-size:11px;">'
          + window.TideChart.QUADRANT_LABEL[s.quadrant] + '</span></td>'
          + '</tr>';
      });

      html += '</tbody></table>';
      $('ranking-mount').innerHTML = html;

      Array.prototype.forEach.call($('ranking-mount').querySelectorAll('tr[data-name]'), function (tr) {
        tr.addEventListener('click', function () {
          var name = tr.getAttribute('data-name');
          var found = state.data.sectors.filter(function (s) { return s.name === name; })[0];
          if (found) openDrawer(found);
        });
      });
      return;
    }

    // 籌碼雷達榜單
    if (rankSortTabs) rankSortTabs.style.display = 'none';

    var radar = state.data.radar || {};
    var radarData = radar[tab] || [];

    var tabTitles = {
      co_buy: '🎯 土洋同買榜（外資＋投信同步大額加碼）',
      co_sell: '❄️ 土洋同賣榜（外資＋投信同步撤退提款）',
      divergence: '⚡ 土洋對作榜（外資與投信多空分歧激烈）',
      foreign_streak_top: '🔥 外資連買榜（外資連續買超天數排行）',
      trust_streak_top: '💎 投信連買榜（投信認養連續買超排行）'
    };

    if (rankTitle) rankTitle.textContent = tabTitles[tab] || '籌碼雷達排行榜';

    if (!radarData.length) {
      $('ranking-mount').innerHTML = '<div style="padding:40px; text-align:center; color:var(--s8);">今日無符合條件之標的</div>';
      return;
    }

    var rHtml = '<table class="rank-table"><thead><tr>'
      + '<th style="width:48px;">#</th>'
      + '<th>代號 / 名稱</th>'
      + '<th class="num">收盤價</th>'
      + '<th class="num">漲跌</th>'
      + '<th class="num">三大法人合計 (億)</th>'
      + '<th class="num" style="color:#64B5F6;">外資買賣 (億)</th>'
      + '<th class="num" style="color:#BA68C8;">投信買賣 (億)</th>'
      + '<th>法人20日成本 (乖離%)</th>'
      + '<th>主力連買狀態</th>'
      + '</tr></thead><tbody>';

    radarData.forEach(function (st, i) {
      var medalHtml = (i === 0) ? '<span class="medal-badge medal-1">1</span>'
        : (i === 1) ? '<span class="medal-badge medal-2">2</span>'
        : (i === 2) ? '<span class="medal-badge medal-3">3</span>'
        : '<span style="color:var(--s8);">' + (i + 1) + '</span>';

      var costBadge = st.cost_20d ? (
        '<span class="badge-cost ' + (st.diff_pct >= 0 ? 'profit' : 'loss') + '">'
        + st.cost_20d.toFixed(1) + ' (' + signed(st.diff_pct, 1) + '%)</span>'
      ) : '<span style="color:var(--s7); font-size:11px;">--</span>';

      var streakBadges = '';
      if (st.foreign_streak >= 3) {
        streakBadges += '<span class="badge-streak buy">🔥 外資 ' + st.foreign_streak + ' 連買</span> ';
      } else if (st.foreign_streak <= -3) {
        streakBadges += '<span class="badge-streak sell">❄️ 外資 ' + Math.abs(st.foreign_streak) + ' 連賣</span> ';
      }

      if (st.trust_streak >= 3) {
        streakBadges += '<span class="badge-streak buy" style="background:rgba(186,104,200,0.18); color:#CE93D8; border-color:rgba(186,104,200,0.35);">💎 投信 ' + st.trust_streak + ' 連買</span>';
      }

      if (!streakBadges) streakBadges = '<span style="color:var(--s7); font-size:11px;">--</span>';

      rHtml += '<tr data-code="' + st.code + '">'
        + '<td>' + medalHtml + '</td>'
        + '<td><span class="mono" style="font-weight:700; color:var(--c-gold); margin-right:6px;">' + st.code + '</span><span style="font-weight:600;">' + st.name + '</span></td>'
        + '<td class="num" style="font-weight:700;">' + st.close.toFixed(2) + '</td>'
        + '<td class="num ' + (st.chg >= 0 ? 'pos' : 'neg') + '">' + signed(st.chg) + '</td>'
        + '<td class="num ' + (st.net_1d_yi >= 0 ? 'pos' : 'neg') + '" style="font-weight:700;">' + signed(st.net_1d_yi, 2) + '</td>'
        + '<td class="num ' + (st.foreign_1d_yi >= 0 ? 'pos' : 'neg') + '">' + signed(st.foreign_1d_yi, 2) + '</td>'
        + '<td class="num ' + (st.trust_1d_yi >= 0 ? 'pos' : 'neg') + '">' + signed(st.trust_1d_yi, 2) + '</td>'
        + '<td>' + costBadge + '</td>'
        + '<td>' + streakBadges + '</td>'
        + '</tr>';
    });

    rHtml += '</tbody></table>';
    $('ranking-mount').innerHTML = rHtml;

    Array.prototype.forEach.call($('ranking-mount').querySelectorAll('tr[data-code]'), function (tr) {
      tr.addEventListener('click', function () {
        focusStockSearch(tr.getAttribute('data-code'));
      });
    });
  }

  function openDrawer(sector) {
    state.selectedSector = sector;
    $('drawer-sector-name').textContent = sector.name;
    var quadBadge = $('drawer-quadrant-badge');
    quadBadge.textContent = window.TideChart.QUADRANT_LABEL[sector.quadrant];
    quadBadge.style.color = 'var(--q-' + sector.quadrant + ')';
    quadBadge.style.background = 'var(--q-' + sector.quadrant + '-bg)';

    $('drawer-sector-summary').textContent = sector.size + ' 檔成分股・近 5 日買超 ' + signed(sector.net_5d_yi, 1) + ' 億';

    var dm5d = $('dm-5d');
    dm5d.textContent = signed(sector.net_5d_yi, 2) + ' 億';
    dm5d.className = 'val ' + (sector.net_5d_yi >= 0 ? 'pos' : 'neg');

    var dmAcc = $('dm-accel');
    dmAcc.textContent = signed(sector.accel, 2);
    dmAcc.className = 'val ' + (sector.accel >= 0 ? 'pos' : 'neg');

    var dm20d = $('dm-20d');
    dm20d.textContent = signed(sector.net_20d_yi, 2) + ' 億';
    dm20d.className = 'val ' + (sector.net_20d_yi >= 0 ? 'pos' : 'neg');

    // 法人三大分項
    var dmForeign = $('dm-foreign');
    if (dmForeign) {
      dmForeign.textContent = signed(sector.foreign_5d_yi, 2) + ' 億';
      dmForeign.className = 'val ' + (sector.foreign_5d_yi >= 0 ? 'pos' : 'neg');
    }

    var dmTrust = $('dm-trust');
    if (dmTrust) {
      dmTrust.textContent = signed(sector.trust_5d_yi, 2) + ' 億';
      dmTrust.className = 'val ' + (sector.trust_5d_yi >= 0 ? 'pos' : 'neg');
    }

    var dmDealer = $('dm-dealer');
    if (dmDealer) {
      dmDealer.textContent = signed(sector.dealer_5d_yi, 2) + ' 億';
      dmDealer.className = 'val ' + (sector.dealer_5d_yi >= 0 ? 'pos' : 'neg');
    }

    updateDrawerFavBtn();
    renderDrawerStocks(sector);

    $('detail-drawer').classList.add('open');
    $('drawer-backdrop').classList.add('open');
  }

  function closeDrawer() {
    $('detail-drawer').classList.remove('open');
    $('drawer-backdrop').classList.remove('open');
    state.selectedSector = null;
  }

  function updateDrawerFavBtn() {
    if (!state.selectedSector) return;
    var fav = isSectorFav(state.selectedSector.name);
    var btn = $('drawer-fav-btn');
    btn.className = 'fav-star-btn ' + (fav ? 'active' : '');
    btn.textContent = fav ? '★' : '☆';
  }

  function renderDrawerStocks(sector, filterKey) {
    var stocks = sector.stocks || [];
    if (filterKey) {
      var q = filterKey.trim().toLowerCase();
      stocks = stocks.filter(function (s) {
        return s.code.toLowerCase().indexOf(q) !== -1 || s.name.toLowerCase().indexOf(q) !== -1;
      });
    }

    var html = '<table class="stocks-table"><thead><tr>'
      + '<th style="width:28px;">⭐</th>'
      + '<th>代號 / 名稱</th>'
      + '<th class="num">收盤價</th>'
      + '<th class="num">法人買超 (億)</th>'
      + '<th>20日成本 (乖離%)</th>'
      + '</tr></thead><tbody>';

    stocks.forEach(function (st) {
      var fav = isStockFav(st.code);

      var costBadge = st.cost_20d ? (
        '<span class="badge-cost ' + (st.diff_pct >= 0 ? 'profit' : 'loss') + '" title="20日法人買進加權均價 ' + st.cost_20d + '">'
        + st.cost_20d.toFixed(1) + ' (' + signed(st.diff_pct, 1) + '%)</span>'
      ) : '<span style="color:var(--s7); font-size:11px;">--</span>';

      var streakBadges = '';
      if (st.foreign_streak >= 3) {
        streakBadges += '<span class="badge-streak buy">🔥 外資 ' + st.foreign_streak + ' 連買</span> ';
      } else if (st.foreign_streak <= -3) {
        streakBadges += '<span class="badge-streak sell">❄️ 外資 ' + Math.abs(st.foreign_streak) + ' 連賣</span> ';
      }

      if (st.trust_streak >= 3) {
        streakBadges += '<span class="badge-streak buy" style="background:rgba(186,104,200,0.18); color:#CE93D8; border-color:rgba(186,104,200,0.35);">💎 投信 ' + st.trust_streak + ' 連買</span>';
      }

      var instiChips = '<div class="insti-chips">'
        + '<span class="chip-insti foreign">外 ' + signed(st.foreign_1d_yi, 2) + '</span>'
        + '<span class="chip-insti trust">投 ' + signed(st.trust_1d_yi, 2) + '</span>'
        + '<span class="chip-insti dealer">自 ' + signed(st.dealer_1d_yi, 2) + '</span>'
        + '</div>';

      html += '<tr>'
        + '<td><button class="fav-star-btn ' + (fav ? 'active' : '') + '" data-stk-code="' + st.code + '" data-stk-name="' + st.name + '" data-stk-mkt="' + st.market + '">' + (fav ? '★' : '☆') + '</button></td>'
        + '<td>'
        + '  <div style="display:flex; align-items:center; gap:6px;">'
        + '    <span class="mono" style="font-weight:700; color:var(--c-gold);">' + st.code + '</span>'
        + '    <span style="font-weight:600;">' + st.name + '</span>'
        + (streakBadges ? '<span style="margin-left:4px;">' + streakBadges + '</span>' : '')
        + '  </div>'
        + instiChips
        + '</td>'
        + '<td class="num">'
        + '  <div style="font-weight:700;">' + st.close.toFixed(2) + '</div>'
        + '  <div class="' + (st.chg >= 0 ? 'pos' : 'neg') + '" style="font-size:11px;">' + signed(st.chg) + '</div>'
        + '</td>'
        + '<td class="num">'
        + '  <div style="font-weight:700;" class="' + (st.net_1d_yi >= 0 ? 'pos' : 'neg') + '">' + signed(st.net_1d_yi, 2) + ' 億</div>'
        + '  <div style="font-size:11px; color:var(--s9);">5日 ' + signed(st.net_5d_yi, 1) + ' 億</div>'
        + '</td>'
        + '<td>' + costBadge + '</td>'
        + '</tr>';
    });

    html += '</tbody></table>';
    $('drawer-stocks-mount').innerHTML = html;

    Array.prototype.forEach.call($('drawer-stocks-mount').querySelectorAll('.fav-star-btn'), function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        toggleStockFav(btn.getAttribute('data-stk-code'), btn.getAttribute('data-stk-name'), btn.getAttribute('data-stk-mkt'));
      });
    });
  }

  function hideOverlapMenu() {
    var menu = $('overlap-menu');
    if (menu) {
      menu.style.display = 'none';
      menu.innerHTML = '';
    }
    if (state.chart) {
      state.chart.clearHighlight();
    }
  }

  function showOverlapMenu(sectors, pos) {
    var menu = $('overlap-menu');
    var chartView = $('chart-view');
    if (!menu || !chartView || !sectors || !sectors.length) {
      hideOverlapMenu();
      return;
    }

    // 關閉 tooltip
    showTooltip(null);

    var html = '<div class="overlap-menu-header">重疊板塊 · ' + sectors.length + ' 個</div>'
      + '<div class="overlap-menu-list">';

    sectors.forEach(function (s) {
      var netYi = Number(s.net_5d_yi);
      var netStr = (netYi >= 0 ? '+' : '') + netYi.toFixed(1) + '億';
      var colorClass = netYi >= 0 ? 'pos' : 'neg';
      html += '<div class="overlap-menu-item" data-name="' + s.name + '">'
        + '<span class="overlap-dot" style="background:var(--q-' + s.quadrant + ');"></span>'
        + '<span class="overlap-name">' + s.name + '</span>'
        + '<span class="overlap-val ' + colorClass + '">' + netStr + '</span>'
        + '</div>';
    });

    html += '</div>';
    menu.innerHTML = html;
    menu.style.display = 'flex';

    // 定位計算（相對於 chart-view）
    var chartRect = chartView.getBoundingClientRect();
    var x = pos.clientX - chartRect.left;
    var y = pos.clientY - chartRect.top;

    var menuW = 230;
    var menuH = menu.offsetHeight || (38 + sectors.length * 36);

    var targetLeft = x + 12;
    var targetTop = y - 20;

    if (targetLeft + menuW > chartRect.width - 12) {
      targetLeft = x - menuW - 12;
    }
    if (targetTop + menuH > chartRect.height - 12) {
      targetTop = chartRect.height - menuH - 12;
    }
    if (targetTop < 12) targetTop = 12;
    if (targetLeft < 12) targetLeft = 12;

    menu.style.left = targetLeft + 'px';
    menu.style.top = targetTop + 'px';

    // 綁定項目點擊與懸浮預覽
    Array.prototype.forEach.call(menu.querySelectorAll('.overlap-menu-item'), function (item) {
      var name = item.getAttribute('data-name');
      var sec = state.data.sectors.filter(function (s) { return s.name === name; })[0];
      if (!sec) return;

      item.addEventListener('click', function (e) {
        e.stopPropagation();
        hideOverlapMenu();
        openDrawer(sec);
      });

      item.addEventListener('mouseenter', function () {
        if (state.chart) {
          state.chart.highlightBubble(name);
        }
      });

      item.addEventListener('mouseleave', function () {
        if (state.chart) {
          state.chart.unhighlightBubble(name);
        }
      });
    });
  }

  function showTooltip(sector, event) {
    var tt = $('bubble-tooltip');
    if (!sector || !event) {
      tt.classList.remove('visible');
      return;
    }

    var topStocks = sector.stocks.slice(0, 3);
    var contribHtml = topStocks.map(function (s) {
      return s.name + ' (' + signed(s.net_1d_yi, 2) + '億)';
    }).join('、');

    tt.innerHTML = '<div class="tt-head">'
      + '<span class="tt-title">' + sector.name + '</span>'
      + '<span class="tt-pill" style="color:var(--q-' + sector.quadrant + '); background:var(--q-' + sector.quadrant + '-bg);">'
      + window.TideChart.QUADRANT_LABEL[sector.quadrant] + '</span>'
      + '</div>'
      + '<div class="tt-metrics">'
      + '<div>近 5 日買超: <b class="' + (sector.net_5d_yi >= 0 ? 'pos' : 'neg') + '">' + signed(sector.net_5d_yi, 1) + ' 億</b></div>'
      + '<div>買超加速度: <b class="' + (sector.accel >= 0 ? 'pos' : 'neg') + '">' + signed(sector.accel, 2) + '</b></div>'
      + '<div>近 20 日買超: <b class="' + (sector.net_20d_yi >= 0 ? 'pos' : 'neg') + '">' + signed(sector.net_20d_yi, 1) + ' 億</b></div>'
      + '<div>成分股檔數: <b>' + sector.size + ' 檔</b></div>'
      + '</div>'
      + (contribHtml ? '<div class="tt-contributors">主力貢獻: ' + contribHtml + '</div>' : '');

    var mountRect = $('chart-view').getBoundingClientRect();
    var x = event.clientX - mountRect.left;
    var y = event.clientY - mountRect.top;

    tt.style.left = x + 'px';
    tt.style.top = y + 'px';
    tt.classList.add('visible');
  }

  function setupSearch() {
    var input = $('search-input');
    var wrapper = $('search-wrapper');
    var dropdown = $('search-dropdown');
    var clearBtn = $('search-clear');

    input.addEventListener('input', function () {
      var val = input.value.trim();
      wrapper.classList.toggle('has-text', !!val);
      if (!val) {
        dropdown.classList.remove('open');
        if (state.chart) state.chart.applyFilter(state.activeQuadrant, null);
        return;
      }

      var q = val.toLowerCase();
      var matchedSectors = [];
      var matchedStocks = [];

      state.data.sectors.forEach(function (sec) {
        if (sec.name.toLowerCase().indexOf(q) !== -1) {
          matchedSectors.push(sec);
        }
        sec.stocks.forEach(function (stk) {
          if (stk.code.toLowerCase().indexOf(q) !== -1 || stk.name.toLowerCase().indexOf(q) !== -1) {
            if (!matchedStocks.some(function (x) { return x.stock.code === stk.code && x.sector.name === sec.name; })) {
              matchedStocks.push({ stock: stk, sector: sec });
            }
          }
        });
      });

      if (!matchedSectors.length && !matchedStocks.length) {
        dropdown.innerHTML = '<div style="padding:12px; font-size:12px; color:var(--s8); text-align:center;">無符合「' + val + '」的板塊或成分股</div>';
        dropdown.classList.add('open');
        return;
      }

      var html = '';
      if (matchedSectors.length) {
        html += '<div class="search-result-group"><div class="search-group-title">主題板塊</div>';
        matchedSectors.slice(0, 5).forEach(function (sec) {
          html += '<div class="search-item" data-action="sector" data-name="' + sec.name + '">'
            + '<div class="search-item-left">'
            + '<span>📁</span> <b>' + sec.name + '</b>'
            + '</div>'
            + '<span class="search-item-tag" style="color:var(--q-' + sec.quadrant + ')">' + window.TideChart.QUADRANT_LABEL[sec.quadrant] + '</span>'
            + '</div>';
        });
        html += '</div>';
      }

      if (matchedStocks.length) {
        html += '<div class="search-result-group"><div class="search-group-title">成分股與所屬板塊</div>';
        matchedStocks.slice(0, 10).forEach(function (m) {
          html += '<div class="search-item" data-action="stock" data-sector="' + m.sector.name + '" data-code="' + m.stock.code + '">'
            + '<div class="search-item-left">'
            + '<span class="search-item-code">' + m.stock.code + '</span>'
            + '<span>' + m.stock.name + '</span>'
            + '</div>'
            + '<span class="search-item-tag">' + m.sector.name + '</span>'
            + '</div>';
        });
        html += '</div>';
      }

      dropdown.innerHTML = html;
      dropdown.classList.add('open');

      // 即時淡化無關泡泡
      var matchedNames = Array.from(new Set(
        matchedSectors.map(function (s) { return s.name; }).concat(
          matchedStocks.map(function (m) { return m.sector.name; })
        )
      ));
      if (state.chart) state.chart.applyFilter(state.activeQuadrant, matchedNames);
    });

    dropdown.addEventListener('click', function (e) {
      var item = e.target.closest('.search-item');
      if (!item) return;
      var action = item.getAttribute('data-action');
      if (action === 'sector') {
        var secName = item.getAttribute('data-name');
        var sec = state.data.sectors.filter(function (s) { return s.name === secName; })[0];
        if (sec) {
          if (state.chart) state.chart.pulseBubble(secName);
          openDrawer(sec);
        }
      } else if (action === 'stock') {
        var sectorName = item.getAttribute('data-sector');
        var targetSector = state.data.sectors.filter(function (s) { return s.name === sectorName; })[0];
        if (targetSector) {
          if (state.chart) state.chart.pulseBubble(sectorName);
          openDrawer(targetSector);
        }
      }
      dropdown.classList.remove('open');
    });

    clearBtn.addEventListener('click', function () {
      input.value = '';
      wrapper.classList.remove('has-text');
      dropdown.classList.remove('open');
      if (state.chart) state.chart.applyFilter(state.activeQuadrant, null);
    });

    document.addEventListener('click', function (e) {
      if (!wrapper.contains(e.target)) {
        dropdown.classList.remove('open');
      }
    });
  }

  function focusStockSearch(code) {
    var input = $('search-input');
    input.value = code;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.focus();
  }

  function bindEvents() {
    // 象限過濾 Pill 按鈕
    Array.prototype.forEach.call(document.querySelectorAll('.q-filter-btn'), function (btn) {
      btn.addEventListener('click', function () {
        Array.prototype.forEach.call(document.querySelectorAll('.q-filter-btn'), function (b) {
          b.classList.remove('active');
        });
        btn.classList.add('active');
        state.activeQuadrant = btn.getAttribute('data-q') || '';
        if (state.chart) state.chart.applyFilter(state.activeQuadrant, null);
        if (state.currentView === 'ranking') renderRanking();
      });
    });

    // 只看熱門 15 切換
    var compactBtn = $('compact-toggle');
    if (compactBtn) {
      compactBtn.addEventListener('click', function () {
        state.isCompact = !state.isCompact;
        try {
          localStorage.setItem('bubble_compact', state.isCompact ? '1' : '0');
        } catch (e) {}
        syncCompactBtn();
        if (state.chart) {
          state.chart.render(getRenderSectors());
          if (state.activeQuadrant) state.chart.applyFilter(state.activeQuadrant, null);
        }
      });
    }

    // 視圖切換
    $('btn-view-chart').addEventListener('click', function () {
      state.currentView = 'chart';
      $('btn-view-chart').classList.add('active');
      $('btn-view-rank').classList.remove('active');
      $('chart-view').style.display = 'block';
      $('ranking-view').classList.remove('active');
      if (state.chart && state.data) {
        state.chart.render(getRenderSectors());
        if (state.activeQuadrant) state.chart.applyFilter(state.activeQuadrant, null);
      }
    });

    $('btn-view-rank').addEventListener('click', function () {
      state.currentView = 'ranking';
      $('btn-view-rank').classList.add('active');
      $('btn-view-chart').classList.remove('active');
      $('chart-view').style.display = 'none';
      $('ranking-view').classList.add('active');
      renderRanking();
    });

    // 籌碼雷達榜單切換
    var radarNavTabs = $('radar-nav-tabs');
    if (radarNavTabs) {
      Array.prototype.forEach.call(radarNavTabs.querySelectorAll('.radar-nav-btn'), function (btn) {
        btn.addEventListener('click', function () {
          Array.prototype.forEach.call(radarNavTabs.querySelectorAll('.radar-nav-btn'), function (b) {
            b.classList.remove('active');
          });
          btn.classList.add('active');
          state.currentRankTab = btn.getAttribute('data-tab');
          renderRanking();
        });
      });
    }

    // 排行榜排序切換
    Array.prototype.forEach.call($('rank-sort-tabs').querySelectorAll('.view-btn'), function (btn) {
      btn.addEventListener('click', function () {
        Array.prototype.forEach.call($('rank-sort-tabs').querySelectorAll('.view-btn'), function (b) {
          b.classList.remove('active');
        });
        btn.classList.add('active');
        state.rankSort = btn.getAttribute('data-sort');
        renderRanking();
      });
    });

    // 縮放控制鈕
    $('btn-zoom-in').addEventListener('click', function () {
      if (state.chart) state.chart.zoomBy(1.2);
    });
    $('btn-zoom-out').addEventListener('click', function () {
      if (state.chart) state.chart.zoomBy(0.8);
    });
    $('btn-zoom-reset').addEventListener('click', function () {
      if (state.chart) state.chart.resetZoom();
    });

    // 抽屜關閉
    $('drawer-close-btn').addEventListener('click', closeDrawer);
    $('drawer-backdrop').addEventListener('click', closeDrawer);

    $('drawer-fav-btn').addEventListener('click', function () {
      if (state.selectedSector) toggleSectorFav(state.selectedSector.name);
    });

    $('drawer-stock-search').addEventListener('input', function (e) {
      if (state.selectedSector) renderDrawerStocks(state.selectedSector, e.target.value);
    });

    // 主題切換
    $('theme-toggle').addEventListener('click', function () {
      var next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem('theme_mode', next); } catch (e) {}
    });

    // 點擊非選單區域關閉重疊選單
    document.addEventListener('click', function (e) {
      if (!e.target.closest('#overlap-menu')) {
        hideOverlapMenu();
      }
    });

    // 鍵盤快速鍵
    window.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        hideOverlapMenu();
        closeDrawer();
      }
      if (e.key === '/' && document.activeElement !== $('search-input')) {
        e.preventDefault();
        $('search-input').focus();
      }
    });

    // 視窗縮放
    var resizeTimer = null;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () {
        hideOverlapMenu();
        if (state.chart && state.data && state.currentView === 'chart') {
          state.chart.render(getRenderSectors());
          if (state.activeQuadrant) state.chart.applyFilter(state.activeQuadrant, null);
        }
      }, 150);
    });
  }

  function init() {
    loadWatchlist();
    bindEvents();
    setupSearch();

    var dataUrl = (window.location.pathname.indexOf('/web/') !== -1)
      ? '../data/latest.json'
      : './data/latest.json';

    fetch(dataUrl, { cache: 'no-cache' })
      .catch(function () {
        // 若在根目錄或特殊路徑下嘗試 fallback
        return fetch('data/latest.json', { cache: 'no-cache' });
      })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        state.data = data;
        syncCompactBtn();
        state.chart = window.TideChart.create(
          $('chart-mount'),
          openDrawer,
          showTooltip,
          function (sectors, pos) {
            if (!sectors || !sectors.length) {
              hideOverlapMenu();
            } else {
              showOverlapMenu(sectors, pos);
            }
          }
        );
        state.chart.render(getRenderSectors());
        renderMarketStats();
        renderWatchlist();
      })
      .catch(function (err) {
        $('chart-mount').innerHTML = '<div style="padding:40px; color:var(--pos); text-align:center;">讀取資料失敗：' + err.message + '</div>';
      });
  }

  init();
}());
