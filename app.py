
import os
import re
import requests
import openai
import fitz  
from flask import Flask, request, jsonify, render_template
from fuzzywuzzy import fuzz
from langid import classify
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import unicodedata
import fitz  



app = Flask(__name__)



GOOGLE_API_KEY = 'AIzaSyCYh-XF6MjQ_pxNUYYBbpTJbTDiiyLkdv8'
openai.api_key = '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'
    
PDF_FILE_PATH = 'event.pdf'

EMAIL_SENDER = 'hind.althabi@gmail.com'
EMAIL_PASSWORD = 'wemg dvqm cgty achl'


import fitz


doc = fitz.open(PDF_FILE_PATH)  





@app.route('/')
def home():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    user_request = request.json.get('request')

    
    prompt = f"""
    You are a tour guide expert. Provide the best locations based on the user request.
    For each location, return the name, address, and city, separated by a pipe (|) for each location.
    Here is the user request: "{user_request}".
    """

    try:
        
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[{"role": "user", "content": prompt}]
        )
    except Exception as e:
        print(f"OpenAI Error: {str(e)}")
        return jsonify({"error": f"OpenAI request failed: {str(e)}"}), 500

    places = response['choices'][0]['message']['content'].strip().split('\n')
    place_data = []

    for place in places:
        parts = place.split('|')
        if len(parts) == 3:
            name, address, city = parts
            place_data.append({
                'name': name.strip(),
                'address': address.strip(),
                'city': city.strip()
            })

    if not place_data:
        return jsonify({"error": "No valid places found from OpenAI response."}), 400

   
    google_places_results = []
    for place in place_data:
        search_query = f"{place['name']} in {place['city']}"
        google_response = requests.get(
            f"https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input={search_query}&inputtype=textquery&fields=name,formatted_address,place_id,rating&key={GOOGLE_API_KEY}"
        )

        if google_response.status_code == 200:
            google_result = google_response.json().get('candidates', [])
            if google_result:
                place_id = google_result[0].get('place_id', '')
                formatted_address = google_result[0].get('formatted_address', 'Address not found')
                rating = google_result[0].get('rating', 'No rating available')
                google_maps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"

                
                google_places_results.append({
                    'name': place['name'],
                    'address': formatted_address,
                    'rating': rating,
                    'google_maps_url': google_maps_url
                })
            else:
                google_places_results.append({
                    'name': place['name'],
                    'address': 'No address found',
                    'rating': 'No rating available',
                    'google_maps_url': ''
                })
        else:
            google_places_results.append({
                'name': place['name'],
                'address': 'No address found',
                'rating': 'No rating available',
                'google_maps_url': ''
            })

    return jsonify(google_places_results)


@app.route('/generate-tour', methods=['POST'])
def generate_tour():
    user_interest = request.json.get('interest')
    
   
    prompt = f"""
    Create a tour schedule based on the following interest: "{user_interest}". 
    Include the following details for each tour not Bold style:
    - "Location": (Name of the location) 
     (Tour details) 
    - "Time": (Start and end times of the tour) 

    Please provide the result in the user's language, either Arabic or English, based on the language of the user input. If the user input is in Arabic, respond in Arabic; otherwise, respond in English.
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[{"role": "user", "content": prompt}]
    )
    
    tour_schedule = response['choices'][0]['message']['content'].strip().split('\n')

    tour_data = []
    for item in tour_schedule:
        item = item.strip()
        if item: 
            if ':' in item:
                title, details = item.split(':', 1)
                tour_data.append({
                    'title': title.strip(),
                    'details': details.strip()
                })
            else:
                print(f"Skipping invalid item (missing ':'): {item}")
    
    return jsonify(tour_data)


@app.route('/generate-tour-from-pdf', methods=['POST'])
def generate_tour_from_pdf():
    try:
        user_interest = request.json.get('interest')

        if not user_interest:
            return jsonify({"error": "User interest is required."}), 400

  
        doc = fitz.open(PDF_FILE_PATH)  
        text = ""
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text += page.get_text("text")
        

        filtered_text = filter_text_by_interest(text, user_interest)

        if not filtered_text:
            return jsonify({"error": "No matching content found in the PDF."}), 404


        prompt = f"""
        Based on the content extracted from the PDF, and considering the user's interest in the term '{user_interest}', generate a list of events related to its interest, including event names, dates, and descriptions. Ensure the output reflects the user's interest and matches both English and Arabic content correctly.
        Please provide the result in the user's language, either Arabic or English, based on the language of the user input. If the user input is in Arabic, respond in Arabic; otherwise, respond in English.


        The extracted PDF content:
        {filtered_text}

        Please return the event data in the following format:
        - Event Name | Event Date | Event Description
        Make sure to:
        1. Only include events related to '{user_interest}' based on onlry the extracted PDF content.
        2. Filter out any unrelated events.
        3. Ensure language consistency with the user’s input.
        """
        


        response = openai.ChatCompletion.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[{"role": "user", "content": prompt}]
        )

    
        event_data = response['choices'][0]['message']['content'].strip().split('\n')

        events = []
        for event in event_data:
            event_parts = event.split('|')
            if len(event_parts) == 3:
                name = event_parts[0].strip()
                date = event_parts[1].strip()
                description = event_parts[2].strip()
                events.append({
                    'name': name,
                    'date': date,
                    'description': description
                })

        # Return the events as a properly structured JSON response
        if events:
            return jsonify({"events": events})
        else:
            return jsonify({"error": "No valid events found in the OpenAI response."}), 404

    except Exception as e:
      
        print(f"Error occurred: {str(e)}")
        return jsonify({"error": f"Error during PDF processing: {str(e)}"}), 500




def normalize_text(text):
    return re.sub(r'\s+', ' ', text.strip()).lower()

def remove_arabic_diacritics(text):
    nfkd_form = unicodedata.normalize('NFKD', text)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

def detect_language(text):
    lang, _ = classify(text)
    return lang


def filter_text_by_interest(text, interest):
    normalized_interest = normalize_text(interest)
    detected_language = detect_language(normalized_interest)
    
    if detected_language == 'ar':
        normalized_interest = remove_arabic_diacritics(normalized_interest)

    lines = text.split("\n")
    matched_lines = []

    for line in lines:
        normalized_line = normalize_text(line)
        if detected_language == 'ar':
            normalized_line = remove_arabic_diacritics(normalized_line)
        
        if fuzz.partial_ratio(normalized_interest, normalized_line) > 60:
            matched_lines.append(line.strip())

    print(f"Filtered text: {matched_lines[:10]}")
    return matched_lines



@app.route('/send-email', methods=['POST'])
def send_email():
    data = request.json
    user_email = data.get('email')
    tour_details = data.get('details')

    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = user_email
        msg['Subject'] = 'Tour Schedule'

        body = f"Here is your personalized tour schedule:\n\n{tour_details}"
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, user_email, msg.as_string())

        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'status': 'failure', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
