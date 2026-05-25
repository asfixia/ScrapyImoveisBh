<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>aImóveis BH — Mappia (CSR) + filtros no painel</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiMzYjgyZjYiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cGF0aCBkPSJNMTAgMjBWMTBNNCAyMFY0YTIgMiAwIDAgMSAyLTJoOGEyIDIgMCAwIDEgMiAydjE2bTQtNFY4YTIgMiAwIDAgMC0yLTJoLTIiPjwvcGF0aD48L3N2Zz4=" />
  <style>
    :root {
      --bg: #0f1419;
      --panel: #1a2332;
      --border: #2d3a4d;
      --text: #e7ecf3;
      --muted: #8b9cb3;
      --accent: #3d8bfd;
      --accent-dim: #2a5fad;
      --track: #2d3a4d;
      --fill: rgba(61, 139, 253, 0.45);
      --thumb: #3d8bfd;
      --thumb-max: #7eb6ff;
    }
    * { box-sizing: border-box; }
    html {
      height: 100%;
      -webkit-text-size-adjust: 100%;
    }
    body {
      margin: 0;
      font-family: system-ui, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      min-height: 100dvh;
      min-height: -webkit-fill-available;
      display: flex;
      flex-direction: column;
    }
    header {
      padding: 0.35rem 0.65rem;
      border-bottom: 1px solid var(--border);
      background: var(--panel);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
      flex-wrap: wrap;
    }
    header h1 {
      margin: 0;
      font-size: 0.88rem;
      font-weight: 600;
    }
    header a { color: var(--accent); }
    .header-bar__start {
      display: flex;
      align-items: center;
      gap: 0.65rem;
      flex-wrap: wrap;
      min-width: 0;
    }
    /**
     * Toggle painel de filtros — componente em “chip” (ícone + título + subtítulo + chevron).
     * Estado espelhado em .filter-toolbar-toggle--collapsed
     */
    .filter-toolbar-toggle {
      flex-shrink: 0;
      display: inline-flex;
      align-items: center;
      gap: 0.55rem;
      margin: 0;
      padding: 0.4rem 0.75rem 0.4rem 0.45rem;
      min-height: 44px;
      max-width: min(100vw - 2rem, 320px);
      font-family: inherit;
      text-align: left;
      cursor: pointer;
      border-radius: 10px;
      border: 1px solid rgba(61, 139, 253, 0.55);
      background: linear-gradient(
        155deg,
        rgba(61, 139, 253, 0.22) 0%,
        rgba(26, 35, 50, 0.98) 48%,
        rgba(15, 20, 25, 0.92) 100%
      );
      color: var(--text);
      box-shadow:
        0 1px 0 rgba(255, 255, 255, 0.06) inset,
        0 4px 18px rgba(0, 0, 0, 0.35),
        0 0 0 1px rgba(0, 0, 0, 0.2);
      transition:
        border-color 0.18s ease,
        box-shadow 0.18s ease,
        transform 0.12s ease;
    }
    .filter-toolbar-toggle:hover {
      border-color: rgba(126, 182, 255, 0.85);
      box-shadow:
        0 1px 0 rgba(255, 255, 255, 0.1) inset,
        0 6px 22px rgba(61, 139, 253, 0.28),
        0 4px 14px rgba(0, 0, 0, 0.4);
    }
    .filter-toolbar-toggle:active {
      transform: scale(0.98);
    }
    .filter-toolbar-toggle:focus-visible {
      outline: 3px solid rgba(126, 182, 255, 0.95);
      outline-offset: 3px;
    }
    .filter-toolbar-toggle__glyph {
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: rgba(61, 139, 253, 0.2);
      color: #b8d4ff;
    }
    .filter-toolbar-toggle__glyph svg {
      display: block;
    }
    .filter-toolbar-toggle__copy {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 0.08rem;
    }
    .filter-toolbar-toggle__head {
      font-size: 0.8rem;
      font-weight: 700;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      color: #f0f4fa;
      line-height: 1.15;
    }
    .filter-toolbar-toggle__sub {
      font-size: 0.65rem;
      font-weight: 500;
      color: var(--muted);
      line-height: 1.25;
    }
    .filter-toolbar-toggle__sub kbd {
      display: inline-block;
      margin: 0 0.12rem;
      padding: 0.06rem 0.28rem;
      border-radius: 4px;
      border: 1px solid var(--border);
      background: rgba(0, 0, 0, 0.35);
      font-size: 0.62rem;
      font-family: ui-monospace, monospace;
      color: var(--text);
    }
    .filter-toolbar-toggle__chev {
      flex-shrink: 0;
      display: flex;
      color: rgba(126, 182, 255, 0.95);
      transition: transform 0.22s ease;
    }
    .filter-toolbar-toggle--collapsed .filter-toolbar-toggle__chev {
      transform: rotate(180deg);
    }
    /** Aba na borda esquerda — só quando o painel está fechado (mapa cheio) */
    .filter-edge-tab {
      position: fixed;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      z-index: 40;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      margin: 0;
      padding: 0.55rem 0.7rem 0.55rem 0.45rem;
      font-family: inherit;
      cursor: pointer;
      border-radius: 0 12px 12px 0;
      background: linear-gradient(90deg, rgba(26, 35, 50, 0.97) 0%, rgba(26, 35, 50, 0.92) 100%);
      color: var(--text);
      border: 1px solid rgba(61, 139, 253, 0.55);
      border-left: none;
      box-shadow:
        4px 4px 24px rgba(0, 0, 0, 0.45),
        0 0 0 1px rgba(0, 0, 0, 0.25);
      transition:
        padding 0.18s ease,
        box-shadow 0.18s ease,
        background 0.18s ease;
    }
    .filter-edge-tab:hover {
      padding-left: 0.55rem;
      background: rgba(61, 139, 253, 0.18);
      box-shadow:
        6px 6px 28px rgba(61, 139, 253, 0.2),
        4px 4px 24px rgba(0, 0, 0, 0.5);
    }
    .filter-edge-tab:focus-visible {
      outline: 3px solid rgba(126, 182, 255, 0.95);
      outline-offset: 2px;
    }
    .filter-edge-tab__icon {
      display: flex;
      color: var(--accent);
    }
    .filter-edge-tab__text {
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      white-space: nowrap;
    }
    @media (max-width: 520px) {
      .filter-toolbar-toggle__head {
        font-size: 0.72rem;
      }
      .filter-toolbar-toggle {
        padding-right: 0.55rem;
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .filter-toolbar-toggle,
      .filter-toolbar-toggle__chev,
      .filter-edge-tab {
        transition: none;
      }
      .filter-toolbar-toggle:active {
        transform: none;
      }
    }
    .layout {
      flex: 1;
      display: flex;
      min-height: 0;
    }
    aside#filter-panel {
      width: min(380px, 100%);
      max-width: 100%;
      flex-shrink: 0;
      border-right: 1px solid var(--border);
      background: var(--panel);
      overflow: auto;
      padding: 0.45rem 0.55rem;
      transition:
        width 0.22s ease,
        min-width 0.22s ease,
        opacity 0.18s ease,
        padding 0.22s ease,
        border-width 0.22s ease;
    }
    body.filter-panel-collapsed aside#filter-panel {
      width: 0 !important;
      min-width: 0;
      max-width: 0;
      padding-left: 0;
      padding-right: 0;
      border-right-width: 0;
      opacity: 0;
      overflow: hidden;
      pointer-events: none;
    }
    aside fieldset {
      margin: 0 0 0.4rem;
      padding: 0.32rem 0.45rem;
      border-radius: 6px;
      border: 1px solid var(--border);
    }
    aside fieldset legend {
      font-size: 0.65rem;
      padding: 0 0.2rem;
    }
    main {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
    }
    #mappia {
      flex: 1;
      width: 100%;
      border: 0;
      background: #111;
    }
    /**
     * Mobile (≤768px): mapa em tela cheia na área útil; painel desliza por cima.
     * Desktop: mantém coluna ao lado (regras acima).
     */
    .filter-panel-backdrop {
      display: none;
      pointer-events: none;
    }
    @media (max-width: 768px) {
      html {
        height: 100%;
        overflow: hidden;
      }
      body {
        height: 100%;
        max-height: 100dvh;
        overflow: hidden;
      }
      header {
        flex-shrink: 0;
        position: relative;
        z-index: 50;
        padding-top: calc(0.35rem + env(safe-area-inset-top, 0px));
        padding-left: calc(0.65rem + env(safe-area-inset-left, 0px));
        padding-right: calc(0.65rem + env(safe-area-inset-right, 0px));
      }
      .layout {
        position: relative;
        flex: 1;
        min-height: 0;
        width: 100%;
        isolation: isolate;
      }
      .filter-panel-backdrop {
        display: none;
        position: absolute;
        inset: 0;
        z-index: 28;
        margin: 0;
        padding: 0;
        border: 0;
        background: rgba(6, 10, 16, 0.55);
        backdrop-filter: blur(3px);
        -webkit-backdrop-filter: blur(3px);
        cursor: pointer;
        touch-action: manipulation;
        -webkit-tap-highlight-color: transparent;
      }
      body:not(.filter-panel-collapsed) .filter-panel-backdrop {
        display: block;
        pointer-events: auto;
      }
      body.filter-panel-collapsed .filter-panel-backdrop {
        display: none !important;
        pointer-events: none !important;
      }
      aside#filter-panel {
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 100%;
        max-width: 100%;
        flex-shrink: 0;
        border-right: none;
        z-index: 35;
        padding-bottom: calc(0.45rem + env(safe-area-inset-bottom, 0px));
        padding-left: calc(0.55rem + env(safe-area-inset-left, 0px));
        padding-right: calc(0.55rem + env(safe-area-inset-right, 0px));
        box-shadow: 10px 0 40px rgba(0, 0, 0, 0.55);
        transform: translateX(0);
        transition:
          transform 0.3s cubic-bezier(0.22, 1, 0.36, 1),
          box-shadow 0.3s ease;
        opacity: 1 !important;
        overflow-x: hidden;
        overflow-y: auto;
        -webkit-overflow-scrolling: touch;
        overscroll-behavior: contain;
      }
      body.filter-panel-collapsed aside#filter-panel {
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
        padding-left: calc(0.55rem + env(safe-area-inset-left, 0px));
        padding-right: calc(0.55rem + env(safe-area-inset-right, 0px));
        transform: translateX(-100%);
        opacity: 1 !important;
        pointer-events: none;
        border-right-width: 0;
        box-shadow: none;
        overflow: hidden;
      }
      main {
        position: absolute;
        inset: 0;
        z-index: 10;
        display: flex;
        flex-direction: column;
        min-height: 0;
      }
      #mappia {
        flex: 1;
        min-height: 0;
        width: 100%;
      }
      .filter-edge-tab {
        z-index: 45;
      }
    }
    @media (max-width: 768px) and (prefers-reduced-motion: reduce) {
      aside#filter-panel {
        transition: transform 0.18s ease;
      }
    }
    fieldset.range-fieldset {
      margin: 0 0 0.4rem;
      padding: 0.32rem 0.45rem;
    }
    legend {
      padding: 0 0.2rem;
      color: var(--muted);
      font-size: 0.65rem;
    }
    label {
      display: block;
      font-size: 0.65rem;
      color: var(--muted);
      margin-top: 0.2rem;
    }
    label:first-of-type { margin-top: 0; }
    input[type="number"], input[type="text"], select, textarea {
      width: 100%;
      margin-top: 0.08rem;
      padding: 0.28rem 0.35rem;
      border-radius: 4px;
      border: 1px solid var(--border);
      background: var(--bg);
      color: var(--text);
      font-size: 0.78rem;
    }
    .bairro-combobox {
      position: relative;
      margin-top: 0.08rem;
    }
    .bairro-combobox__row {
      display: flex;
      gap: 0.25rem;
      align-items: stretch;
    }
    .bairro-combobox__row input[type="text"] {
      flex: 1;
      margin-top: 0;
    }
    .bairro-combobox__clear {
      flex-shrink: 0;
      width: 2rem;
      margin-top: 0;
      padding: 0.28rem 0;
      border-radius: 4px;
      border: 1px solid var(--border);
      background: var(--bg);
      color: var(--muted);
      font-size: 1rem;
      line-height: 1;
      cursor: pointer;
    }
    .bairro-combobox__clear:hover {
      color: var(--text);
      border-color: var(--accent-dim);
    }
    .bairro-combobox__list {
      position: absolute;
      z-index: 40;
      left: 0;
      right: 0;
      top: calc(100% + 2px);
      max-height: 11rem;
      margin: 0;
      padding: 0.2rem 0;
      list-style: none;
      overflow-y: auto;
      border-radius: 6px;
      border: 1px solid var(--border);
      background: var(--panel);
      box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
    }
    .bairro-combobox__list[hidden] {
      display: none;
    }
    .bairro-combobox__option {
      padding: 0.35rem 0.5rem;
      font-size: 0.78rem;
      cursor: pointer;
    }
    .bairro-combobox__option:hover,
    .bairro-combobox__option:focus {
      background: rgba(61, 139, 253, 0.2);
      color: var(--text);
      outline: none;
    }
    .bairro-combobox__empty {
      padding: 0.35rem 0.5rem;
      font-size: 0.72rem;
      color: var(--muted);
    }
    textarea { min-height: 48px; font-family: ui-monospace, monospace; font-size: 0.72rem; }
    .row2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.3rem;
    }
    .data-strip {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 0.35rem 0.75rem;
      font-size: 0.72rem;
      color: var(--muted);
      padding: 0.4rem 0.55rem;
      background: var(--bg);
      border-radius: 8px;
      border: 1px dashed var(--border);
      margin-bottom: 0.45rem;
      display: none;
    }
    .data-strip-label { font-weight: 500; color: var(--muted); }
    .data-strip-values {
      font-variant-numeric: tabular-nums;
      color: var(--text);
      opacity: 0.92;
    }
    .data-strip-values .sep { margin: 0 0.35rem; opacity: 0.5; }
    .range-stack {
      margin: 0 0 0.08rem;
    }
    /* 60-bin mini histogram above slider */
    .hist-row {
      display: flex;
      align-items: stretch;
      gap: 1px;
      height: 24px;
      margin: 0 0 0.12rem;
      padding: 0 8px;
    }
    .hist-bin {
      flex: 1;
      min-width: 0;
      position: relative;
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
      align-items: center;
      background: rgba(0, 0, 0, 0.22);
      border-radius: 1px;
    }
    .hist-fill {
      width: 100%;
      min-height: 2px;
      background: rgba(61, 139, 253, 0.5);
      border-radius: 2px 2px 0 0;
    }
    .hist-fill[data-empty="1"] {
      min-height: 0;
      height: 0 !important;
    }
    .hist-count {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      text-align: center;
      font-size: 5px;
      line-height: 1;
      color: var(--text);
      opacity: 0.9;
      pointer-events: none;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    @media (min-width: 360px) {
      .hist-count { font-size: 6px; }
    }
    /* Dual range */
    .dual-wrap {
      position: relative;
      height: 22px;
      margin: 0;
      --p-low: 0%;
      --p-high: 100%;
    }
    .dual-wrap .track-bg {
      position: absolute;
      left: 8px;
      right: 8px;
      top: 50%;
      transform: translateY(-50%);
      height: 6px;
      border-radius: 3px;
      background: var(--track);
      pointer-events: none;
    }
    .dual-wrap .track-fill {
      position: absolute;
      left: 8px;
      right: 8px;
      top: 50%;
      transform: translateY(-50%);
      height: 6px;
      border-radius: 3px;
      pointer-events: none;
      background: linear-gradient(
        90deg,
        var(--track) 0,
        var(--track) var(--p-low),
        var(--fill) var(--p-low),
        var(--fill) var(--p-high),
        var(--track) var(--p-high),
        var(--track) 100%
      );
    }
    .dual-wrap input[type="range"] {
      position: absolute;
      left: 0;
      right: 0;
      top: 0;
      width: 100%;
      height: 22px;
      margin: 0;
      background: none;
      pointer-events: none;
      -webkit-appearance: none;
      appearance: none;
    }
    .dual-wrap input[type="range"]::-webkit-slider-thumb {
      -webkit-appearance: none;
      appearance: none;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--thumb);
      border: 2px solid #fff;
      box-shadow: 0 1px 4px rgba(0,0,0,0.4);
      cursor: grab;
      pointer-events: auto;
    }
    .dual-wrap input.range-max::-webkit-slider-thumb {
      background: var(--thumb-max);
    }
    .dual-wrap input[type="range"]::-moz-range-thumb {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--thumb);
      border: 2px solid #fff;
      box-shadow: 0 1px 4px rgba(0,0,0,0.4);
      cursor: grab;
      pointer-events: auto;
    }
    .dual-wrap input.range-max::-moz-range-thumb {
      background: var(--thumb-max);
    }
    .dual-wrap input[type="range"]::-webkit-slider-runnable-track {
      height: 6px;
      background: transparent;
    }
    .dual-wrap input[type="range"]::-moz-range-track {
      height: 6px;
      background: transparent;
    }
    /* Contagem de imóveis que batem com todos os filtros atuais (ao arrastar o slider) */
    .slider-match-tooltip {
      position: absolute;
      left: 50%;
      bottom: 100%;
      transform: translateX(-50%);
      margin-bottom: 6px;
      padding: 0.22rem 0.45rem;
      border-radius: 5px;
      font-size: 0.68rem;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
      background: var(--panel);
      border: 1px solid var(--accent-dim);
      color: var(--text);
      white-space: nowrap;
      z-index: 6;
      opacity: 0;
      visibility: hidden;
      transition: opacity 0.12s ease, visibility 0.12s ease;
      pointer-events: none;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.45);
    }
    .slider-match-tooltip.is-visible {
      opacity: 1;
      visibility: visible;
    }
    .slider-hint {
      display: none;
    }
    .filter-labels label {
      font-size: 0.68rem;
      color: var(--text);
      font-weight: 500;
      margin-top: 0.1rem;
    }
    .fs-hidden {
      display: none !important;
    }
    .negocio-row {
      display: flex;
      gap: 0.35rem 0.5rem;
      flex-wrap: wrap;
      align-items: center;
    }
    .negocio-radios {
      display: flex;
      gap: 0.35rem;
      flex-wrap: wrap;
      align-items: center;
    }
    .negocio-row .negocio-tipo-lbl {
      display: inline-block;
      margin: 0;
      font-size: 0.68rem;
      color: var(--muted);
      flex-shrink: 0;
    }
    .negocio-row select.negocio-tipo-sel {
      margin-top: 0;
      width: auto;
      min-width: 6.5rem;
      max-width: 100%;
      flex: 1 1 6.5rem;
    }
    .negocio-row label.seg {
      display: inline-flex;
      align-items: center;
      gap: 0.2rem;
      margin: 0;
      padding: 0.2rem 0.45rem;
      border-radius: 4px;
      border: 1px solid var(--border);
      background: var(--bg);
      font-size: 0.72rem;
      color: var(--text);
      cursor: pointer;
    }
    .negocio-row input {
      margin: 0;
      width: auto;
    }
    button {
      cursor: pointer;
      border: 0;
      border-radius: 6px;
      padding: 0.32rem 0.6rem;
      font-weight: 600;
      font-size: 0.74rem;
      background: var(--accent);
      color: #fff;
    }
    button:hover { background: var(--accent-dim); }
    button.secondary {
      background: transparent;
      border: 1px solid var(--border);
      color: var(--text);
    }
    .actions { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.35rem; }
    .stats {
      font-size: 0.68rem;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.35rem;
      margin-top: 0.25rem;
      white-space: pre-wrap;
      word-break: break-word;
      max-height: 100px;
      overflow: auto;
    }
    .log {
      font-size: 0.65rem;
      color: var(--muted);
      margin-top: 0.35rem;
      max-height: 72px;
      overflow: auto;
      font-family: ui-monospace, monospace;
    }
    .hint { font-size: 0.65rem; color: var(--muted); line-height: 1.25; margin: 0 0 0.35rem; }
    fieldset.range-fieldset[data-limits-pending="1"] .range-stack {
      opacity: 0.45;
      pointer-events: none;
    }
    fieldset.range-fieldset[data-limits-pending="1"] .slider-hint::after {
      content: " (aguardando postMessage do mapa com min/máx)";
      font-size: 0.68rem;
      color: var(--muted);
    }
    /* Tela inicial: aguarda primeiro postMessage com `imoveis` */
    .page-loading {
      position: fixed;
      inset: 0;
      z-index: 1000;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(15, 20, 25, 0.85);
      backdrop-filter: blur(5px);
      transition: opacity 0.4s ease, visibility 0.4s ease;
    }
    .page-loading.page-loading--done {
      opacity: 0;
      visibility: hidden;
      pointer-events: none;
    }
    .page-loading-inner {
      text-align: center;
      padding: 1.25rem;
      max-width: 90vw;
    }
    .page-loading-spinner {
      width: 46px;
      height: 46px;
      margin: 0 auto 0.85rem;
      border: 3px solid var(--border);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: page-loading-spin 0.8s linear infinite;
    }
    @keyframes page-loading-spin {
      to {
        transform: rotate(360deg);
      }
    }
    .page-loading-text {
      margin: 0;
      font-size: 0.85rem;
      color: var(--text);
      font-weight: 500;
    }
    .page-loading-sub {
      margin: 0.35rem 0 0;
      font-size: 0.72rem;
      color: var(--muted);
    }
    @media (prefers-reduced-motion: reduce) {
      .page-loading-spinner {
        animation: none;
        border-top-color: var(--accent);
        opacity: 0.9;
      }
      .page-loading {
        transition: opacity 0.2s ease;
      }
    }
  </style>
