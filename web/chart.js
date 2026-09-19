(function (global) {
  'use strict';

  var QUADRANT_LABEL = {
    surge: '漲潮',
    rotation: '輪動',
    watch: '觀察',
    ebb: '退潮'
  };

  var NS = 'http://www.w3.org/2000/svg';
  var PAD = 64;

  function el(tag, attrs, text) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if (Object.prototype.hasOwnProperty.call(attrs, k)) {
        node.setAttribute(k, attrs[k]);
      }
    }
    if (text != null) { node.textContent = text; }
    return node;
  }

  function extent(values) {
    var lo = Math.min.apply(null, values);
    var hi = Math.max.apply(null, values);
    if (lo === hi) { lo -= 1; hi += 1; }
    var span = hi - lo;
    return [lo - span * 0.12, hi + span * 0.12];
  }

  function scaler(domain, lo, hi) {
    var d0 = domain[0];
    var d1 = domain[1];
    return function (v) { return lo + (v - d0) / (d1 - d0) * (hi - lo); };
  }

  function clip(name, radius, fontSize) {
    var maxEm = (radius * 1.8) / fontSize;
    var width = 0;
    var out = '';
    for (var i = 0; i < name.length; i++) {
      var ch = name.charAt(i);
      var w = ch === ' ' ? 0.28 : ch.charCodeAt(0) < 0x2E80 ? 0.55 : 1;
      if (width + w > maxEm) { return out ? out + '…' : name.charAt(0) + '…'; }
      width += w;
      out += ch;
    }
    return out;
  }

  function ChartInstance(container, onSelect, onHover, onOverlap) {
    this.container = container;
    this.onSelect = onSelect;
    this.onHover = onHover;
    this.onOverlap = onOverlap;
    this.sectors = [];
    this.svg = null;
    this.zoomLayer = null;
    this.scale = 1.0;
    this.tx = 0;
    this.ty = 0;
    this.isDragging = false;
    this.hasMoved = false;
    this.startX = 0;
    this.startY = 0;
    this.downX = 0;
    this.downY = 0;
    this.bubbleMap = {};
  }

  ChartInstance.prototype.render = function (sectors) {
    this.sectors = sectors || [];
    this.container.innerHTML = '';
    this.bubbleMap = {};

    if (!this.sectors.length) return;

    var W = this.container.clientWidth || 960;
    var H = this.container.clientHeight || 640;
    this.width = W;
    this.height = H;

    var gx = scaler(extent(this.sectors.map(function (s) { return s.net_5d_yi; })), PAD, W - PAD);
    var gy = scaler(extent(this.sectors.map(function (s) { return s.accel; })), H - PAD, PAD);

    this.gx = gx;
    this.gy = gy;

    var svg = el('svg', {
      viewBox: '0 0 ' + W + ' ' + H,
      'class': 'chart-svg',
      role: 'img',
      'aria-label': '台股板塊資金流四象限泡泡圖'
    });
    this.svg = svg;

    var zoomLayer = el('g', { 'class': 'zoom-layer' });
    this.zoomLayer = zoomLayer;
    svg.appendChild(zoomLayer);

    // 座標軸線與十字原點
    var x0 = gx(0);
    var y0 = gy(0);

    // 背景象限標籤
    [
      ['surge', W - PAD - 8, PAD + 24, 'end'],
      ['rotation', W - PAD - 8, H - PAD - 14, 'end'],
      ['watch', PAD + 8, PAD + 24, 'start'],
      ['ebb', PAD + 8, H - PAD - 14, 'start']
    ].forEach(function (c) {
      zoomLayer.appendChild(el('text', {
        x: c[1], y: c[2], 'text-anchor': c[3],
        'class': 'quadrant-bg-label ' + c[0]
      }, QUADRANT_LABEL[c[0]]));
    });

    zoomLayer.appendChild(el('line', {
      x1: PAD, y1: y0, x2: W - PAD, y2: y0, 'class': 'axis-line'
    }));
    zoomLayer.appendChild(el('line', {
      x1: x0, y1: PAD, x2: x0, y2: H - PAD, 'class': 'axis-line'
    }));

    zoomLayer.appendChild(el('text', {
      x: W - PAD, y: y0 - 8, 'class': 'axis-text', 'text-anchor': 'end'
    }, '近 5 日法人買超（億元）→'));
    zoomLayer.appendChild(el('text', {
      x: x0 + 8, y: PAD - 8, 'class': 'axis-text'
    }, '↑ 買超加速度（億/日）'));

    // 渲染泡泡
    var self = this;
    this.sectors.forEach(function (s) {
      var cx = gx(s.net_5d_yi);
      var cy = gy(s.accel);
      var r = s.radius;
      var fs = Math.max(10, Math.min(15, r * 0.34));

      var g = el('g', {
        'class': 'bubble q-' + s.quadrant,
        tabindex: '0',
        role: 'button',
        'aria-label': s.name + ' ' + QUADRANT_LABEL[s.quadrant],
        'data-name': s.name,
        'data-quadrant': s.quadrant
      });
      g.appendChild(el('circle', { cx: cx, cy: cy, r: r }));
      g.appendChild(el('text', {
        x: cx, y: cy - 2, 'class': 'b-title', 'text-anchor': 'middle', 'font-size': fs
      }, clip(s.name, r, fs)));
      g.appendChild(el('text', {
        x: cx, y: cy + fs + 2, 'class': 'b-subtitle', 'text-anchor': 'middle', 'font-size': fs * 0.88
      }, (s.net_5d_yi >= 0 ? '+' : '') + s.net_5d_yi.toFixed(1)));

      g.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          if (self.onSelect) self.onSelect(s);
        }
      });

      g.addEventListener('mouseenter', function (e) {
        if (self.onHover) self.onHover(s, e);
      });
      g.addEventListener('mouseleave', function () {
        if (self.onHover) self.onHover(null);
      });

      zoomLayer.appendChild(g);
      self.bubbleMap[s.name] = { node: g, cx: cx, cy: cy, radius: r, data: s };
    });

    this.container.appendChild(svg);
    this.bindPanZoom();
    this.updateTransform();
  };

  ChartInstance.prototype.bindPanZoom = function () {
    var self = this;
    var svg = this.svg;

    svg.addEventListener('mousedown', function (e) {
      if (e.button !== 0) return;
      self.isDragging = true;
      self.hasMoved = false;
      self.downX = e.clientX;
      self.downY = e.clientY;
      self.startX = e.clientX - self.tx;
      self.startY = e.clientY - self.ty;
      svg.classList.add('dragging');
    });

    window.addEventListener('mousemove', function (e) {
      if (!self.isDragging) return;
      if (!self.hasMoved && Math.hypot(e.clientX - self.downX, e.clientY - self.downY) > 5) {
        self.hasMoved = true;
        if (self.onOverlap) self.onOverlap([], null);
      }
      if (self.hasMoved) {
        self.tx = e.clientX - self.startX;
        self.ty = e.clientY - self.startY;
        self.updateTransform();
      }
    });

    window.addEventListener('mouseup', function () {
      if (!self.isDragging) return;
      self.isDragging = false;
      svg.classList.remove('dragging');
    });

    // 使用 click 事件並阻止向上冒泡，確保不會被 document 的全域點擊事件意外關閉
    svg.addEventListener('click', function (e) {
      e.stopPropagation();

      // 若剛剛是拖曳平移畫布，則不觸發點擊選取
      if (self.hasMoved) return;

      var rect = svg.getBoundingClientRect();
      var scaleX = (self.width || 960) / rect.width;
      var scaleY = (self.height || 640) / rect.height;
      var clickSvgX = ((e.clientX - rect.left) * scaleX - self.tx) / self.scale;
      var clickSvgY = ((e.clientY - rect.top) * scaleY - self.ty) / self.scale;

      // 1. 找出滑鼠落點直接涵蓋的氣泡
      var directHits = [];
      Object.values(self.bubbleMap).forEach(function (b) {
        if (b.node.classList.contains('dimmed')) return;
        var dist = Math.hypot(clickSvgX - b.cx, clickSvgY - b.cy);
        if (dist <= b.radius * 1.15 + 8) {
          directHits.push({ item: b, dist: dist });
        }
      });

      directHits.sort(function (a, b) { return a.dist - b.dist; });

      var finalHits = [];
      var seenNames = {};

      if (directHits.length > 0) {
        var primary = directHits[0].item;
        // 將所有 directHits 以及與 primary 氣泡相交重疊的氣泡全部納入
        Object.values(self.bubbleMap).forEach(function (b) {
          if (b.node.classList.contains('dimmed')) return;
          var distToClick = Math.hypot(clickSvgX - b.cx, clickSvgY - b.cy);
          var distToPrimary = Math.hypot(primary.cx - b.cx, primary.cy - b.cy);
          // 若在點擊範圍內，或兩氣泡相交重疊
          if (distToClick <= b.radius * 1.15 + 8 || distToPrimary <= (primary.radius + b.radius) * 0.95) {
            if (!seenNames[b.data.name]) {
              seenNames[b.data.name] = true;
              finalHits.push(b.data);
            }
          }
        });
      }

      if (finalHits.length > 1) {
        // 多個氣泡重疊：觸發重疊選單
        if (self.onOverlap) {
          self.onOverlap(finalHits, {
            clientX: e.clientX,
            clientY: e.clientY
          });
        }
      } else if (finalHits.length === 1) {
        // 單一氣泡命中：直接開啟抽屜並關閉重疊選單
        if (self.onOverlap) self.onOverlap([], null);
        if (self.onSelect) self.onSelect(finalHits[0]);
      } else {
        // 點擊空白處：關閉重疊選單
        if (self.onOverlap) self.onOverlap([], null);
      }
    });

    svg.addEventListener('wheel', function (e) {
      e.preventDefault();
      if (self.onOverlap) self.onOverlap([], null);
      var rect = svg.getBoundingClientRect();
      var mx = e.clientX - rect.left;
      var my = e.clientY - rect.top;

      var factor = e.deltaY < 0 ? 1.15 : 0.87;
      var newScale = Math.max(0.6, Math.min(3.5, self.scale * factor));

      // 以滑鼠游標為錨點縮放
      self.tx = mx - (mx - self.tx) * (newScale / self.scale);
      self.ty = my - (my - self.ty) * (newScale / self.scale);
      self.scale = newScale;
      self.updateTransform();
    }, { passive: false });
  };

  ChartInstance.prototype.updateTransform = function () {
    if (this.zoomLayer) {
      this.zoomLayer.setAttribute(
        'transform',
        'translate(' + this.tx + ', ' + this.ty + ') scale(' + this.scale + ')'
      );
    }
  };

  ChartInstance.prototype.resetZoom = function () {
    if (this.onOverlap) this.onOverlap([], null);
    this.scale = 1.0;
    this.tx = 0;
    this.ty = 0;
    this.updateTransform();
  };

  ChartInstance.prototype.zoomBy = function (delta) {
    if (this.onOverlap) this.onOverlap([], null);
    var newScale = Math.max(0.6, Math.min(3.5, this.scale * delta));
    var cx = (this.width || 960) / 2;
    var cy = (this.height || 640) / 2;
    this.tx = cx - (cx - this.tx) * (newScale / this.scale);
    this.ty = cy - (cy - this.ty) * (newScale / this.scale);
    this.scale = newScale;
    this.updateTransform();
  };

  ChartInstance.prototype.highlightBubble = function (sectorName) {
    var b = this.bubbleMap[sectorName];
    if (!b) return;

    // 將該泡泡元素移至 SVG 圖層最上方（保證懸浮時視覺置頂）
    if (b.node.parentNode) {
      b.node.parentNode.appendChild(b.node);
    }
    b.node.classList.add('highlighted');
  };

  ChartInstance.prototype.unhighlightBubble = function (sectorName) {
    var b = this.bubbleMap[sectorName];
    if (!b) return;
    b.node.classList.remove('highlighted');
  };

  ChartInstance.prototype.clearHighlight = function () {
    Object.values(this.bubbleMap).forEach(function (item) {
      item.node.classList.remove('highlighted');
    });
  };

  ChartInstance.prototype.pulseBubble = function (sectorName) {
    var b = this.bubbleMap[sectorName];
    if (!b) return;

    // 清除既有 pulse
    Object.values(this.bubbleMap).forEach(function (item) {
      item.node.classList.remove('pulse');
    });

    // 聚焦移動至中心
    var targetX = (this.width / 2) - b.cx * this.scale;
    var targetY = (this.height / 2) - b.cy * this.scale;
    this.tx = targetX;
    this.ty = targetY;
    this.updateTransform();

    b.node.classList.add('pulse');
  };

  ChartInstance.prototype.applyFilter = function (activeQuadrant, matchedSectorNames) {
    var hasQuad = !!activeQuadrant;
    var hasMatch = Array.isArray(matchedSectorNames);

    Object.values(this.bubbleMap).forEach(function (item) {
      var s = item.data;
      var matchQuad = !hasQuad || s.quadrant === activeQuadrant;
      var matchSearch = !hasMatch || matchedSectorNames.indexOf(s.name) !== -1;

      if (matchQuad && matchSearch) {
        item.node.classList.remove('dimmed');
      } else {
        item.node.classList.add('dimmed');
      }
    });
  };

  global.TideChart = {
    create: function (container, onSelect, onHover, onOverlap) {
      return new ChartInstance(container, onSelect, onHover, onOverlap);
    },
    QUADRANT_LABEL: QUADRANT_LABEL
  };
}(window));
