let mediaRecorder;
let audioChunks = [];
let isRecording = false;
const recordButton = document.getElementById('recordButton');
const quoteText = document.querySelector('.quote-text');

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
                    quoteText.textContent = data.quote || data.transcription || '+QUOTE';
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