</head>
<body>
  <div id="page-loading" class="page-loading" role="status" aria-live="polite" aria-busy="true">
    <div class="page-loading-inner">
      <div class="page-loading-spinner" aria-hidden="true"></div>
      <p class="page-loading-text">Carregando imóveis…</p>
      <p class="page-loading-sub">Baixando os dados mais recentes.</p>
    </div>
  </div>
  <header>
    <div class="header-bar__start">
      <h1>Imóveis Belo Horizonte</h1>
      <button
        type="button"
        id="btn_toggle_filters"
        class="filter-toolbar-toggle"
        aria-expanded="true"
        aria-controls="filter-panel"
        title="Alternar painel de filtros (atalho: tecla [ )"
      >
        <span class="filter-toolbar-toggle__glyph" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round">
            <rect x="4" y="5" width="7" height="14" rx="1.5" />
            <rect x="14" y="7" width="6" height="10" rx="1" opacity="0.42" />
          </svg>
        </span>
        <span class="filter-toolbar-toggle__copy">
          <span id="filter_toggle_title" class="filter-toolbar-toggle__head">Ocultar painel</span>
          <span id="filter_toggle_hint" class="filter-toolbar-toggle__sub"></span>
        </span>
        <span class="filter-toolbar-toggle__chev" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </span>
      </button>
    </div>
    <span style="font-size:0.72rem;color:var(--muted); display: none;">
      <a href="https://maps.csr.ufmg.br/calculator/?queryid=595&options=capabilities" target="_blank" rel="noopener">Abrir calculadora</a>
      ·
      <a href="https://maps.csr.ufmg.br/mappia_io.js" target="_blank" rel="noopener">mappia_io.js</a>
    </span>
  </header>

  <div class="layout">
    <div
      class="filter-panel-backdrop"
      id="filter_panel_backdrop"
      role="presentation"
      aria-hidden="true"
    ></div>
    <aside id="filter-panel">
      <p class="hint" style="display: none;">
        Com lista <code>imoveis</code> no <code>postMessage</code>, os limites e os gráficos vêm dos dados. Caso contrário, do mapa (<code>inputs</code> / limites).
        Quartos e vagas usam trilho &quot;spread&quot; (mais resolução nos valores baixos). Em outros fieldsets: <code>data-slider-spread=&quot;1&quot;</code> ou <code>data-slider-spread-exponent=&quot;0.42&quot;</code> (0–1]; <code>data-slider-spread=&quot;off&quot;</code> desliga.
      </p>

      <fieldset style="margin-bottom:0.35rem">
        <legend>Negócio</legend>
        <div class="negocio-row">
          <div class="negocio-radios" role="radiogroup" aria-label="Tipo de negócio">
            <label class="seg"><input type="radio" name="tipo_negocio" value="aluguel" checked /> Aluguel</label>
            <label class="seg"><input type="radio" name="tipo_negocio" value="compra" /> Compra</label>
          </div>
          <label for="tipo_imovel" class="negocio-tipo-lbl">Tipo</label>
          <select id="tipo_imovel" class="negocio-tipo-sel" aria-label="Tipo de imóvel">
            <option>Todos</option>
            <option>Apartamento</option>
            <option>Casa</option>
          </select>
        </div>
        <label for="text_filter">Filtrar por bairro</label>
        <div class="bairro-combobox" id="bairro_combobox">
          <div class="bairro-combobox__row">
            <input
              id="text_filter"
              type="text"
              value=""
              placeholder="Buscar ou escolher bairro (opcional)"
              autocomplete="off"
              role="combobox"
              aria-autocomplete="list"
              aria-expanded="false"
              aria-controls="text_filter_list"
            />
            <button type="button" class="bairro-combobox__clear" id="text_filter_clear" title="Limpar filtro de bairro" aria-label="Limpar filtro de bairro">×</button>
          </div>
          <ul id="text_filter_list" class="bairro-combobox__list" role="listbox" hidden></ul>
        </div>
      </fieldset>

      <!-- Aluguel + condomínio (valor total aluguel — não confundir com bloco Condomínio) -->
      <fieldset id="fs-aluguel-total" class="range-fieldset" data-range="aluguel" data-stat="aluguelTotal" data-limits-pending="1">
        <legend>Aluguel + condomínio (total)</legend>
        <div class="data-strip">
          <span class="data-strip-label">Referência (mapa)</span>
          <span class="data-strip-values"><span class="data-ref-min">—</span><span class="sep">…</span><span class="data-ref-max">—</span></span>
        </div>
        <p class="slider-hint">Controle · esquerda = mín · direita = máx</p>
        <div class="range-stack">
          <div class="hist-row" aria-label="Distribuição aluguel+cond (60 faixas)"></div>
          <div class="dual-wrap" data-dual="aluguel">
            <div class="track-bg"></div>
            <div class="track-fill"></div>
            <input type="range" class="range-min" min="0" max="100" value="0" step="1" aria-label="Mínimo aluguel+cond" />
            <input type="range" class="range-max" min="0" max="100" value="100" step="1" aria-label="Máximo aluguel+cond" />
          </div>
        </div>
        <div class="row2 filter-labels">
          <div>
            <label for="aluguel_min">Mín</label>
            <input id="aluguel_min" class="input-num-ptbr" type="text" inputmode="decimal" autocomplete="off" value="0" />
          </div>
          <div>
            <label for="aluguel_max">Máx</label>
            <input id="aluguel_max" class="input-num-ptbr" type="text" inputmode="decimal" autocomplete="off" value="8.000" />
          </div>
        </div>
      </fieldset>

      <fieldset id="fs-venda" class="range-fieldset fs-hidden" data-range="venda" data-stat="venda" data-limits-pending="1">
        <legend>Venda (R$)</legend>
        <div class="data-strip">
          <span class="data-strip-label">Referência (mapa)</span>
          <span class="data-strip-values"><span class="data-ref-min">—</span><span class="sep">…</span><span class="data-ref-max">—</span></span>
        </div>
        <p class="slider-hint">Controle · venda</p>
        <div class="range-stack">
          <div class="hist-row" aria-label="Distribuição venda (60 faixas)"></div>
          <div class="dual-wrap" data-dual="venda">
            <div class="track-bg"></div>
            <div class="track-fill"></div>
            <input type="range" class="range-min" min="0" max="100" value="0" step="1" />
            <input type="range" class="range-max" min="0" max="100" value="100" step="1" />
          </div>
        </div>
        <div class="row2 filter-labels">
          <div>
            <label for="venda_min">Mín</label>
            <input id="venda_min" class="input-num-ptbr" type="text" inputmode="decimal" autocomplete="off" value="0" />
          </div>
          <div>
            <label for="venda_max">Máx</label>
            <input id="venda_max" class="input-num-ptbr" type="text" inputmode="decimal" autocomplete="off" value="2.000.000" />
          </div>
        </div>
      </fieldset>

      <fieldset class="range-fieldset" data-range="area" data-stat="area" data-slider-spread="1" data-limits-pending="1">
        <legend>Área (m²)</legend>
        <div class="data-strip">
          <span class="data-strip-label">Referência (mapa)</span>
          <span class="data-strip-values"><span class="data-ref-min">—</span><span class="sep">…</span><span class="data-ref-max">—</span></span>
        </div>
        <p class="slider-hint">Controle · área (m²)</p>
        <div class="range-stack">
          <div class="hist-row" aria-label="Distribuição área (60 faixas)"></div>
          <div class="dual-wrap" data-dual="area">
            <div class="track-bg"></div>
            <div class="track-fill"></div>
            <input type="range" class="range-min" min="0" max="100" value="0" step="1" />
            <input type="range" class="range-max" min="0" max="100" value="100" step="1" />
          </div>
        </div>
        <div class="row2 filter-labels">
          <div>
            <label for="area_min">Mín</label>
            <input id="area_min" class="input-num-ptbr" type="text" inputmode="decimal" autocomplete="off" value="1" />
          </div>
          <div>
            <label for="area_max">Máx</label>
            <input id="area_max" class="input-num-ptbr" type="text" inputmode="decimal" autocomplete="off" value="400" />
          </div>
        </div>
      </fieldset>

      <fieldset class="range-fieldset" data-range="q" data-stat="quartos" data-limits-pending="1">
        <legend>Quartos</legend>
        <div class="data-strip">
          <span class="data-strip-label">Referência (mapa)</span>
          <span class="data-strip-values"><span class="data-ref-min">—</span><span class="sep">…</span><span class="data-ref-max">—</span></span>
        </div>
        <p class="slider-hint">Controle · quartos (inteiros)</p>
        <div class="range-stack">
          <div class="hist-row" aria-label="Distribuição quartos (60 faixas)"></div>
          <div class="dual-wrap" data-dual="q">
            <div class="track-bg"></div>
            <div class="track-fill"></div>
            <input type="range" class="range-min" min="0" max="100" value="0" step="1" />
            <input type="range" class="range-max" min="0" max="100" value="100" step="1" />
          </div>
        </div>
        <div class="row2 filter-labels">
          <div>
            <label for="q_min">Mín</label>
            <input id="q_min" class="input-num-ptbr" type="text" inputmode="numeric" autocomplete="off" value="0" />
          </div>
          <div>
            <label for="q_max">Máx</label>
            <input id="q_max" class="input-num-ptbr" type="text" inputmode="numeric" autocomplete="off" value="35" />
          </div>
        </div>
      </fieldset>

      <fieldset class="range-fieldset" data-range="v" data-stat="vagas" data-limits-pending="1">
        <legend>Vagas</legend>
        <div class="data-strip">
          <span class="data-strip-label">Referência (mapa)</span>
          <span class="data-strip-values"><span class="data-ref-min">—</span><span class="sep">…</span><span class="data-ref-max">—</span></span>
        </div>
        <p class="slider-hint">Controle · vagas (inteiros)</p>
        <div class="range-stack">
          <div class="hist-row" aria-label="Distribuição vagas (60 faixas)"></div>
          <div class="dual-wrap" data-dual="v">
            <div class="track-bg"></div>
            <div class="track-fill"></div>
            <input type="range" class="range-min" min="0" max="100" value="0" step="1" />
            <input type="range" class="range-max" min="0" max="100" value="100" step="1" />
          </div>
        </div>
        <div class="row2 filter-labels">
          <div>
            <label for="v_min">Mín</label>
            <input id="v_min" class="input-num-ptbr" type="text" inputmode="numeric" autocomplete="off" value="0" />
          </div>
          <div>
            <label for="v_max">Máx</label>
            <input id="v_max" class="input-num-ptbr" type="text" inputmode="numeric" autocomplete="off" value="10" />
          </div>
        </div>
      </fieldset>

      <fieldset style="display: none;">
        <legend>Outros</legend>
        <label for="dias_anuncio">Máx. dias do anúncio</label>
        <input id="dias_anuncio" class="input-num-ptbr" type="text" inputmode="numeric" autocomplete="off" value="190.000" />
      </fieldset>

      <div class="actions" style="display: none;">
        <button type="button" id="btn_send_iframe">Enviar filtros ao iframe</button>
        <button type="button" class="secondary" id="btn_apply_query">Aplicar query (MappiaIO)</button>
      </div>

      <fieldset style="display: none;">
        <legend>Estatísticas (última mensagem do iframe)</legend>
        <div id="stats" class="stats">(aguardando postMessage do mapa…)</div>
      </fieldset>

      <fieldset style="display: none;">
        <legend>Query JSON/JS (opcional — applyQuery)</legend>
        <label for="query_blob">Conteúdo enviado com <code>mappia.applyQuery</code></label>
        <textarea id="query_blob" placeholder='Ex.: [{"title":"…","elements":[…]}]'></textarea>
      </fieldset>

      <div id="log" class="log" style="display: none;"></div>
    </aside>

    <main>
      <iframe
        id="mappia"
        title="CSR Maps"
        src="https://maps.csr.ufmg.br/calculator/?queryid=595&options=capabilities"
        allowfullscreen
      ></iframe>
    </main>
  </div>

  <button
    type="button"
    id="btn_toggle_filters_edge"
    class="filter-edge-tab"
    hidden
    aria-controls="filter-panel"
    aria-expanded="false"
    aria-hidden="true"
    title="Mostrar painel de filtros (atalho: [ )"
    style="display: none;"
  >
    <span class="filter-edge-tab__icon" aria-hidden="true">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 18l6-6-6-6" />
      </svg>
    </span>
    <span class="filter-edge-tab__text">Filtros</span>
  </button>

  <script src="https://maps.csr.ufmg.br/mappia_io.js"></script>
  <script>
    (function () {
      var MAP_ORIGIN = 'https://maps.csr.ufmg.br';
      var iframeEl = document.getElementById('mappia');
      var statsEl = document.getElementById('stats');
      var logEl = document.getElementById('log');
      var btnToggleFilters = document.getElementById('btn_toggle_filters');
      var btnToggleFiltersEdge = document.getElementById('btn_toggle_filters_edge');
      var filterPanelBackdrop = document.getElementById('filter_panel_backdrop');
      var filterToggleTitleEl = document.getElementById('filter_toggle_title');
      var filterToggleHintEl = document.getElementById('filter_toggle_hint');
      var pageLoadingEl = document.getElementById('page-loading');
      /** Oculta overlay após primeiro lote `imoveis` (ou timeout de segurança). */
      var imoveisLoadingComplete = false;
      var loadingFallbackTimer = null;
      var LOADING_IMOVEIS_FALLBACK_MS = 90000;

      function completeImoveisLoading(reason) {
        if (imoveisLoadingComplete) return;
        imoveisLoadingComplete = true;
        if (loadingFallbackTimer) {
          clearTimeout(loadingFallbackTimer);
          loadingFallbackTimer = null;
        }
        if (pageLoadingEl) {
          pageLoadingEl.classList.add('page-loading--done');
          pageLoadingEl.setAttribute('aria-busy', 'false');
        }
        if (reason === 'timeout') {
          log('loading: timeout — overlay fechado sem imoveis');
        }
      }

      loadingFallbackTimer = setTimeout(function () {
        completeImoveisLoading('timeout');
      }, LOADING_IMOVEIS_FALLBACK_MS);

      function persistFilterPanelState(collapsed) {
        try {
          sessionStorage.setItem('filterPanelCollapsed', collapsed ? '1' : '0');
        } catch (e) {}
      }

      function syncFilterPanelToggleUi() {
        var collapsed = document.body.classList.contains('filter-panel-collapsed');
        if (btnToggleFilters) {
          btnToggleFilters.classList.toggle('filter-toolbar-toggle--collapsed', collapsed);
          btnToggleFilters.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
          if (filterToggleTitleEl) {
            filterToggleTitleEl.textContent = collapsed ? 'Mostrar painel' : 'Ocultar painel';
          }
          if (filterToggleHintEl) {
            filterToggleHintEl.innerHTML = collapsed
              ? 'Sliders, histogramas e busca · tecla <kbd>[</kbd>'
              : 'Amplia o mapa · tecla <kbd>[</kbd>';
          }
        }
        if (btnToggleFiltersEdge) {
          btnToggleFiltersEdge.hidden = !collapsed;
          btnToggleFiltersEdge.setAttribute('aria-hidden', collapsed ? 'false' : 'true');
          btnToggleFiltersEdge.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        }
      }

      function setFilterPanelCollapsed(collapsed) {
        document.body.classList.toggle('filter-panel-collapsed', collapsed);
        persistFilterPanelState(collapsed);
        syncFilterPanelToggleUi();
        requestAnimationFrame(function () {
          window.dispatchEvent(new Event('resize'));
        });
      }

      function toggleFilterPanel() {
        setFilterPanelCollapsed(!document.body.classList.contains('filter-panel-collapsed'));
      }

      try {
        var fpStored = sessionStorage.getItem('filterPanelCollapsed');
        if (fpStored === '1') {
          document.body.classList.add('filter-panel-collapsed');
        } else if (fpStored === '0') {
          document.body.classList.remove('filter-panel-collapsed');
        } else if (typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 768px)').matches) {
          document.body.classList.add('filter-panel-collapsed');
        }
      } catch (e) {}
      syncFilterPanelToggleUi();
      if (document.body.classList.contains('filter-panel-collapsed')) {
        requestAnimationFrame(function () {
          window.dispatchEvent(new Event('resize'));
        });
      }

      if (btnToggleFilters) {
        btnToggleFilters.addEventListener('click', function () {
          toggleFilterPanel();
        });
      }
      if (btnToggleFiltersEdge) {
        btnToggleFiltersEdge.addEventListener('click', function () {
          toggleFilterPanel();
        });
      }
      if (filterPanelBackdrop) {
        filterPanelBackdrop.addEventListener('click', function () {
          setFilterPanelCollapsed(true);
        });
      }

      document.addEventListener('keydown', function (ev) {
        if (ev.defaultPrevented) return;
        var keyOk = ev.key === '[' || ev.code === 'BracketLeft';
        if (!keyOk) return;
        var t = ev.target;
        if (t && t.closest && t.closest('input, textarea, select, [contenteditable="true"]')) return;
        ev.preventDefault();
        toggleFilterPanel();
      });

      /** @type {Record<string, { min: number, max: number } | null>} */
      var dataBounds = {};
      /** Último array `imoveis` recebido do iframe — usado para contagem no tooltip dos sliders */
      var lastImoveisBatch = null;
      /** Min/max por dimensão agrupados por `tipo_imovel` (Todos / Apartamento / Casa), após último lote. */
      var lastLimitsByTipo = null;
      /** Bairros distintos do último lote (para combobox de filtro). */
      var allBairrosList = [];
      var bairroFilterInputEl = null;
      var bairroFilterListEl = null;

      function normalizeForSearch(s) {
        if (s == null) return '';
        return String(s)
          .toLowerCase()
          .normalize('NFD')
          .replace(/[\u0300-\u036f]/g, '');
      }

      function collectBairrosFromImoveis(imoveis) {
        var seen = {};
        var out = [];
        if (!imoveis || !imoveis.length) return out;
        for (var i = 0; i < imoveis.length; i++) {
          var raw = imoveis[i] && imoveis[i].bairro;
          if (raw == null) continue;
          var name = String(raw).trim();
          if (!name) continue;
          var key = normalizeForSearch(name);
          if (seen[key]) continue;
          seen[key] = name;
          out.push(name);
        }
        out.sort(function (a, b) {
          return a.localeCompare(b, 'pt-BR', { sensitivity: 'base' });
        });
        return out;
      }

      function hideBairroSuggestions() {
        if (!bairroFilterListEl || !bairroFilterInputEl) return;
        bairroFilterListEl.hidden = true;
        bairroFilterInputEl.setAttribute('aria-expanded', 'false');
      }

      function setBairroCatalog(imoveis) {
        allBairrosList = collectBairrosFromImoveis(imoveis);
        if (bairroFilterInputEl && document.activeElement === bairroFilterInputEl) {
          renderBairroSuggestions();
        } else {
          hideBairroSuggestions();
        }
      }

      function renderBairroSuggestions() {
        if (!bairroFilterListEl || !bairroFilterInputEl) return;
        if (document.activeElement !== bairroFilterInputEl) {
          hideBairroSuggestions();
          return;
        }
        var q = normalizeForSearch(bairroFilterInputEl.value.trim());
        var matches = [];
        var i;
        for (i = 0; i < allBairrosList.length; i++) {
          var b = allBairrosList[i];
          if (!q || normalizeForSearch(b).indexOf(q) !== -1) {
            matches.push(b);
            if (matches.length >= 80) break;
          }
        }
        bairroFilterListEl.innerHTML = '';
        if (!allBairrosList.length) {
          var emptyLi = document.createElement('li');
          emptyLi.className = 'bairro-combobox__empty';
          emptyLi.textContent = 'Carregue imóveis no mapa';
          bairroFilterListEl.appendChild(emptyLi);
          bairroFilterListEl.hidden = false;
          bairroFilterInputEl.setAttribute('aria-expanded', 'true');
          return;
        }
        if (!matches.length) {
          var noneLi = document.createElement('li');
          noneLi.className = 'bairro-combobox__empty';
          noneLi.textContent = 'Nenhum bairro corresponde';
          bairroFilterListEl.appendChild(noneLi);
          bairroFilterListEl.hidden = false;
          bairroFilterInputEl.setAttribute('aria-expanded', 'true');
          return;
        }
        for (i = 0; i < matches.length; i++) {
          (function (bairroName) {
            var li = document.createElement('li');
            li.className = 'bairro-combobox__option';
            li.setAttribute('role', 'option');
            li.textContent = bairroName;
            li.addEventListener('mousedown', function (ev) {
              ev.preventDefault();
              bairroFilterInputEl.value = bairroName;
              bairroFilterListEl.hidden = true;
              bairroFilterInputEl.setAttribute('aria-expanded', 'false');
              scheduleAutoSendFilters();
            });
            bairroFilterListEl.appendChild(li);
          })(matches[i]);
        }
        bairroFilterListEl.hidden = false;
        bairroFilterInputEl.setAttribute('aria-expanded', 'true');
      }

      function initBairroCombobox() {
        bairroFilterInputEl = document.getElementById('text_filter');
        bairroFilterListEl = document.getElementById('text_filter_list');
        var clearBtn = document.getElementById('text_filter_clear');
        if (!bairroFilterInputEl || !bairroFilterListEl) return;

        bairroFilterInputEl.addEventListener('input', function () {
          renderBairroSuggestions();
          scheduleAutoSendFilters();
        });
        bairroFilterInputEl.addEventListener('focus', function () {
          renderBairroSuggestions();
        });
        bairroFilterInputEl.addEventListener('blur', function () {
          setTimeout(hideBairroSuggestions, 160);
        });
        if (clearBtn) {
          clearBtn.addEventListener('click', function () {
            bairroFilterInputEl.value = '';
            hideBairroSuggestions();
            scheduleAutoSendFilters();
            bairroFilterInputEl.focus();
          });
        }
        hideBairroSuggestions();
      }

      function imovelMatchesTextFilter(im, filter) {
        if (filter == null || String(filter).trim() === '') return true;
        var needle = normalizeForSearch(String(filter).trim());
        var fields = [im.bairro, im.endereco];
        var fi;
        for (fi = 0; fi < fields.length; fi++) {
          if (normalizeForSearch(fields[fi]).indexOf(needle) !== -1) return true;
        }
        return false;
      }

      function log(line) {
        var t = new Date().toISOString().slice(11, 19);
        logEl.textContent = '[' + t + '] ' + line + '\n' + logEl.textContent;
      }

      /** ms após última alteração nos filtros → mesmo efeito do botão "Enviar filtros ao iframe" */
      var AUTOSEND_FILTERS_MS = 500;
      var autoSendFiltersTimer = null;
      /** Esconde o tooltip 1 s após a última alteração (input) neste slider */
      var SLIDER_TOOLTIP_HIDE_MS = 1000;
      var sliderTooltipHideByWrap = new WeakMap();

      function scheduleSliderTooltipHide(wrap, tip) {
        var prev = sliderTooltipHideByWrap.get(wrap);
        if (prev) clearTimeout(prev);
        var id = setTimeout(function () {
          sliderTooltipHideByWrap.delete(wrap);
          if (tip && tip.classList) tip.classList.remove('is-visible');
        }, SLIDER_TOOLTIP_HIDE_MS);
        sliderTooltipHideByWrap.set(wrap, id);
      }

      function scheduleAutoSendFilters() {
        if (autoSendFiltersTimer) clearTimeout(autoSendFiltersTimer);
        autoSendFiltersTimer = setTimeout(function () {
          autoSendFiltersTimer = null;
          sendFiltersToIframe();
        }, AUTOSEND_FILTERS_MS);
      }

      function num(id) {
        var el = document.getElementById(id);
        if (!el) return 0;
        var v = parsePtBRNumber(el.value);
        return isNaN(v) ? 0 : v;
      }

      function str(id) {
        return document.getElementById(id).value || '';
      }

      function getNegocio() {
        var r = document.querySelector('input[name="tipo_negocio"]:checked');
        return r && r.value === 'compra' ? 'compra' : 'aluguel';
      }

      function applyNegocioVisibility() {
        var compra = getNegocio() === 'compra';
        var fsAl = document.getElementById('fs-aluguel-total');
        var fsV = document.getElementById('fs-venda');
        if (fsAl) fsAl.classList.toggle('fs-hidden', compra);
        if (fsV) fsV.classList.toggle('fs-hidden', !compra);
      }

      function formatBound(n) {
        if (n === undefined || n === null || isNaN(n)) return '—';
        var abs = Math.abs(n);
        if (abs >= 1e6) return n.toLocaleString('pt-BR', { maximumFractionDigits: 0 });
        if (abs >= 1000) return n.toLocaleString('pt-BR', { maximumFractionDigits: 1 });
        return String(Math.round(n * 100) / 100);
      }

      function swapIfNeeded(a, b) {
        if (a > b) return [b, a];
        return [a, b];
      }

      function clamp(n, lo, hi) {
        return Math.max(lo, Math.min(hi, n));
      }

      /** Venda: granularidade mínima de R$ 10.000 */
      var VENDA_STEP = 10000;

      function snapVendaPrice(n) {
        return Math.round(n / VENDA_STEP) * VENDA_STEP;
      }

      /** Arredonda ao grid de 10k e mantém dentro de [floor, ceil] (ajusta para múltiplo válido nos bordos). */
      function snapVendaInBounds(n, floor, ceil) {
        if (!(typeof floor === 'number' && typeof ceil === 'number' && floor <= ceil)) {
          return snapVendaPrice(n);
        }
        var s = snapVendaPrice(n);
        if (s < floor) s = Math.ceil(floor / VENDA_STEP) * VENDA_STEP;
        if (s > ceil) s = Math.floor(ceil / VENDA_STEP) * VENDA_STEP;
        return clamp(s, floor, ceil);
      }

      /** pt-BR: milhar `.`, decimal `,` */
      function parsePtBRNumber(v) {
        if (v == null || v === '') return NaN;
        var s = String(v).trim().replace(/\s/g, '');
        if (!s) return NaN;
        var parts = s.split(',');
        if (parts.length > 2) return NaN;
        var intPart = parts[0].replace(/\./g, '');
        var decPart = parts.length > 1 ? parts[1].replace(/\./g, '') : '';
        if (!intPart && !decPart) return NaN;
        if (!intPart) intPart = '0';
        if (decPart) return parseFloat(intPart + '.' + decPart);
        return parseFloat(intPart);
      }

      /**
       * @param {number} n
       * @param {boolean} asInteger
       */
      function formatPtBRNumber(n, asInteger) {
        if (typeof n !== 'number' || isNaN(n)) return '';
        if (asInteger) return Math.round(n).toLocaleString('pt-BR', { maximumFractionDigits: 0 });
        return n.toLocaleString('pt-BR', { maximumFractionDigits: 8, minimumFractionDigits: 0 });
      }

      function readNumEl(el) {
        return parsePtBRNumber(el.value);
      }

      /**
       * @param {string} key - data-range value
       * @param {{ floor: number, ceil: number, step: number, integer?: boolean, pending?: boolean }} opts
       */
      function getScale(opts) {
        var floor = opts.floor;
        var ceil = Math.max(opts.ceil, floor + opts.step);
        var span = ceil - floor;
        return {
          floor: floor,
          ceil: ceil,
          span: span,
          step: opts.step,
          pending: !!opts.pending,
        };
      }

      function valueToPercent(v, scale) {
        if (scale.span <= 0) return 0;
        var t = (v - scale.floor) / scale.span;
        return Math.max(0, Math.min(100, t * 100));
      }

      function percentToValue(pct, scale, integer) {
        var t = pct / 100;
        var raw = scale.floor + t * scale.span;
        if (integer) return Math.round(raw);
        return raw;
      }

      /** Log10 slider: útil quando min/max positivos e amplitude grande (ex.: preços). */
      function shouldUseLogScale(scale, integer) {
        if (integer || scale.pending) return false;
        if (!(scale.floor > 0 && scale.ceil > 0)) return false;
        return scale.ceil / scale.floor >= 10;
      }

      function valueToPercentLog(v, scale) {
        var lo = Math.log10(scale.floor);
        var hi = Math.log10(scale.ceil);
        var span = hi - lo;
        if (span <= 0) return 0;
        var vc = clamp(v, scale.floor, scale.ceil);
        var u = Math.log10(Math.max(scale.floor, vc));
        var t = (u - lo) / span;
        return Math.max(0, Math.min(100, t * 100));
      }

      function percentToValueLog(pct, scale, integer) {
        var lo = Math.log10(scale.floor);
        var hi = Math.log10(scale.ceil);
        var span = hi - lo;
        var t = pct / 100;
        var u = lo + t * span;
        var raw = Math.pow(10, u);
        raw = clamp(raw, scale.floor, scale.ceil);
        if (integer) return Math.round(raw);
        return raw;
      }

      function valueToPercentMapped(v, scale, integer) {
        return shouldUseLogScale(scale, integer) ? valueToPercentLog(v, scale) : valueToPercent(v, scale);
      }

      function percentToValueMapped(pct, scale, integer) {
        return shouldUseLogScale(scale, integer) ? percentToValueLog(pct, scale, integer) : percentToValue(pct, scale, integer);
      }

      /**
       * Escala em potência no eixo normalizado: pct = 100 * t^exp, t ∈ [0,1].
       * exp ∈ (0,1) dá mais largura do trilho aos valores baixos (ex.: vagas 0–3 com max 10).
       */
      function valueToPercentPower(v, scale, exp) {
        if (!exp || exp <= 0 || exp > 1 || scale.span <= 0) return valueToPercent(v, scale);
        var vc = clamp(v, scale.floor, scale.ceil);
        var t = (vc - scale.floor) / scale.span;
        t = Math.max(0, Math.min(1, t));
        return Math.max(0, Math.min(100, 100 * Math.pow(t, exp)));
      }

      function percentToValuePower(pct, scale, integer, exp) {
        if (!exp || exp <= 0 || exp > 1 || scale.span <= 0) return percentToValue(pct, scale, integer);
        var u = Math.max(0, Math.min(100, pct)) / 100;
        var t = Math.pow(u, 1 / exp);
        var raw = scale.floor + t * scale.span;
        raw = clamp(raw, scale.floor, scale.ceil);
        if (integer) return Math.round(raw);
        return raw;
      }

      function updateDualFill(wrap, lowPct, highPct) {
        var lo = Math.min(lowPct, highPct);
        var hi = Math.max(lowPct, highPct);
        wrap.style.setProperty('--p-low', lo + '%');
        wrap.style.setProperty('--p-high', hi + '%');
      }

      /**
       * @param {HTMLElement} fieldset
       */
      function wireRangeFieldset(fieldset) {
        var key = fieldset.getAttribute('data-range');
        var statName = fieldset.getAttribute('data-stat');
        var minEl = fieldset.querySelector('[id$="_min"]');
        var maxEl = fieldset.querySelector('[id$="_max"]');
        var wrap = fieldset.querySelector('.dual-wrap');
        var rMin = wrap.querySelector('.range-min');
        var rMax = wrap.querySelector('.range-max');
        var refMin = fieldset.querySelector('.data-ref-min');
        var refMax = fieldset.querySelector('.data-ref-max');

        var integer = key === 'q' || key === 'v';

        /**
         * Exponente da curva "spread" (0–1]: menor → mais espaço para valores baixos no trilho.
         * data-slider-spread="off" desliga. data-slider-spread-exponent="0.4" sobrescreve (0,1].
         * Inteiros (quartos/vagas): ligado por padrão.
         */
        function getSliderSpreadExponent(scale) {
          if (scale.pending || scale.span <= 0) return null;
          if (fieldset.getAttribute('data-slider-spread') === 'off') return null;
          var custom = parseFloat(fieldset.getAttribute('data-slider-spread-exponent'));
          if (!isNaN(custom) && custom > 0 && custom <= 1) return custom;
          if (integer) return 0.46;
          if (fieldset.getAttribute('data-slider-spread') === '1') return 0.58;
          return null;
        }

        function valueToSliderPercent(v, scale) {
          if (shouldUseLogScale(scale, integer)) return valueToPercentLog(v, scale);
          var exp = getSliderSpreadExponent(scale);
          if (exp != null) return valueToPercentPower(v, scale, exp);
          return valueToPercent(v, scale);
        }

        function percentToSliderValue(pct, scale) {
          if (shouldUseLogScale(scale, integer)) return percentToValueLog(pct, scale, integer);
          var exp = getSliderSpreadExponent(scale);
          if (exp != null) return percentToValuePower(pct, scale, integer, exp);
          return percentToValue(pct, scale, integer);
        }

        /** Indica escala do trilho (CSS/acessibilidade): log | spread | linear */
        function setScaleModeAttr(scale) {
          if (shouldUseLogScale(scale, integer)) {
            fieldset.setAttribute('data-slider-scale', 'log');
            return;
          }
          if (getSliderSpreadExponent(scale) != null) {
            fieldset.setAttribute('data-slider-scale', 'spread');
            return;
          }
          fieldset.setAttribute('data-slider-scale', 'linear');
        }

        function quantizeLoHi(lo, hi, scale) {
          if (integer) {
            lo = Math.round(lo);
            hi = Math.round(hi);
          } else if (key === 'venda' && !scale.pending) {
            lo = snapVendaInBounds(lo, scale.floor, scale.ceil);
            hi = snapVendaInBounds(hi, scale.floor, scale.ceil);
            var pq = swapIfNeeded(lo, hi);
            lo = pq[0];
            hi = pq[1];
          }
          return [lo, hi];
        }

        function limitsOk() {
          return (
            !!statName &&
            dataBounds[statName] &&
            typeof dataBounds[statName].min === 'number' &&
            typeof dataBounds[statName].max === 'number' &&
            !isNaN(dataBounds[statName].min) &&
            !isNaN(dataBounds[statName].max)
          );
        }

        function setLimitsPendingAttr() {
          fieldset.setAttribute('data-limits-pending', limitsOk() ? '0' : '1');
        }

        /** Escala do trilho = somente [min,max] recebidos do iframe (sem expandir com o filtro). */
        function readScale() {
          if (!limitsOk()) {
            return getScale({
              floor: 0,
              ceil: 1,
              step: integer ? 1 : 1e-6,
              integer: integer,
              pending: true,
            });
          }
          var st = dataBounds[statName];
          var baseLo = st.min;
          var baseHi = st.max;
          var basePair = swapIfNeeded(baseLo, baseHi);
          baseLo = basePair[0];
          baseHi = basePair[1];
          if (integer) {
            baseLo = Math.floor(baseLo);
            baseHi = Math.ceil(baseHi);
          }
          if (baseHi <= baseLo) baseHi = baseLo + (integer ? 1 : 1e-6);
          var step = integer ? 1 : Math.max(1e-9, (baseHi - baseLo) / 1000);
          return getScale({
            floor: baseLo,
            ceil: baseHi,
            step: step,
            integer: integer,
            pending: false,
          });
        }

        function syncSlidersFromNumbers() {
          var scale = readScale();
          var lo = readNumEl(minEl);
          var hi = readNumEl(maxEl);

          if (scale.pending) {
            fieldset.setAttribute('data-slider-scale', 'linear');
            rMin.min = rMax.min = '0';
            rMin.max = rMax.max = '1000';
            rMin.step = rMax.step = '1';
            rMin.value = '0';
            rMax.value = '1000';
            updateDualFill(wrap, 0, 100);
            return;
          }

          if (isNaN(lo)) lo = scale.floor;
          if (isNaN(hi)) hi = scale.ceil;
          var pair = swapIfNeeded(lo, hi);
          lo = clamp(pair[0], scale.floor, scale.ceil);
          hi = clamp(pair[1], scale.floor, scale.ceil);
          pair = quantizeLoHi(lo, hi, scale);
          lo = pair[0];
          hi = pair[1];
          minEl.value = formatPtBRNumber(lo, integer);
          maxEl.value = formatPtBRNumber(hi, integer);

          rMin.min = rMax.min = '0';
          rMin.max = rMax.max = '1000';
          rMin.step = rMax.step = '1';
          setScaleModeAttr(scale);
          var pLo = valueToSliderPercent(lo, scale);
          var pHi = valueToSliderPercent(hi, scale);
          rMin.value = String(Math.round(pLo * 10));
          rMax.value = String(Math.round(pHi * 10));
          updateDualFill(wrap, pLo, pHi);
        }

        function syncNumbersFromSliders() {
          var scale = readScale();
          if (scale.pending) return;
          setScaleModeAttr(scale);
          var pLo = parseFloat(rMin.value) / 10;
          var pHi = parseFloat(rMax.value) / 10;
          if (pLo > pHi) {
            var t = pLo;
            pLo = pHi;
            pHi = t;
            rMin.value = String(Math.round(pLo * 10));
            rMax.value = String(Math.round(pHi * 10));
          }
          var lo = percentToSliderValue(pLo, scale);
          var hi = percentToSliderValue(pHi, scale);
          var pair = swapIfNeeded(lo, hi);
          lo = clamp(pair[0], scale.floor, scale.ceil);
          hi = clamp(pair[1], scale.floor, scale.ceil);
          pair = quantizeLoHi(lo, hi, scale);
          lo = pair[0];
          hi = pair[1];
          minEl.value = formatPtBRNumber(lo, integer);
          maxEl.value = formatPtBRNumber(hi, integer);
          updateDualFill(wrap, pLo, pHi);
        }

        function refreshRealBoundsDisplay() {
          setLimitsPendingAttr();
          if (!statName || !dataBounds[statName]) {
            refMin.textContent = '—';
            refMax.textContent = '—';
            return;
          }
          var st = dataBounds[statName];
          refMin.textContent = formatBound(st.min);
          refMax.textContent = formatBound(st.max);
        }

        function onNumbersInput() {
          var scale = readScale();
          var lo = readNumEl(minEl);
          var hi = readNumEl(maxEl);
          if (!scale.pending && !isNaN(lo) && !isNaN(hi)) {
            lo = clamp(lo, scale.floor, scale.ceil);
            hi = clamp(hi, scale.floor, scale.ceil);
            var pair = swapIfNeeded(lo, hi);
            lo = pair[0];
            hi = pair[1];
            pair = quantizeLoHi(lo, hi, scale);
            lo = pair[0];
            hi = pair[1];
            minEl.value = formatPtBRNumber(lo, integer);
            maxEl.value = formatPtBRNumber(hi, integer);
          } else if (!isNaN(lo) && !isNaN(hi) && lo > hi) {
            minEl.value = formatPtBRNumber(hi, integer);
            maxEl.value = formatPtBRNumber(lo, integer);
          }
          if (!isNaN(readNumEl(minEl)) && !isNaN(readNumEl(maxEl))) syncSlidersFromNumbers();
          scheduleAutoSendFilters();
        }

        function onNumbersBlur() {
          var scale = readScale();
          var lo = readNumEl(minEl);
          var hi = readNumEl(maxEl);
          if (isNaN(lo)) lo = scale.pending ? 0 : scale.floor;
          if (isNaN(hi)) hi = scale.pending ? 1 : scale.ceil;
          if (!scale.pending) {
            lo = clamp(lo, scale.floor, scale.ceil);
            hi = clamp(hi, scale.floor, scale.ceil);
            var pair = swapIfNeeded(lo, hi);
            lo = pair[0];
            hi = pair[1];
            pair = quantizeLoHi(lo, hi, scale);
            lo = pair[0];
            hi = pair[1];
          } else if (integer) {
            lo = Math.round(lo);
            hi = Math.round(hi);
          }
          minEl.value = formatPtBRNumber(lo, integer);
          maxEl.value = formatPtBRNumber(hi, integer);
          syncSlidersFromNumbers();
          scheduleAutoSendFilters();
        }

        minEl.addEventListener('input', onNumbersInput);
        maxEl.addEventListener('input', onNumbersInput);
        minEl.addEventListener('blur', onNumbersBlur);
        maxEl.addEventListener('blur', onNumbersBlur);
        rMin.addEventListener('input', function () {
          syncNumbersFromSliders();
          scheduleAutoSendFilters();
        });
        rMax.addEventListener('input', function () {
          syncNumbersFromSliders();
          scheduleAutoSendFilters();
        });

        fieldset.__refreshBounds = refreshRealBoundsDisplay;
        fieldset.__syncFromData = function () {
          refreshRealBoundsDisplay();
          syncSlidersFromNumbers();
        };

        setLimitsPendingAttr();
        syncSlidersFromNumbers();
        refreshRealBoundsDisplay();
      }

      document.querySelectorAll('fieldset.range-fieldset').forEach(function (fs) {
        wireRangeFieldset(fs);
      });
      applyNegocioVisibility();

      function refreshAllFromDataBounds() {
        document.querySelectorAll('fieldset.range-fieldset').forEach(function (fs) {
          if (typeof fs.__syncFromData === 'function') fs.__syncFromData();
        });
      }

      /** Igual ao mapa (deletaeu.js): aluguel+condomínio só quando aluguel válido. */
      var MAX_ALUGUEL_VALUE_PER_M2 = 250;

      function extractAluguelTotal(imovel) {
        var aluguel = parseFloat(imovel.aluguel || 0);
        var condominio = parseFloat(imovel.condominio || 0);
        var area = parseFloat(imovel.area || 0);
        var valorErrado = condominio > 3 * aluguel || aluguel > area * MAX_ALUGUEL_VALUE_PER_M2;
        if (!aluguel || valorErrado) return null;
        return aluguel + condominio;
      }

      function safeFiniteNum(v) {
        var n = typeof v === 'number' ? v : parseFloat(v);
        return typeof n === 'number' && !isNaN(n) && isFinite(n) ? n : null;
      }

      function extractStatValue(imovel, statKey) {
        if (statKey === 'aluguelTotal') return extractAluguelTotal(imovel);
        if (statKey === 'venda') return safeFiniteNum(imovel.venda);
        if (statKey === 'area') return safeFiniteNum(imovel.area);
        if (statKey === 'quartos') return safeFiniteNum(imovel.quartos);
        if (statKey === 'vagas') return safeFiniteNum(imovel.vagas);
        return null;
      }

      /** Mesmo critério que o mapa (deletaeu.js): inclui só imóveis com aluguel “aceitável” para faixas de total. */
      function filterImoveisValidAluguel(imoveis) {
        if (!imoveis || !imoveis.length) return [];
        return imoveis.filter(function (i) {
          var aluguel = parseFloat(i.aluguel || 0);
          var condominio = parseFloat(i.condominio || 0);
          var area = parseFloat(i.area || 0);
          var valorErrado = condominio > 3 * aluguel || aluguel > area * MAX_ALUGUEL_VALUE_PER_M2;
          return aluguel && !valorErrado;
        });
      }

      function tipoImovelMatches(imovel, tipoSel) {
        if (!tipoSel || tipoSel === 'Todos') return true;
        var raw = imovel && imovel.tipo_imovel != null ? String(imovel.tipo_imovel).trim().toLowerCase() : '';
        return raw === String(tipoSel).trim().toLowerCase();
      }

      /** Base aluguel-válido + opcionalmente Apartamento ou Casa (`imovel.tipo_imovel`). */
      function filterImoveisByTipoSel(imoveis, tipoSel) {
        var base = filterImoveisValidAluguel(imoveis);
        if (!tipoSel || tipoSel === 'Todos') return base;
        var out = [];
        for (var i = 0; i < base.length; i++) {
          if (tipoImovelMatches(base[i], tipoSel)) out.push(base[i]);
        }
        return out;
      }

      function getMinMaxFromImoveis(imoveis, extractor) {
        var min = Infinity;
        var max = -Infinity;
        if (!imoveis || !imoveis.length) {
          return { min: 0, max: 0 };
        }
        for (var i = 0; i < imoveis.length; i++) {
          var val = extractor(imoveis[i]);
          if (val == null || isNaN(val)) continue;
          if (val < min) min = val;
          if (val > max) max = val;
        }
        return {
          min: min === Infinity ? 0 : min,
          max: max === -Infinity ? 0 : max,
        };
      }

      /** Um objeto compatível com applyLimitsPayload / sliders. */
      function limitsPayloadForImoveisList(list) {
        var aluguelTotal = getMinMaxFromImoveis(list, function (i) {
          return parseFloat(i.aluguel || 0) + parseFloat(i.condominio || 0);
        });
        var venda = getMinMaxFromImoveis(list, function (i) {
          return parseFloat(i.venda || 0);
        });
        var area = getMinMaxFromImoveis(list, function (i) {
          return parseFloat(i.area);
        });
        var quartos = getMinMaxFromImoveis(list, function (i) {
          return parseFloat(i.quartos);
        });
        var vagas = getMinMaxFromImoveis(list, function (i) {
          return parseFloat(i.vagas);
        });
        return {
          aluguelTotal: aluguelTotal,
          venda: venda,
          area: area,
          quartos: quartos,
          vagas: vagas,
        };
      }

      /** Min/max de todas as dimensões para Todos, Apartamento e Casa (lista completa do iframe). */
      function computeLimitsByTipo(imoveis) {
        return {
          Todos: limitsPayloadForImoveisList(filterImoveisByTipoSel(imoveis, 'Todos')),
          Apartamento: limitsPayloadForImoveisList(filterImoveisByTipoSel(imoveis, 'Apartamento')),
          Casa: limitsPayloadForImoveisList(filterImoveisByTipoSel(imoveis, 'Casa')),
        };
      }

      function minMaxFromValues(vals) {
        var min = Infinity;
        var max = -Infinity;
        for (var i = 0; i < vals.length; i++) {
          var v = vals[i];
          if (v == null || isNaN(v)) continue;
          if (v < min) min = v;
          if (v > max) max = v;
        }
        if (min === Infinity) return null;
        if (max <= min) max = min + (Number.isInteger(min) && Number.isInteger(max) ? 1 : 1e-6);
        return { min: min, max: max };
      }

      /**
       * Especificação de bins: contínuos = faixas iguais em [lo,hi];
       * inteiros = um bin por valor inteiro quando couber, senão agrupa inteiros inteiros (groupSize).
       */
      function buildHistogramSpec(lo, hi, nMaxBins, asInteger) {
        if (!(nMaxBins > 0) || hi <= lo) return null;
        if (!asInteger) {
          return { kind: 'continuous', nBins: nMaxBins, lo: lo, hi: hi };
        }
        var loI = Math.floor(lo);
        var hiI = Math.ceil(hi);
        if (hiI <= loI) hiI = loI + 1;
        var span = hiI - loI + 1;
        if (span <= nMaxBins) {
          return { kind: 'integer', nBins: span, loI: loI, hiI: hiI, groupSize: 1 };
        }
        var groupSize = Math.ceil(span / nMaxBins);
        var nBins = Math.ceil(span / groupSize);
        if (nBins > nMaxBins) nBins = nMaxBins;
        return { kind: 'integer', nBins: nBins, loI: loI, hiI: hiI, groupSize: groupSize };
      }

      /** Índice 0..spec.nBins-1 ou -1 se fora da faixa. */
      function histogramBinIndex(value, spec) {
        if (!spec || !(spec.nBins > 0)) return -1;
        if (spec.kind === 'continuous') {
          var v = value;
          if (v < spec.lo || v > spec.hi) return -1;
          var t = (v - spec.lo) / (spec.hi - spec.lo);
          var idx = Math.floor(t * spec.nBins);
          if (idx >= spec.nBins) idx = spec.nBins - 1;
          if (idx < 0) idx = 0;
          return idx;
        }
        var vi = Math.round(value);
        if (vi < spec.loI || vi > spec.hiI) return -1;
        var gs = spec.groupSize > 1 ? spec.groupSize : 1;
        var j = Math.floor((vi - spec.loI) / gs);
        if (j >= spec.nBins) j = spec.nBins - 1;
        if (j < 0) j = 0;
        return j;
      }

      function boundsForHistogram(statKey, values, asInteger) {
        var st = dataBounds[statKey];
        var mm = null;
        if (
          st &&
          typeof st.min === 'number' &&
          typeof st.max === 'number' &&
          !isNaN(st.min) &&
          !isNaN(st.max) &&
          st.max > st.min
        ) {
          mm = { min: st.min, max: st.max };
        } else {
          mm = minMaxFromValues(values);
          if (!mm) return null;
        }
        if (asInteger) {
          mm.min = Math.floor(mm.min);
          mm.max = Math.ceil(mm.max);
          if (mm.max <= mm.min) mm.max = mm.min + 1;
        }
        return mm;
      }

      var HIST_BIN_COUNT = 80;
      /** Altura mínima (% da linha) para bins com count ≥ 1 — escala visual é log(count). */
      var HIST_MIN_HEIGHT_PCT = 5;

      /**
       * Altura em % usando escala logarítmica em count (log ↔ [minPct, 100]).
       * count 0 → 0%; count ≥ 1 → entre HIST_MIN_HEIGHT_PCT e 100%.
       */
      function histogramBarHeightPct(count, maxCount) {
        var c = count;
        if (!(c > 0)) return 0;
        if (!(maxCount > 0)) return HIST_MIN_HEIGHT_PCT;
        if (maxCount <= 1) return 100;
        var logC = Math.log(c);
        var logMax = Math.log(maxCount);
        var logOne = Math.log(1);
        var t = (logC - logOne) / (logMax - logOne);
        if (t < 0) t = 0;
        if (t > 1) t = 1;
        return HIST_MIN_HEIGHT_PCT + t * (100 - HIST_MIN_HEIGHT_PCT);
      }

      function renderHistogramRow(histRow, counts, maxCount) {
        if (!histRow) return;
        histRow.innerHTML = '';
        for (var b = 0; b < counts.length; b++) {
          var bin = document.createElement('div');
          bin.className = 'hist-bin';
          var fill = document.createElement('div');
          fill.className = 'hist-fill';
          var c = counts[b];
          var h = histogramBarHeightPct(c, maxCount);
          if (c <= 0) {
            fill.setAttribute('data-empty', '1');
            fill.style.height = '0';
          } else {
            fill.removeAttribute('data-empty');
            fill.style.height = h + '%';
          }
          bin.appendChild(fill);
          histRow.appendChild(bin);
        }
      }

      /**
       * Preenche os mini-histogramas acima de cada slider com contagem por faixa,
       * usando o mesmo [min,max] dos limites (dataBounds) quando existir, senão o min/max dos dados.
       */
      function updateHistogramsFromImoveis(imoveis) {
        if (!imoveis || !imoveis.length) {
          document.querySelectorAll('fieldset.range-fieldset .hist-row').forEach(function (row) {
            renderHistogramRow(row, new Array(HIST_BIN_COUNT).fill(0), 0);
          });
          return;
        }

        document.querySelectorAll('fieldset.range-fieldset').forEach(function (fs) {
          var statKey = fs.getAttribute('data-stat');
          if (!statKey) return;
          var asInt = statKey === 'quartos' || statKey === 'vagas';
          var histRow = fs.querySelector('.hist-row');
          var values = [];
          for (var j = 0; j < imoveis.length; j++) {
            var x = extractStatValue(imoveis[j], statKey);
            if (x != null && !isNaN(x)) values.push(asInt ? Math.round(x) : x);
          }
          var bounds = boundsForHistogram(statKey, values, asInt);
          if (!bounds) {
            renderHistogramRow(histRow, new Array(HIST_BIN_COUNT).fill(0), 0);
            return;
          }
          var lo = bounds.min;
          var hi = bounds.max;
          var spec = buildHistogramSpec(lo, hi, HIST_BIN_COUNT, asInt);
          if (!spec) {
            renderHistogramRow(histRow, new Array(HIST_BIN_COUNT).fill(0), 0);
            return;
          }
          var counts = new Array(spec.nBins);
          for (var z = 0; z < spec.nBins; z++) counts[z] = 0;
          for (var k = 0; k < values.length; k++) {
            var idx = histogramBinIndex(values[k], spec);
            if (idx >= 0) counts[idx]++;
          }
          var maxCount = 0;
          for (var m = 0; m < counts.length; m++) {
            if (counts[m] > maxCount) maxCount = counts[m];
          }
          renderHistogramRow(histRow, counts, maxCount);
        });
      }

      /**
       * Atualiza dataBounds, campos Mín/Máx, faixa de referência e sliders a partir de um objeto
       * com chaves aluguelTotal, venda, area, quartos, vagas (cada uma { min, max }).
       * Usado pelo MappiaIO (mesmo fluxo que antes era window.postMessage imoveis-to-parent).
       */
      function applyLimitsPayload(src, reason) {
        if (!src || typeof src !== 'object') return;

        function ingestBound(key) {
          var b = src[key];
          if (b && typeof b.min === 'number' && typeof b.max === 'number') {
            dataBounds[key] = { min: b.min, max: b.max };
          }
        }

        ingestBound('aluguelTotal');
        ingestBound('venda');
        ingestBound('area');
        ingestBound('quartos');
        ingestBound('vagas');

        statsEl.textContent =
          'limits (' +
          (reason || 'iframe') +
          '):' +
          '\naluguelTotal: ' +
          JSON.stringify(src.aluguelTotal, null, 2) +
          '\nvenda: ' +
          JSON.stringify(src.venda, null, 2) +
          '\narea: ' +
          JSON.stringify(src.area, null, 2) +
          '\nquartos: ' +
          JSON.stringify(src.quartos, null, 2) +
          '\nvagas: ' +
          JSON.stringify(src.vagas, null, 2);
        if (lastLimitsByTipo) {
          statsEl.textContent +=
            '\n\nlimits por tipo (Todos / Apartamento / Casa):\n' +
            JSON.stringify(lastLimitsByTipo, null, 2);
        }

        function setPairIfBound(key, idLo, idHi, asInt) {
          var b = src[key];
          if (b && typeof b.min === 'number' && typeof b.max === 'number') {
            var lo = b.min;
            var hi = b.max;
            if (key === 'venda') {
              lo = snapVendaInBounds(b.min, b.min, b.max);
              hi = snapVendaInBounds(b.max, b.min, b.max);
            }
            document.getElementById(idLo).value = formatPtBRNumber(lo, asInt);
            document.getElementById(idHi).value = formatPtBRNumber(hi, asInt);
          }
        }

        setPairIfBound('aluguelTotal', 'aluguel_min', 'aluguel_max', false);
        setPairIfBound('venda', 'venda_min', 'venda_max', false);
        setPairIfBound('area', 'area_min', 'area_max', false);
        setPairIfBound('quartos', 'q_min', 'q_max', true);
        setPairIfBound('vagas', 'v_min', 'v_max', true);

        refreshAllFromDataBounds();
        sendFiltersToIframe();
        log('limites aplicados: ' + (reason || ''));
      }

      /** @type {ReturnType<typeof MappiaIO> | null} */
      var mappia = null;
      if (typeof MappiaIO === 'function') {
        mappia = new MappiaIO('mappia', true);
        mappia.addOnMessageCallback(function (msg) {
          log('MappiaIO rx: ' + JSON.stringify(msg).slice(0, 200));
          if (!msg || typeof msg !== 'object') return;

          if (msg.imoveis && Array.isArray(msg.imoveis)) {
            completeImoveisLoading('imoveis');
            lastImoveisBatch = msg.imoveis;
            setBairroCatalog(msg.imoveis);
            lastLimitsByTipo = computeLimitsByTipo(msg.imoveis);
            var tipoSelEl = document.getElementById('tipo_imovel');
            var tipoSel = tipoSelEl && tipoSelEl.value ? tipoSelEl.value : 'Todos';
            var limActive = lastLimitsByTipo[tipoSel] || lastLimitsByTipo.Todos;
            applyLimitsPayload(limActive, 'MappiaIO.imoveis');
            updateHistogramsFromImoveis(filterImoveisByTipoSel(msg.imoveis, tipoSel));
          }

          if (
            msg.inputs &&
            typeof msg.inputs === 'object' &&
            !(msg.imoveis && Array.isArray(msg.imoveis))
          ) {
            var keys = ['aluguelTotal', 'venda', 'area', 'quartos', 'vagas'];
            var hasIn = false;
            for (var ki = 0; ki < keys.length; ki++) {
              var bIn = msg.inputs[keys[ki]];
              if (bIn && typeof bIn.min === 'number' && typeof bIn.max === 'number') {
                hasIn = true;
                break;
              }
            }
            if (hasIn) {
              lastLimitsByTipo = null;
              applyLimitsPayload(msg.inputs, 'MappiaIO.inputs');
            }
          }
        });
        mappia.addReadyCallback(function () {
          log('MappiaIO: iframe pronto');
        });
      } else {
        log('ERRO: MappiaIO não carregou (ver script mappia_io.js).');
      }

      /**
       * Mesma lógica que filterPairForPost, sem escrever nos inputs (para contagem / tooltip).
       */
      function readFilterPairNoWrite(statKey, idLo, idHi, asInteger) {
        var lo = num(idLo);
        var hi = num(idHi);
        var p = swapIfNeeded(lo, hi);
        lo = p[0];
        hi = p[1];
        var st = dataBounds[statKey];
        if (st && typeof st.min === 'number' && typeof st.max === 'number') {
          lo = clamp(lo, st.min, st.max);
          hi = clamp(hi, st.min, st.max);
          p = swapIfNeeded(lo, hi);
          lo = p[0];
          hi = p[1];
        }
        if (asInteger) {
          lo = Math.round(lo);
          hi = Math.round(hi);
        } else if (statKey === 'venda') {
          if (st && typeof st.min === 'number' && typeof st.max === 'number') {
            lo = snapVendaInBounds(lo, st.min, st.max);
            hi = snapVendaInBounds(hi, st.min, st.max);
          } else {
            lo = snapVendaPrice(lo);
            hi = snapVendaPrice(hi);
          }
          p = swapIfNeeded(lo, hi);
          lo = p[0];
          hi = p[1];
        }
        return [lo, hi];
      }

      /**
       * Lê par min/max, ordena e limita aos bounds do iframe quando existirem.
       * @param {string} statKey - chave em dataBounds (ex.: aluguelTotal)
       * @param {string} idLo
       * @param {string} idHi
       * @param {boolean} [asInteger]
       * @returns {[number, number]}
       */
      function filterPairForPost(statKey, idLo, idHi, asInteger) {
        var pair = readFilterPairNoWrite(statKey, idLo, idHi, asInteger);
        document.getElementById(idLo).value = formatPtBRNumber(pair[0], asInteger);
        document.getElementById(idHi).value = formatPtBRNumber(pair[1], asInteger);
        return pair;
      }

      /**
       * Intervalo amplo (min..max dos dados) sem alterar inputs — para dimensões ocultas no modo Aluguel/Compra.
       * @param {string} statKey
       * @param {boolean} asInteger
       * @returns {[number, number]}
       */
      function fullRangePair(statKey, asInteger) {
        var st = dataBounds[statKey];
        if (st && typeof st.min === 'number' && typeof st.max === 'number') {
          var lo = st.min;
          var hi = st.max;
          var p = swapIfNeeded(lo, hi);
          lo = p[0];
          hi = p[1];
          if (asInteger) {
            lo = Math.round(lo);
            hi = Math.round(hi);
          } else if (statKey === 'venda') {
            lo = snapVendaInBounds(lo, st.min, st.max);
            hi = snapVendaInBounds(hi, st.min, st.max);
            p = swapIfNeeded(lo, hi);
            lo = p[0];
            hi = p[1];
          }
          return [lo, hi];
        }
        if (statKey === 'aluguelTotal' || statKey === 'venda') {
          return asInteger ? [0, 0] : [0, 1e15];
        }
        if (statKey === 'area') return asInteger ? [0, 1] : [0, 1e9];
        if (statKey === 'quartos' || statKey === 'vagas') return [0, 99];
        return asInteger ? [0, 999999] : [0, 1e15];
      }

      function getEffectiveFilterPairs() {
        var neg = getNegocio();
        var aluguelPair =
          neg === 'aluguel'
            ? readFilterPairNoWrite('aluguelTotal', 'aluguel_min', 'aluguel_max', false)
            : fullRangePair('aluguelTotal', false);
        var vendaPair =
          neg === 'compra'
            ? readFilterPairNoWrite('venda', 'venda_min', 'venda_max', false)
            : fullRangePair('venda', false);
        return {
          neg: neg,
          aluguel_total: aluguelPair,
          venda: vendaPair,
          area: readFilterPairNoWrite('area', 'area_min', 'area_max', false),
          quartos: readFilterPairNoWrite('quartos', 'q_min', 'q_max', true),
          vagas: readFilterPairNoWrite('vagas', 'v_min', 'v_max', true),
        };
      }

      /** Quantos imóveis satisfazem o mesmo intervalo enviado ao iframe (negócio + faixas). */
      function countMatchingImoveis(imoveis) {
        if (!imoveis || !imoveis.length) return 0;
        var pairs = getEffectiveFilterPairs();
        var neg = pairs.neg;
        var aluguelRange = pairs.aluguel_total;
        var vendaRange = pairs.venda;
        var areaRange = pairs.area;
        var quartosRange = pairs.quartos;
        var vagasRange = pairs.vagas;
        var count = 0;

        for (var i = 0; i < imoveis.length; i++) {
          var im = imoveis[i];
          if (neg === 'aluguel') {
            var at = extractAluguelTotal(im);
            if (at == null || isNaN(at)) continue;
            if (at < aluguelRange[0] || at > aluguelRange[1]) continue;
          } else {
            var vend = safeFiniteNum(im.venda);
            if (vend == null) continue;
            if (vend < vendaRange[0] || vend > vendaRange[1]) continue;
          }

          var ar = safeFiniteNum(im.area);
          if (ar == null || ar < areaRange[0] || ar > areaRange[1]) continue;

          var q = safeFiniteNum(im.quartos);
          if (q == null) continue;
          q = Math.round(q);
          if (q < quartosRange[0] || q > quartosRange[1]) continue;

          var vg = safeFiniteNum(im.vagas);
          if (vg == null) continue;
          vg = Math.round(vg);
          if (vg < vagasRange[0] || vg > vagasRange[1]) continue;

          if (!imovelMatchesTextFilter(im, str('text_filter'))) continue;

          count++;
        }
        return count;
      }

      function ensureSliderMatchTooltip(wrap) {
        var tip = wrap.querySelector('.slider-match-tooltip');
        if (!tip) {
          tip = document.createElement('div');
          tip.className = 'slider-match-tooltip';
          tip.setAttribute('role', 'tooltip');
          wrap.appendChild(tip);
        }
        return tip;
      }

      function updateSliderMatchTooltip(wrap) {
        if (!wrap) return;
        var tip = ensureSliderMatchTooltip(wrap);
        if (!lastImoveisBatch || !lastImoveisBatch.length) {
          tip.textContent = 'Sem lista do mapa';
          tip.classList.add('is-visible');
          scheduleSliderTooltipHide(wrap, tip);
          return;
        }
        var c = countMatchingImoveis(lastImoveisBatch);
        tip.textContent =
          c === 0 ? '0 imóveis' : c === 1 ? '1 imóvel' : c.toLocaleString('pt-BR') + ' imóveis';
        tip.classList.add('is-visible');
        scheduleSliderTooltipHide(wrap, tip);
      }

      function dualWrapFromRangeControl(el) {
        if (!el || !el.closest) return null;
        var wrap = el.closest('.dual-wrap');
        if (wrap) return wrap;
        var fs = el.closest('fieldset.range-fieldset');
        return fs ? fs.querySelector('.dual-wrap') : null;
      }

      function sendFiltersToIframe() {
        document.querySelectorAll('fieldset.range-fieldset').forEach(function (fs) {
          if (fs.classList.contains('fs-hidden')) return;
          var minEl = fs.querySelector('[id$="_min"]');
          var maxEl = fs.querySelector('[id$="_max"]');
          if (!minEl || !maxEl) return;
          var lo = readNumEl(minEl);
          var hi = readNumEl(maxEl);
          var dr = fs.getAttribute('data-range');
          var intRg = dr === 'q' || dr === 'v';
          if (!isNaN(lo) && !isNaN(hi) && lo > hi) {
            var t = lo;
            lo = hi;
            hi = t;
            minEl.value = formatPtBRNumber(lo, intRg);
            maxEl.value = formatPtBRNumber(hi, intRg);
          }
        });

        var neg = getNegocio();
        var aluguelPair =
          neg === 'aluguel'
            ? filterPairForPost('aluguelTotal', 'aluguel_min', 'aluguel_max', false)
            : fullRangePair('aluguelTotal', false);
        var vendaPair =
          neg === 'compra'
            ? filterPairForPost('venda', 'venda_min', 'venda_max', false)
            : fullRangePair('venda', false);

        var payload = {
          source: 'imoveis-parent-filters',
          tipo_negocio: neg,
          aluguel_total: aluguelPair,
          venda: vendaPair,
          area_imovel: filterPairForPost('area', 'area_min', 'area_max', false),
          qnt_quartos: filterPairForPost('quartos', 'q_min', 'q_max', true),
          qnt_vagas: filterPairForPost('vagas', 'v_min', 'v_max', true),
          dias_anuncio: num('dias_anuncio'),
          text_filter: str('text_filter'),
          tipo_imovel: str('tipo_imovel'),
        };
        try {
          if (mappia && typeof mappia.send === 'function') {
            mappia.send(payload);
            log('MappiaIO.send → iframe (filtros)');
          } else {
            iframeEl.contentWindow.postMessage(payload, MAP_ORIGIN);
            log('fallback postMessage → iframe (filtros)');
          }
        } catch (e) {
          log('envio de filtros falhou: ' + e);
        }
      }

      document.getElementById('btn_send_iframe').addEventListener('click', sendFiltersToIframe);

      var asidePanel = document.querySelector('aside');
      if (asidePanel) {
        asidePanel.addEventListener(
          'input',
          function (e) {
            var wrap = dualWrapFromRangeControl(e.target);
            if (wrap) updateSliderMatchTooltip(wrap);
          },
          true
        );
      }

      initBairroCombobox();

      var diasAnuncioFilterEl = document.getElementById('dias_anuncio');
      if (diasAnuncioFilterEl) {
        diasAnuncioFilterEl.addEventListener('input', scheduleAutoSendFilters);
      }
      if (diasAnuncioFilterEl) {
        diasAnuncioFilterEl.addEventListener('blur', function () {
          var v = parsePtBRNumber(diasAnuncioFilterEl.value);
          if (!isNaN(v)) diasAnuncioFilterEl.value = formatPtBRNumber(Math.round(v), true);
        });
      }
      var tipoEl = document.getElementById('tipo_imovel');
      if (tipoEl) {
        tipoEl.addEventListener('change', function () {
          if (lastLimitsByTipo && lastImoveisBatch && lastImoveisBatch.length) {
            var sel = tipoEl.value || 'Todos';
            var lim = lastLimitsByTipo[sel] || lastLimitsByTipo.Todos;
            applyLimitsPayload(lim, 'tipo:' + sel);
            updateHistogramsFromImoveis(filterImoveisByTipoSel(lastImoveisBatch, sel));
          } else {
            scheduleAutoSendFilters();
          }
        });
      }

      document.querySelectorAll('input[name="tipo_negocio"]').forEach(function (r) {
        r.addEventListener('change', function () {
          applyNegocioVisibility();
          scheduleAutoSendFilters();
          document.querySelectorAll('fieldset.range-fieldset:not(.fs-hidden) .dual-wrap').forEach(function (w) {
            updateSliderMatchTooltip(w);
          });
        });
      });

      document.getElementById('btn_apply_query').addEventListener('click', function () {
        var blob = document.getElementById('query_blob').value.trim();
        if (!mappia) {
          log('MappiaIO indisponível');
          return;
        }
        if (!blob) {
          log('Preencha a query no textarea ou use só “Enviar filtros ao iframe”.');
          return;
        }
        mappia.applyQuery(blob);
        log('applyQuery enviado (' + blob.length + ' chars)');
      });
    })();
  </script>
</body>
</html>
