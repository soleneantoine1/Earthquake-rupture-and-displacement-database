from flask import Flask, render_template, request, redirect, url_for
import json

app = Flask(__name__)

# Home route that renders the form
@app.route('/')
def index():
    return render_template('form.html')

# Route that handles form submission
@app.route('/submit', methods=['POST'])
def submit():
    # Get the form data using request.form
    name = request.form['name']
    email = request.form['email']
    
    # Create a dictionary to store the form data
    form_data = {
        'name': name,
        'email': email
    }
    
    # Save the form data into a JSON file
    with open('form_data.json', 'a') as json_file:
        # Read the current content of the JSON file (if it exists)
        try:
            # Read the current JSON content if the file is not empty
            with open('form_data.json', 'r') as file:
                existing_data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            # If file doesn't exist or is empty, start with an empty list
            existing_data = []
        
        # Append new form data
        existing_data.append(form_data)
        
        # Write the updated data back to the file
        json.dump(existing_data, json_file, indent=4)

    # Redirect to a thank-you page or back to the form
    return render_template('thank_you.html', name=name)

if __name__ == '__main__':
    app.run() #debug=True)


