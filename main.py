from flask import Flask, render_template, request, jsonify
import os
import tempfile
import whisper
import re
from datetime import datetime

app = Flask(__name__)

# Initialize Whisper model
model = whisper.load_model("small")

# Bond type mappings with common transcription errors
BOND_MAPPINGS = {
    # France
    'FRANCE': 'OAT', 'OAT': 'OAT', 'OATS': 'OAT',
    # Italy
    'ITALY': 'BTP', 'BTP': 'BTP', 'BTPS': 'BTP', 'BEEPS': 'BTP',
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
    'FINLAND': 'RFGB', 'FINNY': 'RFGB', 'RFGB': 'RFGB'
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
    
    try:
        # Save the audio file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            temp_audio_path = temp_audio.name
            audio_file.save(temp_audio_path)
        
        # Transcribe the audio with English language specified
        result = model.transcribe(temp_audio_path, language="en")
        transcription = result['text']
        print("Transcription:", transcription)
        
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
    
    print("Attempting to match:", text)
    
    # Most flexible switch pattern with debug prints and transcription error handling
    pattern_switch = (
        r'I CAN (BUY|SELL)\s+([A-Z]+)\s+(?:OF\s+)?([A-Z]+)\s+(\d{2})'
        r'\s+AGAINST\s+(?:THE\s+)?([A-Z]+)\s+(?:OF\s+)?([A-Z]+)\s+(\d{2})'
        r'(?:,?\s+(?:I\s+)?(PICK|PEAK|PIC|GIVE)\s+(\d+))?'
        r'(?:\s+IN\s+(\d+)\s+MILLION)?'
    )
    match_switch = re.search(pattern_switch, text)
    if match_switch:
        print("Switch pattern matched!")
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
        
        # Format the switch quote
        base = f"I CAN {action} {bond1} {month1_num}/{year1} VS {bond2} {month2_num}/{year2}"
        if price_type and price:
            base += f" {price_type} {price}"
        if size:
            base += f" IN {size}M"
        
        print("Formatted output:", base)
        
        # Check if both bond types are valid
        if bond1 not in VALID_BONDS or bond2 not in VALID_BONDS:
            return "No valid bond quote found"
        
        return base
    else:
        print("Switch pattern did not match")
    
    # Pattern 6: Simple format without I'm (e.g., "OAT May 55 12 offer 72 million")
    pattern6 = r'([A-Z]+)\s+([A-Z]+)\s+(\d{2})\s+(\d+)\s+OFFER\s+(\d+)\s+MILLION'
    match6 = re.search(pattern6, text)
    if match6:
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
            return "No valid bond quote found"
        
        # Format the quote exactly as required
        return f"{bond_type} {month_num}/{year} {price} OFFER IN {size}"
    
    # Pattern 5: New simple format (e.g., "OAT May 55, I'm 7 offer in 12 million")
    pattern5 = r'([A-Z]+)\s+([A-Z]+)\s+(\d{2}),?\s+(?:I\'M|I AM)\s+(\d+)\s+OFFER\s+IN\s+(\d+)\s+MILLION'
    match5 = re.search(pattern5, text)
    if match5:
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
            return "No valid bond quote found"
        
        # Format the quote exactly as required
        return f"{bond_type} {month_num}/{year} {price} OFFER IN {size}"
    
    # Pattern 4: New format with bond first (e.g., "BTP September 17, 12 offer in 40 million")
    pattern4 = r'([A-Z]+)\s+([A-Z]+)\s+(\d{2}),?\s+(\d+)\s+OFFER\s+IN\s+(\d+)\s+MILLION'
    match4 = re.search(pattern4, text)
    if match4:
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
            return "No valid bond quote found"
        
        # Remove any decimal point from price
        price = price.split('.')[0]
        
        # Format the quote exactly as required
        return f"{bond_type} {month_num}/{year} {price} OFFER IN {size}"
    
    # Pattern 3: New format with price (e.g., "I can sell 30 million of bond September 72 at 79")
    pattern3 = r'I CAN (BUY|SELL)\s+(\d+)\s*(?:MILLION|M)\s*(?:OF)?\s*([A-Z]+)\s*([A-Z]+)\s*(\d{2})\s*(?:AT|IN)\s*(\d+\.?\d*)'
    match3 = re.search(pattern3, text)
    if match3:
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
            return "No valid bond quote found"
        
        # Determine if it's an offer or bid
        quote_type = "OFFER" if action == "SELL" else "BID"
        
        # Remove any decimal point from price
        price = price.split('.')[0]
        
        # Format the quote exactly as required
        return f"{bond_type} {month_num}/{year} {price} {quote_type} IN {size}"
    
    # Pattern 2: Original format without price (e.g., "I can buy 72 million of bund October 71")
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
        
        # Check if bond type is valid
        if bond_type not in VALID_BONDS:
            return "No valid bond quote found"
        
        # Format the quote exactly as required
        return f"CAN {action} {size} {bond_type} {month_num}/{year}"
    
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
        
        # Check if bond type is valid
        if bond_type not in VALID_BONDS:
            return "No valid bond quote found"
        
        # Format the quote exactly as required
        return f"CAN {action} {size} {bond_type} {month_num}/{year}"
    
    return "No valid bond quote found"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port) 