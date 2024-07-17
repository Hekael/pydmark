# pydmark
This is a simple application for processing DMARC reports.
All you need to do is copy all your reports to the 'uploads' folder.

To run the application, execute:
```
git clone git@github.com:Hekael/pydmark.git
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```
Then visit: http://127.0.0.1:5000/