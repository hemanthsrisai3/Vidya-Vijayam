// Force absolute global tracking
window.gameState = {
    baitCount: 0,
    fishingActive: false,
    fishCatchPending: false
};

// Client Game State persist variables
const state = {
    sessionId: null,
    level: 1,
    score: 0,
    xp: 0,
    stars: 0,
    streak: 0,
    bait: 0,
    max_bait: 3,
    inventory: [],
    inventory_limit: 5,
    upgrades: {
        rod: 1,
        backpack: 1,
        bait_bucket: 1
    },
    activeModule: null,
    currentQuestion: null,
    timerInterval: null,
    timeRemaining: 90,
    maxTime: 90,
    placedWords: [],
    sttActive: false,
    audioCtx: null,
    levelUpPending: false,
    nextLevelNumber: 2,
    isMuted: false
};

// Speech recognitions and syntheses
let recognition = null;
const synth = window.speechSynthesis;
let keyboard = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initSession();
    initializeModulesGrid();
    setupPondCastListener();
    setupShopListeners();
    setupControlButtons();
    initializeTeluguSpeechToText();
    initializeAudioControls();
});

// Lazy load AudioContext
function getAudioContext() {
    if (!state.audioCtx) {
        state.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    return state.audioCtx;
}

// ----------------------------------------------------
// 1. Session & State Persistence
// ----------------------------------------------------
function initSession() {
    fetch('/api/state')
        .then(res => res.json())
        .then(data => {
            state.sessionId = data.session_id;
            updateStatsUI(data.state);
        })
        .catch(err => console.error('Error initializing session:', err));
}

function updateStatsUI(stateData) {
    state.level = stateData.level;
    state.xp = stateData.xp;
    state.score = stateData.score;
    state.stars = stateData.stars;
    state.streak = stateData.streak;
    state.bait = stateData.bait;
    state.max_bait = stateData.max_bait;
    state.inventory = stateData.inventory;
    state.inventory_limit = stateData.inventory_limit;
    state.upgrades = stateData.upgrades;

    // Sync HUD Displays
    document.getElementById('global-level').textContent = state.level;
    document.getElementById('global-score').textContent = state.score;
    document.getElementById('global-bait').textContent = state.bait;
    document.getElementById('max-bait-display').textContent = state.max_bait;
    document.getElementById('global-inventory-count').textContent = `${state.inventory.length}/${state.inventory_limit}`;

    // Sync Shop Displays
    document.getElementById('rod-level-display').textContent = `${state.upgrades.rod}/4`;
    document.getElementById('backpack-level-display').textContent = `${state.upgrades.backpack}/4`;
    document.getElementById('bait-bucket-level-display').textContent = `${state.upgrades.bait_bucket}/4`;

    // Cost scaling multipliers
    const rodCosts = { 2: 100, 3: 300, 4: 800 };
    const backpackCosts = { 2: 75, 3: 150, 4: 225 };
    const bucketCosts = { 2: 50, 3: 150, 4: 400 };

    updateUpgradeCostUI('rod', state.upgrades.rod, rodCosts, 'btn-upgrade-rod', 'rod-cost-display');
    updateUpgradeCostUI('backpack', state.upgrades.backpack, backpackCosts, 'btn-upgrade-backpack', 'backpack-cost-display');
    updateUpgradeCostUI('bait_bucket', state.upgrades.bait_bucket, bucketCosts, 'btn-upgrade-bait-bucket', 'bait-bucket-cost-display');

    // Sync Fishing Access button state
    const goFishBtn = document.getElementById('btn-go-fishing');
    if (goFishBtn) {
        if (state.bait >= 3) {
            goFishBtn.disabled = false;
            goFishBtn.className = 'dock-nav-btn unlocked';
            goFishBtn.textContent = '🎣 Go to Fishing Pond (Bait Ready!)';
        } else {
            goFishBtn.disabled = true;
            goFishBtn.className = 'dock-nav-btn locked';
            goFishBtn.textContent = `🎣 Go to Fishing Pond (Needs ${state.bait}/3 Bait)`;
        }
    }

    // Refresh inventory display
    renderBackpackList();
}

function updateUpgradeCostUI(type, currentLvl, costs, btnId, costDisplayId) {
    const btn = document.getElementById(btnId);
    const disp = document.getElementById(costDisplayId);
    if (!btn || !disp) return;

    if (currentLvl >= 4) {
        btn.disabled = true;
        btn.classList.add('disabled');
        btn.innerHTML = 'Fully Upgraded';
    } else {
        const cost = costs[currentLvl + 1];
        disp.textContent = cost;
        
        if (state.score < cost) {
            btn.disabled = true;
            btn.classList.add('disabled');
        } else {
            btn.disabled = false;
            btn.classList.remove('disabled');
        }
    }
}

// Render inventory items in backpack
function renderBackpackList() {
    const list = document.getElementById('inventory-list');
    if (!list) return;

    if (state.inventory.length === 0) {
        list.innerHTML = '<span class="placeholder-text" style="grid-column: span 10;">సంచి ఖాళీగా ఉంది! (Backpack is empty. Cast line to catch fish!)</span>';
        return;
    }

    list.innerHTML = '';
    state.inventory.forEach(item => {
        const card = document.createElement('div');
        card.className = `inventory-item ${item.rarity}`;
        card.innerHTML = `
            <span class="inv-emoji">${item.emoji}</span>
            <span class="inv-name">${item.name}</span>
            <span class="inv-value">${item.value} XP</span>
        `;
        list.appendChild(card);
    });
}

// ----------------------------------------------------
// 2. Navigation Control Buttons
// ----------------------------------------------------
function initializeAudioControls() {
    const muteBtn = document.getElementById('btn-toggle-mute');
    if (muteBtn) {
        muteBtn.addEventListener('click', () => {
            state.isMuted = !state.isMuted;
            if (state.isMuted) {
                if ('speechSynthesis' in window) window.speechSynthesis.cancel();
                muteBtn.innerText = "🔇 Unmute Voice";
                muteBtn.classList.add('audio-muted');
            } else {
                muteBtn.innerText = "🔊 Mute Voice";
                muteBtn.classList.remove('audio-muted');
                speakText("సౌండ్ ఆన్ అయింది");
            }
        });
    }
}

function setupControlButtons() {
    const studyBtn = document.getElementById('btn-go-study');
    const fishBtn = document.getElementById('btn-go-fishing');
    const homeBtn = document.getElementById('btn-back-menu');

    if (studyBtn) {
        studyBtn.addEventListener('click', () => switchToHub('study'));
    }
    if (fishBtn) {
        fishBtn.addEventListener('click', () => switchToHub('fishing'));
    }
    if (homeBtn) {
        homeBtn.addEventListener('click', () => {
            state.activeModule = null;
            state.currentQuestion = null;
            stopTimer();
            stopSTT();
            
            // Show main select menu
            document.getElementById('quiz-question-view').classList.add('hidden');
            document.getElementById('quiz-menu-view').classList.remove('hidden');
            homeBtn.classList.add('hidden');
            
            // Sync session
            initSession();
        });
    }

    // Modal overlays
    const nextBtn = document.getElementById('btn-next-level');
    const retryBtn = document.getElementById('btn-retry');
    const levelupCloseBtn = document.getElementById('btn-close-levelup');

    if (nextBtn) nextBtn.addEventListener('click', advanceToNextQuizStep);
    if (retryBtn) retryBtn.addEventListener('click', advanceToNextQuizStep);
    if (levelupCloseBtn) levelupCloseBtn.addEventListener('click', advanceToNextQuizStep);
}

function switchToHub(hub) {
    const quizPanel = document.getElementById('panel-quiz');
    const fishPanel = document.getElementById('panel-fishing');

    if (hub === 'study') {
        window.gameState.fishingActive = false;
        fishPanel.classList.add('hidden-panel');
        fishPanel.classList.remove('active-panel');
        quizPanel.classList.add('active-panel');
        quizPanel.classList.remove('hidden-panel');
        
        speakText("అక్షరాలతో ఆడుకుందాం!");
        if (state.activeModule) {
            startTimer();
        }
    } else {
        // Fishing
        window.gameState.fishingActive = true;
        stopTimer();
        stopSTT();
        quizPanel.classList.add('hidden-panel');
        quizPanel.classList.remove('active-panel');
        fishPanel.classList.add('active-panel');
        fishPanel.classList.remove('hidden-panel');
        
        speakText("చేపలు పట్టే సమయం వచ్చింది! నీటిని తాకండి!");
    }
}

// ----------------------------------------------------
// 3. Modules Select Screen Routing
// ----------------------------------------------------
function initializeModulesGrid() {
    const modules = [
        { id: 'btn-alphabet', m_id: 'vowels_consonants', label: 'అచ్చులు & హల్లులు' },
        { id: 'btn-spelling', m_id: 'spelling_words', label: 'పదాల అమరిక' },
        { id: 'btn-vocabulary', m_id: 'vocabulary_definitions', label: 'పదాల అర్ధాలు' },
        { id: 'btn-grammar', m_id: 'sentence_formation', label: 'వాక్య నిర్మాణం' },
        { id: 'btn-comprehension', m_id: 'reading_comprehension', label: 'పఠన అవగాహన' }
    ];

    modules.forEach(m => {
        const card = document.getElementById(m.id);
        if (card) {
            card.addEventListener('click', () => startModuleChallenge(m.m_id, m.label));
        }
    });

    // Handle PDF upload custom curricula
    const fileInput = document.getElementById('pdf-file');
    const fileName = document.getElementById('file-name');
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                fileName.textContent = fileInput.files[0].name;
            } else {
                fileName.textContent = 'No file chosen';
            }
        });
    }

    const uploadForm = document.getElementById('upload-form');
    const statusDiv = document.getElementById('upload-status');
    if (uploadForm) {
        uploadForm.addEventListener('submit', (e) => {
            e.preventDefault();
            if (fileInput.files.length === 0) {
                statusDiv.className = 'upload-status error';
                statusDiv.textContent = 'దయచేసి ఒక PDF ఫైల్ ని ఎంచుకోండి. (Please choose a PDF file.)';
                return;
            }
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            statusDiv.className = 'upload-status';
            statusDiv.textContent = 'Uploading... Please wait.';
            
            const uploadBtn = document.getElementById('upload-btn');
            uploadBtn.disabled = true;
            
            fetch('/api/upload-pdf', {
                method: 'POST',
                body: formData
            })
                .then(res => res.json())
                .then(data => {
                    uploadBtn.disabled = false;
                    if (data.success) {
                        statusDiv.className = 'upload-status success';
                        statusDiv.textContent = `✅ ${data.message}`;
                        fileInput.value = '';
                        fileName.textContent = 'No file chosen';
                    } else {
                        statusDiv.className = 'upload-status error';
                        statusDiv.textContent = `❌ Error: ${data.error}`;
                    }
                })
                .catch(err => {
                    uploadBtn.disabled = false;
                    console.error('PDF upload error:', err);
                    statusDiv.className = 'upload-status error';
                    statusDiv.textContent = '❌ Server connection failed.';
                });
        });
    }
}

