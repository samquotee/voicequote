from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import tempfile
import whisper
import re
from datetime import datetime
import csv
import uuid
import difflib

app = Flask(__name__)

# Initialize Whisper model
model = whisper.load_model("small")

# Bond type mappings with common transcription errors
BOND_MAPPINGS = {
    # France
    'FRANCE': 'OAT', 'OAT': 'OAT', 'OATS': 'OAT',
    # Italy
    'ITALY': 'BTP', 'BTP': 'BTP', 'BTPS': 'BTP', 'BEEPS': 'BTP', 'BDP': 'BTP',
    # Germany
    'GERMANY': 'DBR', 'BUND': 'DBR', 'DBR': 'DBR', 'WOOD': 'DBR', 'BOND': 'DBR',
    'BOON': 'DBR', 'BOOND': 'DBR', 'BUN': 'DBR', 'BUNT': 'DBR', 'BUNN': 'DBR',
    'BUNDT': 'DBR', 'BUNDE': 'DBR', 'BUNDA': 'DBR', 'BUNDER': 'DBR', 'BOUND': 'DBR',
    'BUIND': 'DBR', 'BUIN': 'DBR', 'BUINN': 'DBR', 'BUINT': 'DBR',
    # Netherlands
    'HOLLAND': 'NETH', 'NETHER': 'NETH', 'GUILDER': 'NETH', 'NETHERLANDS': 'NETH',
    # Austria
    'AUSTRIA': 'RAGB', 'RAGB': 'RAGB', 'RAG': 'RAGB',
    # Belgium
    'BELGIUM': 'BGB', 'BGB': 'BGB', 'BEEGEEBEE': 'BGB', 'BELG': 'BGB', 'BELGIAN': 'BGB',
    # Portugal
    'PORTUGAL': 'PGB', 'PGB': 'PGB', 'PEEGEEBEE': 'PGB',
    # Spain
    'SPAIN': 'SPGB', 'SPGB': 'SPGB', 'SPEEGEEBEE': 'SPGB',
    # Finland
    'FINLAND': 'RFGB', 'FINNY': 'RFGB', 'RFGB': 'RFGB',
    'OATM': 'OAT',
    '80': 'OAT', 'AM': 'OAT',
}

# Add this near the top, after BOND_MAPPINGS
VALID_BONDS = {'OAT', 'BTP', 'DBR', 'PGB', 'SPGB', 'NETH', 'RAGB', 'RFGB', 'BGB'}

