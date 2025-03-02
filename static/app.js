let datasets = [];
let activeDataset = null;
let darkMode = false;

// DOM Elements
const fileInput = document.getElementById('fileInput');
const queryForm = document.getElementById('queryForm');
const queryInput = document.getElementById('queryInput');
const chatMessages = document.getElementById('chatMessages');
const darkModeToggle = document.getElementById('darkModeToggle');

// Event Listeners
fileInput.addEventListener('change', handleFileUpload);
darkModeToggle.addEventListener('click', toggleDarkMode);
queryForm.addEventListener('submit', handleQuery);

// File Upload Handler
function handleFileUpload(event) {
    const files = event.target.files;
    if (!files.length) return;

    const formData = new FormData();
    for (let file of files) {
        formData.append("file", file);
        console.log
    }
    console.log("Uploading file:", files[0].name); // Debugging log

    // Show loading animation
    document.getElementById("loadingAnimation").style.display = "flex";

    fetch("http://127.0.0.1:5000/upload", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("loadingAnimation").style.display = "none"; // Hide loader
        
        if (data.success) {
            activeDataset = data.message;
            addMessage("assistant", `Successfully uploaded ${data.message}. You can now ask questions about this dataset.`);
        } else {
            addMessage("assistant", "Error uploading file. Please try again.");
        }
    })
    .catch(error => {
        document.getElementById("loadingAnimation").style.display = "none";
        addMessage("assistant", "Server error. Please check your backend.");
        console.error("Upload Error:", error);
    });

    event.target.value = "";
}


// Toggle Dark Mode
function toggleDarkMode() {
    darkMode = !darkMode;
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
}

// Handle Query
    function handleQuery(event) {
        event.preventDefault();
        if (!activeDataset) {
            addMessage('assistant', 'Hold up, data detective! 🕵️‍♂️ I need a dataset before I can work my SQL magic. ');
            return;
        }

        const query = queryInput.value.trim();
        if (!query) return;

        addMessage('user', query);

        fetch('http://127.0.0.1:5000/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        })
        .then(response => response.json())
        .then(data => {
            if (data.results && !data.results.error) {
                addMessage('assistant', data.sql_query, true); // SQL query in a code box
                addMessage('assistant', formatQueryResult(data.results));
                addMessage("assistant", `<strong>Result:</strong> ${data.results.data}`);

            } else {
                addMessage('assistant', data.sql_query, true); // SQL query in a code box
                addMessage('assistant', `<strong>Error:</strong> ${data.results.error || "Unknown error occurred."}`);
            }    
        })
        .catch(error => {
            addMessage('assistant', 'Server error while processing query.');
            console.error('Query Error:', error);
        });

        queryInput.value = '';
    }

// Function to format query results into readable HTML
function formatQueryResult(rawResult) {
    try {
        if (typeof rawResult === "string") {
            rawResult = JSON.parse(rawResult);
        }

        if (!Array.isArray(rawResult) || rawResult.length === 0) {
            return "";
        }

        return rawResult.map(row => {
            return Object.entries(row)
                .map(([key, value]) => `<strong>${key.replace(/_/g, " ")}:</strong> ${value}`)
                .join("<br>");
        }).join("<br><br>");
    } catch (error) {
        console.error("Error formatting result:", error);
        return "<strong>Result:</strong> Invalid result format.";
    }
}

// Add Message to Chat
function addMessage(type, content, isSQL = false) {
    const welcomeMessage = document.getElementById('welcomeMessage');

    // Hide the welcome message on the first message sent
    if (welcomeMessage) {
        welcomeMessage.style.display = 'none';
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;

    if (isSQL) {
        messageDiv.innerHTML = `
            <div class="sql-box">
                <pre><code>${content}</code></pre>
                <button class="copy-btn" onclick="copyToClipboard(this)">📋 Copy</button>
            </div>`;
    } else {
        messageDiv.innerHTML = `
            <p>${content}</p>
            <div class="timestamp">${new Date().toLocaleTimeString()}</div>
        `;
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Copy SQL query to clipboard
function copyToClipboard(button) {
    const codeBlock = button.previousElementSibling.innerText;
    navigator.clipboard.writeText(codeBlock).then(() => {
        button.innerText = "✅ Copied!";
        setTimeout(() => {
            button.innerText = "📋 Copy";
        }, 2000);
    }).catch(err => {
        console.error("Copy failed:", err);
    });
}



// Initialize dark mode based on system preference
if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    toggleDarkMode();
}