function startModuleChallenge(moduleId, labelName) {
    state.activeModule = moduleId;
    
    // Toggle screens
    document.getElementById('quiz-menu-view').classList.add('hidden');
    document.getElementById('quiz-question-view').classList.remove('hidden');
    document.getElementById('btn-back-menu').classList.remove('hidden');
    document.getElementById('active-module-badge').textContent = labelName;

    // Load keyboard
    if (!keyboard) {
        keyboard = new TeluguKeyboard('keyboard-keys', 'keyboard-input-display', (val) => {
            submitAnswer(val);
        });
    }

    getNextQuestion();
}

// ----------------------------------------------------
// 4. Question Loading & Parsing
// ----------------------------------------------------
function getNextQuestion() {
    if (!state.activeModule) return;
    
    stopTimer();
    stopSTT();
    hideOverlays();

    state.placedWords = [];
    if (keyboard) keyboard.clear();
    const display = document.getElementById('keyboard-input-display');
    if (display) display.value = '';
    const kb = document.getElementById('virtual-keyboard');
    if (kb) kb.classList.add('hidden-element');

    fetch(`/api/generate-question?session_id=${state.sessionId}&module=${state.activeModule}`)
        .then(res => res.json())
        .then(data => {
            state.currentQuestion = data.question;
            state.maxTime = data.timer_seconds;
            state.timeRemaining = data.timer_seconds;

            renderQuestionLayout();
            startTimer();

            setTimeout(() => {
                speakText(state.currentQuestion.speech_prompt || state.currentQuestion.question);
            }, 600);
        })
        .catch(err => {
            console.error('Question loading failed:', err);
        });
}

