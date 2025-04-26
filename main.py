from flask import Flask, render_template, request, jsonify
import os
import tempfile
import whisper
import re
from datetime import datetime

app = Flask(__name__)

# Initialize Whisper model
model = whisper.load_model("base")

# Bond type mappings with common transcription errors
BOND_MAPPINGS = {
    # France
    'FRANCE': 'OAT', 'OAT': 'OAT', 'OATS': 'OAT',
    # Italy
    'ITALY': 'BTP', 'BTP': 'BTP', 'BTPS': 'BTP', 'BEEPS': 'BTP',
    # Germany - Added more phonetic variations for BUND/DBR
    'GERMANY': 'DBR', 'BUND': 'DBR', 'DBR': 'DBR', 'WOOD': 'DBR', 'BOND': 'DBR',
    'BOON': 'DBR', 'BOOND': 'DBR', 'BUN': 'DBR', 'BUNT': 'DBR', 'BUNN': 'DBR',
    'BUNDT': 'DBR', 'BUNDE': 'DBR', 'BUNDA': 'DBR', 'BUNDER': 'DBR',
    # Netherlands
    'HOLLAND': 'NETHER', 'NETHER': 'NETHER', 'GUILDER': 'NETHER', 'NETHERLANDS': 'NETHER',
    # Austria
    'AUSTRIA': 'RAGB', 'RAGB': 'RAGB', 'RAG': 'RAGB',
    # Belgium
    'BELGIUM': 'BGB', 'BGB': 'BGB', 'BEEGEEBEE': 'BGB',
    # Portugal
    'PORTUGAL': 'PGB', 'PGB': 'PGB', 'PEEGEEBEE': 'PGB',
    # Spain
    'SPAIN': 'SPGB', 'SPGB': 'SPGB', 'SPEEGEEBEE': 'SPGB',
    # Finland
    'FINLAND': 'RFGB', 'FINNY': 'RFGB', 'RFGB': 'RFGB', 'RIFGB': 'RFGB'
}

@app.route('/')
def index():
    return render_template('front_end.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'file' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['file']
    temp_audio_path = None
    
    try:
        # Save the audio file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            temp_audio_path = temp_audio.name
            audio_file.save(temp_audio_path)
        
        # Transcribe the audio with English language specified
        result = model.transcribe(temp_audio_path, language="en")
        transcription = result['text']
        
        # Parse the quote
        quote = parse_quote(transcription)
        
        return jsonify({
            'transcription': transcription,
            'quote': quote
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up the temporary file
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.unlink(temp_audio_path)
            except:
                pass  # Ignore cleanup errors

def parse_quote(text):
    # Convert to uppercase for standardization
    text = text.upper()
    
    # Pattern 1: Bond and maturity first, then action and size
    pattern1 = r'([A-Z]+)\s+([A-Z]+)\s+(\d{2}),?\s+I CAN (BUY|SELL)\s+(\d+)\s*(?:MILLION|M)'
    match1 = re.search(pattern1, text)
    if match1:
        bond_type, month, year, action, size = match1.groups()
        
        # Convert size to standard format
        size = f"{size}M"
        
        # Convert bond type to standard format
        bond_type = BOND_MAPPINGS.get(bond_type, bond_type)
        
        # Convert month to number
        month_map = {
            'JANUARY': '01', 'FEBRUARY': '02', 'MARCH': '03', 'APRIL': '04',
            'MAY': '05', 'JUNE': '06', 'JULY': '07', 'AUGUST': '08',
            'SEPTEMBER': '09', 'OCTOBER': '10', 'NOVEMBER': '11', 'DECEMBER': '12'
        }
        month_num = month_map.get(month, month)
        
        # Format the quote exactly as required
        return f"CAN {action} {size} {bond_type} {month_num}/{year}"
    
    # Pattern 2: Original format (action first)
    pattern2 = r'I CAN (BUY|SELL)\s+(\d+)\s*(?:MILLION|M)\s*(?:OF)?\s*([A-Z]+)\s*([A-Z]+)\s*(\d{2})'
    match2 = re.search(pattern2, text)
    if match2:
        action, size, bond_type, month, year = match2.groups()
        
        # Convert size to standard format
        size = f"{size}M"
        
        # Convert bond type to standard format
        bond_type = BOND_MAPPINGS.get(bond_type, bond_type)
        
        # Convert month to number
        month_map = {
            'JANUARY': '01', 'FEBRUARY': '02', 'MARCH': '03', 'APRIL': '04',
            'MAY': '05', 'JUNE': '06', 'JULY': '07', 'AUGUST': '08',
            'SEPTEMBER': '09', 'OCTOBER': '10', 'NOVEMBER': '11', 'DECEMBER': '12'
        }
        month_num = month_map.get(month, month)
        
        # Format the quote exactly as required
        return f"CAN {action} {size} {bond_type} {month_num}/{year}"
    
    return "No valid bond quote found"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port) 