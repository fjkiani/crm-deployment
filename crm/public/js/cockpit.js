
class AICockpit {
    constructor() {
        this.isOpen = false;
        this.history = [];
        this.setupUI();
        this.bindEvents();
    }

    setupUI() {
        // Floating Action Button (FAB)
        this.fab = document.createElement('div');
        this.fab.id = 'nyx-fab';
        // HSL(262, 52%, 47%) is a deep purple (Nyx theme)
        this.fab.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"></path>
                <path d="M8.5 8.5v.01"></path>
                <path d="M16 16v.01"></path>
                <path d="M12 12v.01"></path>
            </svg>
        `;
        Object.assign(this.fab.style, {
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            width: '56px',
            height: '56px',
            borderRadius: '50%',
            backgroundColor: '#1a1a1a',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            zIndex: '9999',
            transition: 'transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275)'
        });

        // Chat Window
        this.window = document.createElement('div');
        this.window.id = 'nyx-window';
        Object.assign(this.window.style, {
            position: 'fixed',
            bottom: '90px',
            right: '20px',
            width: '400px',
            height: '600px',
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)',
            borderRadius: '16px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
            display: 'none', // Hidden by default
            flexDirection: 'column',
            zIndex: '9999',
            border: '1px solid rgba(0,0,0,0.1)',
            overflow: 'hidden',
            fontFamily: 'Inter, system-ui, sans-serif'
        });

        // Header
        const header = document.createElement('div');
        header.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-weight: 600; font-size: 16px;">Nyx Intelligence</span>
                <span style="font-size: 11px; background: #e0e7ff; color: #3730a3; padding: 2px 6px; border-radius: 4px;">MARS RULES</span>
            </div>
            <div id="nyx-close" style="cursor: pointer; opacity: 0.6;">✕</div>
        `;
        Object.assign(header.style, {
            padding: '16px',
            borderBottom: '1px solid rgba(0,0,0,0.05)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: '#fff'
        });

        // Messages Area
        this.messages = document.createElement('div');
        this.messages.id = 'nyx-messages';
        Object.assign(this.messages.style, {
            flex: '1',
            padding: '16px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            fontSize: '14px',
            lineHeight: '1.5'
        });

        // Input Area
        const inputArea = document.createElement('div');
        inputArea.innerHTML = `
            <input type="text" id="nyx-input" placeholder="Ask Nyx (e.g., 'Hunt for CIOs' or 'Audit Leads')..." style="
                width: 100%;
                padding: 12px;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                outline: none;
                font-family: inherit;
                transition: border-color 0.2s;
            ">
        `;
        Object.assign(inputArea.style, {
            padding: '16px',
            borderTop: '1px solid rgba(0,0,0,0.05)',
            background: '#f9fafb'
        });

        this.window.appendChild(header);
        this.window.appendChild(this.messages);
        this.window.appendChild(inputArea);

        document.body.appendChild(this.fab);
        document.body.appendChild(this.window);

        // Add Welcome Message
        this.addMessage("system", "Systems Online. Operating under Mars Rules. How can I assist you with the Hunt?");
    }

    bindEvents() {
        // Toggle Window
        this.fab.addEventListener('click', () => {
            this.isOpen = !this.isOpen;
            this.window.style.display = this.isOpen ? 'flex' : 'none';
            this.fab.style.transform = this.isOpen ? 'rotate(45deg)' : 'rotate(0deg)';
            if (this.isOpen) document.getElementById('nyx-input').focus();
        });

        // Close Button
        document.getElementById('nyx-close').addEventListener('click', () => {
            this.isOpen = false;
            this.window.style.display = 'none';
            this.fab.style.transform = 'rotate(0deg)';
        });

        // Send Message
        const input = document.getElementById('nyx-input');
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && input.value.trim()) {
                this.sendMessage(input.value.trim());
                input.value = '';
            }
        });
    }

    addMessage(role, text) {
        const msg = document.createElement('div');
        const isUser = role === 'user';

        Object.assign(msg.style, {
            alignSelf: isUser ? 'flex-end' : 'flex-start',
            maxWidth: '85%',
            padding: '10px 14px',
            borderRadius: '12px',
            fontSize: '14px',
            background: isUser ? '#1a1a1a' : '#fff',
            color: isUser ? '#fff' : '#1f2937',
            border: isUser ? 'none' : '1px solid #e5e7eb',
            boxShadow: isUser ? '0 2px 4px rgba(0,0,0,0.1)' : 'none'
        });

        // Simple Markdown parsing for bold and links
        // In a real app we'd use 'marked' or similar lib
        let formattedText = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');

        msg.innerHTML = formattedText;
        this.messages.appendChild(msg);
        this.messages.scrollTop = this.messages.scrollHeight;
    }

    async sendMessage(text) {
        this.addMessage('user', text);
        this.addMessage('system', '<span style="color: #6b7280; font-style: italic;">Thinking...</span>');

        const loadingMsg = this.messages.lastElementChild;

        try {
            // Call Frappe Proxy
            const response = await frappe.call({
                method: "crm.api.intelligence.ask_nyx",
                args: { message: text },
                freeze: false
            });

            // Remove loading
            this.messages.removeChild(loadingMsg);

            if (response.message) {
                this.addMessage('system', response.message);
            }
        } catch (e) {
            this.messages.removeChild(loadingMsg);
            this.addMessage('system', `❌ <strong>Error:</strong> ${e.message || 'Connection failed'}`);
            console.error(e);
        }
    }
}

// Initialize when ready
frappe.ready(() => {
    // Only inject if authenticated
    if (frappe.session.user !== 'Guest') {
        new AICockpit();
    }
});