function renderQuestionLayout() {
    const q = state.currentQuestion;
    document.getElementById('question-text').textContent = q.question;
    document.getElementById('question-subtitle').textContent = q.english_subtitle;
    document.getElementById('hint-transliteration').textContent = q.roman || '';

    const hintMeaning = document.getElementById('hint-meaning');
    if (q.module === 'vocabulary_definitions' || q.module === 'spelling_words') {
        hintMeaning.textContent = `Meaning: ${q.hint.replace('The full word is', '').replace('The English meaning is', '')}`;
        hintMeaning.classList.remove('hidden');
    } else {
        hintMeaning.classList.add('hidden');
    }

    // Story layout
    const story = document.getElementById('story-block');
    if (q.module === 'reading_comprehension' && q.paragraph) {
        story.classList.remove('hidden');
        document.getElementById('story-text').textContent = q.paragraph;
        document.getElementById('story-roman').textContent = q.paragraph_roman || '';
        document.getElementById('story-meaning').textContent = q.paragraph_meaning || '';
    } else {
        story.classList.add('hidden');
    }

    // Build Interaction Options grid
    const grid = document.getElementById('options-grid');
    grid.innerHTML = '';
    
    if (q.type === 'multiple_choice') {
        grid.className = 'options-layout';
        q.options.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'option-card';
            const isTelugu = /[\u0c00-\u0c7f]/.test(opt);
            if (isTelugu) {
                btn.innerHTML = `${opt}`;
            } else {
                btn.innerHTML = `<span class="opt-sub" style="font-size: 1.4rem; color: var(--text-color);">${opt}</span>`;
            }
            btn.addEventListener('click', () => submitAnswer(opt));
            grid.appendChild(btn);
        });
    } else if (q.type === 'missing_letter' || q.type === 'scrambled_letters') {
        grid.className = 'options-layout-vertical';
        
        const displayWord = document.createElement('div');
        displayWord.className = 'spelling-word-display';
        displayWord.id = 'spelling-word-display';
        if (q.type === 'missing_letter') {
            displayWord.textContent = q.question.split(':').pop().trim();
        } else {
            displayWord.textContent = '_ '.repeat(q.scrambled.length);
        }
        grid.appendChild(displayWord);

        const container = document.createElement('div');
        container.className = 'options-layout';
        container.id = 'spelling-options-container';
        grid.appendChild(container);

        if (q.type === 'missing_letter') {
            q.options.forEach(opt => {
                const btn = document.createElement('button');
                btn.className = 'option-card';
                btn.textContent = opt;
                btn.addEventListener('click', () => submitAnswer(opt));
                container.appendChild(btn);
            });
        } else {
            state.placedWords = [];
            q.scrambled.forEach(letter => {
                const btn = document.createElement('button');
                btn.className = 'option-card';
                btn.textContent = letter;
                btn.addEventListener('click', () => {
                    if (btn.classList.contains('placed')) return;
                    btn.classList.add('placed');
                    btn.style.opacity = '0.3';
                    btn.style.pointerEvents = 'none';
                    state.placedWords.push(letter);
                    displayWord.textContent = state.placedWords.join('');
                    if (state.placedWords.length === q.scrambled.length) {
                        submitAnswer(state.placedWords.join(''));
                    }
                });
                container.appendChild(btn);
            });
            // Add reset spelling button
            const resetBtn = document.createElement('button');
            resetBtn.className = 'option-card';
            resetBtn.style.borderColor = 'var(--danger-color)';
            resetBtn.innerHTML = '<span style="color: var(--danger-color)">🔄 Reset</span>';
            resetBtn.addEventListener('click', () => {
                state.placedWords = [];
                displayWord.textContent = '_ '.repeat(q.scrambled.length);
                container.querySelectorAll('.option-card').forEach(c => {
                    c.classList.remove('placed');
                    c.style.opacity = '1';
                    c.style.pointerEvents = 'auto';
                });
            });
            container.appendChild(resetBtn);
        }
    } else if (q.type === 'drag_drop_sentence') {
        grid.className = 'options-layout-sentence';

        const assembly = document.createElement('div');
        assembly.className = 'sentence-assembly-area';
        assembly.id = 'sentence-assembly-zone';
        assembly.innerHTML = '<span class="placeholder-text">ఇక్కడ పదాలను ఉంచండి (Place words here)</span>';
        grid.appendChild(assembly);

        const pool = document.createElement('div');
        pool.className = 'word-tiles-pool';
        pool.id = 'sentence-words-pool';
        grid.appendChild(pool);

        state.placedWords = [];
        q.scrambled.forEach((word, idx) => {
            const tile = document.createElement('div');
            tile.className = 'word-tile';
            tile.textContent = word;
            tile.dataset.index = idx;
            tile.addEventListener('click', () => {
                if (tile.parentElement === pool) {
                    if (state.placedWords.length === 0) {
                        assembly.innerHTML = '';
                    }
                    state.placedWords.push({ word, tile, index: idx });
                    assembly.appendChild(tile);
                } else {
                    state.placedWords = state.placedWords.filter(item => item.index !== idx);
                    pool.appendChild(tile);
                    if (state.placedWords.length === 0) {
                        assembly.innerHTML = '<span class="placeholder-text">ఇక్కడ పదాలను ఉంచండి (Place words here)</span>';
                    }
                }
            });
            pool.appendChild(tile);
        });

        const actions = document.createElement('div');
        actions.className = 'sentence-actions';
        
        const resetBtn = document.createElement('button');
        resetBtn.className = 'btn clear-btn';
        resetBtn.id = 'clear-sentence-btn';
        resetBtn.textContent = 'మళ్ళీ చేయి (Reset)';
        resetBtn.addEventListener('click', () => {
            renderQuestionLayout();
        });
        
        const checkBtn = document.createElement('button');
        checkBtn.className = 'btn check-btn';
        checkBtn.id = 'submit-sentence-btn';
        checkBtn.textContent = 'సరిచూడు (Check)';
        checkBtn.addEventListener('click', () => {
            submitAnswer('');
        });

        actions.appendChild(resetBtn);
        actions.appendChild(checkBtn);
        grid.appendChild(actions);
    }
}

