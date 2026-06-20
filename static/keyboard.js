class TeluguKeyboard {
    constructor(containerId, inputId, onEnterCallback) {
        this.container = document.getElementById(containerId);
        this.inputField = document.getElementById(inputId);
        this.onEnter = onEnterCallback;
        
        this.currentGroup = 'vowels'; // default tab
        
        this.keysData = {
            vowels: [
                'అ', 'ఆ', 'ఇ', 'ఈ', 'ఉ', 'ఊ', 'ఋ', 'ఎ', 'ఏ', 'ఐ', 'ఒ', 'ఓ', 'ఔ', 'అం', 'అః'
            ],
            consonants: [
                'క', 'ఖ', 'గ', 'ఘ', 'చ', 'ఛ', 'జ', 'ఝ', 'ట', 'ఠ', 'డ', 'ఢ', 'ణ', 
                'త', 'థ', 'ద', 'ధ', 'న', 'ప', 'ఫ', 'బ', 'భ', 'మ', 'య', 'ర', 'ల', 
                'వ', 'శ', 'ష', 'స', 'హ', 'ళ', 'క్ష', 'ఱ'
            ],
            signs: [
                '్', 'ా', 'ి', 'ీ', 'ు', 'ూ', 'ృ', 'ె', 'ే', 'ై', 'ొ', 'ో', 'ౌ', 'ం', 'ః'
            ]
        };

        this.init();
    }

    init() {
        // Find tabs and hook click listeners
        const tabs = document.querySelectorAll('.keyboard-tabs .tab-btn');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                // Remove active class from all tabs
                tabs.forEach(t => t.classList.remove('active'));
                
                // Add active to clicked
                e.target.classList.add('active');
                
                // Change group
                this.currentGroup = e.target.getAttribute('data-group') || 'vowels';
                this.render();
            });
        });

        // Add visual tabs for 'signs' if they don't exist in HTML structure, or let's create it dynamically
        const tabsContainer = document.querySelector('.keyboard-tabs');
        if (tabsContainer && !tabsContainer.querySelector('[data-group="signs"]')) {
            const signsTab = document.createElement('button');
            signsTab.className = 'tab-btn';
            signsTab.setAttribute('data-group', 'signs');
            signsTab.textContent = 'గుణింతాలు (Signs)';
            signsTab.addEventListener('click', (e) => {
                tabs.forEach(t => t.classList.remove('active'));
                signsTab.classList.add('active');
                this.currentGroup = 'signs';
                this.render();
            });
            tabsContainer.appendChild(signsTab);
        }

        // Render keyboard
        this.render();

        // Bind utility buttons
        const clearBtn = document.getElementById('clear-keyboard-input');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.inputField.value = '';
            });
        }

        const submitBtn = document.getElementById('submit-keyboard-input');
        if (submitBtn) {
            submitBtn.addEventListener('click', () => {
                if (this.onEnter) {
                    this.onEnter(this.inputField.value);
                }
            });
        }
    }

    render() {
        this.container.innerHTML = '';
        const keys = this.keysData[this.currentGroup] || [];
        
        keys.forEach(key => {
            const button = document.createElement('button');
            button.className = 'key-btn';
            button.textContent = key;
            button.addEventListener('click', () => {
                this.inputField.value += key;
                this.inputField.focus();
            });
            this.container.appendChild(button);
        });

        // Add Backspace, Space, and Enter action keys at the bottom of keyboard
        const backspaceBtn = document.createElement('button');
        backspaceBtn.className = 'key-btn action-key';
        backspaceBtn.textContent = '⬅️ Back';
        backspaceBtn.addEventListener('click', () => {
            this.deleteLastGrapheme();
        });
        
        const spaceBtn = document.createElement('button');
        spaceBtn.className = 'key-btn action-key';
        spaceBtn.textContent = 'Space ⎵';
        spaceBtn.addEventListener('click', () => {
            this.inputField.value += ' ';
        });
        
        this.container.appendChild(backspaceBtn);
        this.container.appendChild(spaceBtn);
    }

    deleteLastGrapheme() {
        const val = this.inputField.value;
        if (!val) return;

        // In Telugu, characters can consist of multiple code points (consonant + virama + consonant + vowel sign).
        // Standard slice(0, -1) might only remove the vowel sign or the virama, which is actually what we want!
        // (Deleting step by step allows the child to correct typing errors precisely).
        // So we can safely use slice(0, -1).
        this.inputField.value = val.slice(0, -1);
    }

    setValue(value) {
        this.inputField.value = value;
    }

    getValue() {
        return this.inputField.value;
    }

    clear() {
        this.inputField.value = '';
    }
}

// Export class to window context
window.TeluguKeyboard = TeluguKeyboard;
