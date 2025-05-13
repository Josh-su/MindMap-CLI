document.addEventListener('DOMContentLoaded', () => {
    const term = new Terminal({
        cursorBlink: true,
        fontFamily: 'Courier New, Courier, monospace', // Ensure consistent font
        fontSize: 14,
        theme: {
            background: '#1e1e1e', // Dark background for the terminal itself
            foreground: '#d4d4d4', // Light foreground text
            cursor: '#d4d4d4',     // Cursor color
            selectionBackground: '#555555', // Selection color
            black: '#000000',
            red: '#cd3131',
            green: '#0dbc79',
            yellow: '#e5e510',
            blue: '#2472c8',
            magenta: '#bc3fbc',
            cyan: '#11a8cd',
            white: '#e5e5e5',
            brightBlack: '#666666',
            brightRed: '#f14c4c',
            brightGreen: '#23d18b',
            brightYellow: '#f5f543',
            brightBlue: '#3b8eea',
            brightMagenta: '#d670d6',
            brightCyan: '#29b8db',
            brightWhite: '#e5e5e5'
        }
    });

    const fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);

    term.open(document.getElementById('terminal'));
    
    try {
        fitAddon.fit(); // Initial fit
    } catch (e) {
        console.error("Error on initial fit:", e);
    }
    term.focus();

    // --- WebSocket Connection ---
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Assuming your backend WebSocket server is running on the same host and port
    // and the endpoint is /ws. Adjust if necessary.
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`; 
    let socket;
    let currentLineBuffer = ""; // Buffer for the current line input

    function connectWebSocket() {
        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            term.writeln('\r\n\x1b[32mConnected to server.\x1b[0m');
            fitAddon.fit(); // Fit again on connect, in case of layout shifts
        };

        socket.onmessage = (event) => {
            term.write(event.data);
        };

        socket.onerror = (error) => {
            term.writeln(`\r\n\x1b[31mWebSocket Error: ${error.message || 'Could not connect. Ensure backend server is running.'}\x1b[0m`);
            console.error('WebSocket Error: ', error);
        };

        socket.onclose = (event) => {
            term.writeln(`\r\n\x1b[33mWebSocket Connection Closed (Code: ${event.code}, Reason: ${event.reason || 'N/A'}). Attempting to reconnect in 5s...\x1b[0m`);
            setTimeout(connectWebSocket, 5000); // Optional: attempt to reconnect
        };
    }

    term.onData((data) => {
        // data is the raw input from the terminal, e.g., a single character or control sequence
        if (socket && socket.readyState === WebSocket.OPEN) {
            if (data === '\r') { // User pressed Enter
                // For local echo, move to the next line in the terminal
                term.writeln(''); 
                // Send a newline character to the server, which Python's input() expects
                socket.send(currentLineBuffer + '\n');
                currentLineBuffer = ""; // Clear the buffer
            } else if (data.charCodeAt(0) === 127 || data.charCodeAt(0) === 8) { // Backspace (ASCII 127 or 8)
                // Handle backspace locally for visual feedback
                if (currentLineBuffer.length > 0) {
                    currentLineBuffer = currentLineBuffer.slice(0, -1); // Remove last char from buffer
                    term.write('\b \b');
                }
                // Do not send the backspace character itself to the server if we're managing the line buffer
            } else if (data.charCodeAt(0) >= 32 && data.charCodeAt(0) <= 126 || data.charCodeAt(0) >= 160) { // Printable characters
                term.write(data); // Echo printable characters locally
                currentLineBuffer += data; // Add to buffer
            } else {
                // For other control characters (like arrow keys, etc.), you might want to send them
                // or handle them specifically if your backend expects them.
                // For a simple line-based input, we might ignore them or send them if needed.
                // If they are part of multi-byte sequences (e.g. arrow keys), this simple check isn't enough.
                // For now, let's assume we only care about printable, enter, and backspace for line input.
                // If you need to send other control chars, uncomment the line below:
                // socket.send(data); 
            }
        }
    });

    window.addEventListener('resize', () => {
        try {
            fitAddon.fit();
        } catch (e) {
            console.error("Error on resize fit:", e);
        }
    });

    // Initial connection
    connectWebSocket();
});