// ----------------------------------------------------
// 5. Timer Routines
// ----------------------------------------------------
function startTimer() {
    updateTimerProgressUI();
    state.timerInterval = setInterval(() => {
        state.timeRemaining--;
        updateTimerProgressUI();
        
        if (state.timeRemaining <= 0) {
            stopTimer();
            submitAnswer("__TIMEOUT__");
        }
    }, 1000);
}

function stopTimer() {
    if (state.timerInterval) {
        clearInterval(state.timerInterval);
        state.timerInterval = null;
    }
}

function updateTimerProgressUI() {
    const fill = document.getElementById('progress-bar');
    if (fill) {
        const pct = (state.timeRemaining / state.maxTime) * 100;
        fill.style.width = `${pct}%`;
    }
}

// ----------------------------------------------------
// 6. Answer Submission & Overlay Celebrations
// ----------------------------------------------------
function submitAnswer(ans, isSpeech = false) {
    stopTimer();
    stopSTT();

    let finalAnswer = ans;
    if (state.currentQuestion && state.currentQuestion.type === 'drag_drop_sentence') {
        finalAnswer = state.placedWords.map(w => w.word);
    }

    fetch('/api/submit-answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: state.sessionId,
            answer: finalAnswer,
            is_speech: isSpeech
        })
    })
        .then(res => res.json())
        .then(data => {
            updateStatsUI(data.state);
            showAnswerFeedbackOverlay(data);
        })
        .catch(err => {
            console.error('Answer submission failed:', err);
            startTimer();
        });
}

