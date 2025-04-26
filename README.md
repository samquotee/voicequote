# Voice Quote Transcription

A web application that transcribes voice recordings and extracts financial quotes from the transcription.

## Setup

1. Install Python 3.11 or later
2. Install FFmpeg (required for audio processing):
   - Windows: Download from https://ffmpeg.org/download.html and add to PATH
   - Mac: `brew install ffmpeg`
   - Linux: `sudo apt-get install ffmpeg`
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. Start the server:
   ```bash
   python main.py
   ```
2. Open your web browser and navigate to `http://localhost:5000`
3. Click the "Start Recording" button to begin recording your voice
4. Speak your financial quote (e.g., "The price is $123.45")
5. Click "Stop Recording" to process the audio
6. View the transcription and extracted quote

## Features

- Real-time voice recording
- Automatic transcription using OpenAI's Whisper model
- Quote extraction from transcriptions
- Clean, modern user interface
- Error handling and user feedback

## Note

The first time you run the application, it will download the Whisper model (approximately 1GB). This may take a few minutes depending on your internet connection. 

PYTHON_VERSION = 3.11.0
PORT = 10000 