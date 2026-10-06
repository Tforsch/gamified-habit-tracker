import json
import os

with open("parfyme_bot/perfumes_data.json", "r", encoding="utf-8") as f:
    db = json.load(f)

brands_json = json.dumps(db["brands"], ensure_ascii=False)
perfumes_json = json.dumps(db["perfumes"], ensure_ascii=False)

html_template = '''<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <title>L'ÉLIXIR ROYAL — Селективна Парфумерія</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600;700;800&family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-primary: #03140e;
      --bg-secondary: #072218;
      --bg-card: #0a2b1f;
      --bg-card-hover: #0f3729;
      --gold-primary: #d4af37;
      --gold-light: #f7df8b;
      --gold-dark: #9e7a20;
      --gold-gradient: linear-gradient(135deg, #f7df8b 0%, #d4af37 50%, #9e7a20 100%);
      --gold-text-grad: linear-gradient(135deg, #fff2c6 0%, #d4af37 60%, #b28828 100%);
      --emerald-glow: rgba(16, 185, 129, 0.15);
      --gold-glow: rgba(212, 175, 55, 0.25);
      --border-gold: rgba(212, 175, 55, 0.28);
      --border-gold-bright: rgba(212, 175, 55, 0.65);
      --text-main: #f0fdf4;
      --text-muted: #94a3b8;
      --text-gold: #e2c158;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
      user-select: none;
    }

    body {
      font-family: 'Inter', sans-serif;
      background: radial-gradient(circle at 50% 0%, #0d3829 0%, #03140e 70%, #020b08 100%);
      color: var(--text-main);
      min-height: 100vh;
      overflow-x: hidden;
      padding-bottom: 90px;
    }

    /* Luxury Scrollbar */
    ::-webkit-scrollbar {
      width: 4px;
      height: 4px;
    }
    ::-webkit-scrollbar-track {
      background: #020c08;
    }
    ::-webkit-scrollbar-thumb {
      background: var(--gold-dark);
      border-radius: 4px;
    }

    .font-serif {
      font-family: 'Cinzel', 'Cormorant Garamond', serif;
    }

    .gold-gradient-text {
      background: var(--gold-text-grad);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      display: inline-block;
    }

    /* Top Brand Header */
    .app-header {
      position: sticky;
      top: 0;
      z-index: 50;
      background: rgba(3, 20, 14, 0.88);
      backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--border-gold);
      padding: 12px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .brand-logo {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .crown-icon {
      width: 34px;
      height: 34px;
      background: var(--gold-gradient);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #03140e;
      font-size: 17px;
      box-shadow: 0 0 15px var(--gold-glow);
    }

    .brand-title {
      font-family: 'Cinzel', serif;
      font-size: 16px;
      font-weight: 700;
      letter-spacing: 2px;
    }

    .brand-subtitle {
      font-size: 10px;
      color: var(--text-gold);
      letter-spacing: 1.5px;
      text-transform: uppercase;
    }

    .cart-btn-header {
      background: rgba(212, 175, 55, 0.12);
      border: 1px solid var(--border-gold);
      color: var(--gold-light);
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 13px;
      display: flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .cart-btn-header:active {
      transform: scale(0.96);
      background: rgba(212, 175, 55, 0.25);
    }

    .cart-badge {
      background: var(--gold-gradient);
      color: #03140e;
      font-weight: 700;
      font-size: 11px;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    /* Tab Switcher */
    .tab-bar {
      display: flex;
      gap: 8px;
      padding: 10px 16px;
      overflow-x: auto;
      scrollbar-width: none;
      background: rgba(7, 34, 24, 0.5);
      border-bottom: 1px solid rgba(212, 175, 55, 0.15);
    }
    .tab-bar::-webkit-scrollbar {
      display: none;
    }

    .tab-btn {
      padding: 8px 16px;
      border-radius: 24px;
      font-size: 13px;
      font-weight: 500;
      white-space: nowrap;
      background: rgba(10, 43, 31, 0.6);
      border: 1px solid var(--border-gold);
      color: var(--text-muted);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.25s ease;
    }

    .tab-btn.active {
      background: var(--gold-gradient);
      color: #03140e;
      font-weight: 700;
      border-color: var(--gold-light);
      box-shadow: 0 4px 15px var(--gold-glow);
    }

    /* Main Container */
    .main-content {
      padding: 16px;
      max-width: 900px;
      margin: 0 auto;
    }

    /* Volume Selector Bar (Розпив vs Флакон) */
    .mode-bar {
      background: rgba(10, 43, 31, 0.7);
      border: 1px solid var(--border-gold);
      border-radius: 16px;
      padding: 12px;
      margin-bottom: 16px;
      backdrop-filter: blur(10px);
    }

    .mode-title {
      font-size: 11px;
      color: var(--text-gold);
      letter-spacing: 1.2px;
      text-transform: uppercase;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .volume-chips {
      display: flex;
      gap: 6px;
      overflow-x: auto;
      scrollbar-width: none;
    }
    .volume-chips::-webkit-scrollbar {
      display: none;
    }

    .vol-chip {
      flex: 1;
      min-width: 60px;
      text-align: center;
      padding: 8px 6px;
      border-radius: 10px;
      font-size: 12px;
      font-weight: 600;
      background: rgba(3, 20, 14, 0.6);
      border: 1px solid rgba(212, 175, 55, 0.2);
      color: var(--text-main);
      cursor: pointer;
      transition: all 0.2s;
    }

    .vol-chip.active {
      background: var(--gold-gradient);
      color: #03140e;
      border-color: var(--gold-light);
      box-shadow: 0 2px 10px var(--gold-glow);
    }

    /* Search & Filter */
    .search-bar {
      position: relative;
      margin-bottom: 14px;
    }

    .search-input {
      width: 100%;
      padding: 12px 16px 12px 42px;
      border-radius: 14px;
      background: rgba(10, 43, 31, 0.6);
      border: 1px solid var(--border-gold);
      color: var(--text-main);
      font-size: 14px;
      outline: none;
      transition: all 0.2s;
    }

    .search-input:focus {
      border-color: var(--gold-light);
      box-shadow: 0 0 12px var(--gold-glow);
    }

    .search-icon {
      position: absolute;
      left: 14px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--gold-primary);
      font-size: 16px;
    }

    /* Brand Horizontal List */
    .filter-scroll {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      scrollbar-width: none;
      margin-bottom: 16px;
      padding-bottom: 4px;
    }
    .filter-scroll::-webkit-scrollbar {
      display: none;
    }

    .filter-pill {
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 12px;
      white-space: nowrap;
      background: rgba(7, 34, 24, 0.8);
      border: 1px solid rgba(212, 175, 55, 0.2);
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.2s;
    }

    .filter-pill.active {
      background: rgba(212, 175, 55, 0.22);
      color: var(--gold-light);
      border-color: var(--gold-primary);
      font-weight: 600;
    }

    /* Perfume Grid */
    .perfumes-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
    }

    @media (min-width: 640px) {
      .perfumes-grid {
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
      }
    }

    .perfume-card {
      background: var(--bg-card);
      border: 1px solid var(--border-gold);
      border-radius: 16px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      position: relative;
      transition: transform 0.2s, box-shadow 0.2s;
      cursor: pointer;
    }

    .perfume-card:active {
      transform: scale(0.98);
    }

    .card-img-wrap {
      position: relative;
      width: 100%;
      padding-top: 100%;
      background: #020c08;
      overflow: hidden;
    }

    .card-img {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.4s ease;
    }

    .perfume-card:hover .card-img {
      transform: scale(1.06);
    }

    .card-badge-vibe {
      position: absolute;
      top: 8px;
      right: 8px;
      background: rgba(3, 20, 14, 0.75);
      border: 1px solid var(--border-gold);
      border-radius: 12px;
      padding: 3px 8px;
      font-size: 10px;
      color: var(--gold-light);
      backdrop-filter: blur(8px);
    }

    .card-body {
      padding: 12px;
      display: flex;
      flex-direction: column;
      flex: 1;
      justify-content: space-between;
    }

    .card-brand {
      font-size: 10px;
      letter-spacing: 1.2px;
      text-transform: uppercase;
      color: var(--text-gold);
      font-weight: 600;
      margin-bottom: 2px;
    }

    .card-name {
      font-family: 'Cinzel', serif;
      font-size: 13px;
      font-weight: 700;
      color: #fff;
      line-height: 1.3;
      margin-bottom: 6px;
      display: -webkit-box;
      -webkit-line-clamp: 1;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .card-notes {
      font-size: 11px;
      color: #94a3b8;
      line-height: 1.3;
      margin-bottom: 10px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .card-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: auto;
      padding-top: 8px;
      border-top: 1px solid rgba(212, 175, 55, 0.15);
    }

    .card-price {
      font-family: 'Cinzel', serif;
      font-size: 14px;
      font-weight: 700;
      color: var(--gold-light);
    }

    .card-add-btn {
      background: var(--gold-gradient);
      border: none;
      color: #03140e;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      font-weight: 800;
      font-size: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 2px 8px var(--gold-glow);
      transition: transform 0.15s;
    }

    .card-add-btn:active {
      transform: scale(0.9);
    }

    /* Aroma Box Builder Section */
    .aroma-box-container {
      background: linear-gradient(180deg, #0a2d20 0%, #061a13 100%);
      border: 1px solid var(--border-gold-bright);
      border-radius: 20px;
      padding: 20px 16px;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4), 0 0 20px var(--gold-glow);
      margin-bottom: 20px;
    }

    .aroma-box-header {
      text-align: center;
      margin-bottom: 18px;
    }

    .aroma-box-title {
      font-family: 'Cinzel', serif;
      font-size: 20px;
      font-weight: 700;
      color: var(--gold-light);
      margin-bottom: 6px;
      letter-spacing: 1px;
    }

    .aroma-discount-badge {
      display: inline-block;
      background: var(--gold-gradient);
      color: #03140e;
      font-weight: 800;
      font-size: 11px;
      padding: 3px 10px;
      border-radius: 12px;
      letter-spacing: 1px;
      text-transform: uppercase;
      margin-bottom: 8px;
    }

    .aroma-slots-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin-bottom: 20px;
    }

    .aroma-slot {
      background: rgba(3, 20, 14, 0.7);
      border: 1.5px dashed var(--border-gold);
      border-radius: 14px;
      min-height: 125px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 8px;
      text-align: center;
      cursor: pointer;
      position: relative;
      transition: all 0.2s;
    }

    .aroma-slot.filled {
      border-style: solid;
      border-color: var(--gold-primary);
      background: #09271c;
      box-shadow: 0 4px 15px rgba(212, 175, 55, 0.15);
    }

    .slot-num {
      font-family: 'Cinzel', serif;
      font-size: 11px;
      color: var(--text-gold);
      margin-bottom: 4px;
    }

    .slot-icon {
      font-size: 24px;
      color: var(--gold-primary);
      margin-bottom: 4px;
    }

    .slot-placeholder-text {
      font-size: 10px;
      color: var(--text-muted);
      line-height: 1.2;
    }

    .slot-filled-name {
      font-size: 11px;
      font-weight: 600;
      color: #fff;
      line-height: 1.2;
      margin-top: 4px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .slot-remove-btn {
      position: absolute;
      top: 4px;
      right: 4px;
      background: rgba(239, 68, 68, 0.85);
      color: #fff;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      border: none;
      font-size: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
    }

    .aroma-summary {
      background: rgba(3, 20, 14, 0.8);
      border: 1px solid var(--border-gold);
      border-radius: 12px;
      padding: 12px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .aroma-summary-text {
      font-size: 12px;
      color: var(--text-muted);
    }

    .aroma-final-price {
      font-family: 'Cinzel', serif;
      font-size: 18px;
      font-weight: 700;
      color: var(--gold-light);
    }

    .luxury-gold-btn {
      width: 100%;
      background: var(--gold-gradient);
      border: none;
      color: #03140e;
      font-family: 'Cinzel', serif;
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 1.5px;
      padding: 14px;
      border-radius: 14px;
      cursor: pointer;
      box-shadow: 0 4px 20px var(--gold-glow);
      transition: all 0.2s;
      text-transform: uppercase;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }

    .luxury-gold-btn:disabled {
      opacity: 0.45;
      cursor: not-allowed;
      box-shadow: none;
    }

    .luxury-gold-btn:active:not(:disabled) {
      transform: scale(0.98);
      filter: brightness(1.1);
    }

    /* Sommelier Section */
    .sommelier-card {
      background: linear-gradient(180deg, #092c1f 0%, #051912 100%);
      border: 1px solid var(--border-gold-bright);
      border-radius: 20px;
      padding: 24px 18px;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
    }

    .quiz-step-title {
      font-family: 'Cinzel', serif;
      font-size: 17px;
      color: var(--gold-light);
      margin-bottom: 6px;
      text-align: center;
    }

    .quiz-step-subtitle {
      font-size: 12px;
      color: var(--text-muted);
      text-align: center;
      margin-bottom: 18px;
    }

    .quiz-options-grid {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-bottom: 20px;
    }

    .quiz-option-btn {
      background: rgba(3, 20, 14, 0.65);
      border: 1px solid var(--border-gold);
      border-radius: 14px;
      padding: 14px 16px;
      color: var(--text-main);
      font-size: 14px;
      font-weight: 500;
      text-align: left;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
      transition: all 0.2s;
    }

    .quiz-option-btn:active {
      background: rgba(212, 175, 55, 0.2);
      border-color: var(--gold-light);
    }

    /* Modal / Drawer */
    .modal-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(2, 11, 8, 0.82);
      backdrop-filter: blur(12px);
      z-index: 100;
      display: none;
      align-items: flex-end;
      justify-content: center;
    }

    .modal-backdrop.open {
      display: flex;
    }

    .modal-sheet {
      background: #072218;
      border: 1px solid var(--border-gold-bright);
      border-bottom: none;
      border-radius: 24px 24px 0 0;
      width: 100%;
      max-width: 600px;
      max-height: 90vh;
      overflow-y: auto;
      padding: 24px 20px 40px;
      position: relative;
      animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }

    @keyframes slideUp {
      from { transform: translateY(100%); }
      to { transform: translateY(0); }
    }

    .modal-close-bar {
      width: 44px;
      height: 4px;
      background: var(--gold-primary);
      border-radius: 4px;
      margin: 0 auto 16px;
      opacity: 0.6;
    }

    .pyramid-box {
      background: rgba(3, 20, 14, 0.7);
      border: 1px solid var(--border-gold);
      border-radius: 14px;
      padding: 14px;
      margin: 16px 0;
    }

    .pyramid-level {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      font-size: 12px;
      margin-bottom: 8px;
    }
    .pyramid-level:last-child {
      margin-bottom: 0;
    }

    .pyramid-label {
      color: var(--text-gold);
      font-weight: 600;
      min-width: 90px;
    }

    /* Cart Drawer */
    .cart-item-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 0;
      border-bottom: 1px solid rgba(212, 175, 55, 0.15);
    }

    .cart-item-info {
      flex: 1;
    }

    .cart-item-title {
      font-size: 13px;
      font-weight: 600;
      color: #fff;
    }

    .cart-item-subtitle {
      font-size: 11px;
      color: var(--text-gold);
    }

    .cart-item-price {
      font-family: 'Cinzel', serif;
      font-weight: 700;
      color: var(--gold-light);
      margin: 0 12px;
    }

    .cart-remove-icon {
      color: #ef4444;
      cursor: pointer;
      font-size: 16px;
      padding: 4px;
    }

    /* Form Fields */
    .form-group {
      margin-bottom: 12px;
    }
    .form-label {
      font-size: 11px;
      color: var(--text-gold);
      letter-spacing: 1px;
      text-transform: uppercase;
      margin-bottom: 4px;
      display: block;
    }
    .form-input {
      width: 100%;
      padding: 12px 14px;
      background: rgba(3, 20, 14, 0.8);
      border: 1px solid var(--border-gold);
      border-radius: 12px;
      color: #fff;
      font-size: 14px;
      outline: none;
    }
    .form-input:focus {
      border-color: var(--gold-light);
    }

    /* Toast Notification */
    .toast {
      position: fixed;
      top: 70px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(10, 43, 31, 0.95);
      border: 1px solid var(--gold-light);
      box-shadow: 0 4px 25px var(--gold-glow);
      color: #fff;
      padding: 10px 20px;
      border-radius: 25px;
      font-size: 13px;
      font-weight: 600;
      z-index: 200;
      display: none;
      align-items: center;
      gap: 8px;
    }
  </style>
</head>
<body>

  <!-- Toast -->
  <div id="toastNotification" class="toast">
    <span id="toastIcon">✨</span>
    <span id="toastMessage">Додано у кошик</span>
  </div>

  <!-- Header -->
  <header class="app-header">
    <div class="brand-logo">
      <div class="crown-icon">👑</div>
      <div>
        <div class="brand-title gold-gradient-text">L'ÉLIXIR ROYAL</div>
        <div class="brand-subtitle">Селективна Парфумерія</div>
      </div>
    </div>
    <div class="cart-btn-header" onclick="openCartView()">
      <span>🛒</span>
      <span id="headerCartTotal">0 ₴</span>
      <div id="headerCartCount" class="cart-badge">0</div>
    </div>
  </header>

  <!-- Navigation Tab Bar -->
  <nav class="tab-bar">
    <button class="tab-btn active" onclick="switchTab('catalog')" id="tabBtnCatalog">
      <span>✨</span> Каталог (90)
    </button>
    <button class="tab-btn" onclick="switchTab('aroma_box')" id="tabBtnAroma">
      <span>🎁</span> Aroma Box (-15%)
    </button>
    <button class="tab-btn" onclick="switchTab('sommelier')" id="tabBtnSommelier">
      <span>🧠</span> Сомельє
    </button>
    <button class="tab-btn" onclick="switchTab('cart')" id="tabBtnCart">
      <span>🛍</span> Кошик
    </button>
  </nav>

  <!-- Main Container -->
  <main class="main-content">

    <!-- ================= CATALOG VIEW ================= -->
    <section id="catalogView">

      <!-- Volume Selector Bar -->
      <div class="mode-bar">
        <div class="mode-title">
          <span>Оберіть формат покупки:</span>
          <span id="currentModeLabel" class="gold-gradient-text">Розпив (5 мл)</span>
        </div>
        <div class="volume-chips">
          <div class="vol-chip" onclick="setCatalogVolume(3)" id="volChip3">💧 3 мл</div>
          <div class="vol-chip active" onclick="setCatalogVolume(5)" id="volChip5">💧 5 мл</div>
          <div class="vol-chip" onclick="setCatalogVolume(10)" id="volChip10">💧 10 мл</div>
          <div class="vol-chip" onclick="setCatalogVolume(15)" id="volChip15">💧 15 мл</div>
          <div class="vol-chip" onclick="setCatalogVolume(0)" id="volChip0">📦 Флакон</div>
        </div>
      </div>

      <!-- Search Input -->
      <div class="search-bar">
        <span class="search-icon">🔍</span>
        <input 
          type="text" 
          id="searchInput" 
          class="search-input" 
          placeholder="Пошук аромату, бренду, ноти (напр. Tobacco, ваніль)..."
          oninput="handleSearch(this.value)"
        >
      </div>

      <!-- Brand Carousel Filter -->
      <div class="filter-scroll" id="brandsFilterScroll">
        <div class="filter-pill active" onclick="filterByBrand('all')">Всі бренди (15)</div>
      </div>

      <!-- Vibe / Notes Filter -->
      <div class="filter-scroll" id="vibesFilterScroll">
        <div class="filter-pill active" onclick="filterByVibe('all')">Всі настрої</div>
        <div class="filter-pill" onclick="filterByVibe('f')">🌿 Свіжі & Морські</div>
        <div class="filter-pill" onclick="filterByVibe('t')">🍂 Тютюнові & Пряні</div>
        <div class="filter-pill" onclick="filterByVibe('s')">🍨 Солодкі & Ваніль</div>
        <div class="filter-pill" onclick="filterByVibe('w')">🪵 Деревні & Сандал</div>
        <div class="filter-pill" onclick="filterByVibe('floral')">🌸 Квіткові & Фрукти</div>
      </div>

      <!-- Perfumes Counter -->
      <div style="font-size: 11px; color: var(--text-gold); margin-bottom: 12px; display: flex; justify-content: space-between;">
        <span id="perfumesCount">Знайдено: 90 парфумів</span>
        <span>✨ Тільки оригінальний нішевий парфум</span>
      </div>

      <!-- Perfumes Grid -->
      <div class="perfumes-grid" id="perfumesGrid">
      </div>
    </section>


    <!-- ================= AROMA BOX BUILDER VIEW ================= -->
    <section id="aromaBoxView" style="display: none;">
      <div class="aroma-box-container">
        <div class="aroma-box-header">
          <div class="aroma-discount-badge">Вигода 15% на весь сет</div>
          <h2 class="aroma-box-title">Конструктор Aroma Box</h2>
          <p style="font-size: 12px; color: var(--text-muted);">
            Складіть індивідуальний бокс із <b>3 будь-яких ароматів по 5 мл</b> у скляних атомайзерах
          </p>
        </div>

        <div class="aroma-slots-grid">
          <!-- Slot 1 -->
          <div class="aroma-slot" id="slot0" onclick="handleSlotClick(0)">
            <div class="slot-num">№ 1</div>
            <div class="slot-icon">🧴</div>
            <div class="slot-placeholder-text">+ Обрати аромат</div>
          </div>
          <!-- Slot 2 -->
          <div class="aroma-slot" id="slot1" onclick="handleSlotClick(1)">
            <div class="slot-num">№ 2</div>
            <div class="slot-icon">🧴</div>
            <div class="slot-placeholder-text">+ Обрати аромат</div>
          </div>
          <!-- Slot 3 -->
          <div class="aroma-slot" id="slot2" onclick="handleSlotClick(2)">
            <div class="slot-num">№ 3</div>
            <div class="slot-icon">🧴</div>
            <div class="slot-placeholder-text">+ Обрати аромат</div>
          </div>
        </div>

        <div class="aroma-summary">
          <div>
            <div class="aroma-summary-text">Статус: <b id="aromaSlotsStatus" style="color:#fff;">0 з 3 ароматів</b></div>
            <div class="aroma-summary-text" id="aromaRawSum">Звичайна ціна: 0 ₴</div>
          </div>
          <div style="text-align: right;">
            <div class="aroma-summary-text" style="color: var(--text-gold);">Зі знижкою 15%:</div>
            <div class="aroma-final-price" id="aromaFinalSum">0 ₴</div>
          </div>
        </div>

        <button 
          class="luxury-gold-btn" 
          id="btnOrderAromaBox" 
          disabled 
          onclick="addAromaBoxToCart()"
        >
          🎁 Додати Aroma Box у кошик
        </button>
      </div>

      <!-- Quick pick grid for aroma box -->
      <div style="margin-top: 24px;">
        <h3 class="font-serif gold-gradient-text" style="font-size: 16px; margin-bottom: 12px;">
          Швидкий вибір для вашого боксу:
        </h3>
        <div class="perfumes-grid" id="aromaQuickPickGrid">
        </div>
      </div>
    </section>


    <!-- ================= SOMMELIER VIEW ================= -->
    <section id="sommelierView" style="display: none;">
      <div class="sommelier-card">
        <div style="text-align: center; margin-bottom: 12px;">
          <span style="font-size: 32px;">🧠</span>
          <h2 class="quiz-step-title" id="quizStepTitle">Парфумерний Сомельє</h2>
          <p class="quiz-step-subtitle" id="quizStepSubtitle">
            Дайте відповідь на 3 коротких питання, і ми підберемо ваш ідеальний нішевий аромат
          </p>
        </div>

        <!-- Quiz Container -->
        <div id="quizContainer">
          <!-- Step 1: Gender -->
          <div id="quizStep1" class="quiz-step">
            <div style="font-size: 13px; color: var(--text-gold); margin-bottom: 10px; font-weight: 600;">
              Крок 1 з 3: Для кого підбираємо композицію?
            </div>
            <div class="quiz-options-grid">
              <button class="quiz-option-btn" onclick="selectQuizOption('gender', 'm')">
                <span>👨 Джентльмен (Мужній, харизматичний)</span>
                <span>➔</span>
              </button>
              <button class="quiz-option-btn" onclick="selectQuizOption('gender', 'w')">
                <span>👩 Леді (Чуттєвий, витончений)</span>
                <span>➔</span>
              </button>
              <button class="quiz-option-btn" onclick="selectQuizOption('gender', 'u')">
                <span>✨ Унісекс (Абсолютна сучасна ніша)</span>
                <span>➔</span>
              </button>
            </div>
          </div>

          <!-- Step 2: Occasion -->
          <div id="quizStep2" class="quiz-step" style="display: none;">
            <div style="font-size: 13px; color: var(--text-gold); margin-bottom: 10px; font-weight: 600;">
              Крок 2 з 3: Для якого приводу та сезону?
            </div>
            <div class="quiz-options-grid">
              <button class="quiz-option-btn" onclick="selectQuizOption('occasion', 'd')">
                <span>☀️ Щодень, офіс, бізнес-зустрічі</span>
                <span>➔</span>
              </button>
              <button class="quiz-option-btn" onclick="selectQuizOption('occasion', 'e')">
                <span>🌙 Вечірній вихід, романтика та побачення</span>
                <span>➔</span>
              </button>
              <button class="quiz-option-btn" onclick="selectQuizOption('occasion', 'c')">
                <span>❄️ Осінь & Зима (Теплий, затишний шлейф)</span>
                <span>➔</span>
              </button>
              <button class="quiz-option-btn" onclick="selectQuizOption('occasion', 's')">
                <span>🌊 Весна & Літо (Свіжість, легкість, сонце)</span>
                <span>➔</span>
              </button>
            </div>
          </div>

          <!-- Step 3: Vibe -->
          <div id="quizStep3" class="quiz-step" style="display: none;">
            <div style="font-size: 13px; color: var(--text-gold); margin-bottom: 10px; font-weight: 600;">
              Крок 3 з 3: Який напрямок вам найближчий?
            </div>
            <div class="quiz-options-grid">
              <button class="quiz-option-btn" onclick="selectQuizOption('vibe', 'f')">
                <span>🌿 Морські ноти, свіжі цитруси та мінерали</span>
                <span>➔</span>
              </button>
              <button class="quiz-option-btn" onclick="selectQuizOption('vibe', 's')">
                <span>🍨 Солодка ваніль, вишня та десертні акорди</span>
                <span>➔</span>
              </button>
              <button class="quiz-option-btn" onclick="selectQuizOption('vibe', 't')">
                <span>🍂 Дорогий тютюн, коньяк, ром та спеції</span>
                <span>➔</span>
              </button>
              <button class="quiz-option-btn" onclick="selectQuizOption('vibe', 'w')">
                <span>🪵 Шляхетний сандал, шкіра, кедр та уд</span>
                <span>➔</span>
              </button>
              <button class="quiz-option-btn" onclick="selectQuizOption('vibe', 'floral')">
                <span>🌸 Стиглі фрукти, жасмин та білі квіти</span>
                <span>➔</span>
              </button>
            </div>
          </div>

          <!-- Result Step -->
          <div id="quizResultStep" style="display: none;">
            <div style="text-align: center; margin-bottom: 16px;">
              <span style="font-size: 40px;">🥂</span>
              <h3 class="font-serif gold-gradient-text" style="font-size: 18px; margin-top: 6px;">
                Ваша персональна добірка ароматів:
              </h3>
              <p style="font-size: 12px; color: var(--text-muted);">
                Парфуми, які бездоганно розкриють вашу індивідуальність:
              </p>
            </div>
            <div class="perfumes-grid" id="quizResultsGrid">
            </div>
            <button class="luxury-gold-btn" style="margin-top: 16px;" onclick="restartQuiz()">
              🔄 Пройти тест ще раз
            </button>
          </div>
        </div>
      </div>
    </section>


    <!-- ================= CART VIEW ================= -->
    <section id="cartView" style="display: none;">
      <div style="background: var(--bg-card); border: 1px solid var(--border-gold); border-radius: 20px; padding: 20px 16px;">
        <h2 class="font-serif gold-gradient-text" style="font-size: 20px; margin-bottom: 14px; text-align: center;">
          Ваш Кошик
        </h2>

        <div id="cartItemsList">
        </div>

        <div id="cartEmptyMessage" style="text-align: center; padding: 40px 10px; display: none;">
          <div style="font-size: 48px; margin-bottom: 12px; opacity: 0.6;">🧴</div>
          <div style="font-size: 16px; font-weight: 600; color: #fff;">Кошик поки що порожній</div>
          <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px; margin-bottom: 20px;">
            Оберіть розпив або повнорозмірний флакон у каталозі
          </div>
          <button class="luxury-gold-btn" onclick="switchTab('catalog')">
            Перейти до каталогу
          </button>
        </div>

        <div id="cartCheckoutSection" style="margin-top: 24px;">
          <!-- Pricing Summary -->
          <div style="background: rgba(3, 20, 14, 0.7); border: 1px solid var(--border-gold); border-radius: 14px; padding: 14px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; font-size: 13px; color: var(--text-muted); margin-bottom: 6px;">
              <span>Сума замовлення:</span>
              <span id="cartSubtotal" style="color: #fff; font-weight: 600;">0 ₴</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 13px; color: var(--text-muted); margin-bottom: 8px;">
              <span>Доставка:</span>
              <span style="color: var(--text-gold);">За тарифами НП</span>
            </div>
            <div style="border-top: 1px solid rgba(212, 175, 55, 0.2); padding-top: 8px; display: flex; justify-content: space-between; align-items: center;">
              <span style="font-weight: 600; font-size: 15px;">Разом до сплати:</span>
              <span id="cartGrandTotal" class="font-serif" style="font-size: 20px; font-weight: 700; color: var(--gold-light);">0 ₴</span>
            </div>
          </div>

          <!-- Nova Poshta Checkout Form -->
          <h3 class="font-serif gold-gradient-text" style="font-size: 16px; margin-bottom: 12px;">
            Дані для доставки (Нова Пошта):
          </h3>

          <div class="form-group">
            <label class="form-label">Прізвище та Ім'я одержувача *</label>
            <input type="text" id="orderName" class="form-input" placeholder="Шевченко Олександр">
          </div>

          <div class="form-group">
            <label class="form-label">Номер телефону *</label>
            <input type="tel" id="orderPhone" class="form-input" placeholder="+380 97 123 45 67">
          </div>

          <div class="form-group">
            <label class="form-label">Місто та номер відділення / поштомату *</label>
            <input type="text" id="orderAddress" class="form-input" placeholder="м. Київ, Відділення №25 або Поштомат 8412">
          </div>

          <div class="form-group">
            <label class="form-label">Спосіб оплати *</label>
            <select id="orderPayment" class="form-input" style="background: #03140e; cursor: pointer;">
              <option value="card">💳 Оплата на картку / Monobank</option>
              <option value="cod">💵 Накладений платіж (при отриманні)</option>
            </select>
          </div>

          <button class="luxury-gold-btn" style="margin-top: 14px;" onclick="submitOrder()">
            🚚 Підтвердити Замовлення
          </button>
        </div>
      </div>
    </section>

  </main>


  <!-- ================= PERFUME DETAIL MODAL ================= -->
  <div class="modal-backdrop" id="perfumeModalBackdrop" onclick="closePerfumeModal(event)">
    <div class="modal-sheet" id="perfumeModalSheet" onclick="event.stopPropagation()">
      <div class="modal-close-bar"></div>

      <div style="position: relative; width: 100%; height: 260px; border-radius: 16px; overflow: hidden; margin-bottom: 14px; background: #020c08;">
        <img id="modalPerfumeImg" src="" alt="Perfume" style="width: 100%; height: 100%; object-fit: cover;">
        <div id="modalGenderBadge" class="card-badge-vibe">Унісекс</div>
      </div>

      <div id="modalBrand" class="card-brand" style="font-size: 12px;">TOM FORD</div>
      <h2 id="modalName" class="font-serif" style="font-size: 22px; color: #fff; margin-bottom: 8px;">Tobacco Vanille</h2>

      <p id="modalDesc" style="font-size: 13px; color: var(--text-muted); line-height: 1.5; margin-bottom: 14px;">
        Опис аромату...
      </p>

      <!-- Olfactory Pyramid -->
      <div class="pyramid-box">
        <div style="font-size: 11px; text-transform: uppercase; color: var(--gold-light); letter-spacing: 1px; margin-bottom: 10px; font-weight: 700;">
          🎼 Ольфакторна піраміда:
        </div>
        <div class="pyramid-level">
          <span class="pyramid-label">Верхні ноти:</span>
          <span id="modalTopNotes" style="color: #fff;"></span>
        </div>
        <div class="pyramid-level">
          <span class="pyramid-label">Ноти серця:</span>
          <span id="modalHeartNotes" style="color: #fff;"></span>
        </div>
        <div class="pyramid-level">
          <span class="pyramid-label">Базові ноти:</span>
          <span id="modalBaseNotes" style="color: #fff;"></span>
        </div>
      </div>

      <!-- Volume Selector inside Modal -->
      <div style="margin-bottom: 18px;">
        <label class="form-label">Оберіть об'єм для замовлення:</label>
        <div class="volume-chips">
          <div class="vol-chip" onclick="setModalVolume(3)" id="mVol3">3 мл</div>
          <div class="vol-chip active" onclick="setModalVolume(5)" id="mVol5">5 мл</div>
          <div class="vol-chip" onclick="setModalVolume(10)" id="mVol10">10 мл</div>
          <div class="vol-chip" onclick="setModalVolume(15)" id="mVol15">15 мл</div>
          <div class="vol-chip" onclick="setModalVolume(0)" id="mVol0">100 мл флакон</div>
        </div>
      </div>

      <!-- Add to Cart CTA -->
      <button class="luxury-gold-btn" id="modalAddToCartBtn" onclick="addModalPerfumeToCart()">
        Додати в кошик • <span id="modalPriceTag">715 ₴</span>
      </button>
    </div>
  </div>


  <!-- ================= ORDER SUCCESS MODAL ================= -->
  <div class="modal-backdrop" id="successModalBackdrop">
    <div class="modal-sheet" style="text-align: center; padding: 36px 20px;">
      <div style="font-size: 54px; margin-bottom: 14px;">👑</div>
      <h2 class="font-serif gold-gradient-text" style="font-size: 22px; margin-bottom: 8px;">
        Замовлення Прийнято!
      </h2>
      <p style="font-size: 13px; color: var(--text-muted); line-height: 1.5; margin-bottom: 16px;" id="successModalText">
        Ваше замовлення успішно зареєстровано. Наш менеджер незабаром зв'яжеться з вами та надішле ТТН Нової Пошти.
      </p>
      <div style="background: rgba(3, 20, 14, 0.8); border: 1px solid var(--border-gold); border-radius: 14px; padding: 14px; margin-bottom: 20px;" id="successReceiptDetails">
      </div>
      <button class="luxury-gold-btn" onclick="closeSuccessModal()">
        Продовжити покупки
      </button>
    </div>
  </div>


  <!-- ================= JAVASCRIPT APP LOGIC ================= -->
  <script>
    // Database injected directly from backend
    const BRANDS_DB = __BRANDS_JSON__;
    const PERFUMES_DB = __PERFUMES_JSON__;

    const ATOMIZER_FEE = 40;
    const DEFAULT_IMG = "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?q=80&w=800&auto=format&fit=crop";

    // Application State
    let currentCatalogVolume = 5; // 3, 5, 10, 15, or 0 (full bottle)
    let selectedBrandFilter = 'all';
    let selectedVibeFilter = 'all';
    let searchQuery = '';

    // Cart
    let cart = JSON.parse(localStorage.getItem('parfume_cart') || '[]');

    // Aroma Box Builder: array of up to 3 perfume IDs
    let aromaBoxItems = [];

    // Sommelier State
    let quizAnswers = { gender: null, occasion: null, vibe: null };

    // Modal Active Perfume
    let activeModalPerfumeId = null;
    let modalSelectedVolume = 5;

    // Telegram WebApp Setup
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.ready();
      tg.expand();
      try {
        tg.enableClosingConfirmation();
      } catch (e) {}
    }

    function haptic(type = 'light') {
      try {
        if (tg && tg.HapticFeedback) {
          if (type === 'selection') tg.HapticFeedback.selectionChanged();
          else if (type === 'success') tg.HapticFeedback.notificationOccurred('success');
          else tg.HapticFeedback.impactOccurred(type);
        }
      } catch (e) {}
    }

    function showToast(message, icon = '✨') {
      const toast = document.getElementById('toastNotification');
      document.getElementById('toastMessage').innerText = message;
      document.getElementById('toastIcon').innerText = icon;
      toast.style.display = 'flex';
      haptic('selection');
      setTimeout(() => {
        toast.style.display = 'none';
      }, 2400);
    }

    // Calculate Price Helper
    function calculatePrice(perfume, volume) {
      if (volume === 0) {
        return perfume.price_full_bottle;
      }
      return (perfume.price_per_ml * volume) + ATOMIZER_FEE;
    }

    // Tab Navigation
    function switchTab(tab) {
      haptic('selection');
      const tabs = ['catalog', 'aroma_box', 'sommelier', 'cart'];
      tabs.forEach(t => {
        const view = document.getElementById(t === 'catalog' ? 'catalogView' : 
                                              t === 'aroma_box' ? 'aromaBoxView' : 
                                              t === 'sommelier' ? 'sommelierView' : 'cartView');
        if (view) view.style.display = (t === tab) ? 'block' : 'none';
      });

      document.getElementById('tabBtnCatalog').classList.toggle('active', tab === 'catalog');
      document.getElementById('tabBtnAroma').classList.toggle('active', tab === 'aroma_box');
      document.getElementById('tabBtnSommelier').classList.toggle('active', tab === 'sommelier');
      document.getElementById('tabBtnCart').classList.toggle('active', tab === 'cart');

      window.scrollTo({ top: 0, behavior: 'smooth' });

      if (tab === 'cart') renderCartView();
      if (tab === 'aroma_box') renderAromaBoxView();
    }

    function openCartView() {
      switchTab('cart');
    }

    // ================= CATALOG LOGIC =================
    function initBrandsFilter() {
      const container = document.getElementById('brandsFilterScroll');
      let html = '<div class="filter-pill active" onclick="filterByBrand(\\'all\\')" id="brandPillAll">Всі бренди (15)</div>';
      for (const [key, name] of Object.entries(BRANDS_DB)) {
        html += `<div class="filter-pill" onclick="filterByBrand('${key}')" id="brandPill_${key}">${name}</div>`;
      }
      container.innerHTML = html;
    }

    function filterByBrand(bId) {
      haptic('selection');
      selectedBrandFilter = bId;
      document.querySelectorAll('#brandsFilterScroll .filter-pill').forEach(el => el.classList.remove('active'));
      const activeEl = bId === 'all' ? document.getElementById('brandPillAll') : document.getElementById(`brandPill_${bId}`);
      if (activeEl) activeEl.classList.add('active');
      renderCatalogGrid();
    }

    function filterByVibe(vId) {
      haptic('selection');
      selectedVibeFilter = vId;
      document.querySelectorAll('#vibesFilterScroll .filter-pill').forEach(el => el.classList.remove('active'));
      event.target.classList.add('active');
      renderCatalogGrid();
    }

    function setCatalogVolume(vol) {
      haptic('selection');
      currentCatalogVolume = vol;
      [3, 5, 10, 15, 0].forEach(v => {
        const chip = document.getElementById(`volChip${v}`);
        if (chip) chip.classList.toggle('active', v === vol);
      });

      const label = document.getElementById('currentModeLabel');
      label.innerText = vol === 0 ? 'Повний флакон (100 мл)' : `Розпив (${vol} мл)`;
      renderCatalogGrid();
    }

    function handleSearch(val) {
      searchQuery = val.trim().toLowerCase();
      renderCatalogGrid();
    }

    function renderCatalogGrid() {
      const grid = document.getElementById('perfumesGrid');
      const countEl = document.getElementById('perfumesCount');
      
      const filtered = Object.entries(PERFUMES_DB).filter(([id, p]) => {
        if (selectedBrandFilter !== 'all' && p.brand_id !== selectedBrandFilter) return false;
        if (selectedVibeFilter !== 'all' && p.vibe !== selectedVibeFilter) return false;
        if (searchQuery) {
          const text = `${p.brand} ${p.name} ${p.description} ${p.top_notes} ${p.heart_notes} ${p.base_notes}`.toLowerCase();
          if (!text.includes(searchQuery)) return false;
        }
        return true;
      });

      countEl.innerText = `Знайдено: ${filtered.length} парфумів`;

      if (filtered.length === 0) {
        grid.innerHTML = `
          <div style="grid-column: 1 / -1; text-align: center; padding: 40px 10px; color: var(--text-muted);">
            <div style="font-size: 32px; margin-bottom: 8px;">🔍</div>
            <div style="font-size: 15px; color: #fff;">Нічого не знайдено</div>
            <div style="font-size: 12px; margin-top: 4px;">Спробуйте інший пошуковий запит або скиньте фільтри</div>
          </div>
        `;
        return;
      }

      let html = '';
      filtered.forEach(([id, p]) => {
        const price = calculatePrice(p, currentCatalogVolume);
        const formatLabel = currentCatalogVolume === 0 ? 'Флакон' : `${currentCatalogVolume} мл`;
        const vibeNames = { 'f': '🌿 Свіжий', 't': '🍂 Тютюновий', 's': '🍨 Гурманський', 'w': '🪵 Деревний', 'floral': '🌸 Квітковий' };
        const vibeText = vibeNames[p.vibe] || '✨ Ніша';

        html += `
          <div class="perfume-card" onclick="openPerfumeModal('${id}')">
            <div class="card-img-wrap">
              <img class="card-img" src="${p.image_url || DEFAULT_IMG}" alt="${p.name}" loading="lazy" onerror="this.src='${DEFAULT_IMG}'">
              <div class="card-badge-vibe">${vibeText}</div>
            </div>
            <div class="card-body">
              <div>
                <div class="card-brand">${p.brand}</div>
                <div class="card-name">${p.name}</div>
                <div class="card-notes">${p.top_notes} • ${p.heart_notes}</div>
              </div>
              <div class="card-footer">
                <div>
                  <div class="card-price">${price} ₴</div>
                  <div style="font-size: 10px; color: var(--text-muted);">${formatLabel}</div>
                </div>
                <button class="card-add-btn" onclick="event.stopPropagation(); quickAddToCart('${id}', ${currentCatalogVolume})">
                  +
                </button>
              </div>
            </div>
          </div>
        `;
      });

      grid.innerHTML = html;
    }

    // ================= MODAL PERFUME DETAILS =================
    function openPerfumeModal(id) {
      haptic('light');
      const p = PERFUMES_DB[id];
      if (!p) return;

      activeModalPerfumeId = id;
      modalSelectedVolume = currentCatalogVolume;

      document.getElementById('modalPerfumeImg').src = p.image_url || DEFAULT_IMG;
      document.getElementById('modalBrand').innerText = p.brand.toUpperCase();
      document.getElementById('modalName').innerText = p.name;
      document.getElementById('modalDesc').innerText = p.description;

      const gLabels = { 'm': 'Чоловічий', 'w': 'Жіночий', 'u': 'Унісекс' };
      document.getElementById('modalGenderBadge').innerText = gLabels[p.gender] || 'Унісекс';

      document.getElementById('modalTopNotes').innerText = p.top_notes;
      document.getElementById('modalHeartNotes').innerText = p.heart_notes;
      document.getElementById('modalBaseNotes').innerText = p.base_notes;

      setModalVolume(modalSelectedVolume);

      document.getElementById('perfumeModalBackdrop').classList.add('open');
    }

    function closePerfumeModal(e) {
      if (e) e.stopPropagation();
      document.getElementById('perfumeModalBackdrop').classList.remove('open');
    }

    function setModalVolume(vol) {
      haptic('selection');
      modalSelectedVolume = vol;
      [3, 5, 10, 15, 0].forEach(v => {
        const el = document.getElementById(`mVol${v}`);
        if (el) el.classList.toggle('active', v === vol);
      });

      if (activeModalPerfumeId) {
        const p = PERFUMES_DB[activeModalPerfumeId];
        const pr = calculatePrice(p, vol);
        document.getElementById('modalPriceTag').innerText = `${pr} ₴`;
      }
    }

    function addModalPerfumeToCart() {
      if (!activeModalPerfumeId) return;
      quickAddToCart(activeModalPerfumeId, modalSelectedVolume);
      closePerfumeModal();
    }

    // ================= CART LOGIC =================
    function quickAddToCart(id, volume) {
      const p = PERFUMES_DB[id];
      if (!p) return;

      const price = calculatePrice(p, volume);
      const typeLabel = volume === 0 ? 'Повний флакон (100 мл)' : `Розпив ${volume} мл`;

      cart.push({
        id: id,
        brand: p.brand,
        name: p.name,
        price: price,
        volume: volume,
        typeLabel: typeLabel,
        isBundle: false
      });

      saveCart();
      showToast(`${p.name} додано у кошик!`, '🛒');
      haptic('success');
    }

    function saveCart() {
      localStorage.setItem('parfume_cart', JSON.stringify(cart));
      updateCartHeader();
    }

    function updateCartHeader() {
      const total = cart.reduce((sum, it) => sum + it.price, 0);
      document.getElementById('headerCartCount').innerText = cart.length;
      document.getElementById('headerCartTotal').innerText = `${total} ₴`;
    }

    function renderCartView() {
      const list = document.getElementById('cartItemsList');
      const emptyMsg = document.getElementById('cartEmptyMessage');
      const checkoutSec = document.getElementById('cartCheckoutSection');

      if (cart.length === 0) {
        list.innerHTML = '';
        emptyMsg.style.display = 'block';
        checkoutSec.style.display = 'none';
        return;
      }

      emptyMsg.style.display = 'none';
      checkoutSec.style.display = 'block';

      let html = '';
      let subtotal = 0;

      cart.forEach((it, idx) => {
        subtotal += it.price;
        html += `
          <div class="cart-item-row">
            <div class="cart-item-info">
              <div class="cart-item-title">${it.brand} — ${it.name}</div>
              <div class="cart-item-subtitle">${it.typeLabel}</div>
            </div>
            <div class="cart-item-price">${it.price} ₴</div>
            <span class="cart-remove-icon" onclick="removeCartItem(${idx})">✕</span>
          </div>
        `;
      });

      list.innerHTML = html;
      document.getElementById('cartSubtotal').innerText = `${subtotal} ₴`;
      document.getElementById('cartGrandTotal').innerText = `${subtotal} ₴`;
    }

    function removeCartItem(idx) {
      haptic('light');
      cart.splice(idx, 1);
      saveCart();
      renderCartView();
    }

    function submitOrder() {
      const name = document.getElementById('orderName').value.trim();
      const phone = document.getElementById('orderPhone').value.trim();
      const address = document.getElementById('orderAddress').value.trim();
      const payment = document.getElementById('orderPayment').value;

      if (!name || name.length < 3) {
        alert("Будь ласка, введіть коректне ім'я та прізвище.");
        return;
      }
      if (!phone || phone.length < 9) {
        alert("Будь ласка, введіть дійсний номер телефону.");
        return;
      }
      if (!address || address.length < 5) {
        alert("Будь ласка, вкажіть місто та відділення Нової Пошти.");
        return;
      }

      const total = cart.reduce((sum, it) => sum + it.price, 0);
      const orderId = '#RO-' + Math.floor(100000 + Math.random() * 900000);
      const payLabel = payment === 'card' ? 'Оплата на картку / Monobank' : 'Накладений платіж';

      const orderData = {
        order_id: orderId,
        customer_name: name,
        customer_phone: phone,
        customer_address: address,
        payment_method: payLabel,
        total_amount: total,
        items: cart
      };

      haptic('success');

      // Send to Telegram WebApp if available
      if (tg && tg.sendData) {
        try {
          tg.sendData(JSON.stringify(orderData));
        } catch (e) {
          console.warn("Telegram WebApp sendData failed:", e);
        }
      }

      // Display Success Modal
      document.getElementById('successReceiptDetails').innerHTML = `
        <div style="font-size: 13px; color: var(--gold-light); font-weight: 700; margin-bottom: 6px;">Номер замовлення: ${orderId}</div>
        <div style="font-size: 12px; color: #fff;">Одержувач: <b>${name}</b></div>
        <div style="font-size: 12px; color: #fff;">Телефон: <b>${phone}</b></div>
        <div style="font-size: 12px; color: #fff;">Доставка: <b>${address}</b></div>
        <div style="font-size: 12px; color: #fff;">Оплата: <b>${payLabel}</b></div>
        <div style="font-size: 14px; color: var(--gold-light); font-weight: 700; margin-top: 8px;">Сума: ${total} ₴</div>
      `;

      cart = [];
      saveCart();
      document.getElementById('successModalBackdrop').classList.add('open');
    }

    function closeSuccessModal() {
      document.getElementById('successModalBackdrop').classList.remove('open');
      switchTab('catalog');
    }

    // ================= AROMA BOX BUILDER =================
    function renderAromaBoxView() {
      for (let i = 0; i < 3; i++) {
        const slotEl = document.getElementById(`slot${i}`);
        const pid = aromaBoxItems[i];
        if (pid && PERFUMES_DB[pid]) {
          const p = PERFUMES_DB[pid];
          slotEl.classList.add('filled');
          slotEl.innerHTML = `
            <button class="slot-remove-btn" onclick="event.stopPropagation(); removeAromaSlot(${i})">✕</button>
            <div style="font-size: 10px; color: var(--gold-light);">${p.brand}</div>
            <div class="slot-filled-name">${p.name}</div>
            <div style="font-size: 10px; color: var(--text-gold); margin-top: 4px;">✓ 5 мл</div>
          `;
        } else {
          slotEl.classList.remove('filled');
          slotEl.innerHTML = `
            <div class="slot-num">№ ${i + 1}</div>
            <div class="slot-icon">🧴</div>
            <div class="slot-placeholder-text">+ Обрати аромат</div>
          `;
        }
      }

      const statusEl = document.getElementById('aromaSlotsStatus');
      const rawEl = document.getElementById('aromaRawSum');
      const finalEl = document.getElementById('aromaFinalSum');
      const btn = document.getElementById('btnOrderAromaBox');

      statusEl.innerText = `${aromaBoxItems.length} з 3 ароматів`;

      const rawSum = aromaBoxItems.reduce((acc, pid) => {
        return acc + calculatePrice(PERFUMES_DB[pid], 5);
      }, 0);

      const discountSum = Math.round(rawSum * 0.85);

      rawEl.innerText = `Звичайна ціна: ${rawSum} ₴`;
      finalEl.innerText = `${discountSum} ₴`;

      btn.disabled = aromaBoxItems.length !== 3;

      renderAromaQuickPickGrid();
    }

    function handleSlotClick(slotIdx) {
      haptic('light');
      window.scrollTo({ top: 380, behavior: 'smooth' });
    }

    function addPerfumeToAromaBox(pid) {
      if (aromaBoxItems.length >= 3) {
        showToast("Сет уже заповнено (3 аромати). Видаліть один, щоб змінити.", "⚠️");
        return;
      }
      if (aromaBoxItems.includes(pid)) {
        showToast("Цей аромат уже є у вашому сеті!", "ℹ️");
        return;
      }
      haptic('selection');
      aromaBoxItems.push(pid);
      renderAromaBoxView();
      showToast(`${PERFUMES_DB[pid].name} додано у сет!`, "🎁");
    }

    function removeAromaSlot(slotIdx) {
      haptic('light');
      aromaBoxItems.splice(slotIdx, 1);
      renderAromaBoxView();
    }

    function addAromaBoxToCart() {
      if (aromaBoxItems.length !== 3) return;

      const rawSum = aromaBoxItems.reduce((acc, pid) => {
        return acc + calculatePrice(PERFUMES_DB[pid], 5);
      }, 0);
      const discountSum = Math.round(rawSum * 0.85);

      const names = aromaBoxItems.map(pid => PERFUMES_DB[pid].name).join(', ');

      cart.push({
        id: 'aroma_box_bundle',
        brand: 'Ексклюзивний Сет',
        name: `Aroma Box (${names})`,
        price: discountSum,
        volume: 5,
        typeLabel: '3 аромати по 5 мл зі знижкою 15%',
        isBundle: true
      });

      aromaBoxItems = [];
      saveCart();
      haptic('success');
      showToast("Aroma Box успішно додано до кошика!", "🎉");
      switchTab('cart');
    }

    function renderAromaQuickPickGrid() {
      const grid = document.getElementById('aromaQuickPickGrid');
      let html = '';
      Object.entries(PERFUMES_DB).slice(0, 18).forEach(([pid, p]) => {
        const isPicked = aromaBoxItems.includes(pid);
        html += `
          <div class="perfume-card" style="opacity: ${isPicked ? 0.45 : 1};" onclick="addPerfumeToAromaBox('${pid}')">
            <div class="card-img-wrap" style="padding-top: 80%;">
              <img class="card-img" src="${p.image_url || DEFAULT_IMG}" alt="${p.name}">
            </div>
            <div class="card-body" style="padding: 10px;">
              <div class="card-brand">${p.brand}</div>
              <div class="card-name">${p.name}</div>
              <button class="luxury-gold-btn" style="padding: 6px; font-size: 11px; margin-top: 6px;">
                ${isPicked ? '✓ У сеті' : '+ Додати у бокс'}
              </button>
            </div>
          </div>
        `;
      });
      grid.innerHTML = html;
    }

    // ================= SOMMELIER LOGIC =================
    function selectQuizOption(type, value) {
      haptic('selection');
      quizAnswers[type] = value;

      if (type === 'gender') {
        document.getElementById('quizStep1').style.display = 'none';
        document.getElementById('quizStep2').style.display = 'block';
      } else if (type === 'occasion') {
        document.getElementById('quizStep2').style.display = 'none';
        document.getElementById('quizStep3').style.display = 'block';
      } else if (type === 'vibe') {
        document.getElementById('quizStep3').style.display = 'none';
        calculateQuizResults();
      }
    }

    function calculateQuizResults() {
      haptic('success');
      document.getElementById('quizResultStep').style.display = 'block';
      const grid = document.getElementById('quizResultsGrid');

      const g = quizAnswers.gender;
      const o = quizAnswers.occasion;
      const v = quizAnswers.vibe;

      const scored = Object.entries(PERFUMES_DB).map(([pid, p]) => {
        let score = 0;
        if (p.gender === g || p.gender === 'u') score += 3;
        if (p.occasion === o) score += 3;
        if (p.vibe === v) score += 4;
        return { pid, p, score };
      });

      scored.sort((a, b) => b.score - a.score);
      const topPicks = scored.slice(0, 4);

      let html = '';
      topPicks.forEach(({ pid, p }) => {
        const price = calculatePrice(p, 5);
        html += `
          <div class="perfume-card" onclick="openPerfumeModal('${pid}')">
            <div class="card-img-wrap">
              <img class="card-img" src="${p.image_url || DEFAULT_IMG}" alt="${p.name}">
            </div>
            <div class="card-body">
              <div>
                <div class="card-brand">${p.brand}</div>
                <div class="card-name">${p.name}</div>
                <div style="font-size: 11px; color: var(--gold-light); margin-bottom: 6px;">Ідеальне влучання 98%</div>
                <div class="card-notes">${p.top_notes}</div>
              </div>
              <div class="card-footer">
                <div>
                  <div class="card-price">${price} ₴</div>
                  <div style="font-size: 10px; color: var(--text-muted);">5 мл розпив</div>
                </div>
                <button class="card-add-btn" onclick="event.stopPropagation(); quickAddToCart('${pid}', 5)">
                  +
                </button>
              </div>
            </div>
          </div>
        `;
      });

      grid.innerHTML = html;
    }

    function restartQuiz() {
      haptic('light');
      quizAnswers = { gender: null, occasion: null, vibe: null };
      document.getElementById('quizStep1').style.display = 'block';
      document.getElementById('quizStep2').style.display = 'none';
      document.getElementById('quizStep3').style.display = 'none';
      document.getElementById('quizResultStep').style.display = 'none';
    }

    // Initial Bootstrap
    document.addEventListener('DOMContentLoaded', () => {
      initBrandsFilter();
      renderCatalogGrid();
      updateCartHeader();
    });
  </script>
</body>
</html>
'''

final_html = html_template.replace("__BRANDS_JSON__", brands_json).replace("__PERFUMES_JSON__", perfumes_json)

output_path = "parfyme_bot/webapp/index.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(final_html)

print(f"Generated {output_path} successfully ({len(final_html)} bytes)!")