function showAnswerFeedbackOverlay(res) {
    if (res.correct) {
        playSuccessSound();
        speakText("భలే చెప్పావ్!");
        
        if (res.level_up) {
            state.levelUpPending = true;
            state.nextLevelNumber = res.state.level;
        } else {
            state.levelUpPending = false;
        }

        // Automatic switch to fishing hub on collects
        // But only if they are not already in fishing!
        const correctOverlay = document.getElementById('correct-overlay');
        const streakOverlay = document.getElementById('streak-bonus-overlay');
        const praises = ["చాలా బాగుంది!", "అద్భుతం!", "సబాష్!", "శుభం!", "భలే చేసావ్!"];
        const idx = Math.floor(Math.random() * praises.length);
        
        if (res.streak_bonus) {
            streakOverlay.classList.remove('hidden');
            setTimeout(() => {
                streakOverlay.classList.add('hidden');
                document.getElementById('feedback-success-title').textContent = praises[idx];
                document.getElementById('feedback-success-sub').textContent = `Correct! Bait: ${state.bait}/${state.max_bait} 🐛`;
                correctOverlay.classList.remove('hidden');
            }, 2500);
        } else {
            document.getElementById('feedback-success-title').textContent = praises[idx];
            document.getElementById('feedback-success-sub').textContent = `Correct! Bait: ${state.bait}/${state.max_bait} 🐛`;
            correctOverlay.classList.remove('hidden');
        }

        // Check if we hit 3 bait and user is still in Study panel -> trigger navigation guidance!
        if (state.bait >= 3) {
            speakText("ఎర సిద్ధంగా ఉంది! చేపలు పడదామా!");
        }
    } else {
        playErrorSound();
        speakText("పర్లేదు, ఇంకోసారి ప్రయత్నిద్దాం!");
        
        const wrongOverlay = document.getElementById('wrong-overlay');
        let displayStr = res.correct_answer;
        if (Array.isArray(displayStr)) displayStr = displayStr.join(' ');
        
        document.getElementById('correct-answer-text').textContent = displayStr;
        wrongOverlay.classList.remove('hidden');
        state.levelUpPending = false;
    }
}

