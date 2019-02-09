import csv
import os
import urllib.request
import qrcode
import pdfkit
import datetime

from flask import redirect, render_template, request, session
from functools import wraps
from fpdf import FPDF
from cs50 import SQL

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///festival.db")

ks = "" # kaartsoort


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        #for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
        #                 ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
        #    s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code

def apology_payment(message):

    return render_template("apology_payment.html", bottom=message)


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Reject symbol if it starts with caret
    if symbol.startswith("^"):
        return None

    # Reject symbol if it contains comma
    if "," in symbol:
        return None

    # Query Alpha Vantage for quote
    # https://www.alphavantage.co/documentation/
    try:

        # GET CSV
        url = f"https://www.alphavantage.co/query?apikey={os.getenv('API_KEY')}&datatype=csv&function=TIME_SERIES_INTRADAY&interval=1min&symbol={symbol}"
        webpage = urllib.request.urlopen(url)

        # Parse CSV
        datareader = csv.reader(webpage.read().decode("utf-8").splitlines())

        # Ignore first row
        next(datareader)

        # Parse second row
        row = next(datareader)

        # Ensure stock exists
        try:
            price = float(row[4])
        except:
            return None

        # Return stock's name (as a str), price (as a float), and (uppercased) symbol (as a str)
        return {
            "price": price,
            "symbol": symbol.upper()
        }

    except:
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

def create_ticket(klantID, soort, t, klantnaam_volledig):

    global ks

    ks = soort

    ''' Registering ticket in Database '''

    result = db.execute("INSERT INTO aangemaakte_tickets (ticketsoort, klantID , nummer , gescand) VALUES(:ticketsoort, :klantID , :nummer, :gescand)",
        ticketsoort=soort, klantID=klantID , nummer = "0", gescand = "False")

    if not result:
        return apology("Database Error1", 406)

    tempstr1 = '00'+str(t+1)  # t+1  om bij het nummer 001 te beginnen (i.p.v. 000) ; t = teller van tickets zelfde soort
    tempstr1 = tempstr1[-3:]

    tempstr2 = str(datetime.datetime.now().time())
    tempstr2 = tempstr2[-6:]    # laatste 6 cijfers van de tijd (in picoseconden of zo...)

    nummer = str(datetime.datetime.now().date()) + "|" + tempstr2 + "|" + str(klantID) + "|" + str(soort) + "|" + tempstr1

    db.execute("UPDATE aangemaakte_tickets SET nummer= :nummer WHERE t_id= (SELECT MAX(t_id) FROM aangemaakte_tickets)" , nummer = nummer)

    #print("** "+ nummer)

    ''' Creating and saving the QR - code: '''

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=12, border=4, )
    #qr.add_data('klantID: '+str(klantID)+' soort: '+str(soort))
    qr.add_data('http://ide50-alexicoo.cs50.io:8080/scantest?ticketnr=12')
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    #filename_QR = "QR-"+ nummer +".png"
    filename_QR = "QR-temp.png"

    img.save(filename_QR)

    # Create PDF
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font('Times', '', 12)
    for i in range(1, 3):
        pdf.cell(0, 10, '' , 0, 1)
    pdf.cell(0, 10, 'Dit is uw ticket dat toegang geeft tot het KuylKamp Familiefestival' , 0, 1)
    pdf.cell(0, 10, 'Neem dit ticket mee en laat het scannen bij de info-stand' , 0, 1)
    pdf.cell(0, 10, 'Ticketnummer : '+nummer , 0, 1)
    pdf.cell(0, 10, 'Op naam van : ' + klantnaam_volledig , 0, 1)

    pdf_filename = nummer + ".pdf"
    pdf.output( "PDF/" + pdf_filename, 'F')

    return ("PDF/" + pdf_filename)

class PDF(FPDF):
    def header(self):

        global ks

        # Logo
        self.image('img/LOGO.jpg', 10, 8, 33)
        self.image('QR-temp.png', 170, 8, 33)
        # Arial bold 15
        self.set_font('Arial', 'B', 15)
        # Move to the right
        self.cell(50)
        # Title
        self.cell(100, 10, 'KuylKamp Familiefestival - ticket', 1, 0, 'C')
        # Line break
        self.ln(20)
        # Move to the right
        self.cell(50)
        # print kaartsoort
        self.cell(100, 10, ks, 1, 0, 'C')

    # Page footer
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, 'Pagina ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')
