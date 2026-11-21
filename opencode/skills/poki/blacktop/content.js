// Poki Blacktop: bypass rewarded/commercial breaks + unlock all cars.
(function () {
  'use strict';

  // --- 1. Hook PokiSDK (all frames, document-start) ---
  function hookSDK(sdk) {
    if (!sdk || sdk.__bypassed) return sdk;
    try {
      Object.defineProperty(sdk, 'rewardedBreak', {
        configurable: true, writable: true,
        value: function (onStart) {
          try { if (typeof onStart === 'function') onStart(); } catch (_) {}
          console.log('[Poki Bypass] rewardedBreak -> success');
          return Promise.resolve(true);
        }
      });
      Object.defineProperty(sdk, 'commercialBreak', {
        configurable: true, writable: true,
        value: function (onStart) {
          try { if (typeof onStart === 'function') onStart(); } catch (_) {}
          console.log('[Poki Bypass] commercialBreak -> skip');
          return Promise.resolve();
        }
      });
      sdk.__bypassed = true;
    } catch (e) {
      sdk.rewardedBreak = () => Promise.resolve(true);
      sdk.commercialBreak = () => Promise.resolve();
      sdk.__bypassed = true;
    }
    return sdk;
  }

  if (window.PokiSDK) hookSDK(window.PokiSDK);
  let _sdk = window.PokiSDK;
  try {
    Object.defineProperty(window, 'PokiSDK', {
      configurable: true, enumerable: true,
      get: () => _sdk,
      set: (v) => { _sdk = hookSDK(v); }
    });
  } catch (_) {}

  const t = setInterval(() => {
    if (window.PokiSDK && !window.PokiSDK.__bypassed) hookSDK(window.PokiSDK);
  }, 50);
  setTimeout(() => clearInterval(t), 30000);

  // --- 2. Patch Blacktop save (only on the poki-gdn game frame) ---
  function patchBlacktopSave() {
    try {
      const key = 'Blacktop1_Save';
      const raw = localStorage.getItem(key);
      if (!raw) return; // no save yet — nothing to patch
      const s = JSON.parse(raw);
      const cars = [];
      for (let x = 0; x <= 20; x++)
        for (let y = 0; y <= 10; y++)
          cars.push({ x: x, y: y });
      s.money = 999999999;
      s.hiScore = Math.max(Number(s.hiScore) || 0, 999999);
      s.unlockedCars = cars;
      localStorage.setItem(key, JSON.stringify(s));
      console.log('[Poki Bypass] Blacktop save patched: money=' + s.money + ' cars=' + cars.length);
    } catch (e) {
      console.log('[Poki Bypass] patch error', e);
    }
  }

  // Patch once, and again after any reload/navigation
  window.addEventListener('load', patchBlacktopSave);
  document.addEventListener('DOMContentLoaded', patchBlacktopSave);

  // Also re-patch on beforeunload (some games rewrite save on unload)
  window.addEventListener('beforeunload', patchBlacktopSave);

  // Expose for manual console calls too
  window.__pokiPatchBlacktop = patchBlacktopSave;
})();