function advanceToNextQuizStep() {
    hideOverlays();
    if (state.levelUpPending) {
        state.levelUpPending = false;
        showLevelUpBadge(state.nextLevelNumber);
    } else {
        getNextQuestion();
    }
}

function showLevelUpBadge(newLevel) {
    playLevelUpSound();
    const overlay = document.getElementById('levelup-overlay');
    document.getElementById('levelup-badge').textContent = newLevel;
    overlay.classList.remove('hidden');
    speakText("స్థాయి పెరిగింది! అభినందనలు! నువ్వు సూపర్!");
}

function hideOverlays() {
    document.getElementById('correct-overlay').classList.add('hidden');
    document.getElementById('wrong-overlay').classList.add('hidden');
    document.getElementById('levelup-overlay').classList.add('hidden');
}

// ----------------------------------------------------
// 7. Interactive Fishing Dock Operations (Canvas click-to-cast)
// ----------------------------------------------------
function setupPondCastListener() {
    const pond = document.getElementById('fishing-pond');
    if (!pond) return;

    const clickHandler = (e) => {
        e.preventDefault();
        
        if (!window.gameState.fishingActive) return;
        if (window.gameState.fishCatchPending) return;
        
        if (state.bait <= 0) {
            speakText("ఎర లేదు! చదువుకుందాం!");
            alert("ఎర లేదు! (No bait! Switch back to Study Station to answer questions.)");
            return;
        }

        if (state.inventory.length >= state.inventory_limit) {
            speakText("సంచి నిండిపోయింది! చేపలు అమ్మండి!");
            alert("సంచి నిండిపోయింది! (Your inventory is full! Click 'Sell All Fish'.)");
            return;
        }

        window.gameState.fishCatchPending = true;

        // Coordinates calculations
        const rect = pond.getBoundingClientRect();
        let clientX = e.clientX;
        let clientY = e.clientY;
        
        if (e.touches && e.touches.length > 0) {
            clientX = e.touches[0].clientX;
            clientY = e.touches[0].clientY;
        }

        const x = clientX - rect.left;
        const y = clientY - rect.top;

        // Animate Hook and ripples
        const hook = document.getElementById('fishing-hook');
        const ripple = document.querySelector('.water-ripple');

        if (hook) {
            hook.style.left = `${x}px`;
            hook.style.top = `${y}px`;
            hook.classList.remove('hook-active');
            void hook.offsetWidth;
            hook.classList.add('hook-active');
        }

        if (ripple) {
            ripple.style.left = `${x}px`;
            ripple.style.top = `${y}px`;
            ripple.classList.remove('splash-active');
            void ripple.offsetWidth;
            ripple.classList.add('splash-active');
        }

        playSplashSound();

        // Query backend for catch
        fetch('/api/catch-fish', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: state.sessionId })
        })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                    window.gameState.fishCatchPending = false;
                    return;
                }

                // Update UI state
                updateStatsUI(data.state);
                playSuccessSound();

                // Trigger catch popup
                const modal = document.getElementById('catch-modal');
                document.getElementById('caught-fish-emoji').textContent = data.fish.emoji;
                document.getElementById('caught-fish-name').textContent = `భలే! ${data.fish.name}`;
                document.getElementById('caught-fish-rarity').textContent = data.fish.rarity;
                document.getElementById('caught-fish-rarity').className = `rarity-tag ${data.fish.rarity}`;
                document.getElementById('caught-fish-value').textContent = data.fish.value;

                modal.classList.remove('hidden-element');
                speakText(`${data.fish.name} దొరికింది!`);

                setTimeout(() => {
                    modal.classList.add('hidden-element');
                    window.gameState.fishCatchPending = false;

                    // Automatically return if bait hits 0
                    if (state.bait <= 0) {
                        speakText("ఎర పూర్తి అయింది! అక్షరాలతో ఆడుకుందాం!");
                        switchToHub('study');
                    }
                }, 1600);
            })
            .catch(err => {
                console.error('Catch failed:', err);
                window.gameState.fishCatchPending = false;
            });
    };

    pond.addEventListener('click', clickHandler);
    pond.addEventListener('touchstart', clickHandler, { passive: false });

    // Sell fish listener
    const sellBtn = document.getElementById('btn-sell-fish');
    if (sellBtn) {
        sellBtn.addEventListener('click', () => {
            fetch('/api/sell-fish', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: state.sessionId })
            })
                .then(res => res.json())
                .then(data => {
                    updateStatsUI(data.state);
                    playSuccessSound();
                    speakText("చేపలు అమ్మబడ్డాయి!");
                    alert(`చేపలు అమ్మబడ్డాయి! You earned ${data.points_earned} points!`);
                })
                .catch(err => console.error('Selling failed:', err));
        });
    }
}

