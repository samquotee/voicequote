let mediaRecorder;
let audioChunks = [];
let isRecording = false;
const recordButton = document.getElementById('recordButton');
const quoteText = document.querySelector('.quote-text');

// Function to copy text to clipboard
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        // Flash the quote box to indicate successful copy
        quoteText.style.transition = 'background-color 0.3s';
        quoteText.style.backgroundColor = '#333333';
        setTimeout(() => {
            quoteText.style.backgroundColor = 'transparent';
        }, 300);
    } catch (err) {
        console.error('Failed to copy text: ', err);
    }
}

recordButton.addEventListener('click', async () => {
    if (!isRecording) {
        // Start recording
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            
            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                const formData = new FormData();
                formData.append('file', audioBlob, 'recording.wav');
                
                quoteText.textContent = 'Processing...';
                
                try {
                    const response = await fetch('/transcribe', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    const quote = data.quote || data.transcription || '+QUOTE';
                    quoteText.textContent = quote;
                    
                    // Automatically copy the quote to clipboard
                    if (quote !== '+QUOTE') {
                        await copyToClipboard(quote);
                    }
                } catch (error) {
                    quoteText.textContent = 'Error: Try again';
                }
            };

            mediaRecorder.start();
            isRecording = true;
            recordButton.classList.add('recording');
            recordButton.textContent = 'STOP';
            quoteText.textContent = 'Recording...';
        } catch (error) {
            quoteText.textContent = 'Error: Microphone access denied';
        }
    } else {
        // Stop recording
        mediaRecorder.stop();
        isRecording = false;
        recordButton.classList.remove('recording');
        recordButton.textContent = 'QUOTE!';
    }
}); 