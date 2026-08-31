// PRAMAAN Client Script — Cryptography, Sarvam AI Translation, DigiLocker e-KYC & Blockchain Inspector

document.addEventListener('DOMContentLoaded', () => {
  // 1. Toast Notification System
  window.showToast = function(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    const bgColors = {
      success: 'bg-emerald-900 border-emerald-500 text-emerald-100',
      danger: 'bg-red-900 border-red-500 text-red-100',
      warning: 'bg-amber-900 border-amber-500 text-amber-100',
      info: 'bg-slate-900 border-[#C9A227] text-white'
    };

    toast.className = `p-3.5 rounded-lg border shadow-xl text-xs font-medium flex items-center justify-between gap-3 animate-slide-down transition-all duration-300 ${bgColors[type] || bgColors.info}`;
    toast.innerHTML = `
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full ${type === 'success' ? 'bg-emerald-400' : type === 'danger' ? 'bg-red-400' : 'bg-[#E7C766]'} animate-pulse"></span>
        <span>${message}</span>
      </div>
      <button onclick="this.parentElement.remove()" class="text-slate-400 hover:text-white text-sm font-bold ml-2">✕</button>
    `;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  };

  // 2. Hash Chip Clipboard Copy
  window.copyToClipboard = function(text, label = 'Hash') {
    navigator.clipboard.writeText(text).then(() => {
      window.showToast(`${label} copied to clipboard!`, 'success');
    }).catch(err => {
      console.error('Copy failed', err);
      window.showToast('Failed to copy', 'danger');
    });
  };

  // 3. Live Stopwatch Timer for Emergency Intake Form (/cases/new)
  const timerDisplay = document.getElementById('speed-timer-display');
  const timerInput = document.getElementById('entry_duration_seconds');
  if (timerDisplay && timerInput) {
    let seconds = 0;
    const interval = setInterval(() => {
      seconds++;
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      timerDisplay.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
      timerInput.value = seconds;
    }, 1000);
  }

  // 4. Clinical Trauma Intake Form 15-Second Presets (/cases/new)
  window.applyIntakePreset = function(presetType) {
    const now = new Date();
    const formattedDate = now.toISOString().slice(0, 16).replace('T', ' ');

    const presets = {
      accident: {
        alias: 'Ramesh Kumar, 34M',
        type: 'Road Accident',
        date: formattedDate.slice(0, 10),
        doctor: 'Dr. A. Sharma, CMO',
        summary: 'Blunt trauma head, compound fracture right tibia-fibula following high-speed RTA hit-and-run at Ring Road Junction. Active scalp bleeding, GCS 13/15.',
        content: `MEDICO-LEGAL CERTIFICATE (EMERGENCY INTAKE)\nPatient: Ramesh Kumar, 34/M\nDate: ${formattedDate}\nType: RTA Hit & Run\nVitals: BP 90/60, Pulse 118 bpm, GCS 13/15 (E3V4M6)\nInjuries: Deep laceration over right parietal scalp (6x2cm bone deep), deformed right lower limb with active bleeding.\nProvisional Opinion: Grievous blunt force trauma.`
      },
      road_trauma: {
        alias: 'Ramesh Kumar, 34M',
        type: 'Road Accident',
        date: formattedDate.slice(0, 10),
        doctor: 'Dr. A. Sharma, CMO',
        summary: 'Blunt trauma head, compound fracture right tibia-fibula following high-speed RTA hit-and-run at Ring Road Junction. Active scalp bleeding, GCS 13/15.',
        content: `MEDICO-LEGAL CERTIFICATE (EMERGENCY INTAKE)\nPatient: Ramesh Kumar, 34/M\nDate: ${formattedDate}\nType: RTA Hit & Run\nVitals: BP 90/60, Pulse 118 bpm, GCS 13/15 (E3V4M6)\nInjuries: Deep laceration over right parietal scalp (6x2cm bone deep), deformed right lower limb with active bleeding.\nProvisional Opinion: Grievous blunt force trauma.`
      },
      assault: {
        alias: 'Suresh Patel, 28M',
        type: 'Assault',
        date: formattedDate.slice(0, 10),
        doctor: 'Dr. A. Sharma, CMO',
        summary: 'Multiple defense wounds over bilateral forearms, incised laceration 4cm over left zygomatic arch inflicted with sharp weapon during street altercation.',
        content: `MEDICO-LEGAL EMERGENCY INTAKE - PHYSICAL ASSAULT\nPatient: Suresh Patel, 28/M\nIncident: Physical altercation with sharp weapon\nInjuries: Incised wound 4x0.5cm over left zygomatic region, contusions on bilateral forearms.\nExamining Officer: Dr. A. Sharma, CMO (NMC-2018-84920)`
      },
      assault_emergency: {
        alias: 'Suresh Patel, 28M',
        type: 'Assault',
        date: formattedDate.slice(0, 10),
        doctor: 'Dr. A. Sharma, CMO',
        summary: 'Multiple defense wounds over bilateral forearms, incised laceration 4cm over left zygomatic arch inflicted with sharp weapon during street altercation.',
        content: `MEDICO-LEGAL EMERGENCY INTAKE - PHYSICAL ASSAULT\nPatient: Suresh Patel, 28/M\nIncident: Physical altercation with sharp weapon\nInjuries: Incised wound 4x0.5cm over left zygomatic region, contusions on bilateral forearms.\nExamining Officer: Dr. A. Sharma, CMO (NMC-2018-84920)`
      },
      pocso: {
        alias: 'Minor Subject (Confidential)',
        type: 'POCSO Case',
        date: formattedDate.slice(0, 10),
        doctor: 'Dr. N. Joshi, Gynaecologist',
        summary: 'Statutory confidential medical examination requisitioned by Special Juvenile Police Unit under POCSO Act §33 / DPDP 2023. Biological specimen kit sealed.',
        content: `POCSO CONFIDENTIAL EMERGENCY INTAKE\nCase: Statutory Child Protection Proceeding\nDoctor: Dr. N. Joshi, Gynaecologist (NMC-2016-72819)\nVictim Identity Protected under Section 33, POCSO Act 2012.\nPreliminary examination completed in presence of female medical officer and legal support person.`
      },
      pocso_protected: {
        alias: 'Minor Subject (Confidential)',
        type: 'POCSO Case',
        date: formattedDate.slice(0, 10),
        doctor: 'Dr. N. Joshi, Gynaecologist',
        summary: 'Statutory confidential medical examination requisitioned by Special Juvenile Police Unit under POCSO Act §33 / DPDP 2023. Biological specimen kit sealed.',
        content: `POCSO CONFIDENTIAL EMERGENCY INTAKE\nCase: Statutory Child Protection Proceeding\nDoctor: Dr. N. Joshi, Gynaecologist (NMC-2016-72819)\nVictim Identity Protected under Section 33, POCSO Act 2012.\nPreliminary examination completed in presence of female medical officer and legal support person.`
      }
    };

    const data = presets[presetType];
    if (!data) return;

    if (document.getElementById('patient_alias')) document.getElementById('patient_alias').value = data.alias;
    if (document.getElementById('case_type')) document.getElementById('case_type').value = data.type;
    if (document.getElementById('incident_date')) document.getElementById('incident_date').value = data.date;
    if (document.getElementById('duty_doctor')) document.getElementById('duty_doctor').value = data.doctor;
    if (document.getElementById('injury_summary')) document.getElementById('injury_summary').value = data.summary;

    const fileContentInput = document.getElementById('file_content_text');
    if (fileContentInput) fileContentInput.value = data.content;

    window.showToast(`Applied ${data.type} rapid intake preset! Ready to seal.`, 'success');
  };
  window.applyTraumaPreset = window.applyIntakePreset;

  // 5. Client-Side WebCrypto SHA-256 Drag-and-Drop Hasher for Judges (/verify/{id})
  window.handleJudgeDrop = async function(event, expectedContentHash) {
    event.preventDefault();
    const dropzone = document.getElementById('judge-dropzone');
    const resultBox = document.getElementById('judge-drop-result');
    if (!dropzone || !resultBox) return;

    dropzone.classList.remove('border-[#C9A227]', 'bg-amber-50/20');

    const files = event.dataTransfer ? event.dataTransfer.files : event.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    resultBox.classList.remove('hidden');
    resultBox.innerHTML = `
      <div class="flex items-center gap-2 text-xs text-slate-600">
        <svg class="w-4 h-4 animate-spin text-[#C9A227]" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
        </svg>
        <span>Computing client-side SHA-256 via browser WebCrypto API...</span>
      </div>
    `;

    try {
      const arrayBuffer = await file.arrayBuffer();
      const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const computedHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

      const isMatch = (computedHash.toLowerCase() === expectedContentHash.toLowerCase());

      if (isMatch) {
        resultBox.innerHTML = `
          <div class="p-4 bg-emerald-50 border-2 border-emerald-500 rounded-xl space-y-2 animate-slide-down">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-emerald-900 font-bold text-xs">
                <svg class="w-4 h-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" />
                </svg>
                <span>MATCH CONFIRMED: 100% Cryptographic Equivalence</span>
              </div>
              <span class="text-[10px] font-mono bg-emerald-200 text-emerald-900 px-2 py-0.5 rounded font-bold">WebCrypto Validated</span>
            </div>
            <div class="text-[11px] font-mono text-slate-700 space-y-1">
              <div>File: <strong class="text-navy">${file.name}</strong> (${file.size} bytes)</div>
              <div>Computed WebCrypto SHA-256: <span class="text-emerald-700 font-bold break-all">${computedHash}</span></div>
            </div>
          </div>
        `;
        window.showToast('Client-side WebCrypto SHA-256 matches sealed record hash!', 'success');
      } else {
        resultBox.innerHTML = `
          <div class="p-4 bg-red-50 border-2 border-crimson rounded-xl space-y-2 animate-slide-down">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-red-800 font-bold text-xs">
                <svg class="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" />
                </svg>
                <span>MISMATCH: Dropped file does NOT match the sealed cryptographic hash</span>
              </div>
              <span class="text-[10px] font-mono bg-red-200 text-red-900 px-2 py-0.5 rounded font-bold">Tamper Alert</span>
            </div>
            <div class="text-[11px] font-mono text-slate-700 space-y-1">
              <div>File: <strong class="text-navy">${file.name}</strong> (${file.size} bytes)</div>
              <div>Computed WebCrypto Hash: <span class="text-red-700 font-bold break-all">${computedHash}</span></div>
              <div>Expected Sealed Hash: <span class="text-emerald-700 font-bold break-all">${expectedContentHash}</span></div>
            </div>
          </div>
        `;
        window.showToast('Hash mismatch: Dropped file was altered', 'danger');
      }
    } catch (e) {
      console.error(e);
      resultBox.innerHTML = `<div class="p-3 bg-red-100 text-red-700 text-xs rounded">Error computing hash: ${e.message}</div>`;
    }
  };

  // 6. Sarvam AI Multilingual Translation Switcher
  window.changeLanguage = function(langCode) {
    localStorage.setItem('pramaan_lang', langCode);
    const translations = (window.SARVAM_TRANSLATIONS && window.SARVAM_TRANSLATIONS[langCode]) || {};

    // Translate DOM nodes that match dictionary phrases
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    let node;
    while (node = walker.nextNode()) {
      const text = node.nodeValue.trim();
      if (text && translations[text]) {
        node.nodeValue = node.nodeValue.replace(text, translations[text]);
      }
    }

    const langNames = { en: 'English', hi: 'हिंदी (Hindi)', mr: 'मराठी (Marathi)', ta: 'தமிழ் (Tamil)', te: 'తెలుగు (Telugu)', bn: 'বাংলা (Bengali)' };
    window.showToast(`Switched language to ${langNames[langCode] || langCode} via Sarvam AI Indic Engine`, 'info');
  };

  // Initialize saved language if set
  const savedLang = localStorage.getItem('pramaan_lang');
  if (savedLang && savedLang !== 'en') {
    setTimeout(() => {
      window.changeLanguage(savedLang);
    }, 150);
  }

  // 7. Blockchain Explorer Modal Inspector
  window.openBlockchainModal = function(txHash, blockNumber, recordId) {
    let modal = document.getElementById('blockchain-explorer-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'blockchain-explorer-modal';
      modal.className = 'fixed inset-0 z-50 bg-navy/80 backdrop-blur-sm flex items-center justify-center p-4';
      document.body.appendChild(modal);
    }

    modal.innerHTML = `
      <div class="bg-slate-900 border-2 border-[#C9A227] rounded-xl max-w-xl w-full p-6 text-white shadow-2xl space-y-4 animate-slide-down">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 rounded-full bg-emerald-400 animate-pulse"></div>
            <h3 class="font-fraunces text-base font-bold text-[#E7C766]">Polygon PoS / Indian Blockchain Explorer</h3>
          </div>
          <button onclick="document.getElementById('blockchain-explorer-modal').classList.add('hidden')" class="text-slate-400 hover:text-white">✕</button>
        </div>

        <div class="space-y-2.5 text-xs font-mono">
          <div class="p-3 bg-slate-950 rounded border border-slate-800 space-y-1.5">
            <div class="text-[10px] text-slate-400 uppercase tracking-wider">Transaction Hash (TxHash)</div>
            <div class="text-emerald-400 font-bold break-all">${txHash || '0x7f8a9b2c3d4e5f60718293a4b5c6d7e8f90a1b2c'}</div>
          </div>

          <div class="grid grid-cols-2 gap-2">
            <div class="p-3 bg-slate-950 rounded border border-slate-800">
              <div class="text-[10px] text-slate-400 uppercase">Block Number</div>
              <div class="text-white font-bold text-sm">#${blockNumber || '19842038'}</div>
            </div>
            <div class="p-3 bg-slate-950 rounded border border-slate-800">
              <div class="text-[10px] text-slate-400 uppercase">Network Status</div>
              <div class="text-emerald-400 font-bold">128+ Confirmations (Finalized)</div>
            </div>
          </div>

          <div class="p-3 bg-slate-950 rounded border border-slate-800 space-y-1">
            <div class="text-[10px] text-slate-400 uppercase">Smart Contract Address</div>
            <div class="text-slate-300 break-all">0x91F5C7A87A656a297E59b2d8cD6d3F3e4F2bc842</div>
            <div class="text-[10px] text-slate-500">Method: sealEvidenceBlock(bytes32 recordHash, string nmcReg)</div>
          </div>
        </div>

        <div class="pt-2 flex justify-end gap-3">
          <button onclick="document.getElementById('blockchain-explorer-modal').classList.add('hidden')" class="px-4 py-2 rounded bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300">Close</button>
          <a href="https://polygonscan.com" target="_blank" class="px-4 py-2 rounded bg-[#C9A227] hover:bg-[#B08D1E] text-navy font-bold text-xs uppercase tracking-wider flex items-center gap-1.5 shadow">
            <span>View on Public Explorer ↗</span>
          </a>
        </div>
      </div>
    `;
    modal.classList.remove('hidden');
  };

  // 8. DigiLocker Doctor e-KYC Modal Inspector
  window.openDigiLockerKycModal = function(doctorName, nmcReg) {
    let modal = document.getElementById('digilocker-kyc-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'digilocker-kyc-modal';
      modal.className = 'fixed inset-0 z-50 bg-navy/80 backdrop-blur-sm flex items-center justify-center p-4';
      document.body.appendChild(modal);
    }

    modal.innerHTML = `
      <div class="bg-white border-2 border-emerald-600 rounded-xl max-w-lg w-full p-6 text-slate-800 shadow-2xl space-y-4 animate-slide-down">
        <div class="flex items-center justify-between border-b border-slate-200 pb-3">
          <div class="flex items-center gap-2">
            <div class="p-1 rounded bg-emerald-100 text-emerald-800 font-bold text-xs">DigiLocker Verified</div>
            <h3 class="font-fraunces text-base font-bold text-navy">National Medical Commission (NMC) KYC</h3>
          </div>
          <button onclick="document.getElementById('digilocker-kyc-modal').classList.add('hidden')" class="text-slate-400 hover:text-slate-700">✕</button>
        </div>

        <div class="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-2 text-xs">
          <div class="flex justify-between border-b border-slate-200 pb-1.5">
            <span class="text-slate-500">Medical Practitioner:</span>
            <strong class="text-navy">${doctorName || 'Dr. A. Sharma, CMO'}</strong>
          </div>
          <div class="flex justify-between border-b border-slate-200 pb-1.5">
            <span class="text-slate-500">NMC Registration No:</span>
            <span class="font-mono font-bold text-emerald-700">${nmcReg || 'NMC-2018-84920'}</span>
          </div>
          <div class="flex justify-between border-b border-slate-200 pb-1.5">
            <span class="text-slate-500">State Medical Council:</span>
            <span>Delhi / State Medical Council</span>
          </div>
          <div class="flex justify-between border-b border-slate-200 pb-1.5">
            <span class="text-slate-500">Aadhaar e-KYC:</span>
            <span class="font-mono text-emerald-800 font-semibold">✓ Biometrically Verified (XXXX-XXXX-8492)</span>
          </div>
          <div class="flex justify-between">
            <span class="text-slate-500">Digital Seal Status:</span>
            <span class="text-emerald-700 font-bold">Authorized Forensic Signing Authority</span>
          </div>
        </div>

        <div class="pt-2 flex justify-end">
          <button onclick="document.getElementById('digilocker-kyc-modal').classList.add('hidden')" class="px-5 py-2 rounded-lg bg-navy text-white text-xs font-semibold uppercase tracking-wider">Close</button>
        </div>
      </div>
    `;
    modal.classList.remove('hidden');
  };

  // 9. Demo Drawer Toggle
  window.toggleDemoDrawer = function() {
    const drawer = document.getElementById('demo-tools-drawer');
    if (drawer) {
      drawer.classList.toggle('hidden');
    }
  };

  // 10. Fast Tamper / Untamper Actions
  window.executeTamper = async function(recordId) {
    try {
      const resp = await fetch(`/dev/tamper/${recordId}`, { method: 'POST' });
      const data = await resp.json();
      if (data.status === 'ok') {
        window.showToast(`Tampered record #${recordId} ("12 Mar" → "10 Mar")`, 'danger', 5000);
        setTimeout(() => window.location.reload(), 600);
      }
    } catch (e) {
      console.error(e);
      window.showToast('Failed to execute tamper', 'danger');
    }
  };

  window.executeUntamper = async function(recordId) {
    try {
      const resp = await fetch(`/dev/untamper/${recordId}`, { method: 'POST' });
      const data = await resp.json();
      if (data.status === 'ok') {
        window.showToast(`Restored original sealed state for record #${recordId}`, 'success', 5000);
        setTimeout(() => window.location.reload(), 600);
      }
    } catch (e) {
      console.error(e);
      window.showToast('Failed to untamper record', 'danger');
    }
  };

  window.simulateAdminAttack = async function() {
    try {
      const resp = await fetch('/dev/admin-attack', { method: 'POST' });
      const data = await resp.json();
      if (data.status === 'ok') {
        window.showToast('Executed Rogue Admin Re-Hash: SQLite rewritten, but External Anchor fails!', 'danger', 6000);
        setTimeout(() => window.location.href = '/anchor', 800);
      }
    } catch (e) {
      console.error(e);
    }
  };

  window.restoreAdminAttack = async function() {
    try {
      const resp = await fetch('/dev/admin-restore', { method: 'POST' });
      const data = await resp.json();
      if (data.status === 'ok') {
        window.showToast('Restored clean database state and re-synced anchor', 'success', 5000);
        setTimeout(() => window.location.reload(), 800);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // 11. Multi-Role Persona Switcher (RBAC)
  window.switchUserRole = async function(newRole) {
    try {
      const resp = await fetch('/api/set-role', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole })
      });
      const data = await resp.json();
      const roleIcons = { Hospital: '🏥', Police: '🚔', Court: '⚖️' };
      window.showToast(`Switched active workspace to ${roleIcons[newRole] || ''} ${newRole} mode`, 'info', 3000);
      setTimeout(() => window.location.reload(), 400);
    } catch (e) {
      console.error(e);
      document.cookie = `pramaan_role=${newRole}; path=/; max-age=2592000`;
      window.location.reload();
    }
  };
});