// ----------------------------------------------------
// 8. Upgrades Shop persistent calls
// ----------------------------------------------------
function setupShopListeners() {
    // Map backend upgrade_type keys to their actual HTML button IDs.
    // CRITICAL: The HTML uses hyphens (btn-upgrade-bait-bucket) but the
    // backend key is "bait_bucket" (underscore). This mapping bridges that.
    const upgradeMap = {
        'rod':         'btn-upgrade-rod',
        'backpack':    'btn-upgrade-backpack',
        'bait_bucket': 'btn-upgrade-bait-bucket'
    };

    Object.entries(upgradeMap).forEach(([upgradeType, btnId]) => {
        bindShopUpgradeButton(btnId, upgradeType);
    });
}

function bindShopUpgradeButton(btnId, upgradeType) {
    const originalBtn = document.getElementById(btnId);
    if (!originalBtn) {
        console.warn(`⚠️ Shop button #${btnId} not found in DOM. Skipping listener binding.`);
        return;
    }

    // Clone-replace to strip any previously attached listeners (prevents duplication on re-init)
    const cleanBtn = originalBtn.cloneNode(true);
    originalBtn.parentNode.replaceChild(cleanBtn, originalBtn);

    const handler = (e) => {
        e.preventDefault();
        e.stopPropagation();
        purchaseUpgrade(upgradeType);
    };

    cleanBtn.addEventListener('click', handler);
    cleanBtn.addEventListener('touchstart', handler, { passive: false });

    console.log(`✅ Secure event handler bound to shop button #${btnId} for upgrade "${upgradeType}".`);
}

function purchaseUpgrade(upgradeType) {
    console.log(`🛒 Attempting to purchase upgrade: ${upgradeType}`);

    // Quick client-side guard: don't fire if button is disabled
    const btnIdMap = { 'rod': 'btn-upgrade-rod', 'backpack': 'btn-upgrade-backpack', 'bait_bucket': 'btn-upgrade-bait-bucket' };
    const btn = document.getElementById(btnIdMap[upgradeType]);
    if (btn && btn.disabled) {
        console.log(`🚫 Button for ${upgradeType} is disabled. Aborting purchase.`);
        return;
    }

    fetch('/api/buy-upgrade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: state.sessionId,
            upgrade_type: upgradeType
        })
    })
        .then(res => {
            if (!res.ok) {
                return res.json().then(errData => { throw errData; });
            }
            return res.json();
        })
        .then(data => {
            if (data.error) {
                speakText("పాయింట్లు సరిపోలేదు! ఇంకా చదవండి.");
                alert(data.error);
                return;
            }
            updateStatsUI(data.state);
            playLevelUpSound();

            // Friendly upgrade-specific audio feedback
            const msgs = {
                'rod':         "గాలం మెరుగైంది! ఇప్పుడు అరుదైన చేపలు దొరుకుతాయి!",
                'backpack':    "సంచి పరిమాణం పెరిగింది! ఎక్కువ చేపలు పట్టుకో!",
                'bait_bucket': "సక్సెస్! బుట్ట పరిమాణం పెరిగింది!"
            };
            speakText(msgs[upgradeType] || "అప్‌గ్రేడ్ విజయవంతమైంది!");
            console.log(`🎉 Upgrade "${upgradeType}" purchased successfully! New level: ${data.new_level}`);
        })
        .catch(err => {
            if (err && err.error) {
                speakText("పాయింట్లు సరిపోలేదు! ఇంకా చదవండి.");
                alert(err.error);
            } else {
                console.error('Upgrade request failed:', err);
            }
        });
}

// ----------------------------------------------------
// 9. Sound Synthesis (Web Audio API)
// ----------------------------------------------------
function playSuccessSound() {
    try {
        if (state.isMuted) return;
        const ctx = getAudioContext();
        if (ctx.state === 'suspended') ctx.resume();
        const now = ctx.currentTime;
        const notes = [523.25, 659.25, 783.99]; // C5 -> E5 -> G5
        notes.forEach((freq, idx) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, now + idx * 0.12);
            gain.gain.setValueAtTime(0.15, now + idx * 0.12);
            gain.gain.exponentialRampToValueAtTime(0.01, now + idx * 0.12 + 0.3);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(now + idx * 0.12);
            osc.stop(now + idx * 0.12 + 0.35);
        });
    } catch (e) { console.warn('Audio Context failed:', e); }
}