@app.route('/')
def index():
    return render_template('front_end.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'file' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    audio_file = request.files['file']
    temp_audio_path = None
    unique_audio_filename = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{uuid.uuid4().hex[:8]}.wav"
    try:
        # Save the audio file temporarily with a unique name
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            temp_audio_path = temp_audio.name
            audio_file.save(temp_audio_path)
        # Transcribe the audio with English language specified
        result = model.transcribe(temp_audio_path, language="en")
        transcription = result['text']
        print("Transcription:", transcription)
        # Parse the quote and get pattern name
        quote, pattern_name = parse_quote(transcription, return_pattern=True)
        return jsonify({
            'transcription': transcription,
            'quote': quote,
            'audio_filename': unique_audio_filename,
            'pattern': pattern_name
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.unlink(temp_audio_path)
            except:
                pass

def parse_quote(text, return_pattern=False):
    # Convert to uppercase for standardization
    text = text.upper()
    print("parse_quote called with:", text)
    
    # Pattern: Bond name and maturity first
    print("Trying pattern_bond_first...")
    pattern_bond_first = r'([A-Z]+)\s+([A-Z]+|\d{1,2})/(\d{2}),?\s*(?:I CAN\s+)?(BUY|SELL|BID|OFFER)?\s*(\d+)M?(?:\s*(?:AT|IN)?\s*(\d+))?'
    match_bond_first = re.search(pattern_bond_first, text)
    if match_bond_first:
        print("pattern_bond_first matched!", match_bond_first.groups())
        bond_type, month, year, action, size, price = match_bond_first.groups()
        bond_token = bond_type
        if bond_type not in BOND_MAPPINGS and month in BOND_MAPPINGS:
            bond_token = month
            month = bond_type
        bond_type = BOND_MAPPINGS.get(bond_token, bond_token)
        if bond_type not in VALID_BONDS:
            return "No valid bond quote found", None
        month_map = {
            'JANUARY': '01', 'FEBRUARY': '02', 'MARCH': '03', 'APRIL': '04',
            'MAY': '05', 'JUNE': '06', 'JULY': '07', 'AUGUST': '08',
            'SEPTEMBER': '09', 'OCTOBER': '10', 'NOVEMBER': '11', 'DECEMBER': '12'
        }
        month_num = month_map.get(month, month.zfill(2))
        size = f"{size}M" if size else ''
        if action in ('BUY', 'BID'):
            quote_type = 'BID'
        elif action in ('SELL', 'OFFER'):
            quote_type = 'OFFER'
        else:
            quote_type = ''
        out = f"{bond_type} {month_num}/{year}"
        if price:
            out += f" {price}"
        if quote_type:
            out += f" {quote_type}"
        if size:
            out += f" IN {size}"
        if return_pattern:
            return out, "pattern_bond_first"
        return out
    else:
        print("pattern_bond_first did not match")

    # Pattern: Maturity first, then bond name
    print("Trying pattern_maturity_first...")
    pattern_maturity_first = r'([A-Z]+|\d{1,2})/(\d{2})\s+([A-Z]+)\s*(?:I CAN\s+)?(BUY|SELL|BID|OFFER)?\s*(\d+)M?(?:\s*(?:AT|IN)?\s*(\d+))?'
    match_maturity_first = re.search(pattern_maturity_first, text)
    if match_maturity_first:
        print("pattern_maturity_first matched!", match_maturity_first.groups())
        month, year, bond_type, action, size, price = match_maturity_first.groups()
        bond_token = bond_type
        if bond_type not in BOND_MAPPINGS and month in BOND_MAPPINGS:
            bond_token = month
            month = bond_type
        bond_type = BOND_MAPPINGS.get(bond_token, bond_token)
        if bond_type not in VALID_BONDS:
            return "No valid bond quote found", None
        month_map = {
            'JANUARY': '01', 'FEBRUARY': '02', 'MARCH': '03', 'APRIL': '04',
            'MAY': '05', 'JUNE': '06', 'JULY': '07', 'AUGUST': '08',
            'SEPTEMBER': '09', 'OCTOBER': '10', 'NOVEMBER': '11', 'DECEMBER': '12'
        }
        month_num = month_map.get(month, month.zfill(2))
        size = f"{size}M" if size else ''
        if action in ('BUY', 'BID'):
            quote_type = 'BID'
        elif action in ('SELL', 'OFFER'):
            quote_type = 'OFFER'
        else:
            quote_type = ''
        out = f"{bond_type} {month_num}/{year}"
        if price:
            out += f" {price}"
        if quote_type:
            out += f" {quote_type}"
        if size:
            out += f" IN {size}"
        if return_pattern:
            return out, "pattern_maturity_first"
        return out
    else:
        print("pattern_maturity_first did not match")
    
    # Most flexible switch pattern with debug prints and transcription error handling
    print("Trying switch pattern...")
    pattern_switch = (
        r'I CAN (BUY|SELL)\s+(?:A\s+)?([A-Z]+)\s+(?:THE\s+)?([A-Z]+)\s+(\d{2})'
        r'\s+AGAINST\s+(?:THE\s+)?([A-Z]+)\s+(?:THE\s+)?([A-Z]+)\s+(\d{2})'
        r'(?:,?\s+(?:I\s+)?(PICK|PEAK|PIC|GIVE)\s+(\d+)(?:\s+IN\s+(\d+)\s*MILLION)?)?'
    )
    match_switch = re.search(pattern_switch, text)
    if match_switch:
        print("Switch pattern matched!", match_switch.groups())
        action, bond1, month1, year1, bond2, month2, year2, price_type, price, size = match_switch.groups()
        print(f"Matched groups: {match_switch.groups()}")
        # Convert bond types to standard format
        bond1 = BOND_MAPPINGS.get(bond1, bond1)
        bond2 = BOND_MAPPINGS.get(bond2, bond2)
        # Convert month names to numbers
        month_map = {
            'JANUARY': '01', 'FEBRUARY': '02', 'MARCH': '03', 'APRIL': '04',
            'MAY': '05', 'JUNE': '06', 'JULY': '07', 'AUGUST': '08',
            'SEPTEMBER': '09', 'OCTOBER': '10', 'NOVEMBER': '11', 'DECEMBER': '12'
        }
        month1_num = month_map.get(month1, month1)
        month2_num = month_map.get(month2, month2)
        # Normalize price_type to PICK if it's PEAK or PIC
        if price_type in ('PEAK', 'PIC'):
            price_type = 'PICK'
        # If price_type, price, or size are missing, search the rest of the text
        if not (price_type and price and size):
            # Remove the matched part from text
            end_idx = match_switch.end()
            rest = text[end_idx:]
            extra = re.search(r'(PICK|PEAK|PIC|GIVE)\s+(\d+)(?:\s+IN\s+(\d+)\s*MILLION)?', rest)
            if extra:
                pt, p, s = extra.groups()
                if pt in ('PEAK', 'PIC'):
                    pt = 'PICK'
                price_type = price_type or pt
                price = price or p
                size = size or s
        # Format the switch quote
        base = f"I CAN {action} {bond1} {month1_num}/{year1} VS {bond2} {month2_num}/{year2}"
        if price_type and price:
            base += f" {price_type} {price}"
        if size:
            base += f" IN {size}M"
        print("Formatted output:", base)
        # Check if both bond types are valid
        if bond1 not in VALID_BONDS or bond2 not in VALID_BONDS:
            return "No valid bond quote found", None
        if return_pattern:
            return base, "switch"
        return base
    else:
        print("Switch pattern did not match")
    
    # Pattern 6: Simple format without I'm (e.g., "OAT May 55 12 offer 72 million")
    print("Trying pattern 6...")
    pattern6 = r'([A-Z]+)\s+([A-Z]+)\s+(\d{2})\s+(\d+)\s+OFFER\s+(\d+)\s+MILLION'
    match6 = re.search(pattern6, text)
    if match6:
        print("Pattern 6 matched!", match6.groups())
        bond_type, month, year, price, size = match6.groups()
        
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
        
        # Check if bond type is valid
        if bond_type not in VALID_BONDS:
            return "No valid bond quote found", None
        
        # Format the quote exactly as required
        if return_pattern:
            return f"{bond_type} {month_num}/{year} {price} OFFER IN {size}", "pattern6"
        return f"{bond_type} {month_num}/{year} {price} OFFER IN {size}"
    else:
        print("Pattern 6 did not match")
    
    # Pattern 5: New simple format (e.g., "OAT May 55, I'm 7 offer in 12 million")
    print("Trying pattern 5...")
    pattern5 = r'([A-Z]+)\s+([A-Z]+)\s+(\d{2}),?\s+(?:I\'M|I AM)\s+(\d+)\s+OFFER\s+IN\s+(\d+)\s+MILLION'
    match5 = re.search(pattern5, text)
    if match5:
        print("Pattern 5 matched!", match5.groups())
        bond_type, month, year, price, size = match5.groups()
        
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
        
        # Check if bond type is valid
        if bond_type not in VALID_BONDS:
            return "No valid bond quote found", None
        
        # Format the quote exactly as required
        if return_pattern:
            return f"{bond_type} {month_num}/{year} {price} OFFER IN {size}", "pattern5"
        return f"{bond_type} {month_num}/{year} {price} OFFER IN {size}"
    else:
        print("Pattern 5 did not match")
    
    # Pattern 4: New format with bond first (e.g., "BTP September 17, 12 offer in 40 million")
    print("Trying pattern 4...")
    pattern4 = r'([A-Z]+)\s+([A-Z]+)\s+(\d{2}),?\s+(\d+)\s+OFFER\s+IN\s+(\d+)\s+MILLION'
    match4 = re.search(pattern4, text)
    if match4:
        print("Pattern 4 matched!", match4.groups())
        bond_type, month, year, price, size = match4.groups()
        
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
        
        # Check if bond type is valid
        if bond_type not in VALID_BONDS:
            return "No valid bond quote found", None
        
        # Remove any decimal point from price
        price = price.split('.')[0]
        
        # Format the quote exactly as required
        if return_pattern:
            return f"{bond_type} {month_num}/{year} {price} OFFER IN {size}", "pattern4"
        return f"{bond_type} {month_num}/{year} {price} OFFER IN {size}"
    else:
        print("Pattern 4 did not match")
    
    # Pattern 3: New format with price (e.g., "I can sell 30 million of bond September 72 at 79")
    print("Trying pattern 3...")
    pattern3 = r'I CAN (BUY|SELL)\s+(\d+)\s*(?:MILLION|M)\s*(?:OF)?\s*([A-Z]+)\s*([A-Z]+)\s*(\d{2})\s*(?:AT|IN)\s*(\d+\.?\d*)'
    match3 = re.search(pattern3, text)
    if match3:
        print("Pattern 3 matched!", match3.groups())
        action, size, bond_type, month, year, price = match3.groups()
        
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
        
        # Check if bond type is valid
        if bond_type not in VALID_BONDS:
            return "No valid bond quote found", None
        
        # Determine if it's an offer or bid
        quote_type = "OFFER" if action == "SELL" else "BID"
        
        # Remove any decimal point from price
        price = price.split('.')[0]
        
        # Format the quote exactly as required
        if return_pattern:
            return f"{bond_type} {month_num}/{year} {price} {quote_type} IN {size}", "pattern3"
        return f"{bond_type} {month_num}/{year} {price} {quote_type} IN {size}"
    else:
        print("Pattern 3 did not match")
    
    # Pattern 2: Original format without price (e.g., "I can buy 72 million of bund October 71")
    print("Trying pattern 2...")
    pattern2 = r'I CAN (BUY|SELL)\s+(\d+)\s*(?:MILLION|M)\s*(?:OF)?\s*([A-Z]+)\s*([A-Z]+)\s*(\d{2})'
    match2 = re.search(pattern2, text)
    if match2:
        print("Pattern 2 matched!", match2.groups())
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
        
        # Check if bond type is valid
        if bond_type not in VALID_BONDS:
            return "No valid bond quote found", None
        
        # Format the quote exactly as required
        if return_pattern:
            return f"CAN {action} {size} {bond_type} {month_num}/{year}", "pattern2"
        return f"CAN {action} {size} {bond_type} {month_num}/{year}"
    else:
        print("Pattern 2 did not match")
    
    # Pattern 1: Bond and maturity first, then action and size
    print("Trying pattern 1...")
    pattern1 = r'([A-Z]+)\s+([A-Z]+)\s+(\d{2}),?\s+I CAN (BUY|SELL)\s+(\d+)\s*(?:MILLION|M)'
    match1 = re.search(pattern1, text)
    if match1:
        print("Pattern 1 matched!", match1.groups())
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
        
        # Check if bond type is valid
        if bond_type not in VALID_BONDS:
            return "No valid bond quote found", None
        
        # Format the quote exactly as required
        if return_pattern:
            return f"CAN {action} {size} {bond_type} {month_num}/{year}", "pattern1"
        return f"CAN {action} {size} {bond_type} {month_num}/{year}"
    else:
        print("Pattern 1 did not match")
    
    print("No pattern matched. Returning 'No valid bond quote found'.")
    return "No valid bond quote found", None

@app.route('/save_training_data', methods=['POST'])
def save_training_data():
    audio = request.files.get('audio')
    transcription = request.form.get('transcription')
    quote = request.form.get('quote')
    pattern = request.form.get('pattern')
    audio_filename = request.form.get('audio_filename')
    if not (audio and transcription and quote and pattern and audio_filename):
        return jsonify({'error': 'Missing data'}), 400
    audio_dir = 'training_audio'
    os.makedirs(audio_dir, exist_ok=True)
    audio_path = os.path.join(audio_dir, audio_filename)
    audio.save(audio_path)
    csv_path = 'training_data.csv'
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([audio_filename, transcription, quote, pattern])
    return jsonify({'status': 'ok'})

@app.route('/save_correction', methods=['POST'])
def save_correction():
    audio = request.files.get('audio')
    transcription = request.form.get('transcription')
    wrong_quote = request.form.get('wrong_quote')
    correct_quote = request.form.get('correct_quote')
    pattern = request.form.get('pattern')
    audio_filename = request.form.get('audio_filename')
    if not (audio and transcription and wrong_quote and correct_quote and pattern and audio_filename):
        return jsonify({'error': 'Missing data'}), 400
    audio_dir = 'correction_audio'
    os.makedirs(audio_dir, exist_ok=True)
    audio_path = os.path.join(audio_dir, audio_filename)
    audio.save(audio_path)
    csv_path = 'corrections.csv'
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([audio_filename, transcription, wrong_quote, correct_quote, pattern])
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port) 