function playErrorSound() {
    try {
        if (state.isMuted) return;
        const ctx = getAudioContext();
        if (ctx.state === 'suspended') ctx.resume();
        const now = ctx.currentTime;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(150, now);
        osc.frequency.linearRampToValueAtTime(100, now + 0.4);
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.4);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.4);
    } catch (e) { console.warn('Audio Context failed:', e); }
}

function playLevelUpSound() {
    try {
        if (state.isMuted) return;
        const ctx = getAudioContext();
        if (ctx.state === 'suspended') ctx.resume();
        const now = ctx.currentTime;
        const notes = [261.63, 392.00, 523.25, 659.25]; // C4 -> G4 -> C5 -> E5
        notes.forEach((freq, idx) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(freq, now + idx * 0.08);
            gain.gain.setValueAtTime(0.15, now + idx * 0.08);
            gain.gain.exponentialRampToValueAtTime(0.01, now + idx * 0.08 + 0.6);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(now + idx * 0.08);
            osc.stop(now + idx * 0.08 + 0.7);
        });
    } catch (e) { console.warn('Audio Context failed:', e); }
}

function playSplashSound() {
    try {
        if (state.isMuted) return;
        const ctx = getAudioContext();
        if (ctx.state === 'suspended') ctx.resume();
        const now = ctx.currentTime;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(800, now);
        osc.frequency.exponentialRampToValueAtTime(150, now + 0.3);
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.3);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.3);
    } catch (e) { console.warn('Splash audio failed:', e); }
}

// ----------------------------------------------------
// 10. Text-To-Speech (TTS) friendly Telugu engine
// ----------------------------------------------------
function speakText(text) {
    if (state.isMuted || !('speechSynthesis' in window)) {
        if (!('speechSynthesis' in window)) console.log("Speech synthesis not supported. Falling back to friendly text hints!");
        return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'te-IN';
    utterance.pitch = 1.2;
    utterance.rate = 0.85;

    let voices = window.speechSynthesis.getVoices();
    let bestVoice = voices.find(voice => voice.lang === 'te-IN' && !voice.name.includes('Default')) 
                    || voices.find(voice => voice.lang === 'te-IN')
                    || voices.find(voice => voice.lang.startsWith('te'));

    if (bestVoice) {
        utterance.voice = bestVoice;
        console.log(`Friendly voice selected: ${bestVoice.name}`);
    }
    window.speechSynthesis.speak(utterance);
}

// ----------------------------------------------------
// 11. Speech-To-Text (STT) Toddler Recognition
// ----------------------------------------------------
function initializeTeluguSpeechToText() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        const micBtn = document.getElementById('btn-mic');
        if (micBtn) micBtn.style.display = 'none';
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'te-IN';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
        state.sttActive = true;
        updateMicButtonState(true);
    };

    recognition.onresult = (e) => {
        const spokenText = e.results[0][0].transcript.trim();
        submitAnswer(spokenText, true);
    };

    recognition.onerror = (e) => {
        console.error("Speech recognition error:", e.error);
        updateMicButtonState(false);
        state.sttActive = false;
    };

    recognition.onend = () => {
        state.sttActive = false;
        updateMicButtonState(false);
    };

    const micBtn = document.getElementById('btn-mic');
    if (micBtn) {
        micBtn.addEventListener('click', toggleSTTRecognition);
    }

    const kbToggle = document.getElementById('btn-keyboard-toggle');
    if (kbToggle) {
        kbToggle.addEventListener('click', () => {
            const kb = document.getElementById('virtual-keyboard');
            if (kb) kb.classList.toggle('hidden-element');
        });
    }
}

function toggleSTTRecognition() {
    if (!recognition) return;
    getAudioContext();

    if (state.sttActive) {
        recognition.stop();
    } else {
        if (synth) synth.cancel();
        try {
            recognition.start();
        } catch (e) {
            console.error("Failed to start speech recognition:", e);
        }
    }
}

function updateMicButtonState(active) {
    const btn = document.getElementById('btn-mic');
    if (btn) {
        if (active) {
            btn.classList.add('recording-pulse');
            btn.innerHTML = '🎙️ వింటున్నాను... (Listening...)';
        } else {
            btn.classList.remove('recording-pulse');
            btn.innerHTML = '🎙️ మాట్లాడండి (Speak)';
        }
    }
}

function stopSTT() {
    state.sttActive = false;
    updateMicButtonState(false);
    if (recognition) {
        try {
            recognition.stop();
        } catch (e) {}
    }
}

if (typeof speechSynthesis !== 'undefined' && speechSynthesis.onvoiceschanged !== undefined) {
    speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}
